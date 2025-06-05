from flask import Flask, request, render_template
from dotenv import load_dotenv
from services.routers.astar_fuel_router import AStarFuelRouter
from services.routers.dijkstra_router import DijkstraFuelRouter
from services.routers.ant_colony_router import AntColonyRouter
from api_clients.ors_client import geocode_address
from services.poi_service import get_pois_along_route
from services.instruction_service import InstructionGenerator

# Завантаження змінних середовища
load_dotenv()

# Ініціалізація Flask-додатку
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/result", methods=["POST"])
def result():
    # Зчитування з форми
    start_address = request.form.get("start_address")
    end_address = request.form.get("end_address")
    car_brand_raw = request.form.get("car_brand")
    fuel_custom_raw = request.form.get("fuel_custom")
    metric = request.form.get("metric", "fuel_weight")

    print(" Дані з форми:", dict(request.form))

    # Розбір марки авто
    if car_brand_raw:
        parts = car_brand_raw.strip().split(" ")
        car_brand = parts[0] if len(parts) > 0 else ""
        car_model = parts[1] if len(parts) > 1 else ""
        try:
            car_year = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            car_year = 0
    else:
        car_brand = car_model = ""
        car_year = 0

    # Витрата пального
    try:
        custom_rate = float(fuel_custom_raw) if fuel_custom_raw else None
    except ValueError:
        custom_rate = None

    # Геокодування
    start_coords = geocode_address(start_address)
    end_coords = geocode_address(end_address)
    print(" Старт:", start_coords)
    print(" Кінець:", end_coords)

    # Алгоритми в залежності від обраної метрики
    if metric == "poi_score":
        algorithms = [("ant_colony", AntColonyRouter(car_brand, car_model, car_year))]
    else:
        algorithms = [
            ("a_star", AStarFuelRouter(car_brand, car_model, car_year)),
            ("djikstra", DijkstraFuelRouter(car_brand, car_model, car_year)),
        ]


    results = []

    for name, router in algorithms:
        if custom_rate is not None:
            router.avg_consumption = custom_rate
            if hasattr(router, "update_weights"):
                router.update_weights()


        try:
            if name == "ant_colony":
                route_nodes, distance_km, fuel, duration_hr = router.find_route(
                    start_coords[1], start_coords[0],
                    end_coords[1], end_coords[0]
                )
            else:
                route_nodes, distance_km, fuel, duration_hr = router.find_route(
                    start_coords[1], start_coords[0],
                    end_coords[1], end_coords[0],
                    weight_type=metric
                )

            if route_nodes:
                coords = [(router.G.nodes[n]['y'], router.G.nodes[n]['x']) for n in route_nodes]
                line_coords = [[lon, lat] for lat, lon in coords]

                pois = get_pois_along_route(line_coords)
                poi_count = len(pois)

                print(f" {name}: dist={distance_km:.2f} km, fuel={fuel:.2f} L, time={duration_hr:.2f} h, pois={poi_count} ")

                results.append({
                    "name": name,
                    "router": router,
                    "route_nodes": route_nodes,
                    "distance_km": distance_km,
                    "fuel": fuel,
                    "duration_hr": duration_hr,
                    "poi_count": poi_count,
                    "pois": pois,
                    "geojson": {
                        "type": "FeatureCollection",
                        "features": [{"type": "Feature", "geometry": {
                            "type": "LineString", "coordinates": line_coords
                        }}]
                    }
                })
        except Exception as e:
            return render_template("error.html", message="Система не змогла побудувати маршрут. Некоректний ввод даних.")

    # Вибір найкращого маршруту
    if not results:
        return render_template("error.html", message="Маршрут не знайдено жодним з алгоритмів.")

    if metric == "fuel_weight":
        best = min(results, key=lambda r: r["fuel"])
    elif metric == "duration":
        best = min(results, key=lambda r: r["duration_hr"])
    elif metric == "poi":
        best = max(results, key=lambda r: r["poi_count"])
    else:
        best = results[0]

    print(f" Обрано: {best['name']}")

    # Генерація інструкцій
    steps = InstructionGenerator.generate(best["router"].G, best["route_nodes"])

    # Повернення у шаблон
    return render_template(
        "result.html",
        geojson=best["geojson"],
        distance=round(best["distance_km"], 2),
        duration=round(best["duration_hr"], 0),
        fuel=round(best["fuel"], 2),
        poi_count=best["poi_count"],
        steps=steps,
        route_type=best["name"],
        pois=best.get("pois", []) if best["name"] == "ant_colony" else []

    )

if __name__ == "__main__":
    app.run(debug=True)


