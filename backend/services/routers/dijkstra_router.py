import heapq
import networkx as nx
import time
from services.routers.base_router import BaseRouter

class DijkstraFuelRouter(BaseRouter):
    def __init__(self, car_brand, car_model, car_year):
        super().__init__(car_brand, car_model, car_year)

    def find_route(self, start_lat, start_lon, end_lat, end_lon, weight_type="fuel_weight"):
        start_time = time.time()

        # Обчислюємо стартовий і цільовий вузли
        orig = self._nearest(start_lat, start_lon)
        dest = self._nearest(end_lat, end_lon)
        print(f" Dijkstra з метрикою '{weight_type}'")
        print(f" Старт: {orig}, Фініш: {dest}")

        # Ініціалізуємо структури для Dijkstra
        distances = {node: float('inf') for node in self.G.nodes}
        previous  = {}
        distances[orig] = 0
        queue = [(0, orig)]
        visited = set()

        # Основний цикл пошуку
        while queue:
            curr_dist, u = heapq.heappop(queue)
            if u in visited:
                continue
            visited.add(u)
            if u == dest:
                break

            for v in self.G.successors(u):
                edge_data = self.G.get_edge_data(u, v, 0) or {}
                w = edge_data.get(weight_type, float('inf'))
                nd = curr_dist + w
                if nd < distances[v]:
                    distances[v] = nd
                    previous[v] = u
                    heapq.heappush(queue, (nd, v))

        # Реконструюємо шлях
        path = []
        node = dest
        while node in previous:
            path.append(node)
            node = previous[node]
        if not path:
            print(" Dijkstra не знайшов шлях.")
            return [], 0, 0, 0
        path.append(orig)
        path.reverse()

        # Підрахунок метрик
        total_distance = sum(self.G.edges[u, v, 0].get("length", 0)
                             for u, v in zip(path[:-1], path[1:]))
        total_fuel     = sum(self.G.edges[u, v, 0].get("fuel_weight", 0)
                             for u, v in zip(path[:-1], path[1:]))
        total_duration = sum(self.G.edges[u, v, 0].get("duration_weight", 0)
                             for u, v in zip(path[:-1], path[1:]))

        elapsed = time.time() - start_time
        print(f" Dijkstra виконано за {elapsed:.4f} секунд")

        # Повертаємо (вузли, км, л, хв)
        return path, total_distance/1000, total_fuel, total_duration/60

