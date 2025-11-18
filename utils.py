import numpy as np
from annoy import AnnoyIndex

VECTOR_SIZE = 5
ANNOY_TREES = 10

def encode_major(major): return hash(major) % 1000
def encode_year(year): return int(year)
def encode_pref(p): return hash(p) % 100
def normalize_age(age): return float(age) / 100.0

def user_to_vector(u):
    return np.array([
        encode_major(u["major"]),
        encode_year(u["year_level"]),
        encode_pref(u["meet_pref"]),
        encode_pref(u["sound_pref"]),
        normalize_age(int(u["age"]))
    ], dtype=np.float32)

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

    index.build(ANNOY_TREES)
    return index, id_map, reverse_map
