import osmnx as ox
import networkx as nx
import requests
from shapely.geometry import LineString, Point
from tqdm import tqdm

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def count_pois_near_edge(line_coords, key="tourism", value="museum", buffer_m=500):
    line = LineString(line_coords)
    minlon, minlat, maxlon, maxlat = line.bounds

    query = f"""
    [out:json][timeout:25];
    (
      node["{key}"="{value}"]({minlat},{minlon},{maxlat},{maxlon});
      way["{key}"="{value}"]({minlat},{minlon},{maxlat},{maxlon});
      relation["{key}"="{value}"]({minlat},{minlon},{maxlat},{maxlon});
    );
    out center;
    """
    try:
        response = requests.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        data = response.json()
        elements = data.get("elements", [])
        count = 0
        for el in elements:
            if "lon" in el and "lat" in el:
                point = Point(el["lon"], el["lat"])
            elif "center" in el:
                point = Point(el["center"]["lon"], el["center"]["lat"])
            else:
                continue

            if line.distance(point) * 111000 <= buffer_m:
                count += 1
        return count
    except Exception:
        return 0

# Завантаження існуючого графа
G = ox.load_graphml("data/kyiv.graphml")

# Додавання POI до кожного ребра
for u, v, k, data in tqdm(G.edges(keys=True, data=True), desc="Обчислення POI для ребер"):
    if "geometry" in data:
        line_coords = list(data["geometry"].coords)
    else:
        x1, y1 = G.nodes[u]["x"], G.nodes[u]["y"]
        x2, y2 = G.nodes[v]["x"], G.nodes[v]["y"]
        line_coords = [(x1, y1), (x2, y2)]
    
    data["poi_count"] = count_pois_near_edge(line_coords)

# Збереження
ox.save_graphml(G, "data/kyiv_with_poi.graphml")
