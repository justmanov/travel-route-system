import openrouteservice
import os
from dotenv import load_dotenv

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
client = openrouteservice.Client(key=ORS_API_KEY)

# Повертає координати [lng, lat] для введеної адреси
def geocode_address(address):
    try:
        result = client.pelias_search(text=address)
        coords = result['features'][0]['geometry']['coordinates']
        return coords
    except Exception as e:
        print(f"Помилка геокодування: {e}")
        return None

# Повертає маршрут GeoJSON + відстань (км), час (год), сегменти маршруту
def get_route_data(start_coords, end_coords):
    try:
        response = client.directions(
            coordinates=[start_coords, end_coords],
            profile='driving-car',
            format='geojson',
            instructions=True
        )
        route_geojson = response
        distance_m = response["features"][0]["properties"]["summary"]["distance"]
        duration_s = response["features"][0]["properties"]["summary"]["duration"]
        segments = response["features"][0]["properties"]["segments"]
        return route_geojson, distance_m / 1000, duration_s / 3600, segments
    except Exception as e:
        print(f"Помилка маршруту: {e}")
        return {}, 0, 0, []
