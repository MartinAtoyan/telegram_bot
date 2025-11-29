import json
from telegram.ext import ContextTypes
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove

from utils import user_to_vector, build_annoy_index
from config import (
    QUESTIONS,
    YEAR_LEVELS,
    MAJORS,
    PARTNER_MAJOR_PREF,
    PARTNER_YEAR_PREF,
    STUDY_LOCATION_PREF,
    STUDY_SOUND_PREF,
    STUDY_QUESTION_PREF,
    QUESTION_METHOD_PREF,
    PARTNER_YEAR_TO_YEAR
)

#DATA_FILE = abs_path_to_users.json
# BOT TOKEN = token_telegram_bot

def load_users():
    users = {}
    try:
        with open(DATA_FILE, "r") as f:
            data_list = json.load(f)
            for data in data_list:
                users[str(data["telegram_id"])] = data
    except FileNotFoundError:
        pass
    return users


def save_user(user_data):
    users = load_users()
    users[str(user_data["telegram_id"])] = user_data

    with open(DATA_FILE, "w") as f:
        json.dump(list(users.values()), f, indent=2)


def delete_user(telegram_id):
    users = load_users()
    uid = str(telegram_id)

    if uid in users:
        del users[uid]
        with open(DATA_FILE, "w") as f:
            json.dump(list(users.values()), f, indent=2)
        return True

    return False


user_sessions = {}
annoy_index, id_map, reverse_map = build_annoy_index(load_users())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(update.effective_user.id)

    if uid in users:
        menu_keyboard = ReplyKeyboardMarkup([["/match"], ["/delete"]], resize_keyboard=True)
        await update.message.reply_text(
            f"Hey {users[uid]['first_name']}! Welcome back!\n\n"
            f"Ready to find your study buddy? Just use /match!\n"
            f"Want to start over? Use /delete to remove your info.",
            reply_markup=menu_keyboard
        )
        return

    user_sessions[uid] = {"answers": [], "step": 0}
    await update.message.reply_text(
        "Let's find you the perfect study partner!\n\n"
        "I'll ask you a few quick questions to get started.\n\n" + QUESTIONS[0],
        reply_markup=ReplyKeyboardRemove()
    )


async def send_options(update, options, question):
    keyboard = ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(question, reply_markup=keyboard)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid not in user_sessions:
        await update.message.reply_text(
            "Hmm, it looks like we haven't started yet!\n"
            "Send /start to begin finding your study partner!"
        )
        return

    session = user_sessions[uid]
    response = update.message.text

    session["answers"].append(response)
    session["step"] += 1

    if session["step"] == 5:
        await send_options(update, YEAR_LEVELS, QUESTIONS[5])
    elif session["step"] == 6:
        await send_options(update, MAJORS, QUESTIONS[6])
    elif session["step"] == 7:
        await send_options(update, PARTNER_MAJOR_PREF, QUESTIONS[7])
    elif session["step"] == 8:
        await send_options(update, PARTNER_YEAR_PREF, QUESTIONS[8])
    elif session["step"] == 9:
        await send_options(update, STUDY_LOCATION_PREF, QUESTIONS[9])
    elif session["step"] == 10:
        await send_options(update, STUDY_SOUND_PREF, QUESTIONS[10])
    elif session["step"] == 11:
        await send_options(update, STUDY_QUESTION_PREF, QUESTIONS[11])
    elif session["step"] == 12:
        if "asking questions" in session["answers"][11].lower():
            await send_options(update, QUESTION_METHOD_PREF, QUESTIONS[12])
        else:
            session["answers"].append("N/A")
            session["step"] += 1

    if session["step"] >= len(QUESTIONS):
        d = session["answers"]

        user_record = {
            "telegram_id": uid,
            "first_name": d[0],
            "family_name": d[1],
            "age": d[2],
            "email": d[3],
            "kakaotalk": d[4],
            "year_level": d[5],
            "major": d[6],
            "partner_pref_major": d[7],
            "partner_pref_year": d[8],
            "meet_pref": d[9],
            "sound_pref": d[10],
            "question_pref": d[11],
            "question_method": d[12] if len(d) > 12 else "N/A"}

        save_user(user_record)
        menu_keyboard = ReplyKeyboardMarkup([["/match"], ["/delete"]], resize_keyboard=True)
        await update.message.reply_text(
            f"Awesome, {d[0]}!\n\n"
            f"Send /match to find study partner.\n\n",
            reply_markup=menu_keyboard
        )
        del user_sessions[uid]
        return

    if session["step"] < 5:
        await update.message.reply_text(QUESTIONS[session["step"]])

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(update.effective_user.id)

    if uid not in users:
        await update.message.reply_text("You need to register first using /start")
        return

    you = users[uid]

    if "seen_matches" not in you:
        you["seen_matches"] = []

    your_vec = user_to_vector(you)

    nn_ids, distances = annoy_index.get_nns_by_vector(
        your_vec,
        50,
        include_distances=True
    )

    best_mutual_id = None
    best_mutual_dist = float("inf")

    best_one_sided_id = None
    best_one_sided_dist = float("inf")

    index = 0
    while index < len(nn_ids):
        annoy_i = nn_ids[index]
        dist = distances[index]
        index = index + 1

        cand_id = id_map[annoy_i]

        if cand_id == uid:
            continue

        if cand_id in you["seen_matches"]:
            continue

        cand = users[cand_id]

        you_like_them = is_candidate_compatible(you, cand)
        they_like_you = is_candidate_compatible(cand, you)

        if (you_like_them is False) and (they_like_you is False):
            continue

        if (you_like_them is True) and (they_like_you is True):
            if dist < best_mutual_dist:
                best_mutual_id = cand_id
                best_mutual_dist = dist
        else:
            if dist < best_one_sided_dist:
                best_one_sided_id = cand_id
                best_one_sided_dist = dist

    if best_mutual_id is not None:
        best_user_id = best_mutual_id
        base_distance = best_mutual_dist
        mutual = True
    elif best_one_sided_id is not None:
        best_user_id = best_one_sided_id
        base_distance = best_one_sided_dist
        mutual = False
    else:
        await update.message.reply_text("No compatible matches found yet!")
        return

    match_user = users[best_user_id]

    you["seen_matches"].append(best_user_id)
    save_user(you)

    display_distance = base_distance

    if not mutual:
        same_major = (you.get("major") == match_user.get("major"))
        same_year = (you.get("year_level") == match_user.get("year_level"))

        if (same_major is False) and (same_year is False):
            display_distance = display_distance + 1.0
        else:
            display_distance = display_distance + 0.5

    if not mutual:
        display_distance = display_distance + 0.5

    await update.message.reply_text(
        "New match found!\n\n"
        "Name: " + match_user["first_name"] + " " + match_user["family_name"] + "\n"
        "Age: " + str(match_user["age"]) + "\n"
        "Major: " + match_user["major"] + "\n"
        "Email: " + match_user["email"] + "\n"
        "KakaoTalk: " + match_user["kakaotalk"] + "\n\n"
        "Distance score: " + f"{display_distance:.2f}"
    )

def is_candidate_compatible(you: dict, cand: dict):

    py = you.get("partner_pref_year", "No preference")
    target_year = PARTNER_YEAR_TO_YEAR.get(py, None)
    if target_year is not None:
        if cand.get("year_level") != target_year:
            return False

    pm = you.get("partner_pref_major", "I don't have a specific preference")
    if pm == "I prefer a study partner from my major":
        if cand.get("major") != you.get("major"):
            return False

    return True


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = load_users()

    if uid not in users:
        await update.message.reply_text(
            "You don't have any registered info to delete!\n\n"
            "Send /start if you want to register!",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    user_name = users[uid]['first_name']

    if delete_user(uid):
        await update.message.reply_text(
            f"Got it, {user_name}! Your information has been deleted.️\n\n"
            f"Send /start to register again!\n\n",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Something went wrong. Please try again!",
            reply_markup=ReplyKeyboardRemove()
        )
