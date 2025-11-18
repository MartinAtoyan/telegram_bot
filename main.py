import os
import json
from dotenv import load_dotenv
from telegram.ext import ContextTypes
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove

from utils import user_to_vector, build_annoy_index

load_dotenv()

DATA_FILE = os.environ.get("DATA_FILE")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

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

QUESTIONS = [
    "What's your first name?",
    "Great! And your last name?",
    "How old are you?",
    "What's your email address?",
    "What's your KakaoTalk ID?",
    "What year are you in?",
    "Which major are you studying?",
    "Who would you prefer as a study partner?",
    "Do you have a preference for your study partner's year level?",
    "Where would you like to study?",
    "What kind of study environment do you prefer?",
    "How do you like to study?",
    "How would you like to ask questions?"
]

YEAR_LEVELS = [
    ["Freshman"],
    ["Sophomore"],
    ["Junior"],
    ["Senior"]
]

MAJORS = [
    ["Comparative Literature and Culture (CLC)"],
    ["Economics (ECON)"],
    ["International Studies (IS)"],
    ["Political Science and International Relations (PSIR)"],
    ["Life Science and Biotechnology (LSBT)"],
    ["Asian Studies (AS)"],
    ["Culture and Design Management (CDM)"],
    ["Information and Interaction Design (IID)"],
    ["Creative Technology Management (CTM)"],
    ["Justice and Civil Leadership (JCL)"],
    ["Quantitative Risk Management (QRM)"],
    ["Science, Technology, and Policy (STP)"],
    ["Sustainable Development and Cooperation (SDC)"],
    ["Nano Science and Engineering (NSE)"],
    ["Energy and Environmental Science and Engineering (EESE)"],
    ["Bio-Convergence (BC)"]
]

PARTNER_MAJOR_PREF = [
    ["I prefer a study partner from my major"],
    ["I prefer a study partner from my division"],
    ["I don't have a specific preference"]
]

PARTNER_YEAR_PREF = [
    ["I prefer a freshman"],
    ["I prefer a sophomore"],
    ["I prefer a junior"],
    ["I prefer a senior"],
    ["No preference"]
]

STUDY_LOCATION_PREF = [
    ["I prefer studying online"],
    ["I prefer meeting in real life"]
]

STUDY_SOUND_PREF = [
    ["I prefer a silent environment"],
    ["I prefer studying with music"]
]

STUDY_QUESTION_PREF = [
    ["I like asking questions about the material"],
    ["I prefer studying independently"]
]

QUESTION_METHOD_PREF = [
    ["I prefer asking questions in the chat"],
    ["I prefer asking questions face to face"]
]

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
        "Hi there! Let's find you the perfect study partner!\n\n"
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
    step = session["step"]
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
            "question_method": d[12] if len(d) > 12 else "N/A",
        }

        save_user(user_record)
        menu_keyboard = ReplyKeyboardMarkup([["/match"], ["/delete"]], resize_keyboard=True)
        await update.message.reply_text(
            f"Awesome, {d[0]}! You're all set!\n\n"
            f"Whenever you're ready to find your study partner, just send /match.\n\n"
            f"Happy studying!",
            reply_markup=menu_keyboard
        )
        del user_sessions[uid]
        return

    if session["step"] < 5:
        await update.message.reply_text(QUESTIONS[session["step"]])


# async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     users = load_users()
#     uid = str(update.effective_user.id)
#
#     if uid not in users:
#         await update.message.reply_text("You need to register first using /start")
#         return
#
#     you = users[uid]
#
#     your_vec = user_to_vector(you)
#
#     nearest = annoy_index.get_nns_by_vector(your_vec, 10, include_distances=True)
#
#     nn_ids, distances = nearest
#
#     best_user_id = None
#     best_distance = float('inf')
#
#     for annoy_i, dist in zip(nn_ids, distances):
#         if id_map[annoy_i] == uid:
#             continue
#         if dist < best_distance:
#             best_distance = dist
#             best_user_id = id_map[annoy_i]
#
#     if not best_user_id:
#         await update.message.reply_text("No matches yet!")
#         return
#
#     match_user = users[best_user_id]
#
#     await update.message.reply_text(
#         f"Best match found!\n\n"
#         f"Name: {match_user['first_name']} {match_user['family_name']}\n"
#         f"Age: {match_user['age']}\n"
#         f"Major: {match_user['major']}\n"
#         f"Email: {match_user['email']}\n"
#         f"KakaoTalk: {match_user['kakaotalk']}\n\n"
#         f"Distance score: {best_distance:.2f}"
#     )

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
    # your_annoy_id = reverse_map[uid]

    nn_ids, distances = annoy_index.get_nns_by_vector(your_vec, 50, include_distances=True)

    best_user_id = None
    best_distance = float('inf')

    for annoy_i, dist in zip(nn_ids, distances):
        cand_id = id_map[annoy_i]

        if cand_id == uid:
            continue

        if cand_id in you["seen_matches"]:
            continue

        best_user_id = cand_id
        best_distance = dist
        break

    if not best_user_id:
        await update.message.reply_text("You've seen all available matches!")
        return

    match_user = users[best_user_id]

    you["seen_matches"].append(best_user_id)
    save_user(you)

    await update.message.reply_text(
        f"New match found!\n\n"
        f"Name: {match_user['first_name']} {match_user['family_name']}\n"
        f"Age: {match_user['age']}\n"
        f"Major: {match_user['major']}\n"
        f"Email: {match_user['email']}\n"
        f"KakaoTalk: {match_user['kakaotalk']}\n\n"
        f"Distance score: {best_distance:.2f}"
    )

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
            f"If you change your mind, just send /start to register again!\n\n"
            f"Take care!",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Oops! Something went wrong. Please try again!",
            reply_markup=ReplyKeyboardRemove()
        )

#
# telegram_app = Application.builder().token(BOT_TOKEN).build()
# telegram_app.add_handler(CommandHandler("start", start))
# telegram_app.add_handler(CommandHandler("match", match))
# telegram_app.add_handler(CommandHandler("delete", delete))
# telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
#
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await telegram_app.initialize()
#     await telegram_app.start()
#     asyncio.create_task(telegram_app.updater.start_polling())
#
#     yield
#
#     await telegram_app.updater.stop()
#     await telegram_app.stop()
#     await telegram_app.shutdown()
#
# app = FastAPI(lifespan=lifespan)
#
#
# @app.get("/")
# async def root():
#     return {"status": "Study Partner Matching Bot - Active", "message": "Ready to connect students!"}
#
#
# @app.get("/health")
# async def health():
#     return {
#         "status": "healthy",
#         "bot_running": telegram_app.running,
#         "total_users": len(load_users())
#     }
#
#
# if __name__ == "__main__":
#     import uvicorn
#
#     uvicorn.run(app, host="0.0.0.0", port=8000)