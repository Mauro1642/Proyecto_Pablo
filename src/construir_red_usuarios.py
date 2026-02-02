import pandas as pd
import networkx as nx
import os
import json
from itertools import combinations

def construir_red_global_usuarios(input_car="usuarios_por_canal"):
    """
    Crea un grafo global con videos de todos los canales.
    Retorna el grafo, un DataFrame con información de la red y genera archivo GEXF para Gephi.
    """
    G = nx.Graph()
    todos_los_datos = {}
    
    # Cargar datos de todos los canales
    for archivo in os.listdir(input_car):
        nombre_canal = archivo.split(".")[0]
        ruta = os.path.join(input_car, archivo)
        
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Agregar nodos (videos) con identificador único por canal
        for video_id, usuarios_video in data.items():
            video_node = f"{nombre_canal}_{video_id}"
            todos_los_datos[video_node] = {
                'usuarios': set(usuarios_video),
                'canal': nombre_canal,
                'video_id': video_id
            }
            
            G.add_node(video_node, 
                      canal=nombre_canal, 
                      video_id=video_id,
                      num_usuarios=str(len(set(usuarios_video))))
    
    # Crear aristas entre todos los videos (inter e intra canal)
    videos = list(todos_los_datos.keys())
    edge_data = []
    
    for v1, v2 in combinations(videos, 2):
        usuarios_v1 = todos_los_datos[v1]['usuarios']
        usuarios_v2 = todos_los_datos[v2]['usuarios']
        interseccion = usuarios_v1 & usuarios_v2
        
        peso = len(interseccion)
        if peso > 0:  # solo agregar aristas si hay usuarios en común
            canal1 = todos_los_datos[v1]['canal']
            canal2 = todos_los_datos[v2]['canal']
            tipo_conexion = 'intra_canal' if canal1 == canal2 else 'inter_canal'
            
            G.add_edge(v1, v2, 
                      weight=peso,
                      tipo_conexion=tipo_conexion,
                      usuarios_compartidos=str(list(interseccion)))
            
            # Guardar información de la arista para el DataFrame
            edge_data.append({
                'source': v1,
                'target': v2,
                'canal_source': canal1,
                'canal_target': canal2,
                'weight': peso,
                'tipo_conexion': tipo_conexion,
                'num_usuarios_compartidos': peso
            })
    
    # Crear DataFrame de la red
    df_red = pd.DataFrame(edge_data)
    
    # Generar archivo GEXF para Gephi
    nx.write_gexf(G, "grafo_para_gephi.gexf")
    print(f"Archivo 'grafo_para_gephi.gexf' generado exitosamente")
    print(f"Nodos (videos): {G.number_of_nodes()}")
    print(f"Aristas (conexiones): {G.number_of_edges()}")
    
    return G, df_red