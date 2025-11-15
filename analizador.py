import os
import sqlite3
from datetime import datetime
from google.cloud import vision
<<<<<<< HEAD
from PIL import Image, ImageDraw, ImageFont
=======
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5

# Ruta al JSON de credenciales
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'hackaton-segiridad-500d3a7a5a64.json'


# ------------------ BASE DE DATOS ------------------ #

DB_PATH = "alertas.db"

def init_db():
    """Crea la base de datos y la tabla si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            imagen TEXT NOT NULL,
<<<<<<< HEAD
            tipo TEXT NOT NULL,
=======
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
            objeto TEXT NOT NULL,
            confianza REAL NOT NULL,
            x1 REAL,
            y1 REAL,
            x2 REAL,
<<<<<<< HEAD
            y2 REAL,
            ubicacion TEXT
        )
    """)
    
    # Migración: agregar columna 'tipo' si no existe
    try:
        cur.execute("ALTER TABLE alertas ADD COLUMN tipo TEXT")
        # Si la tabla ya tenía datos, actualizar los tipos basándose en el objeto
        cur.execute("""
            UPDATE alertas 
            SET tipo = CASE 
                WHEN objeto LIKE 'incendio:%' THEN 'incendio'
                WHEN objeto IN ('gun', 'knife', 'weapon', 'firearm', 'rifle') 
                     OR objeto LIKE '%gun%' OR objeto LIKE '%knife%' 
                     OR objeto LIKE '%weapon%' OR objeto LIKE '%firearm%' 
                     OR objeto LIKE '%rifle%' THEN 'arma'
                ELSE 'otro'
            END
            WHERE tipo IS NULL
        """)
        conn.commit()
    except sqlite3.OperationalError:
        # La columna ya existe, no hacer nada
        pass
    
    # Migración: agregar columna 'ubicacion' si no existe
    try:
        cur.execute("ALTER TABLE alertas ADD COLUMN ubicacion TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # La columna ya existe, no hacer nada
        pass
    
    conn.commit()
    conn.close()

def guardar_alerta(imagen, tipo, objeto, confianza, x1=None, y1=None, x2=None, y2=None, ubicacion=None):
    """Guarda una alerta en la base de datos y envía notificaciones si es crítica."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alertas (fecha_hora, imagen, tipo, objeto, confianza, x1, y1, x2, y2, ubicacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        imagen,
        tipo,
        objeto,
        confianza,
        x1, y1, x2, y2,
        ubicacion
    ))
    conn.commit()
    conn.close()
    
    # Enviar alerta a destinatarios si es crítica (arma, incendio o agresión con confianza >= 50%)
    if tipo in ['arma', 'incendio', 'agresion'] and confianza >= 0.50 and ubicacion:
        try:
            # Importación condicional para evitar importación circular
            import sys
            if 'app' in sys.modules:
                from app import enviar_alerta_ubicacion
                enviar_alerta_ubicacion(ubicacion, tipo, objeto, confianza, imagen)
        except Exception as e:
            print(f"[ERROR] No se pudo enviar alerta: {e}")

# ------------------ ANÁLISIS DE IMÁGENES ------------------ #

def dibujar_bounding_boxes(ruta_imagen, detecciones, ruta_salida=None):
    """
    Dibuja bounding boxes en la imagen y guarda una versión anotada.
    
    Args:
        ruta_imagen: Ruta de la imagen original
        detecciones: Lista de tuplas (tipo, objeto, confianza, x1, y1, x2, y2)
        ruta_salida: Ruta donde guardar la imagen anotada (None = auto-generar)
    
    Returns:
        Ruta de la imagen guardada
    """
    # Leer imagen con PIL para mejor compatibilidad
    img = Image.open(ruta_imagen)
    draw = ImageDraw.Draw(img)
    
    # Colores por tipo de amenaza
    colores = {
        'arma': (255, 0, 0),      # Rojo
        'incendio': (255, 165, 0), # Naranja
        'vehiculo': (255, 255, 0), # Amarillo
        'otro': (0, 0, 255)        # Azul
    }
    
    # Obtener dimensiones de la imagen
    width, height = img.size
    
    for tipo, objeto, confianza, x1, y1, x2, y2 in detecciones:
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue  # Saltar si no hay coordenadas
        
        # Convertir coordenadas normalizadas a píxeles
        x1_px = int(x1 * width)
        y1_px = int(y1 * height)
        x2_px = int(x2 * width)
        y2_px = int(y2 * height)
        
        # Color según tipo
        color = colores.get(tipo, colores['otro'])
        
        # Dibujar rectángulo
        draw.rectangle([x1_px, y1_px, x2_px, y2_px], outline=color, width=3)
        
        # Dibujar etiqueta con fondo
        etiqueta = f"{objeto} ({confianza:.2f})"
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Obtener tamaño del texto
        bbox = draw.textbbox((0, 0), etiqueta, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Fondo para el texto
        draw.rectangle(
            [x1_px, y1_px - text_height - 4, x1_px + text_width + 4, y1_px],
            fill=color
        )
        
        # Texto
        draw.text((x1_px + 2, y1_px - text_height - 2), etiqueta, fill=(255, 255, 255), font=font)
    
    # Guardar imagen
    if ruta_salida is None:
        nombre_base = os.path.splitext(ruta_imagen)[0]
        ruta_salida = f"{nombre_base}_anotada.jpg"
    
    img.save(ruta_salida)
    return ruta_salida


def detectar_amenazas(ruta_imagen, generar_imagen_anotada=True, ubicacion=None):
    """
    Detecta amenazas en una imagen: armas, incendios y vehículos sospechosos.
    
    Args:
        ruta_imagen: Ruta de la imagen a analizar
        generar_imagen_anotada: Si True, genera una imagen con bounding boxes dibujados
        ubicacion: Ubicación donde se tomó la imagen (opcional)
    """
=======
            y2 REAL
        )
    """)
    conn.commit()
    conn.close()

def guardar_alerta(imagen, objeto, confianza, x1, y1, x2, y2):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alertas (fecha_hora, imagen, objeto, confianza, x1, y1, x2, y2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        imagen,
        objeto,
        confianza,
        x1, y1, x2, y2
    ))
    conn.commit()
    conn.close()

# ------------------ ANÁLISIS DE IMÁGENES ------------------ #
def detectar_amenazas(ruta_imagen):
    """Detecta personas, armas y objetos peligrosos en una imagen."""
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5

    cliente = vision.ImageAnnotatorClient()

    with open(ruta_imagen, 'rb') as f:
        content = f.read()

    image = vision.Image(content=content)

<<<<<<< HEAD
    # Detección de objetos (ARMAS / PERSONAS / VEHÍCULOS)
=======
    # Detección de objetos (ARMAS / PERSONAS)
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
    respuesta = cliente.object_localization(image=image)

    print("\n--- RESULTADOS DEL OJO DE DIOS ---")

    alerta = False
<<<<<<< HEAD
    detecciones = []  # Lista para almacenar todas las detecciones para dibujar

    # Lista de objetos peligrosos que queremos detectar
    OBJETOS_PELIGROSOS = [
        "gun", "knife", "weapon", "firearm", "rifle", "pistol", "sword",
        "blade", "cutting tool", "kitchen knife", "dagger", "machete",
        "scalpel", "razor", "bayonet"
    ]
    
    # Vehículos sospechosos (pueden ser usados para ataques)
    VEHICULOS_SOSPECHOSOS = ["truck", "van", "suv", "vehicle", "car", "automobile"]

    for obj in respuesta.localized_object_annotations:
        nombre = obj.name.lower()
        score = obj.score
        box = obj.bounding_poly.normalized_vertices
        x1, y1 = box[0].x, box[0].y
        x2, y2 = box[2].x, box[2].y

        # (A) Si detecta persona (informativo)
        if "person" in nombre:
            print(f"[OK] Persona detectada (confianza: {score:.2f})")
=======

    # Lista de objetos peligrosos que queremos detectar
    OBJETOS_PELIGROSOS = ["gun", "knife", "weapon", "firearm", "rifle"]

    for obj in respuesta.localized_object_annotations:
        nombre = obj.name.lower()

        # (A) Si detecta persona (informativo)
        if "person" in nombre:
            print(f"[OK] Persona detectada (confianza: {obj.score:.2f})")
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5

        # (B) Si detecta un arma (ALERTA)
        for peligro in OBJETOS_PELIGROSOS:
            if peligro in nombre:
                alerta = True
<<<<<<< HEAD
=======
                score = obj.score
                box = obj.bounding_poly.normalized_vertices
                x1, y1 = box[0].x, box[0].y
                x2, y2 = box[2].x, box[2].y

>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
                print(f"\n🚨 ALERTA PELIGROSA (ARMA) 🚨")
                print(f"Objeto detectado: {nombre.upper()}")
                print(f"Confianza: {score:.2f}")
                print(f"Coordenadas: {x1:.2f},{y1:.2f} → {x2:.2f},{y2:.2f}")
                print("----------------------------------")

<<<<<<< HEAD
                guardar_alerta(
                    imagen=ruta_imagen,
                    tipo="arma",
                    objeto=nombre,
                    confianza=score,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    ubicacion=ubicacion
                )
                detecciones.append(("arma", nombre, score, x1, y1, x2, y2))
                break

        # (C) Detección de vehículos sospechosos
        for vehiculo in VEHICULOS_SOSPECHOSOS:
            if vehiculo in nombre and score >= 0.60:
                alerta = True
                print(f"\n⚠️ ALERTA: VEHÍCULO SOSPECHOSO ⚠️")
                print(f"Vehículo detectado: {nombre.upper()}")
                print(f"Confianza: {score:.2f}")
                print(f"Coordenadas: {x1:.2f},{y1:.2f} → {x2:.2f},{y2:.2f}")
                print("----------------------------------")

                guardar_alerta(
                    imagen=ruta_imagen,
                    tipo="vehiculo",
                    objeto=nombre,
                    confianza=score,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    ubicacion=ubicacion
                )
                detecciones.append(("vehiculo", nombre, score, x1, y1, x2, y2))
                break

    # ================================
    # 🔥 DETECCIÓN DE INCENDIO
=======
                # Guarda arma en la BD (como antes)
                guardar_alerta(
                    imagen=ruta_imagen,
                    objeto=nombre,
                    confianza=score,
                    x1=x1, y1=y1, x2=x2, y2=y2
                )

    # ================================
    # 🔥 NUEVO: DETECCIÓN DE INCENDIO
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
    # ================================
    PATRONES_INCENDIO = [
        "fire", "flames", "flame", "smoke",
        "wildfire", "conflagration", "explosion", "burning"
    ]
<<<<<<< HEAD
    
    # ================================
    # ⚔️ DETECCIÓN DE AGRESIÓN (MEJORADA)
    # ================================
    PATRONES_AGRESION_DIRECTOS = [
        "violence", "aggression", "aggressive", "fight", "fighting",
        "assault", "attack", "conflict", "combat", "brawl",
        "altercation", "struggle", "hostility", "hostile",
        "physical violence", "physical altercation", "physical conflict",
        "punch", "punching", "hitting", "striking", "kicking",
        "wrestling", "grappling", "scuffle", "tussle", "melee"
    ]
    
    PATRONES_AGRESION_CONTEXTO = [
        "action", "tension", "drama", "martial arts", "boxing",
        "self defense", "defense", "street", "urban", "outdoor",
        "person", "people", "crowd", "group", "gathering"
    ]
    
    PATRONES_POSTURAS_AGRESIVAS = [
        "lying", "lying down", "on ground", "ground", "floor",
        "standing", "over", "above", "leaning", "bending",
        "arm", "arms", "raised", "extended", "outstretched"
    ]
    
    # Detectar múltiples personas (puede indicar pelea)
    personas_detectadas = 0
    personas_en_suelo = 0
    personas_de_pie = 0
    
    for obj in respuesta.localized_object_annotations:
        nombre_obj = obj.name.lower()
        if "person" in nombre_obj:
            personas_detectadas += 1
            # Intentar detectar postura (esto es aproximado)
            box = obj.bounding_poly.normalized_vertices
            if len(box) >= 4:
                altura_obj = abs(box[2].y - box[0].y)
                posicion_y = (box[0].y + box[2].y) / 2
                # Si está en la parte inferior de la imagen, probablemente está en el suelo
                if posicion_y > 0.7:  # Parte inferior de la imagen
                    personas_en_suelo += 1
                else:
                    personas_de_pie += 1

    resp_labels = cliente.label_detection(image=image)
    
    # Modo debug: mostrar todas las etiquetas detectadas (SIEMPRE activo para diagnóstico)
    print("\n[DEBUG] Etiquetas detectadas por Google Vision:")
    todas_las_etiquetas = []
    for label in resp_labels.label_annotations[:25]:  # Primeras 25
        desc_lower = label.description.lower()
        todas_las_etiquetas.append((desc_lower, label.score))
        print(f"  - {label.description}: {label.score:.3f}")
        # Resaltar si alguna coincide con patrones de agresión
        if any(palabra in desc_lower for palabra in PATRONES_AGRESION_DIRECTOS):
            print(f"    ⚠️ COINCIDE CON PATRÓN DE AGRESIÓN DIRECTA!")
        elif any(palabra in desc_lower for palabra in PATRONES_AGRESION_CONTEXTO):
            print(f"    ⚠️ COINCIDE CON PATRÓN DE CONTEXTO DE AGRESIÓN!")
    
    print(f"\n[DEBUG] Personas detectadas: {personas_detectadas}")
    print(f"[DEBUG] Personas en suelo: {personas_en_suelo}, Personas de pie: {personas_de_pie}")

    resp_labels = cliente.label_detection(image=image)

    # Estrategia 1: Detección directa de agresión (umbral bajo: 0.40)
    agresion_detectada = False
    confianza_agresion = 0.0
    descripcion_agresion = ""
    
=======

    resp_labels = cliente.label_detection(image=image)

>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
    for label in resp_labels.label_annotations:
        desc = label.description.lower()
        score = label.score

<<<<<<< HEAD
        # Umbral muy bajo para agresión directa
        if score >= 0.40:
            for palabra in PATRONES_AGRESION_DIRECTOS:
                if palabra in desc:
                    agresion_detectada = True
                    confianza_agresion = max(confianza_agresion, score)
                    descripcion_agresion = desc
                    break
    
    # Estrategia 2: Detección por contexto (múltiples personas + etiquetas de acción)
    if not agresion_detectada and personas_detectadas >= 2:
        etiquetas_accion = []
        confianza_total = 0.0
        
        for desc, score in todas_las_etiquetas:
            if score >= 0.35:  # Umbral muy bajo
                # Buscar etiquetas de acción/tensión
                if any(palabra in desc for palabra in ["action", "tension", "drama", "movement", "motion"]):
                    etiquetas_accion.append(desc)
                    confianza_total += score
                # Buscar posturas agresivas
                if any(palabra in desc for palabra in PATRONES_POSTURAS_AGRESIVAS):
                    etiquetas_accion.append(desc)
                    confianza_total += score * 0.5
        
        if len(etiquetas_accion) >= 2:
            # Si hay múltiples personas y varias etiquetas de acción, es probable agresión
            confianza_calculada = min(0.75, (confianza_total / len(etiquetas_accion)) + 0.2)
            agresion_detectada = True
            confianza_agresion = confianza_calculada
            descripcion_agresion = f"conflicto detectado ({', '.join(etiquetas_accion[:3])})"
    
    # Estrategia 3: Detección por posturas (persona en suelo + persona de pie)
    if not agresion_detectada and personas_en_suelo >= 1 and personas_de_pie >= 1:
        # Si hay una persona en el suelo y otra de pie, es muy probable agresión
        agresion_detectada = True
        confianza_agresion = 0.65
        descripcion_agresion = "persona en suelo con otra persona de pie (posible agresión)"
    
    # Guardar alerta si se detectó agresión
    if agresion_detectada:
        alerta = True
        print(f"\n⚔️🚨 ALERTA DE AGRESIÓN 🚨⚔️")
        print(f"Etiqueta/Contexto detectado: {descripcion_agresion.upper()}")
        print(f"Confianza: {confianza_agresion:.2f}")
        print(f"Personas detectadas: {personas_detectadas} (en suelo: {personas_en_suelo}, de pie: {personas_de_pie})")
        print("----------------------------------")

        guardar_alerta(
            imagen=ruta_imagen,
            tipo="agresion",
            objeto=descripcion_agresion,
            confianza=confianza_agresion,
            x1=None, y1=None, x2=None, y2=None,
            ubicacion=ubicacion
        )
        detecciones.append(("agresion", descripcion_agresion, confianza_agresion, None, None, None, None))
    
    # Detectar incendio (después de agresión)
    for label in resp_labels.label_annotations:
        desc = label.description.lower()
        score = label.score
        
        if score >= 0.70:
            for palabra in PATRONES_INCENDIO:
                if palabra in desc:
                    alerta = True
                    print(f"\n🔥🚨 ALERTA DE INCENDIO 🚨🔥")
                    print(f"Etiqueta detectada: {desc.upper()}")
                    print(f"Confianza: {score:.2f}")
                    print("----------------------------------")

                    guardar_alerta(
                        imagen=ruta_imagen,
                        tipo="incendio",
                        objeto=desc,
                        confianza=score,
                        x1=None, y1=None, x2=None, y2=None,
                        ubicacion=ubicacion
                    )
                    # Para incendios no hay bounding box, pero lo agregamos a detecciones sin coordenadas
                    detecciones.append(("incendio", desc, score, None, None, None, None))
                    break

    # Generar imagen anotada si hay detecciones
    if generar_imagen_anotada and detecciones:
        try:
            ruta_anotada = dibujar_bounding_boxes(ruta_imagen, detecciones)
            print(f"\n📸 Imagen anotada guardada en: {ruta_anotada}")
        except Exception as e:
            print(f"\n⚠️ Error al generar imagen anotada: {e}")

    # Mensaje final
    if alerta:
        print("\n🔥 *** ALERTA ROJA: AMENAZA DETECTADA *** 🔥\n")
    else:
        print("\n✔️ Imagen analizada: No se detectaron amenazas.\n")
    
    return detecciones
=======
        # Ignoramos etiquetas con baja confianza
        if score < 0.70:
            continue

        for palabra in PATRONES_INCENDIO:
            if palabra in desc:
                alerta = True
                print(f"\n🔥🚨 ALERTA DE INCENDIO 🚨🔥")
                print(f"Etiqueta detectada: {desc.upper()}")
                print(f"Confianza: {score:.2f}")
                print("----------------------------------")

                # No hay bounding box, guardamos coordenadas como None
                guardar_alerta(
                    imagen=ruta_imagen,
                    objeto=f"incendio:{desc}",
                    confianza=score,
                    x1=None, y1=None, x2=None, y2=None
                )
                # Para no repetir la misma etiqueta muchas veces
                break

    # Mensaje final (NO lo toqué, solo amplía la condición)
    if alerta:
        print("\n🔥 *** ALERTA ROJA: AMENAZA DETECTADA (ARMA Y/O INCENDIO) *** 🔥\n")
    else:
        print("\n✔️ Imagen analizada: No se detectaron amenazas.\n")
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5



if __name__ == "__main__":
<<<<<<< HEAD
    import sys
    
    init_db()
    
    # Permite pasar la imagen como argumento
    if len(sys.argv) > 1:
        ruta_imagen = sys.argv[1]
    else:
        ruta_imagen = "prueba.jpg"
    
    if not os.path.exists(ruta_imagen):
        print(f"❌ Error: No se encontró la imagen '{ruta_imagen}'")
        sys.exit(1)
    
    detectar_amenazas(ruta_imagen)
=======
    init_db()
    detectar_amenazas("pruebaimg.jpeg")
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5


