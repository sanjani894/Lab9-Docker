
import os
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse

from app.search import (
    find_candidates,
    coordinate_to_id,
    rank_candidates,
    load_locations_data
)
from app.graph import load_graph, shortest_distances

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Lab 7 – Proximity Search API",
    description=(
        "Given a current position, a category, a circular search radius, and a "
        "road-network linkage file, returns the **10 closest** matching locations "
        "ranked by actual BFS traversal distance over the grid road network.\n\n"
        "## Fields\n"
        "| Field | Type | Description |\n"
        "|-------|------|-------------|\n"
        "| `lat` | float | Current latitude (normalised 0–1) |\n"
        "| `long` | float | Current longitude (normalised 0–1) |\n"
        "| `cat` | string | Category to search (e.g. `bank`, `hospital`) |\n"
        "| `rad` | float | Circular Euclidean search radius |\n"
        "| `link` | file (.txt) | Road-network linkage file |\n\n"
        "## How it works\n"
        "1. Filter dataset by **category** and **Euclidean radius**.\n"
        "2. Build a road graph from the uploaded `link.txt`.\n"
        "3. Run **BFS** from the query point to find shortest traversal distances.\n"
        "4. Return the top-10 candidates sorted by BFS hop-count."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Preload CSV once at startup – builds in-memory category index for fast lookups
df_locations = load_locations_data()


# ---------------------------------------------------------------------------
# Root – redirect hint to docs
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return """
    <html><head><title>Lab 7 Proximity Search API</title></head>
    <body style="font-family:sans-serif;max-width:600px;margin:60px auto">
      <h2>Lab 7 – Proximity Search API</h2>
      <p>Status: <strong style="color:green">Online ✔</strong></p>
      <ul>
        <li><a href="/docs">Interactive Swagger UI (upload & test here)</a></li>
        <li><a href="/redoc">ReDoc documentation</a></li>
      </ul>
      <hr/>
      <p><strong>Endpoint:</strong> <code>POST /search/</code></p>
      <p><strong>Fields:</strong> <code>lat</code>, <code>long</code>,
         <code>cat</code>, <code>rad</code>, <code>link</code> (file)</p>
    </body></html>
    """


# ---------------------------------------------------------------------------
# Primary search endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/search/",
    summary="Find 10 closest locations by road-network distance",
    tags=["Search"],
    response_description="List of up to 10 recommended location IDs",
)
@app.post("/search", include_in_schema=False)
@app.post("/IP/search/", include_in_schema=False)
@app.post("/IP/search", include_in_schema=False)
async def search(
    lat: float = Form(
        ...,
        description="Current latitude (normalised in [0.0, 1.0])",
        openapi_examples={"default": {"summary": "Origin", "value": 0.0}},
    ),
    long: float = Form(
        ...,
        description="Current longitude (normalised in [0.0, 1.0])",
        openapi_examples={"default": {"summary": "Origin", "value": 0.0}},
    ),
    cat: str = Form(
        ...,
        description="Category to search for (e.g. bank, hospital, pharmacy, school, store, park, cafe, restaurant)",
        openapi_examples={"bank": {"summary": "Bank", "value": "bank"}},
    ),
    rad: float = Form(
        ...,
        description="Circular Euclidean search radius (same unit as lat/long, e.g. 0.1)",
        openapi_examples={"default": {"summary": "10% of grid", "value": 0.1}},
    ),
    link: UploadFile = File(
        ...,
        description="Road-network linkage .txt file. Each line: `Lon_A Lat_A Lon_B Lat_B` (space-separated).",
    ),
):
    """
    **Returns** a JSON object with a `results` key containing up to **10 location IDs**
    representing the closest valid locations (matching `cat` and within `rad`) ranked
    by shortest BFS traversal distance over the uploaded road network.

    Example response:
    ```json
    {"results": [1, 102, 3, 203, 503, 603, 801, 508, 607]}
    ```
    """
    # 1. Parse the uploaded linkage file and build undirected road graph
    link_bytes = await link.read()
    graph = load_graph(link_bytes)

    # 2. Filter dataset: only locations matching category inside the circular radius
    candidates = find_candidates(df_locations, lat, long, cat, rad)

    # 3. Map query coordinates onto the 100×100 grid node ID
    source_id = coordinate_to_id(lat, long)

    # 4. BFS from query node – O(V + E) with unit-weight edges
    distances = shortest_distances(source_id, graph)

    # 5. Rank reachable candidates by BFS hops (tie-break by ID)
    ranked = rank_candidates(candidates, distances)

    # 6. Return top-10 results with full location details
    return {
        "results": [item["id"] for item in ranked],
        "details": [
            {
                "id": item["id"],
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "category": item.get("category"),
                "graph_distance_hops": item["graph_distance"],
                "euclidean_distance": item["euclidean_distance"],
            }
            for item in ranked
        ]
    }


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"], summary="Health check")
def health():
    """Returns server status and dataset row count."""
    return {
        "status": "ok",
        "locations_loaded": len(df_locations) if df_locations is not None else 0,
    }