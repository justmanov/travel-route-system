import math

class InstructionGenerator:
    """
    Генерує покрокові інструкції для маршруту на основі графа OSMnx і списку вузлів.
    """
    @staticmethod
    def compute_bearing(a: tuple, b: tuple) -> float:
        lat1, lon1 = math.radians(a[0]), math.radians(a[1])
        lat2, lon2 = math.radians(b[0]), math.radians(b[1])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
        theta = math.degrees(math.atan2(x, y))
        return (theta + 360) % 360

    @classmethod
    def generate(cls, G, path: list) -> list:
        # Групування ребер за назвою дороги
        segments = []
        prev_name = None
        seg_edges = []
        for u, v in zip(path[:-1], path[1:]):
            data = G.get_edge_data(u, v, 0) or {}
            name = data.get("name") or data.get("ref") or "невідомій дорозі"
            if name != prev_name and prev_name is not None:
                segments.append((prev_name, seg_edges))
                seg_edges = []
            seg_edges.append((u, v))
            prev_name = name
        segments.append((prev_name, seg_edges))

        # Генерація тексту
        instructions = []
        prev_bearing = None
        for idx, (road_name, edges) in enumerate(segments):
            u0, v0 = edges[0]
            a = (G.nodes[u0]["y"], G.nodes[u0]["x"])
            b = (G.nodes[v0]["y"], G.nodes[v0]["x"])
            bearing = cls.compute_bearing(a, b)

            if idx == 0:
                instructions.append(f"Виїжджайте на {road_name}")
            else:
                # обчислити різницю кутів
                diff = (bearing - prev_bearing + 360) % 360
                turn = "праворуч" if diff < 180 else "ліворуч"
                instructions.append(f"Поверніть {turn} на {road_name}")

            prev_bearing = bearing

        return instructions
