import requests
from shapely.geometry import LineString, Point

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def get_pois_along_route(route_coords, key="tourism", value="museum", buffer_m=500):
    """
    Повертає POI (назви, координати), які знаходяться в межах буфера від маршруту.
    """
    from shapely.geometry import LineString, Point
    import requests

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    line = LineString(route_coords)
    minlon, minlat, maxlon, maxlat = line.bounds

    query = f"""
    [out:json][timeout:25];
    (
      node["{key}"="{value}"]({minlat},{minlon},{maxlat},{maxlon});
      way["{key}"="{value}"]({minlat},{minlon},{maxlat},{maxlon});
      relation["{key}"="{value}"]({minlat},{minlon},{maxlat},{maxlon});
    );
    out center tags;
    """

    try:
        response = requests.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        data = response.json()

        pois = []

        for el in data.get("elements", []):
            if "lon" in el and "lat" in el:
                point = Point(el["lon"], el["lat"])
                coords = (el["lat"], el["lon"])
            elif "center" in el:
                point = Point(el["center"]["lon"], el["center"]["lat"])
                coords = (el["center"]["lat"], el["center"]["lon"])
            else:
                continue

            if line.distance(point) * 111000 <= buffer_m:
                name = el.get("tags", {}).get("name", "Без назви")
                pois.append({"name": name, "lat": coords[0], "lon": coords[1]})

        return pois

    except Exception as e:
        print(f" Помилка при отриманні POI: {e}")
        return []

