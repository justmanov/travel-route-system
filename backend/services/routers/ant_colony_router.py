import networkx as nx
import osmnx as ox
import random
import time
import heapq
import math
from services.graph_service import load_kyiv_graph
from services.fuel_api import get_fuel_consumption_from_api

class AntColonyRouter:
    def __init__(self, car_brand, car_model, car_year, num_ants=5, num_iterations=5, alpha=1.0, beta=2.0, evaporation=0.5):
        self.car_brand = car_brand
        self.car_model = car_model
        self.car_year = car_year
        self.avg_consumption = self._get_consumption()
        self.num_ants = num_ants
        self.num_iterations = num_iterations
        self.alpha = alpha
        self.beta = beta
        self.evaporation = evaporation

# Отримання середньої витрати пального з API
    def _get_consumption(self):
        try:
            consumption = get_fuel_consumption_from_api(self.car_brand, self.car_model, self.car_year)
            print(f"Витрата з API: {consumption} л/100км")
            return consumption
        except Exception as e:
            print(f"Помилка при отриманні витрати пального: {e}")
            return 8.0

# Оцінка середньої швидкості руху залежно від типу дороги
    def _estimate_speed_kmh(self, highway):
        if highway in ["motorway", "trunk"]:
            return 90
        elif highway in ["primary", "secondary"]:
            return 60
        elif highway in ["tertiary", "residential"]:
            return 40
        elif highway in ["living_street", "service"]:
            return 20
        return 30

# Додавання до графа ваг ребер за трьома метриками
    def _add_all_weights(self, G):
        for u, v, k, data in G.edges(keys=True, data=True):
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
            data["length_weight"] = length_m

            speed_kmh = self._estimate_speed_kmh(highway)
            data["duration_weight"] = (length_m / 1000) / speed_kmh * 3600 if speed_kmh > 0 else length_m / 5

            poi = data.get("poi_count", 0)
            try:
                poi_int = int(poi)
            except:
                poi_int = 0
            data["poi_score"] = 1 / (1 + poi_int)

 # Нормалізація ваг
    def _normalize_weights(self):
        min_fuel, max_fuel = float('inf'), float('-inf')
        min_length, max_length = float('inf'), float('-inf')
        min_poi_log, max_poi_log = float('inf'), float('-inf')

        for _, _, _, data in self.G.edges(keys=True, data=True):
            min_fuel = min(min_fuel, data["fuel_weight"])
            max_fuel = max(max_fuel, data["fuel_weight"])
            min_length = min(min_length, data["length_weight"])
            max_length = max(max_length, data["length_weight"])

            # ➕ Обчислюємо лише якщо ще не рахували
            if "poi_score_log" not in data:
                poi_val = max(data["poi_score"], 1e-3)  # щоб log(0) уникнути
                log_val = math.log(poi_val + 1)
                data["poi_score_log"] = log_val

            min_poi_log = min(min_poi_log, data["poi_score_log"])
            max_poi_log = max(max_poi_log, data["poi_score_log"])

        for _, _, _, data in self.G.edges(keys=True, data=True):
            data["fuel_weight"] = (data["fuel_weight"] - min_fuel) / (max_fuel - min_fuel + 1e-6)
            data["length_weight"] = (data["length_weight"] - min_length) / (max_length - min_length + 1e-6)
            data["poi_score"] = 1.0 - ((data["poi_score_log"] - min_poi_log) / (max_poi_log - min_poi_log + 1e-6))
            del data["poi_score_log"]


# Евристична оцінка відстані між вузлами
    def _heuristic(self, node, dest):
        x1, y1 = self.G.nodes[node]['x'], self.G.nodes[node]['y']
        x2, y2 = self.G.nodes[dest]['x'], self.G.nodes[dest]['y']
        return ((x1 - x2)**2 + (y1 - y2)**2)**0.5

# Побудова початкового шляху за алгоритмом Дейкстри 
    def dijkstra_path(self, G, start, end):
        queue = [(0, start, [])]
        visited = set()

        while queue:
            (cost, node, path) = heapq.heappop(queue)
            if node in visited:
                continue
            path = path + [node]
            if node == end:
                return path
            visited.add(node)
            for neighbor in G.successors(node):
                if neighbor not in visited:
                    data = G.get_edge_data(node, neighbor, 0)
                    weight = self._combined_weight(data)
                    if weight < float('inf'):
                        heapq.heappush(queue, (cost + weight, neighbor, path))
        return None

# Обчислення ваги ребра з урахуванням трьох факторів
    def _combined_weight(self, data, alpha=0.2, beta=0.2, gamma=5):
        try:
            fuel = float(data.get("fuel_weight", 0.0))
            length = float(data.get("length_weight", 0.0)) 
            poi = float(data.get("poi_score", 0.0)) 

            # Формула: чим менше fuel і length і більше POI — тим краща вага
            score = alpha * fuel + beta * length + gamma * poi

            if score < 0:
                print(f"‼️ Негативний score: fuel={fuel:.3f}, length={length:.3f}, poi={poi:.3f} => score={score:.3f}")

            return max(score, 1e-6)

        except (ValueError, TypeError) as e:
            print(f"⚠️ Weight error: {e}, data: {data}")
            return float('inf')


 # Основна функція
    def find_route(self, start_lat, start_lon, end_lat, end_lon):
        start_time = time.time()
        self.G = load_kyiv_graph()
        self._add_all_weights(self.G)
        self._normalize_weights()
        self.G.remove_edges_from(nx.selfloop_edges(self.G))

        orig = ox.distance.nearest_nodes(self.G, X=start_lon, Y=start_lat)
        dest = ox.distance.nearest_nodes(self.G, X=end_lon, Y=end_lat)
        print(f"ACO з комбінованою вагою (fuel + length - poi)")
        print(f"Старт: {orig}, Фініш: {dest}")

        pheromones = {(u, v): 1.0 for u, v in self.G.edges()}

        try:
            initial_path = self.dijkstra_path(self.G, orig, dest)
            for u, v in zip(initial_path[:-1], initial_path[1:]):
                pheromones[(u, v)] += 10
        except:
            print("⚠️ Dijkstra не знайшов шлях")

        best_path = []
        best_cost = float('inf')

        for iteration in range(self.num_iterations):
            all_paths = []
            for _ in range(self.num_ants):
                path = self._construct_solution(orig, dest, pheromones)
                if path:
                    cost = self._calculate_cost(path)
                    all_paths.append((path, cost))
                    if cost < best_cost:
                        best_cost = cost
                        best_path = path
            self._update_pheromones(pheromones, all_paths)
            print(f" Ітерація {iteration+1}/{self.num_iterations}, найкраща ціна: {best_cost}")

        if not best_path:
            print("ACO не знайшов шлях.")
            return [], 0, 0, 0

        total_distance = total_fuel = total_duration = 0
        for u, v in zip(best_path[:-1], best_path[1:]):
            data = self.G.get_edge_data(u, v, 0)
            total_distance += data.get("length", 0)
            total_fuel += data.get("fuel_weight", 0)
            total_duration += data.get("duration_weight", 0)

        elapsed = time.time() - start_time
        print(f"ACO виконано за {elapsed:.4f} секунд")
        return best_path, total_distance / 1000, total_fuel, total_duration / 60

 # Побудова одного маршруту однією мурахою з урахуванням феромонів і евристики       
    def _construct_solution(self, start, end, pheromones):
        path = [start]
        current = start
        visits = {start: 1}
        MAX_STEPS = 400
        steps = 0

        while current != end and steps < MAX_STEPS:
            neighbors = list(self.G.successors(current))
            if not neighbors:
                print(f"Немає сусідів у вузла {current}")
                return None

            probabilities = []
            total = 0
            for v in neighbors:
                if visits.get(v, 0) >= 2:
                    continue

                edge = (current, v)
                pheromone = pheromones.get(edge, 1.0)
                data = self.G[current][v][0]

                score = self._combined_weight(data)
                if score <= 0 or score == float('inf'):
                    continue

                heuristic = 1.0 / (score + self._heuristic(v, end) + 1e-6)
                prob = (pheromone ** self.alpha) * (heuristic ** self.beta)
                probabilities.append((v, prob))
                total += prob

            if not probabilities:
                print(f"⚠️ Мураха застрягла у {current}, крок {steps}")
                return None

            nodes, probs = zip(*probabilities)
            probs = [p / total for p in probs]
            next_node = random.choices(nodes, weights=probs, k=1)[0]

            path.append(next_node)
            visits[next_node] = visits.get(next_node, 0) + 1
            current = next_node
            steps += 1

        if current == end:
            print(f"✅ Мураха завершила маршрут за {steps} кроків.")
            return path
        else:
            print(f"⚠️ Мураха не дісталась до цілі за {steps} кроків")
            return None

# Обчислення загальної вартості (метрики) маршруту
    def _calculate_cost(self, path):
        cost = 0
        for u, v in zip(path[:-1], path[1:]):
            data = self.G.get_edge_data(u, v, 0)
            cost += self._combined_weight(data)
        return cost

# Оновлення феромонів: випаровування + підсилення на кращих маршрутах
    def _update_pheromones(self, pheromones, paths):
        for edge in pheromones:
            pheromones[edge] *= (1 - self.evaporation)

        for path, cost in paths:
            if cost == 0:
                continue
            for u, v in zip(path[:-1], path[1:]):
                pheromones[(u, v)] += 1.0 / cost