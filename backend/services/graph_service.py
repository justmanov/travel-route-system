import os
import osmnx as ox
import networkx as nx

GRAPHML_DIR = "data"
GRAPHML_FILENAME = "kyiv_with_poi.graphml"

def load_kyiv_graph(filepath: str = None) -> nx.MultiDiGraph:
    """
    Завантажує граф Києва з GraphML-файлу. Якщо не існує — створює новий.
    """
    if filepath is None:
        filepath = os.path.join(GRAPHML_DIR, GRAPHML_FILENAME)

    if os.path.exists(filepath):
        print(f"Завантаження графа з файлу: {filepath}")
        return ox.load_graphml(filepath)
    else:
        print(" Створення графа Києва через OSMnx...")
        G = ox.graph_from_place("Kyiv, Ukraine", network_type="drive")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        ox.save_graphml(G, filepath)
        print(f"Граф збережено в {filepath}")
        return G
    