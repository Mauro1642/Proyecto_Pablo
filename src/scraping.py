import pandas as pd
import re
import json
import os
from datetime import datetime, timedelta
import pytz
import time
import random
import yt_dlp

ap_key = "AIzaSyCnx9KNELdutZ4XJPZgWfFspQTnPmPj08M" # Esta clave no se usa con yt_dlp, pero se mantiene.
canales = [
    'UCZ2V316UTXTyvd8w5wjA_Aw',
    'UCx6h-dWzJ5NpAlja1YsApdg',
    'UC8BxSGcBKriJvoeyKOnJ6tA',
    'UCCjG8NtOig0USdrT5D1FpxQ',
    'UCmgnsaQIK1IR808Ebde-ssA','UCPWXiRWZ29zrxPFIQT7eHSA',
    'UCqnbDFdCpuN8CMEg0VuEBqA','UCBi2mrWuNuyYy4gbM6fU18Q',
    'UCXIJgqnII2ZOINSWNOGFThA', 'UCeY0bbntWzzVIaj2z3QigXg',
    'UCw0_9Iih3qM_I_gFLrJeNRg', 'UC8p1vwvWtl6T73JiExfWs1g',
    'UCHd62-u_v4DvJ8TCFtpi4GA', 'UC7qZ_e097NBkgOljy1joVRA',
    'UC2a35q7eyzkfoIusBzdH4Hw', 'UCsCE4IMMFuwPYbwDqaz7udQ',
    'UCvAnclelY8eSq8GyPE19KTw', 'UCk2FZi3N0h8APcVBOisQCMQ',
    'UC7-bB8X0-0vntXO1K3ZgNfg', 'UCn4sPeUomNGIr26bElVdDYg'
]

# --- Funciones Auxiliares (Modificadas para recibir 'info' dict) ---

def get_channel_name(channel_id):
    try:
        url = f"https://www.youtube.com/channel/{channel_id}/about"
        channel_id = channel_id.strip('"\'')
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "extract_flat": True, # Para obtener info del canal, no videos
            "ignoreerrors": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and "channel" in info and "uploader_id" in info:
                name = info["channel"]
                handle = info["uploader_id"]
                return name, handle
            else:
                print(f"❌ No se pudo obtener la información del canal {channel_id}.")
                return "desconocido", None
    except Exception as e:
        print(f"❌ Error al obtener info del canal {channel_id}: {e}")
        return "desconocido", None

def fecha_video(info):
    """Extrae la fecha de publicación de un diccionario de información de video."""
    return info.get('upload_date') # formato: 'YYYYMMDD'

def get_video_metadata(info):
    """Extrae vistas y likes de un diccionario de información de video."""
    return {
        'views': info.get('view_count'),
        'likes': info.get('like_count'),
    }

def get_comments(info):
    """Extrae comentarios de un diccionario de información de video."""
    comentarios = {}
    if info and "comments" in info:
        for comentario in info["comments"]:
            cid = comentario["id"]
            fecha = comentario["_time_text"]
            fecha = time_text_to_iso_argentina(fecha)
            comentarios[cid] = {
                "texto": comentario["text"],
                "fecha": fecha,
                "likes": comentario["like_count"],
                "autor": comentario["author"]
            }
    return comentarios

# --- Funciones sin cambios significativos ---

def pasaron_48_horas(upload_date_str):
    if upload_date_str is None: # Manejar el caso donde no se pudo obtener la fecha
        return timedelta(hours=999), True # Considerarlo como "pasaron 48h"
    fecha_publicacion = datetime.strptime(upload_date_str, "%Y%m%d")
    argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
    fecha_publicacion = argentina_tz.localize(fecha_publicacion)
    ahora = datetime.now(argentina_tz)
    diferencia = ahora - fecha_publicacion
    return [diferencia, diferencia.total_seconds() > 24 * 3600] # Cambiado a 48h

def cargar_json(path):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}

def guardar_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def id_videos_por_dia(channel_url, videos_por_dia=10, dias_atras=30):
    """
    Obtiene videos del canal publicados en el último mes.
    Solo incluye videos regulares (excluye shorts, livestreams, premieres, etc.)
    
    Parámetros:
    - channel_url: URL del canal de YouTube
    - videos_por_dia: No se usa en esta versión (mantenido por compatibilidad)
    - dias_atras: Cantidad de días hacia atrás (default: 30 = último mes)
    """
    argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
    hoy = datetime.now(argentina_tz).date()
    hace_un_mes = hoy - timedelta(days=dias_atras)
    
    fecha_inicio = hace_un_mes.strftime("%Y%m%d")
    fecha_fin = hoy.strftime("%Y%m%d")
    
    print(f"📅 Buscando videos desde {hace_un_mes} hasta {hoy}...")
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'force_json': False,
        'playlistend': 500,  # Buscar más videos para asegurar cobertura del mes
        'no_warnings': True,
        'ignoreerrors': True,
        'daterange': yt_dlp.utils.DateRange(fecha_inicio, fecha_fin),
    }
    
    videos_validos = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
            if info and "entries" in info:
                for entry in info["entries"]:
                    if entry and entry.get("id"):
                        # Filtros para asegurar solo videos regulares publicados por el canal
                        es_video_regular = True
                        
                        # Filtro 1: Excluir livestreams, premieres y upcoming
                        live_status = entry.get("live_status")
                        if live_status in ["is_live", "is_upcoming", "was_live", "post_live"]:
                            es_video_regular = False
                            print(f"  ⏭️ Excluido {entry.get('id')}: livestream/premiere")
                        
                        # Filtro 2: Excluir si no está públicamente disponible
                        availability = entry.get("availability")
                        if availability and availability not in ["public"]:
                            es_video_regular = False
                            print(f"  ⏭️ Excluido {entry.get('id')}: no público ({availability})")
                        
                        # Filtro 3: Excluir shorts por URL/path
                        url = entry.get("url", "")
                        webpage_url = entry.get("webpage_url", "")
                        if "/shorts/" in url or "/shorts/" in webpage_url:
                            es_video_regular = False
                            print(f"  ⏭️ Excluido {entry.get('id')}: Short detectado por URL")
                        
                        # Filtro 4: Excluir shorts por duración (menos de 61 segundos)
                        duracion = entry.get("duration")
                        if duracion and duracion < 61:
                            es_video_regular = False
                            print(f"  ⏭️ Excluido {entry.get('id')}: duración corta ({duracion}s)")
                        
                        # Filtro 5: Verificar que la fecha esté dentro del rango
                        upload_date = entry.get("upload_date")
                        if upload_date:
                            try:
                                fecha_video = datetime.strptime(upload_date, "%Y%m%d").date()
                                if not (hace_un_mes <= fecha_video <= hoy):
                                    es_video_regular = False
                                    print(f"  ⏭️ Excluido {entry.get('id')}: fuera de rango de fechas")
                            except:
                                pass
                        
                        # Filtro 6: Verificar que sea del canal (evitar videos compartidos/playlists mixtas)
                        channel_id_video = entry.get("channel_id")
                        uploader_id = entry.get("uploader_id")
                        # Extraer channel_id de la URL del canal si es posible
                        if channel_id_video or uploader_id:
                            # Este filtro es más relevante si tienes el channel_id del canal
                            # Por ahora lo dejamos preparado
                            pass
                        
                        if es_video_regular:
                            videos_validos.append(entry["id"])
                            print(f"  ✅ Video válido: {entry.get('id')} - {entry.get('title', 'Sin título')[:50]}")
        
        print(f"\n  📊 Total: {len(videos_validos)} videos regulares encontrados en el último mes")
        
    except Exception as e:
        print(f"  ❌ Error al buscar videos: {e}")
    
    # Pausa para evitar rate limiting
    time.sleep(random.uniform(2, 4))
    
    return videos_validos

def convertir_a_argentina(published_at_str):
    utc_dt = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_dt = utc_dt.replace(tzinfo=pytz.utc)
    argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
    local_dt = utc_dt.astimezone(argentina_tz)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

def time_text_to_iso_argentina(_time_text):
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    now = datetime.now(tz)
    match = re.match(r"(\d+)\s(\w+)\sago", _time_text)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    if unit.startswith("second"):
        delta = timedelta(seconds=value)
    elif unit.startswith("minute"):
        delta = timedelta(minutes=value)
    elif unit.startswith("hour"):
        delta = timedelta(hours=value)
    elif unit.startswith("day"):
        delta = timedelta(days=value)
    else:
        return None
    comment_time = now - delta
    return comment_time.strftime("%Y-%m-%dT%H:%M:%SZ")

# --- Función Principal (extraer_comentarios) ---

def extraer_comentarios(channel_ids=canales,
                        processed_file="processed_videos.json",
                        comments_dir="data",
                        actualizar_videos=True,
                        max_comen=200,
                        videos_por_dia=10,
                        dias_atras=30):
    """
    Extrae comentarios de videos publicados en el último mes.
    
    Parámetros:
    - channel_ids: Lista de IDs de canales
    - processed_file: Archivo con videos ya procesados
    - comments_dir: Directorio para guardar comentarios
    - actualizar_videos: Si actualizar videos ya procesados
    - max_comen: Cantidad máxima de comentarios por video
    - videos_por_dia: No usado (mantenido por compatibilidad)
    - dias_atras: Cantidad de días hacia atrás (default: 30 = último mes)
    """

    if os.path.exists(processed_file):
        with open(processed_file, "r", encoding="utf-8") as f:
            processed_videos = json.load(f)
            processed_videos = {ch: set(ids) for ch, ids in processed_videos.items()}
    else:
        processed_videos = {}

    for channel_id in channel_ids:
        print(f"\n{'='*80}")
        print(f"🎯 Procesando canal: {channel_id}")
        print(f"{'='*80}\n")
        
        channel_name, handle = get_channel_name(channel_id)
        if not handle:
            print(f"⚠️ Skipping channel {channel_id} due to missing handle.")
            continue
        
        url = f"https://www.youtube.com/{handle}/videos"

        canal_comments_file = os.path.join(comments_dir, f"comentarios_{channel_name}.json")
        if os.path.exists(canal_comments_file):
            with open(canal_comments_file, "r", encoding="utf-8") as f:
                canal_comments = json.load(f)
        else:
            canal_comments = {}
        
        updated_video_ids = set()
        
        # Asegurarse de que el canal_name esté en processed_videos
        if channel_name not in processed_videos:
            processed_videos[channel_name] = set()

        videos_a_procesar_ahora = set()

        # Añadir videos existentes que necesitan actualización
        if actualizar_videos:
            videos_a_procesar_ahora.update(processed_videos[channel_name])
            print(f"🔄 Actualizando {len(processed_videos[channel_name])} videos existentes para {channel_name}...")

        # Obtener videos del último mes (solo videos regulares)
        print(f"\n🔍 Obteniendo videos del último mes para {channel_name}...")
        latest_video_ids = id_videos_por_dia(url, videos_por_dia=videos_por_dia, dias_atras=dias_atras)
        print(f"📊 Total de videos regulares encontrados: {len(latest_video_ids)}\n")
        videos_a_procesar_ahora.update(latest_video_ids)

        contador_procesados = 0
        total_a_procesar = len(videos_a_procesar_ahora)
        
        for video_id in videos_a_procesar_ahora:
            contador_procesados += 1
            print(f"\n[{contador_procesados}/{total_a_procesar}] Procesando video: {video_id}")
            
            if not (video_id in canal_comments):
                # Pausa aleatoria antes de cada video para evitar rate limiting
                pausa = random.uniform(2.0, 5.0)
                print(f"⏳ Pausando {pausa:.2f} segundos...")
                time.sleep(pausa)

                # Única llamada a yt_dlp.extract_info por video
                ydl_opts_video = {
                    'quiet': True,
                    'skip_download': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'getcomments': True,
                    'comment_limit': max_comen,
                    'ignoreerrors': True,
                    'force_json': False,
                }
                video_id = video_id.strip('"\'')
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            
                info_dict = None
                try:
                    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                        info_dict = ydl.extract_info(video_url, download=False)
                except yt_dlp.DownloadError as e:
                    print(f"❌ Error al extraer info de {video_id}: {e}")

                # Si no se pudo obtener info, saltamos este video
                if not info_dict:
                    print(f"⚠️ No se pudo obtener información del video {video_id}. Saltando...")
                    continue

                # Verificación adicional: confirmar que NO es un short
                duracion = info_dict.get("duration")
                if duracion and duracion < 61:
                    print(f"⏭️ Saltando {video_id}: detectado como Short (duración: {duracion}s)")
                    continue

                updated_video_ids.add(video_id)

                stats = get_video_metadata(info_dict)
                metrics = {
                    "_metrics": {
                        "views": stats.get("views"),
                        "likes": stats.get("likes"),
                    }
                }
                nuevos_comentarios = get_comments(info_dict)

                historico_video = {
                    k: v for k, v in canal_comments.get(video_id, {}).items() if k != "_metrics"
                }

                for cid, data in nuevos_comentarios.items():
                    if cid not in historico_video:
                        historico_video[cid] = data

                canal_comments[video_id] = {**metrics, **historico_video}
                print(f"✅ Video procesado: {len(nuevos_comentarios)} comentarios extraídos")
        
        # Guardar comentarios actualizados por canal
        os.makedirs(comments_dir, exist_ok=True)
        with open(canal_comments_file, "w", encoding="utf-8") as f:
            json.dump(canal_comments, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Guardados comentarios de {len(updated_video_ids)} videos para {channel_name}")
        
        # Actualizar processed_videos para este canal
        processed_videos[channel_name] = list(updated_video_ids)

    # Guardar processed_videos global
    with open(processed_file, "w", encoding="utf-8") as f:
        json.dump({ch: list(ids) for ch, ids in processed_videos.items()}, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✨ Proceso completado exitosamente")
    print(f"{'='*80}\n")

# --- Extrae usuarios por canal ---
def usuarios_canal(input_dir="comentarios_por_canal", output_dir="usuarios_por_canal"):
    os.makedirs(output_dir, exist_ok=True)

    for archivo in os.listdir(input_dir):
        if archivo.endswith(".json"):
            ruta = os.path.join(input_dir, archivo)

            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)

            canal_nombre_archivo = os.path.splitext(archivo)[0].replace("comentarios_", "")
            salida = os.path.join(output_dir, f"{canal_nombre_archivo}.json")

            if os.path.exists(salida):
                with open(salida, "r", encoding="utf-8") as f:
                    canal_data = json.load(f)
            else:
                canal_data = {}
            
            id_videos = [k for k in data.keys() if k != "_metrics"]

            for video in id_videos:
                usuarios = set(canal_data.get(video, []))

                comentarios_del_video = data[video].keys()
                for comentario_key in comentarios_del_video:
                    if comentario_key != "_metrics":
                        autor = data[video][comentario_key]["autor"]
                        usuarios.add(autor)

                canal_data[video] = list(usuarios)
            
            with open(salida, "w", encoding="utf-8") as f:
                json.dump(canal_data, f, ensure_ascii=False, indent=2)


# --- Ejecución del script ---
if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     EXTRACTOR DE COMENTARIOS DE YOUTUBE - VERSIÓN 2.0      ║
    ║                                                            ║
    ║  Configuración:                                            ║
    ║  • Solo videos regulares (NO shorts)                       ║
    ║  • Últimos 30 días                                         ║
    ║  • Excluye livestreams y premieres                         ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Ejecutar extracción
    extraer_comentarios(
        channel_ids=canales,
        dias_atras=30,  # Último mes
        max_comen=200,
        actualizar_videos=True
    )
    
    print("\n🎉 ¡Extracción completada!")

