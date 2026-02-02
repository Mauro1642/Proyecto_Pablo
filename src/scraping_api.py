import json
import os
from datetime import datetime, timedelta
import pytz
import time
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# ⭐ TU API KEY ACÁ
YOUTUBE_API_KEY = 'AIzaSyDn2pqFrV_Q7pcd8EHdhzcwwnArEuF9mII' # Reemplazar con tu key

# Canales a procesar
canales = [
    "UCZfsrIV68Oegr5bJgAMLBDA"
]

otros_canales = [
    "UCZfsrIV68Oegr5bJgAMLBDA",
    'UC2a35q7eyzkfoIusBzdH4Hw',
    'UCZ2V316UTXTyvd8w5wjA_Aw',
    'UCx6h-dWzJ5NpAlja1YsApdg',
    'UC8BxSGcBKriJvoeyKOnJ6tA',
    'UCCjG8NtOig0USdrT5D1FpxQ',
    'UCmgnsaQIK1IR808Ebde-ssA',
    'UCPWXiRWZ29zrxPFIQT7eHSA',
    'UCqnbDFdCpuN8CMEg0VuEBqA',
    'UCBi2mrWuNuyYy4gbM6fU18Q',
    'UCXIJgqnII2ZOINSWNOGFThA',
    'UCeY0bbntWzzVIaj2z3QigXg',
    'UCw0_9Iih3qM_I_gFLrJeNRg',
    'UC8p1vwvWtl6T73JiExfWs1g',
    'UCHd62-u_v4DvJ8TCFtpi4GA',
    'UC7qZ_e097NBkgOljy1joVRA',
    'UCsCE4IMMFuwPYbwDqaz7udQ',
    'UCk2FZi3N0h8APcVBOisQCMQ',
    'UCvAnclelY8eSq8GyPE19KTw',
    'UCmh7afBz-uWwOSSNTqUBAhg',
    'UCn4sPeUomNGIr26bElVdDYg'
]

# ============================================================================
# INICIALIZAR CLIENTE DE YOUTUBE API
# ============================================================================

def get_youtube_client():
    """Crea y retorna un cliente de YouTube API."""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        print("✅ Cliente de YouTube API inicializado correctamente")
        return youtube
    except Exception as e:
        print(f"❌ Error al inicializar YouTube API: {e}")
        return None

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def get_channel_info(youtube, channel_id):
    """
    Obtiene información básica del canal.
    
    Args:
        youtube: Cliente de YouTube API
        channel_id: ID del canal
    
    Returns:
        dict: Información del canal o None si falla
    """
    try:
        request = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        )
        response = request.execute()
        
        if response.get('items'):
            channel = response['items'][0]
            snippet = channel['snippet']
            stats = channel['statistics']
            
            info = {
                'name': snippet['title'],
                'description': snippet.get('description', ''),
                'subscribers': stats.get('subscriberCount', 0),
                'video_count': stats.get('videoCount', 0),
                'view_count': stats.get('viewCount', 0)
            }
            
            print(f"✅ Canal: {info['name']}")
            print(f"   📊 Suscriptores: {int(info['subscribers']):,}")
            print(f"   🎬 Videos: {info['video_count']}")
            
            return info
        else:
            print(f"⚠️ No se encontró el canal {channel_id}")
            return None
            
    except HttpError as e:
        print(f"❌ Error HTTP al obtener info del canal: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None


def get_channel_videos(youtube, channel_id, max_results=50, dias_atras=15):
    """
    Obtiene videos recientes de un canal.
    
    Args:
        youtube: Cliente de YouTube API
        channel_id: ID del canal
        max_results: Máximo de videos a obtener
        dias_atras: Días hacia atrás desde hoy
    
    Returns:
        list: Lista de videos con su información
    """
    videos = []
    
    # Calcular fecha de inicio
    argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
    fecha_inicio = (datetime.now(argentina_tz) - timedelta(days=dias_atras)).isoformat()
    
    try:
        # Obtener ID de playlist de uploads del canal
        request = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        response = request.execute()
        
        if not response.get('items'):
            print(f"⚠️ No se encontró el canal {channel_id}")
            return videos
        
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Obtener videos de la playlist
        next_page_token = None
        
        while len(videos) < max_results:
            request = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response.get('items', []):
                snippet = item['snippet']
                
                # Verificar fecha de publicación
                published_at = snippet['publishedAt']
                if published_at < fecha_inicio:
                    # Ya pasamos la fecha límite
                    return videos
                
                video_id = snippet['resourceId']['videoId']
                
                video_info = {
                    'video_id': video_id,
                    'title': snippet['title'],
                    'description': snippet.get('description', ''),
                    'published_at': published_at,
                    'thumbnail': snippet['thumbnails'].get('default', {}).get('url', '')
                }
                
                videos.append(video_info)
                
                if len(videos) >= max_results:
                    break
            
            next_page_token = response.get('nextPageToken')
            
            if not next_page_token:
                break
            
            # Pequeña pausa entre requests
            time.sleep(0.5)
        
        print(f"📊 Encontrados {len(videos)} videos en los últimos {dias_atras} días")
        return videos
        
    except HttpError as e:
        print(f"❌ Error HTTP al obtener videos: {e}")
        return videos
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return videos


def get_video_details(youtube, video_ids):
    """
    Obtiene detalles de múltiples videos (estadísticas, duración, etc).
    
    Args:
        youtube: Cliente de YouTube API
        video_ids: Lista de IDs de videos
    
    Returns:
        dict: Diccionario {video_id: detalles}
    """
    video_details = {}
    
    # API permite hasta 50 IDs por request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        
        try:
            request = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch)
            )
            response = request.execute()
            
            for item in response.get('items', []):
                video_id = item['id']
                snippet = item['snippet']
                stats = item['statistics']
                content = item['contentDetails']
                
                # Parsear duración ISO 8601
                duration_str = content['duration']
                duration_seconds = parse_duration(duration_str)
                
                video_details[video_id] = {
                    'title': snippet['title'],
                    'published_at': snippet['publishedAt'],
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments_count': int(stats.get('commentCount', 0)),
                    'duration': duration_seconds,
                    'is_short': duration_seconds < 61  # Shorts son < 61 segundos
                }
            
            # Pausa entre batches
            time.sleep(0.5)
            
        except HttpError as e:
            print(f"❌ Error HTTP al obtener detalles: {e}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    return video_details


def parse_duration(duration_str):
    """
    Convierte duración ISO 8601 (PT1H2M3S) a segundos.
    
    Args:
        duration_str: String en formato ISO 8601
    
    Returns:
        int: Duración en segundos
    """
    import re
    
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def get_video_comments(youtube, video_id, max_comments=50):
    """
    Obtiene comentarios de un video.
    
    Args:
        youtube: Cliente de YouTube API
        video_id: ID del video
        max_comments: Máximo de comentarios a obtener
    
    Returns:
        dict: Diccionario de comentarios {comment_id: datos}
    """
    comentarios = {}
    next_page_token = None
    
    try:
        while len(comentarios) < max_comments:
            request = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(100, max_comments - len(comentarios)),
                order='relevance',  # Comentarios más relevantes primero
                textFormat='plainText',
                pageToken=next_page_token
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                comment_id = item['snippet']['topLevelComment']['id']
                
                comentarios[comment_id] = {
                    'texto': comment['textDisplay'],
                    'fecha': comment['publishedAt'],
                    'likes': comment.get('likeCount', 0),
                    'autor': comment['authorDisplayName']
                }
                
                if len(comentarios) >= max_comments:
                    break
            
            next_page_token = response.get('nextPageToken')
            
            if not next_page_token:
                break
            
            # Pausa entre requests
            time.sleep(0.5)
        
        return comentarios
        
    except HttpError as e:
        error_reason = e.resp.get('reason', '')
        
        if e.resp.status == 403:
            if 'commentsDisabled' in str(e):
                print(f"ℹ️ Comentarios deshabilitados en este video")
            else:
                print(f"⚠️ Cuota API excedida o sin permisos: {e}")
        else:
            print(f"❌ Error HTTP al obtener comentarios: {e}")
        
        return comentarios
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return comentarios


# ============================================================================
# FUNCIÓN PRINCIPAL DE EXTRACCIÓN
# ============================================================================

def extraer_comentarios_api(channel_ids=canales,
                           processed_file="processed_videos.json",
                           comments_dir="data_pablo",
                           actualizar_videos=True,
                           max_comentarios=50,
                           videos_por_dia=10,
                           dias_atras=15,
                           max_videos_total=300):
    """
    Extrae comentarios usando YouTube Data API v3.
    
    IMPORTANTE: La API tiene límites de cuota:
    - 10,000 unidades por día (default gratuito)
    - Cada operación consume unidades diferentes:
      * list videos: 1 unidad
      * list comments: 1 unidad
      * list playlists: 1 unidad
    
    Parámetros:
    - channel_ids: Lista de IDs de canales
    - processed_file: Archivo con videos procesados
    - comments_dir: Directorio para guardar comentarios
    - actualizar_videos: Si actualizar videos ya procesados
    - max_comentarios: Máximo de comentarios por video
    - videos_por_dia: Videos por día a procesar
    - dias_atras: Días hacia atrás
    - max_videos_total: Máximo total de videos del canal
    """
    
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║     EXTRACTOR DE COMENTARIOS - YOUTUBE API v3              ║
    ║                                                            ║
    ║  📊 Configuración:                                         ║
    ║  • {max_comentarios} comentarios por video                           ║
    ║  • {videos_por_dia} videos por día                                  ║
    ║  • {dias_atras} días hacia atrás                                 ║
    ║  • Max {max_videos_total} videos del canal                        ║
    ║                                                            ║
    ║  ⚠️ LÍMITES DE API:                                        ║
    ║  • 10,000 unidades/día (cuota gratuita)                    ║
    ║  • ~200-300 videos con comentarios por día                 ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Inicializar cliente
    youtube = get_youtube_client()
    if not youtube:
        print("❌ No se pudo inicializar la API de YouTube")
        return
    
    # Cargar videos procesados
    if os.path.exists(processed_file):
        try:
            with open(processed_file, "r", encoding="utf-8") as f:
                processed_videos = json.load(f)
        except Exception as e:
            print(f"⚠️ Error al cargar {processed_file}: {e}")
            processed_videos = {}
    else:
        processed_videos = {}
    
    total_canales = len(channel_ids)
    
    for idx_canal, channel_id in enumerate(channel_ids, 1):
        print(f"\n{'='*80}")
        print(f"🎯 CANAL {idx_canal}/{total_canales}: {channel_id}")
        print(f"{'='*80}\n")
        
        # Obtener información del canal
        channel_info = get_channel_info(youtube, channel_id)
        if not channel_info:
            print(f"⚠️ Saltando canal {channel_id}")
            continue
        
        channel_name = channel_info['name']
        
        # Preparar archivo de comentarios
        canal_comments_file = os.path.join(comments_dir, f"comentarios_{channel_name}.json")
        
        if os.path.exists(canal_comments_file):
            try:
                with open(canal_comments_file, "r", encoding="utf-8") as f:
                    canal_comments = json.load(f)
                print(f"📂 Cargados {len(canal_comments)} videos existentes")
            except Exception as e:
                print(f"⚠️ Error al cargar: {e}")
                canal_comments = {}
        else:
            canal_comments = {}
        
        # Obtener videos del canal
        print(f"\n🔍 Obteniendo videos del canal...")
        videos = get_channel_videos(youtube, channel_id, max_videos_total, dias_atras)
        
        if not videos:
            print(f"⚠️ No se encontraron videos")
            continue
        
        # Filtrar por fecha y seleccionar aleatoriamente
        argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
        hoy = datetime.now(argentina_tz).date()
        fecha_inicio = hoy - timedelta(days=dias_atras)
        
        videos_por_fecha = {}
        
        for video in videos:
            fecha_pub = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
            fecha_pub_date = fecha_pub.date()
            
            if fecha_inicio <= fecha_pub_date <= hoy:
                fecha_str = fecha_pub_date.strftime("%Y-%m-%d")
                videos_por_fecha.setdefault(fecha_str, []).append(video['video_id'])
        
        # Seleccionar videos_por_dia de cada fecha
        print(f"\n📊 Videos por día:")
        videos_seleccionados = []
        
        for fecha in sorted(videos_por_fecha.keys(), reverse=True):
            videos_del_dia = videos_por_fecha[fecha]
            print(f"  {fecha}: {len(videos_del_dia)} videos", end="")
            
            if len(videos_del_dia) > videos_por_dia:
                seleccionados = random.sample(videos_del_dia, videos_por_dia)
                print(f" → 🎲 {videos_por_dia} seleccionados")
            else:
                seleccionados = videos_del_dia
                print(" → ✅ todos")
            
            videos_seleccionados.extend(seleccionados)
        
        print(f"\n✨ Total seleccionados: {len(videos_seleccionados)}")
        
        # Obtener detalles de los videos
        print(f"\n📋 Obteniendo detalles de videos...")
        video_details = get_video_details(youtube, videos_seleccionados)
        
        # Filtrar shorts
        videos_sin_shorts = []
        shorts_filtrados = 0
        
        for video_id in videos_seleccionados:
            details = video_details.get(video_id)
            if details and not details['is_short']:
                videos_sin_shorts.append(video_id)
            elif details and details['is_short']:
                shorts_filtrados += 1
        
        print(f"⏭️ Filtrados {shorts_filtrados} shorts")
        print(f"📦 Videos a procesar: {len(videos_sin_shorts)}")
        
        # Procesar comentarios
        contador_exitosos = 0
        contador_errores = 0
        
        print(f"\n💬 Extrayendo comentarios...\n")
        
        for idx, video_id in enumerate(videos_sin_shorts, 1):
            print(f"[{idx}/{len(videos_sin_shorts)}] 🎬 {video_id}")
            
            details = video_details.get(video_id, {})
            print(f"   📊 {details.get('views', 0):,} views | "
                  f"{details.get('likes', 0):,} likes | "
                  f"{details.get('comments_count', 0):,} comentarios disponibles")
            
            # Obtener comentarios
            comentarios = get_video_comments(youtube, video_id, max_comentarios)
            
            if comentarios:
                # Guardar en estructura
                canal_comments[video_id] = {
                    '_metrics': {
                        'views': details.get('views', 0),
                        'likes': details.get('likes', 0),
                        'comments_count': details.get('comments_count', 0),
                        'duration': details.get('duration', 0)
                    },
                    **comentarios
                }
                
                print(f"   ✅ {len(comentarios)} comentarios extraídos")
                contador_exitosos += 1
            else:
                print(f"   ⚠️ Sin comentarios")
                contador_errores += 1
            
            # Guardar progreso cada 10 videos
            if idx % 10 == 0:
                print(f"\n💾 Guardando progreso...")
                os.makedirs(comments_dir, exist_ok=True)
                with open(canal_comments_file, "w", encoding="utf-8") as f:
                    json.dump(canal_comments, f, ensure_ascii=False, indent=2)
            
            # Pequeña pausa
            time.sleep(0.5)
        
        # Guardar final
        print(f"\n💾 Guardando archivo final...")
        os.makedirs(comments_dir, exist_ok=True)
        with open(canal_comments_file, "w", encoding="utf-8") as f:
            json.dump(canal_comments, f, ensure_ascii=False, indent=2)
        
        # Resumen
        print(f"\n{'─'*60}")
        print(f"📊 RESUMEN - {channel_name}")
        print(f"{'─'*60}")
        print(f"   ✅ Videos exitosos:  {contador_exitosos}")
        print(f"   ⚠️ Sin comentarios:  {contador_errores}")
        print(f"   💾 Total en archivo: {len(canal_comments)}")
        
        # Actualizar processed_videos
        processed_videos[channel_name] = list(canal_comments.keys())
        
        # Pausa entre canales
        if idx_canal < total_canales:
            print(f"\n⏸️ Pausando 30 segundos antes del siguiente canal...")
            time.sleep(30)
    
    # Guardar progreso global
    with open(processed_file, "w", encoding="utf-8") as f:
        json.dump(processed_videos, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✨ PROCESO COMPLETADO")
    print(f"{'='*80}\n")


# ============================================================================
# EXTRACCIÓN DE USUARIOS
# ============================================================================

def usuarios_canal(input_dir="data_pablo", output_dir="usuarios_por_canal"):
    """Extrae usuarios únicos por video."""
    
    print(f"\n{'='*80}")
    print(f"👥 EXTRAYENDO USUARIOS POR CANAL")
    print(f"{'='*80}\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    for archivo in os.listdir(input_dir):
        if not archivo.endswith(".json"):
            continue
        
        ruta = os.path.join(input_dir, archivo)
        
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
        
        canal_nombre = archivo.replace("comentarios_", "").replace(".json", "")
        salida = os.path.join(output_dir, f"usuarios_{canal_nombre}.json")
        
        canal_data = {}
        
        for video_id, video_data in data.items():
            if video_id == "_metrics":
                continue
            
            usuarios = set()
            
            for comment_id, comment_data in video_data.items():
                if comment_id == "_metrics":
                    continue
                
                if isinstance(comment_data, dict):
                    autor = comment_data.get('autor')
                    if autor:
                        usuarios.add(autor)
            
            canal_data[video_id] = sorted(list(usuarios))
        
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(canal_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {canal_nombre}: {len(canal_data)} videos procesados")
    
    print(f"\n✨ Usuarios extraídos correctamente\n")


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    
    # Verificar que tenés API key
    if YOUTUBE_API_KEY == "TU_API_KEY_AQUI":
        print("""
        ╔════════════════════════════════════════════════════════════╗
        ║                    ⚠️ API KEY FALTANTE                     ║
        ╚════════════════════════════════════════════════════════════╝
        
        Para usar este script necesitás una YouTube API Key:
        
        1. Andá a: https://console.cloud.google.com/
        2. Creá un proyecto
        3. Habilitá "YouTube Data API v3"
        4. Creá credenciales → API Key
        5. Copiá la key y pegala en YOUTUBE_API_KEY
        
        """)
    else:
        try:
            # Ejecutar extracción
            extraer_comentarios_api(
                channel_ids=canales,
                dias_atras=15,
                videos_por_dia=10,
                max_comentarios=50,
                actualizar_videos=False,
                max_videos_total=150
            )
            
            print("\n🎉 ¡Extracción completada!")
            
            # Extraer usuarios
            respuesta = input("\n¿Extraer usuarios por canal? (s/n): ")
            if respuesta.lower() == 's':
                usuarios_canal()
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Proceso interrumpido")
        except Exception as e:
            print(f"\n❌ Error: {e}")


def usuarios_canal(input_dir="data_pablo", output_dir="usuarios_por_canal"):
    os.makedirs(output_dir, exist_ok=True)

    for archivo in os.listdir(input_dir):
        if archivo.endswith(".json"):
            ruta = os.path.join(input_dir, archivo)

            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Inferimos canal a partir del nombre del archivo (ej: comentarios_NombreCanal.json)
            # Ajustar para que el nombre del canal sea correcto si tiene espacios, etc.
            canal_nombre_archivo = os.path.splitext(archivo)[0].replace("comentarios_", "")
            salida = os.path.join(output_dir, f"{canal_nombre_archivo}.json")

            if os.path.exists(salida):
                with open(salida, "r", encoding="utf-8") as f:
                    canal_data = json.load(f)
            else:
                canal_data = {}
            
            # Obtener solo las claves que son IDs de video (excluyendo _metrics)
            id_videos = [k for k in data.keys() if k != "_metrics"]

            for video in id_videos:
                usuarios = set(canal_data.get(video, []))

                # Obtener las claves que son IDs de comentario (excluyendo _metrics)
                comentarios_del_video = data[video].keys()
                for comentario_key in comentarios_del_video:
                    if comentario_key != "_metrics":
                        autor = data[video][comentario_key]["autor"]
                        usuarios.add(autor)

                canal_data[video] = list(usuarios)
            
            with open(salida, "w", encoding="utf-8") as f:
                json.dump(canal_data, f, ensure_ascii=False, indent=2)