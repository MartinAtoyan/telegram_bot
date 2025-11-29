from annoy import AnnoyIndex
from config import MAJORS, PARTNER_YEAR_ORDER


MAJOR_NAMES = [row[0] for row in MAJORS]
MAJOR_INDEX = {name: i for i, name in enumerate(MAJOR_NAMES)}
NUM_MAJORS = len(MAJOR_NAMES)


MIN_AGE = 18
MAX_AGE = 30


def encode_major_one_hot(major):
    vec = [0.0] * NUM_MAJORS
    i = MAJOR_INDEX.get(major)
    if i is not None:
        vec[i] = 1.0
    return vec


YEAR_ORDER = ["Freshman", "Sophomore", "Junior", "Senior"]
YEAR_INDEX = {y: i for i, y in enumerate(YEAR_ORDER)}


def encode_year_scaled(year: str):
    if year not in YEAR_INDEX:
        return 0.5
    i = YEAR_INDEX[year]
    return float(i) / (len(YEAR_ORDER) - 1)



PARTNER_YEAR_INDEX = {y: i for i, y in enumerate(PARTNER_YEAR_ORDER)}

def encode_partner_year_pref(p: str):
    if p not in PARTNER_YEAR_INDEX:
        return 0.5
    i = PARTNER_YEAR_INDEX[p]
    return float(i) / (len(PARTNER_YEAR_ORDER) - 1)


PARTNER_MAJOR_PREF_MAP = {
    "I prefer a study partner from my major": 1.0,
    "I prefer a study partner from my division": 0.5,
    "I don't have a specific preference": 0.0,
}


def encode_partner_major_pref(p: str):
    return PARTNER_MAJOR_PREF_MAP.get(p, 0.0)


MEET_PREF_MAP = {
    "I prefer studying online": 0.0,
    "I prefer meeting in real life": 1.0,
}


def encode_meet_pref(p: str):
    return MEET_PREF_MAP.get(p, 0.5)


SOUND_PREF_MAP = {
    "I prefer a silent environment where everyone is muted": 0.0,
    "I prefer studying with music": 1.0,
}


def encode_sound_pref(p: str):
    return SOUND_PREF_MAP.get(p, 0.5)


QUESTION_PREF_MAP = {
    "I prefer being able to ask questions reagrding the study material ": 1.0,
    "I prefer individual studying with no help": 0.0,
}


def encode_question_pref(p: str):
    return QUESTION_PREF_MAP.get(p, 0.5)


QUESTION_METHOD_MAP = {
    "I prefer asking questions in the chat": 0.0,
    "I prefer asking questions face to face": 1.0,
    "N/A": 0.5,
}


def encode_question_method(p: str):
    return QUESTION_METHOD_MAP.get(p, 0.5)


def normalize_age(age_str: str):
    try:
        age = int(age_str)
    except ValueError:
        return 0.5

    age_clipped = max(MIN_AGE, min(MAX_AGE, age))
    return (age_clipped - MIN_AGE) / (MAX_AGE - MIN_AGE)


def user_to_vector(u):
    major_vec = encode_major_one_hot(u["major"])

    year_val = encode_year_scaled(u["year_level"])
    partner_major_val = encode_partner_major_pref(u["partner_pref_major"])
    partner_year_val = encode_partner_year_pref(u["partner_pref_year"])
    meet_val = encode_meet_pref(u["meet_pref"])
    sound_val = encode_sound_pref(u["sound_pref"])
    question_pref_val = encode_question_pref(u["question_pref"])
    question_method_val = encode_question_method(u.get("question_method", "N/A"))
    age_val = normalize_age(u["age"])

    scalar_vec = [
        year_val,
        partner_major_val,
        partner_year_val,
        meet_val,
        sound_val,
        question_pref_val,
        question_method_val,
        age_val,
    ]

    return major_vec + scalar_vec


VECTOR_SIZE = NUM_MAJORS + 8
ANNOY_TREES = 10


def build_annoy_index(users):
    index = AnnoyIndex(VECTOR_SIZE, 'euclidean')
    id_map = {}
    reverse_map = {}

    i = 0
    for user_id, data in users.items():
        vec = user_to_vector(data)
        index.add_item(i, vec)
        id_map[i] = user_id
        reverse_map[user_id] = i
        i += 1

    index.build(10)
    return index, id_map, reverse_map