import os
import cv2
import numpy as np
from datetime import datetime
from google.cloud import vision

# Ruta al JSON de credenciales
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'hackaton-segiridad-500d3a7a5a64.json'

# Importar funciones del analizador
from analizador import init_db, guardar_alerta

# ------------------ CONFIGURACIÓN ------------------ #
DB_PATH = "alertas.db"
FRAME_INTERVAL = 2  # Analizar cada N segundos (para no saturar la API)
UMBRAL_CONFIANZA_INCENDIO = 0.50  # Reducido para detectar llamas pequeñas
UMBRAL_CONFIANZA_ARMA = 0.50
UMBRAL_CONFIANZA_VEHICULO = 0.60
UMBRAL_CONFIANZA_AGRESION = 0.50  # Umbral para detectar agresión (reducido para mayor sensibilidad)
MODO_DEBUG = False  # Activar para ver todas las etiquetas detectadas

# Colores para dibujar en el video
COLORES = {
    'arma': (0, 0, 255),        # Rojo (BGR)
    'incendio': (0, 165, 255),  # Naranja
    'vehiculo': (0, 255, 255),  # Amarillo
    'agresion': (255, 0, 255),  # Magenta
    'persona': (0, 255, 0)       # Verde
}

# ------------------ FUNCIONES DE DETECCIÓN ------------------ #

def detectar_fuego_por_color(frame_rgb, umbral_pixeles=150, umbral_porcentaje=0.3):
    """
    Detecta fuego analizando colores rojo/naranja/amarillo brillantes en el frame.
    Versión balanceada: detecta fuego real pero evita falsos positivos.
    
    Args:
        frame_rgb: Frame en formato RGB
        umbral_pixeles: Número mínimo de píxeles de color fuego (ajustado para llamas pequeñas)
        umbral_porcentaje: Porcentaje mínimo del frame que debe ser fuego
    
    Returns:
        (detectado, porcentaje, bbox) o (False, 0, None)
    """
    # Convertir RGB a HSV para mejor detección de color
    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    
    # Rangos de color balanceados: detectan fuego real pero filtran piel/objetos amarillos
    # Saturación y brillo moderados para detectar llamas pequeñas
    
    # Rojo brillante (fuego intenso)
    lower_red1 = np.array([0, 120, 180])  # Saturación y brillo moderados
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 180])
    upper_red2 = np.array([180, 255, 255])
    
    # Naranja brillante (llamas)
    lower_orange = np.array([10, 120, 180])  # Saturación y brillo moderados
    upper_orange = np.array([25, 255, 255])
    
    # Amarillo brillante (llamas intensas)
    lower_yellow = np.array([25, 120, 180])  # Saturación y brillo moderados
    upper_yellow = np.array([35, 255, 255])
    
    # Crear máscaras
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    # Combinar máscaras
    mask_fuego = cv2.bitwise_or(mask_red1, mask_red2)
    mask_fuego = cv2.bitwise_or(mask_fuego, mask_orange)
    mask_fuego = cv2.bitwise_or(mask_fuego, mask_yellow)
    
    # Aplicar filtro morfológico para eliminar ruido
    kernel = np.ones((5, 5), np.uint8)
    mask_fuego = cv2.morphologyEx(mask_fuego, cv2.MORPH_CLOSE, kernel)
    mask_fuego = cv2.morphologyEx(mask_fuego, cv2.MORPH_OPEN, kernel)
    
    # Contar píxeles de fuego
    pixeles_fuego = cv2.countNonZero(mask_fuego)
    total_pixeles = frame_rgb.shape[0] * frame_rgb.shape[1]
    porcentaje = (pixeles_fuego / total_pixeles) * 100
    
    # Validaciones balanceadas: detecta fuego real pero evita ruido
    # 1. Debe haber suficientes píxeles
    # 2. Debe ser al menos un porcentaje mínimo del frame
    # 3. El área detectada debe ser razonable (no muy pequeña)
    if pixeles_fuego >= umbral_pixeles and porcentaje >= umbral_porcentaje:
        # Encontrar contornos
        contours, _ = cv2.findContours(mask_fuego, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Encontrar el contorno más grande
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            # Validar que el área sea razonable (ajustado para llamas pequeñas)
            if area < 300:  # Área mínima de 300 píxeles (reducido para detectar llamas pequeñas)
                return False, porcentaje, None
            
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Validar que el bounding box tenga un tamaño razonable (ajustado para llamas pequeñas)
            if w < 20 or h < 20:  # Mínimo 20x20 píxeles (reducido para detectar llamas pequeñas)
                return False, porcentaje, None
            
            # Normalizar coordenadas
            altura, ancho = frame_rgb.shape[:2]
            x1_norm = x / ancho
            y1_norm = y / altura
            x2_norm = (x + w) / ancho
            y2_norm = (y + h) / altura
            
            return True, porcentaje, (x1_norm, y1_norm, x2_norm, y2_norm)
    
    return False, porcentaje, None


def detectar_amenazas_frame(cliente, frame_rgb, modo_debug=False):
    """
    Detecta amenazas en un frame de video.
    
    Args:
        cliente: Cliente de Google Vision
        frame_rgb: Frame en formato RGB
        modo_debug: Si True, muestra información de debug
    
    Returns:
        Lista de detecciones: [(tipo, objeto, confianza, x1, y1, x2, y2), ...]
    """
    detecciones = []
    
    # Convertir frame a formato para Google Vision
    _, buffer = cv2.imencode('.jpg', frame_rgb)
    content = buffer.tobytes()
    
    image = vision.Image(content=content)
    
    # Detección de objetos
    respuesta = cliente.object_localization(image=image)
    
    OBJETOS_PELIGROSOS = [
        "gun", "knife", "weapon", "firearm", "rifle", "pistol", "sword",
        "blade", "cutting tool", "kitchen knife", "dagger", "machete",
        "scalpel", "razor", "bayonet"
    ]
    VEHICULOS_SOSPECHOSOS = ["truck", "van", "suv", "vehicle", "car", "automobile"]
    OBJETOS_FUEGO = ["lighter", "match", "torch", "candle", "flame"]  # Objetos relacionados con fuego
    
    # Lista de objetos que NO queremos detectar (falsos positivos)
    OBJETOS_IGNORAR = [
        "finger", "thumb", "nail", "hand", "glove", "medical glove",
        "safety glove", "plastic", "person", "human", "skin", "science",
        "medical", "body part", "anatomy"
    ]
    
    # Procesar objetos detectados
    for obj in respuesta.localized_object_annotations:
        nombre = obj.name.lower()
        score = obj.score
        box = obj.bounding_poly.normalized_vertices
        
        if len(box) < 4:
            continue
            
        x1, y1 = box[0].x, box[0].y
        x2, y2 = box[2].x, box[2].y
        
        # Ignorar objetos no relevantes
        if any(ignorar in nombre for ignorar in OBJETOS_IGNORAR):
            if modo_debug:
                print(f"[DEBUG] Objeto ignorado: {nombre} (score: {score:.3f})")
            continue
        
        # Detectar armas
        for peligro in OBJETOS_PELIGROSOS:
            if peligro in nombre and score >= UMBRAL_CONFIANZA_ARMA:
                detecciones.append(("arma", nombre, score, x1, y1, x2, y2))
                break
        
        # Detectar vehículos
        for vehiculo in VEHICULOS_SOSPECHOSOS:
            if vehiculo in nombre and score >= UMBRAL_CONFIANZA_VEHICULO:
                detecciones.append(("vehiculo", nombre, score, x1, y1, x2, y2))
                break
        
        # Detectar objetos relacionados con fuego (encendedores, velas, etc.)
        for objeto_fuego in OBJETOS_FUEGO:
            if objeto_fuego in nombre and score >= 0.55:
                # Si detecta un encendedor o similar, también es alerta de incendio
                detecciones.append(("incendio", f"{nombre} (objeto)", score, x1, y1, x2, y2))
                break
    
    # ============================================
    # DETECCIÓN DE INCENDIO - MÉTODO 1: Por color
    # ============================================
    # Usar umbrales balanceados: detecta fuego real pero evita falsos positivos
    fuego_por_color, porcentaje_color, bbox_color = detectar_fuego_por_color(
        frame_rgb, 
        umbral_pixeles=150,  # Ajustado para detectar llamas pequeñas (encendedor)
        umbral_porcentaje=0.3  # Mínimo 0.3% del frame (más sensible)
    )
    
    if fuego_por_color and porcentaje_color >= 0.3:  # Si es al menos 0.3% del frame
        # Si detectamos fuego por color, agregarlo a las detecciones
        detecciones.append(("incendio", f"fuego_detectado_por_color ({porcentaje_color:.1f}%)", 
                           min(0.95, porcentaje_color / 100.0), 
                           bbox_color[0], bbox_color[1], bbox_color[2], bbox_color[3]))
        if modo_debug:
            print(f"[DEBUG] ✅ Fuego detectado por COLOR: {porcentaje_color:.2f}% del frame")
    elif modo_debug and porcentaje_color > 0.1:
        print(f"[DEBUG] Fuego por color descartado (muy poco): {porcentaje_color:.2f}%")
    
    # ============================================
    # DETECCIÓN DE INCENDIO - MÉTODO 2: Google Vision Labels
    # ============================================
    resp_labels = cliente.label_detection(image=image)
    PATRONES_INCENDIO = [
        "fire", "flames", "flame", "smoke", "smoking",
        "wildfire", "conflagration", "explosion", "burning",
        "lighter", "match", "torch", "candle", "spark",
        "ignition", "combustion", "blaze", "ember", "flame"
    ]
    
    # Patrones de agresión directos
    PATRONES_AGRESION_DIRECTOS = [
        "violence", "aggression", "aggressive", "fight", "fighting",
        "assault", "attack", "conflict", "combat", "brawl",
        "altercation", "struggle", "hostility", "hostile",
        "physical violence", "physical altercation", "physical conflict",
        "punch", "punching", "hitting", "striking", "kicking",
        "wrestling", "grappling", "scuffle", "tussle", "melee"
    ]
    
    PATRONES_POSTURAS_AGRESIVAS = [
        "lying", "lying down", "on ground", "ground", "floor",
        "standing", "over", "above", "leaning", "bending"
    ]
    
    # Contar personas detectadas y sus posturas
    personas_detectadas = 0
    personas_en_suelo = 0
    personas_de_pie = 0
    
    for obj in respuesta.localized_object_annotations:
        nombre_obj = obj.name.lower()
        if "person" in nombre_obj:
            personas_detectadas += 1
            # Intentar detectar postura
            box = obj.bounding_poly.normalized_vertices
            if len(box) >= 4:
                posicion_y = (box[0].y + box[2].y) / 2
                # Si está en la parte inferior de la imagen, probablemente está en el suelo
                if posicion_y > 0.7:
                    personas_en_suelo += 1
                else:
                    personas_de_pie += 1
    
    # Lista de etiquetas a ignorar (falsos positivos)
    ETIQUETAS_IGNORAR = [
        "finger", "thumb", "nail", "hand", "glove", "medical",
        "plastic", "science", "anatomy", "body part"
    ]
    
    # Modo debug: mostrar todas las etiquetas detectadas
    if modo_debug:
        print("\n[DEBUG] Etiquetas detectadas:")
        for label in resp_labels.label_annotations[:10]:  # Primeras 10
            print(f"  - {label.description}: {label.score:.3f}")
    
    for label in resp_labels.label_annotations:
        desc = label.description.lower()
        score = label.score
        
        # Ignorar etiquetas no relevantes
        if any(ignorar in desc for ignorar in ETIQUETAS_IGNORAR):
            continue
        
        # ============================================
        # DETECCIÓN DE AGRESIÓN (MEJORADA)
        # ============================================
        # Estrategia 1: Detección directa (umbral bajo: 0.40)
        if score >= 0.40:
            for palabra in PATRONES_AGRESION_DIRECTOS:
                if palabra in desc:
                    detecciones.append(("agresion", desc, score, 0.0, 0.0, 1.0, 1.0))
                    if modo_debug:
                        print(f"[DEBUG] ✅ Agresión detectada: {desc} (confianza: {score:.3f}, personas: {personas_detectadas})")
                    break
        
        # Estrategia 2: Múltiples personas con contexto de conflicto
        if personas_detectadas >= 2 and score >= 0.35:
            palabras_conflicto = ["struggle", "conflict", "tension", "action", "drama", "movement", "motion"]
            if any(palabra in desc for palabra in palabras_conflicto):
                # Evitar falsos positivos de deportes
                if "sport" not in desc and "competition" not in desc and "game" not in desc:
                    detecciones.append(("agresion", f"{desc} (múltiples personas)", min(0.75, score + 0.15), 0.0, 0.0, 1.0, 1.0))
                    if modo_debug:
                        print(f"[DEBUG] ✅ Agresión detectada (múltiples personas): {desc} (confianza: {min(0.75, score + 0.15):.3f})")
        
        # Estrategia 3: Posturas agresivas
        if any(palabra in desc for palabra in PATRONES_POSTURAS_AGRESIVAS) and score >= 0.40:
            if personas_detectadas >= 2:
                detecciones.append(("agresion", f"{desc} (postura agresiva)", min(0.70, score + 0.1), 0.0, 0.0, 1.0, 1.0))
                if modo_debug:
                    print(f"[DEBUG] ✅ Agresión detectada (postura): {desc} (confianza: {min(0.70, score + 0.1):.3f})")
    
    # Estrategia 4: Detección por posturas (persona en suelo + persona de pie)
    if personas_en_suelo >= 1 and personas_de_pie >= 1:
        # Si hay una persona en el suelo y otra de pie, es muy probable agresión
        detecciones.append(("agresion", "persona en suelo con otra persona de pie (posible agresión)", 0.65, 0.0, 0.0, 1.0, 1.0))
        if modo_debug:
            print(f"[DEBUG] ✅ Agresión detectada (posturas): persona en suelo ({personas_en_suelo}) + persona de pie ({personas_de_pie})")
    
    # ============================================
    # DETECCIÓN DE INCENDIO
    # ============================================
    for label in resp_labels.label_annotations:
        desc = label.description.lower()
        score = label.score
        
        # Ignorar etiquetas no relevantes
        if any(ignorar in desc for ignorar in ETIQUETAS_IGNORAR):
            continue
        
        # Bajar umbral para detectar llamas pequeñas
        if score < UMBRAL_CONFIANZA_INCENDIO:
            if modo_debug and any(palabra in desc for palabra in PATRONES_INCENDIO):
                print(f"[DEBUG] Incendio descartado (confianza baja): {desc} ({score:.3f})")
            continue
        
        for palabra in PATRONES_INCENDIO:
            if palabra in desc:
                # Para incendios no hay bounding box específico, usamos toda la imagen
                detecciones.append(("incendio", desc, score, 0.0, 0.0, 1.0, 1.0))
                if modo_debug:
                    print(f"[DEBUG] ✅ Incendio detectado por LABEL: {desc} (confianza: {score:.3f})")
                break
    
    return detecciones


def dibujar_detecciones(frame, detecciones, altura_frame, ancho_frame):
    """
    Dibuja bounding boxes y etiquetas en el frame.
    """
    alerta_detectada = False
    
    for tipo, objeto, confianza, x1, y1, x2, y2 in detecciones:
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue
        
        # Convertir coordenadas normalizadas a píxeles
        x1_px = int(x1 * ancho_frame)
        y1_px = int(y1 * altura_frame)
        x2_px = int(x2 * ancho_frame)
        y2_px = int(y2 * altura_frame)
        
        color = COLORES.get(tipo, (255, 255, 255))
        
        # Dibujar rectángulo
        cv2.rectangle(frame, (x1_px, y1_px), (x2_px, y2_px), color, 3)
        
        # Preparar texto
        etiqueta = f"{objeto} ({confianza:.2f})"
        tipo_texto = tipo.upper()
        
        # Fondo para el texto
        (text_width, text_height), baseline = cv2.getTextSize(
            etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        
        # Dibujar fondo del texto
        cv2.rectangle(
            frame,
            (x1_px, y1_px - text_height - 10),
            (x1_px + text_width + 10, y1_px),
            color,
            -1
        )
        
        # Dibujar texto
        cv2.putText(
            frame,
            etiqueta,
            (x1_px + 5, y1_px - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
        
        # Indicador de alerta
        if tipo in ['arma', 'incendio', 'agresion']:
            alerta_detectada = True
            cv2.putText(
                frame,
                f"ALERTA: {tipo_texto}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                3
            )
    
    return alerta_detectada


def guardar_frame_con_alerta(frame, detecciones, ruta_base="alertas_camara"):
    """
    Guarda el frame cuando se detecta una alerta crítica.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_imagen = f"{ruta_base}_{timestamp}.jpg"
    
    # Crear directorio si no existe
    os.makedirs("alertas_frames", exist_ok=True)
    ruta_completa = os.path.join("alertas_frames", ruta_imagen)
    
    cv2.imwrite(ruta_completa, frame)
    return ruta_completa


# ------------------ FUNCIÓN PRINCIPAL ------------------ #

def iniciar_camara_vivo():
    """
    Inicia la captura de video en vivo y detecta amenazas en tiempo real.
    """
    print("\n" + "="*60)
    print("  OJO DE DIOS - DETECCIÓN EN VIVO")
    print("="*60)
    print("\nPresiona 'q' para salir")
    print("Presiona 's' para capturar frame actual")
    print("Presiona 'd' para activar/desactivar modo debug")
    print(f"Umbral de confianza - Incendio: {UMBRAL_CONFIANZA_INCENDIO}, Arma: {UMBRAL_CONFIANZA_ARMA}")
    print(f"Umbral de confianza - Agresión: {UMBRAL_CONFIANZA_AGRESION}, Vehículo: {UMBRAL_CONFIANZA_VEHICULO}")
    print("\n💡 TIP: Presiona 'd' para ver todas las etiquetas detectadas por Google Vision")
    print("-"*60 + "\n")
    
    # Inicializar base de datos
    init_db()
    
    # Inicializar cliente de Vision
    cliente = vision.ImageAnnotatorClient()
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: No se pudo abrir la cámara")
        return
    
    # Configurar resolución (opcional)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    frame_count = 0
    ultima_analisis = 0
    detecciones_actuales = []
    modo_debug_activo = MODO_DEBUG
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("❌ Error: No se pudo leer el frame")
                break
            
            # Voltear frame horizontalmente (espejo)
            frame = cv2.flip(frame, 1)
            
            altura_frame, ancho_frame = frame.shape[:2]
            
            # Analizar frame cada N segundos (para no saturar la API)
            frame_count += 1
            tiempo_actual = datetime.now().timestamp()
            
            if tiempo_actual - ultima_analisis >= FRAME_INTERVAL:
                # Convertir BGR a RGB para Google Vision
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                print(f"[Frame {frame_count}] Analizando...", end="\r")
                
                try:
                    detecciones_actuales = detectar_amenazas_frame(cliente, frame_rgb, modo_debug_activo)
                    ultima_analisis = tiempo_actual
                    
                    # Guardar alertas críticas en BD
                    for tipo, objeto, confianza, x1, y1, x2, y2 in detecciones_actuales:
                        if tipo in ['arma', 'incendio', 'agresion']:
                            # Guardar frame
                            ruta_frame = guardar_frame_con_alerta(frame, detecciones_actuales)
                            
                            # Guardar en BD (ubicación por defecto para cámara en vivo)
                            guardar_alerta(
                                imagen=ruta_frame,
                                tipo=tipo,
                                objeto=objeto,
                                confianza=confianza,
                                x1=x1 if x1 != 0.0 else None,
                                y1=y1 if y1 != 0.0 else None,
                                x2=x2 if x2 != 1.0 else None,
                                y2=y2 if y2 != 1.0 else None,
                                ubicacion="Cámara en Vivo"
                            )
                            
                            # Mensaje especial para cuchillos
                            if "knife" in objeto.lower() or "blade" in objeto.lower():
                                print(f"\n🔪🚨 ALERTA: CUCHILLO DETECTADO 🚨🔪")
                                print(f"   Objeto: {objeto.upper()}")
                                print(f"   Confianza: {confianza:.2f}")
                            else:
                                print(f"\n🚨 ALERTA {tipo.upper()} DETECTADA: {objeto} (confianza: {confianza:.2f})")
                            print(f"   Frame guardado en: {ruta_frame}")
                
                except Exception as e:
                    print(f"\n⚠️ Error en detección: {e}")
                    detecciones_actuales = []
            
            # Dibujar detecciones en el frame
            alerta = dibujar_detecciones(frame, detecciones_actuales, altura_frame, ancho_frame)
            
            # Información en pantalla
            estado = "🔴 ALERTA ACTIVA" if alerta else "🟢 MONITOREO"
            cv2.putText(
                frame,
                estado,
                (10, altura_frame - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0) if not alerta else (0, 0, 255),
                2
            )
            
            cv2.putText(
                frame,
                f"Frame: {frame_count} | Detecciones: {len(detecciones_actuales)}",
                (10, altura_frame - 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
            
            # Mostrar frame
            cv2.imshow('Ojo de Dios - Detección en Vivo', frame)
            
            # Controles
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Guardar frame actual
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ruta = f"captura_{timestamp}.jpg"
                cv2.imwrite(ruta, frame)
                print(f"\n📸 Frame guardado: {ruta}")
            elif key == ord('d'):
                # Activar/desactivar modo debug
                modo_debug_activo = not modo_debug_activo
                estado = "ACTIVADO" if modo_debug_activo else "DESACTIVADO"
                print(f"\n🔍 Modo debug {estado}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupción del usuario")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n✔️ Cámara cerrada correctamente\n")


if __name__ == "__main__":
    iniciar_camara_vivo()

