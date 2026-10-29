import math
import os
from collections import defaultdict
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCATIONS_FILE = os.path.join(BASE_DIR, "data", "locations.csv")

_CATEGORIES_INDEX = defaultdict(list)
_DF = None


def load_locations_data(csv_path=None):
    global _CATEGORIES_INDEX, _DF
    path = csv_path or LOCATIONS_FILE
    if not os.path.exists(path):
        path = "data/locations.csv"
    if not os.path.exists(path):
        return None

    _DF = pd.read_csv(path)
    _CATEGORIES_INDEX.clear()
    for row in _DF.itertuples():
        _CATEGORIES_INDEX[str(row.Category).strip().lower()].append(
            (int(row.ID), float(row.Latitude), float(row.Longitude))
        )
    return _DF


# Initialize index on import if file exists
try:
    load_locations_data()
except Exception:
    pass


def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def find_candidates(df, current_lat, current_long, category, radius):
    cat_key = str(category).strip().lower()

    # Fast path using pre-indexed spatial data
    if _CATEGORIES_INDEX and cat_key in _CATEGORIES_INDEX:
        entries = _CATEGORIES_INDEX[cat_key]
        candidates = []
        rad_sq = radius * radius
        for loc_id, lat, lon in entries:
            dist_sq = (current_lat - lat) ** 2 + (current_long - lon) ** 2
            if dist_sq <= rad_sq + 1e-12:
                candidates.append({
                    "id": loc_id,
                    "latitude": lat,
                    "longitude": lon,
                    "category": cat_key,
                    "distance": math.sqrt(dist_sq)
                })
        return candidates

    # Fallback to iterating df if index not populated
    candidates = []
    if df is not None:
        for row in df.itertuples():
            if str(row.Category).strip().lower() != cat_key:
                continue
            distance = calculate_distance(
                current_lat,
                current_long,
                float(row.Latitude),
                float(row.Longitude)
            )
            if distance <= radius + 1e-9:
                candidates.append({
                    "id": int(row.ID),
                    "latitude": float(row.Latitude),
                    "longitude": float(row.Longitude),
                    "category": cat_key,
                    "distance": distance
                })
    return candidates


def coordinate_to_id(lat, lon):
    row = max(0, min(99, round(lat * 99)))
    col = max(0, min(99, round(lon * 99)))
    return row * 100 + col + 1


def rank_candidates(candidates, graph_distances):
    reachable = []

    for candidate in candidates:
        candidate_id = candidate["id"]

        if candidate_id in graph_distances:
            reachable.append({
                "id": candidate_id,
                "latitude": candidate.get("latitude"),
                "longitude": candidate.get("longitude"),
                "category": candidate.get("category"),
                "graph_distance": graph_distances[candidate_id],
                "euclidean_distance": round(candidate.get("distance", 0.0), 8)
            })

    reachable.sort(key=lambda x: (x["graph_distance"], x["id"]))

    return reachable[:10]