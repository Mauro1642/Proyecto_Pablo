import pandas as pd
import re
import json
import os
from datetime import datetime, timedelta
import pytz
import time
import random
import yt_dlp
otros_canales=[ 'UCZ2V316UTXTyvd8w5wjA_Aw',
    'UCx6h-dWzJ5NpAlja1YsApdg',
    'UC8BxSGcBKriJvoeyKOnJ6tA',
    'UCCjG8NtOig0USdrT5D1FpxQ',
    'UCmgnsaQIK1IR808Ebde-ssA','UCPWXiRWZ29zrxPFIQT7eHSA',
    'UCqnbDFdCpuN8CMEg0VuEBqA','UCBi2mrWuNuyYy4gbM6fU18Q',
    'UCXIJgqnII2ZOINSWNOGFThA', 'UCeY0bbntWzzVIaj2z3QigXg',
    'UCw0_9Iih3qM_I_gFLrJeNRg', 'UC8p1vwvWtl6T73JiExfWs1g',
    'UCHd62-u_v4DvJ8TCFtpi4GA','UC7qZ_e097NBkgOljy1joVRA','UC2a35q7eyzkfoIusBzdH4Hw'
        'UCsCE4IMMFuwPYbwDqaz7udQ',
    'UCvAnclelY8eSq8GyPE19KTw', 'UCk2FZi3N0h8APcVBOisQCMQ',
    "UCmh7afBz-uWwOSSNTqUBAhg", ]
ap_key = "AIzaSyCnx9KNELdutZ4XJPZgWfFspQTnPmPj08M" # Esta clave no se usa con yt_dlp, pero se mantiene.
canales = [
'UCn4sPeUomNGIr26bElVdDYg'
]

# --- Funciones Auxiliares ---

def get_channel_name(channel_id):
    try:
        url = f"https://www.youtube.com/channel/{channel_id}/about"
        channel_id = channel_id.strip('"\'')
        ydl_opts = {
            #"cookiefile": "cookies.txt",
            "quiet": True,
            "skip_download": True,
            "format": "best",
            "no_warnings": True,
            "extract_flat": True,
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

# --- Función principal para obtener videos ---

def obtener_videos_recientes(channel_videos_url,
                             videos_por_dia=10,
                             dias_atras=15,
                             max_videos_canal=300,
                             random_state=None):
    """
    Obtiene videos de un canal publicados en los últimos `dias_atras` días.
    Selecciona hasta `videos_por_dia` por cada día.
    """

    if random_state is not None:
        random.seed(random_state)

    argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
    hoy = datetime.now(argentina_tz).date()
    fecha_inicio_periodo = hoy - timedelta(days=dias_atras)

    print(
        f"📅 Buscando videos desde {fecha_inicio_periodo} "
        f"hasta {hoy} ({dias_atras} días)..."
    )

    ydl_opts = {
        #"cookiefile":"cookies.txt",
        "format": "best",
        "quiet": True,
        "skip_download": True,
        "playlistend": max_videos_canal,
        "ignoreerrors": True,
        "no_warnings": True,
        "sleep_interval": 5,         
        "max_sleep_interval": 10, 
    }

    videos_por_fecha = {}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_videos_url, download=False)

        if not info or "entries" not in info:
            print("⚠️ No se pudieron obtener videos del canal.")
            return []

        for entry in info["entries"]:
            if not entry:
                continue

            # Saltar livestreams
            if entry.get("is_live"):
                continue

            upload_date = entry.get("upload_date")
            if not upload_date:
                continue

            try:
                fecha_video = datetime.strptime(upload_date, "%Y%m%d").date()
            except ValueError:
                continue

            # Filtrar por rango de fechas
            if not (fecha_inicio_periodo <= fecha_video <= hoy):
                continue

            video_id = entry.get("id")
            if not video_id:
                continue

            fecha_str = fecha_video.strftime("%Y-%m-%d")
            videos_por_fecha.setdefault(fecha_str, []).append(video_id)

    # Selección final
    print("\n📊 Videos por día:")
    videos_seleccionados = []

    for fecha in sorted(videos_por_fecha.keys(), reverse=True):
        videos_del_dia = videos_por_fecha[fecha]
        print(f"  {fecha}: {len(videos_del_dia)} videos", end="")

        # Mantener orden cronológico
        videos_del_dia = list(reversed(videos_del_dia))

        if len(videos_del_dia) > videos_por_dia:
            seleccionados = random.sample(videos_del_dia, videos_por_dia)
            print(f" → 🎲 {videos_por_dia} seleccionados")
        else:
            seleccionados = videos_del_dia
            print(" → ✓ todos")

        videos_seleccionados.extend(seleccionados)

    print(f"\n✨ Total de videos seleccionados: {len(videos_seleccionados)}\n")

    # Pausa leve para evitar rate limit
    time.sleep(random.uniform(1.5, 3.0))

    return videos_seleccionados


# --- Función Principal (extraer_comentarios) ---

def extraer_comentarios(channel_ids=canales,
                        processed_file="processed_videos.json",
                        comments_dir="data_pablo",
                        actualizar_videos=True,
                        max_comentarios=50,
                        videos_por_dia=10,
                        dias_atras=15):
    """
    Extrae comentarios de videos publicados recientemente.
    
    Parámetros:
    - channel_ids: Lista de IDs de canales
    - processed_file: Archivo con videos ya procesados
    - comments_dir: Directorio para guardar comentarios
    - actualizar_videos: Si actualizar videos ya procesados
    - max_comentarios: Cantidad máxima de comentarios por video (default: 50)
    - videos_por_dia: Cantidad de videos aleatorios por día (default: 10)
    - dias_atras: Cantidad de días hacia atrás (default: 15)
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

        # Obtener videos recientes (10 por día durante los últimos 15 días)
        print(f"\n🔍 Obteniendo videos recientes para {channel_name}...")
        print(f"   Configuración: {videos_por_dia} videos/día × {dias_atras} días")
        latest_video_ids = obtener_videos_recientes(url, videos_por_dia=videos_por_dia, dias_atras=dias_atras)
        print(f"📊 Total de videos seleccionados: {len(latest_video_ids)}\n")
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
                    #"cookiefile": "cookies.txt",
                    'quiet': True,
                    'skip_download': True,
                    "format": "best",
                    'no_warnings': True,
                    'extract_flat': False,
                    'getcomments': True,
                    'comment_limit': max_comentarios,
                    'ignoreerrors': True,
                    'force_json': False,
                    "sleep_interval": 5,          
                    "max_sleep_interval": 10, 
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
    ║     EXTRACTOR DE COMENTARIOS DE YOUTUBE - VERSIÓN 2.3      ║
    ║                                                            ║
    ║  Configuración:                                            ║
    ║  • 10 videos aleatorios por día                            ║
    ║  • Hasta 50 comentarios por video                          ║
    ║  • Últimos 15 días                                         ║
    ║  • Solo videos regulares (NO shorts)                       ║
    ║  • Excluye livestreams                                     ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Ejecutar extracción
    extraer_comentarios(
        channel_ids=canales,
        dias_atras=15,           # Últimos 15 días
        videos_por_dia=10,       # 10 videos aleatorios por día
        max_comentarios=50,      # Hasta 50 comentarios por video
        actualizar_videos=True
    )
    
    print("\n🎉 ¡Extracción completada!")