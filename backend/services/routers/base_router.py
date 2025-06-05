import time
import networkx as nx
import osmnx as ox
from services.graph_service import load_kyiv_graph
from services.fuel_api import get_fuel_consumption_from_api

class BaseRouter:
    """
    Базовий клас для всіх алгоритмів маршрутизації:
    - завантажує граф
    - отримує витрату пального
    - розраховує ваги ребер: fuel_weight, length_weight, duration_weight, poi_score
    """
    def __init__(self, car_brand: str, car_model: str, car_year: int):
        self.car_brand = car_brand
        self.car_model = car_model
        self.car_year = car_year
        self.avg_consumption = self._get_consumption()
        self.G = load_kyiv_graph()
        self._prepare_graph()

# Отримує середню витрату пального через API
    def _get_consumption(self) -> float:
        try:
            consumption = get_fuel_consumption_from_api(self.car_brand, self.car_model, self.car_year)
            print(f"Витрата з API: {consumption} л/100км")
            return consumption
        except Exception as e:
            print(f"Помилка при отриманні витрати пального: {e}")
            return 8.0

# Оцінює середню швидкість для дороги залежно від типу
    def _estimate_speed_kmh(self, highway: str) -> float:
        if highway in ["motorway", "trunk"]:
            return 90
        if highway in ["primary", "secondary"]:
            return 60
        if highway in ["tertiary", "residential"]:
            return 40
        if highway in ["living_street", "service"]:
            return 20
        return 30

# Основна підготовка графа
    def _prepare_graph(self) -> None:
        """Встановлює ваги для всіх ребер графа."""
        self.G.remove_edges_from(nx.selfloop_edges(self.G))
        for u, v, k, data in self.G.edges(keys=True, data=True):
            length_m = data.get("length", 1.0)
            highway = data.get("highway", "")
            if isinstance(highway, list):
                highway = highway[0]

            # коефіцієнт витрати
            coeff = 1.0
            if highway in ["motorway", "trunk"]:
                coeff = 0.8
            elif highway in ["residential", "living_street", "service"]:
                coeff = 1.3

            # витрата пального
            data["fuel_weight"] = (length_m / 100_000) * self.avg_consumption * coeff
            # довжина
            data["length_weight"] = length_m
            # тривалість 
            speed_kmh = self._estimate_speed_kmh(highway)
            data["duration_weight"] = (length_m / 1000) / speed_kmh * 3600 if speed_kmh > 0 else length_m / 5

 # Оновлює ваги витрати пального для всіх ребер графа            
    def update_weights(self):
        for u, v, k, data in self.G.edges(keys=True, data=True):
            length_m = data.get("length", 1.0)
            highway = data.get("highway", "")
            if isinstance(highway, list):
                highway = highway[0]

            coeff = 1.0
            if highway in ["motorway", "trunk"]:
                coeff = 0.9
            elif highway in ["residential", "living_street", "service"]:
                coeff = 1.2

            data["fuel_weight"] = (length_m / 100_000) * self.avg_consumption * coeff

# Знаходить найближчу вершину графа до заданих координат
    def _nearest(self, lat: float, lon: float) -> int:
        return ox.distance.nearest_nodes(self.G, X=lon, Y=lat)