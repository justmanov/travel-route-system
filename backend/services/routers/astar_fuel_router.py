import time
import heapq
import networkx as nx
from services.routers.base_router import BaseRouter

# Клас реалізує пошук маршруту за алгоритмом A*
class AStarFuelRouter(BaseRouter):

    def __init__(self, car_brand: str, car_model: str, car_year: int):
        super().__init__(car_brand, car_model, car_year)

    def _heuristic(self, n1, n2) -> float:
        # Евклідова відстань між вузлами за координатами
        x1, y1 = self.G.nodes[n1]['x'], self.G.nodes[n1]['y']
        x2, y2 = self.G.nodes[n2]['x'], self.G.nodes[n2]['y']
        return ((x1 - x2)**2 + (y1 - y2)**2) ** 0.5

# Основна реалізація A*
    def _astar_search(self, start, goal, weight_type: str):
        open_set = [(0, start)]
        came_from = {}
        g_score = {node: float('inf') for node in self.G.nodes}
        g_score[start] = 0
        f_score = {node: float('inf') for node in self.G.nodes}
        f_score[start] = self._heuristic(start, goal)

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                # Відновлення шляху
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            for neighbor in self.G.neighbors(current):
                # може бути декілька паралельних ребер
                for key in self.G[current][neighbor]:
                    weight_value = self.G[current][neighbor][key].get(weight_type, 1)
                    tentative = g_score[current] + weight_value
                    if tentative < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative
                        f_score[neighbor] = tentative + self._heuristic(neighbor, goal)
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return []

# Головна функція для виклику A*
    def find_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        weight_type: str = "fuel_weight"
    ):
        start_time = time.time()
        orig = self._nearest(start_lat, start_lon)
        dest = self._nearest(end_lat, end_lon)
        print(f" A* з метрикою '{weight_type}'")

        try:
            route = self._astar_search(orig, dest, weight_type)
        except nx.NetworkXNoPath:
            print("A* не знайшов шлях.")
            return [], 0, 0, 0

        # Обчислення метрик
        total_distance = sum(
            self.G.edges[u, v, 0]["length"] for u, v in zip(route[:-1], route[1:])
        )
        total_fuel     = sum(
            self.G.edges[u, v, 0]["fuel_weight"] for u, v in zip(route[:-1], route[1:])
        )
        total_duration = sum(
            self.G.edges[u, v, 0]["duration_weight"] for u, v in zip(route[:-1], route[1:])
        )
        elapsed = time.time() - start_time
        print(f"A* виконано за {elapsed:.4f} секунд")
        return route, total_distance/1000, total_fuel, total_duration/60

