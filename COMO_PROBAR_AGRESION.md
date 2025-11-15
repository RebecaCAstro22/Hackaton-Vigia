# ⚔️ Cómo Probar la Detección de Agresión

## 📋 Pasos para Probar

### 1. Activar la Cámara

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
python camara_vivo.py
```

### 2. Activar Modo Debug (Recomendado)

Una vez que se abra la ventana de la cámara:
- **Presiona 'd'** para activar el modo debug
- Verás en la consola todas las etiquetas que Google Vision está detectando
- Esto te ayudará a entender qué está viendo la cámara

### 3. Simular Agresión

Para que la cámara detecte agresión, necesitas mostrar acciones que Google Vision identifique como violencia o pelea:

#### ✅ Formas de Probar:

1. **Simular una Pelea**:
   - Dos personas haciendo movimientos de pelea
   - Puños en el aire
   - Movimientos de golpeo
   - Forcejeo o lucha

2. **Gestos Agresivos**:
   - Movimientos bruscos y rápidos
   - Posturas de combate
   - Acciones de ataque (simuladas)

3. **Usar Videos o Imágenes**:
   - Puedes mostrar un video en tu pantalla de personas peleando
   - O una imagen de una pelea/conflicto

### 4. Qué Buscar en la Consola

Cuando detecte agresión, verás mensajes como:

```
⚔️ ALERTA CRÍTICA: AGRESIÓN DETECTADA - fight (Confianza: 75.2%)
```

O en modo debug:
```
[DEBUG] ✅ Agresión detectada: fighting (confianza: 0.752)
```

### 5. Verificar en la Base de Datos

Después de detectar agresión:

1. **Cierra la cámara** (presiona 'q')
2. **Abre el dashboard web**: `http://localhost:5000/dashboard`
3. **Verás**:
   - Widget de "Agresiones" con el contador
   - En "Alertas Recientes" aparecerá con badge ⚔️ Agresión

### 6. Ver Detalles

- Ve a la página de **Alertas**: `http://localhost:5000/alertas`
- Filtra por tipo "Agresión"
- Verás todas las agresiones detectadas con fecha, hora y ubicación

## 🎯 Consejos para Mejor Detección

1. **Buena Iluminación**: Asegúrate de tener buena luz
2. **Movimientos Claros**: Los gestos de pelea deben ser evidentes
3. **Múltiples Personas**: Es más fácil detectar agresión cuando hay 2+ personas
4. **Modo Debug**: Úsalo para ver qué está detectando Google Vision

## ⚠️ Nota Importante

La detección de agresión usa **Google Cloud Vision API** que analiza:
- Etiquetas de la escena (labels)
- Contexto visual
- Patrones de movimiento (en video)

**No detecta**:
- Expresiones faciales específicas
- Micro-gestos sutiles
- Agresión psicológica (solo física)

## 🔍 Si No Detecta Agresión

1. **Activa modo debug** (presiona 'd')
2. Revisa qué etiquetas está detectando Google Vision
3. Prueba con movimientos más evidentes
4. Verifica que la confianza sea ≥ 60% (umbral configurado)

## 📊 Umbrales de Confianza

- **Agresión**: ≥ 60% de confianza
- **Arma**: ≥ 50% de confianza  
- **Incendio**: ≥ 50% de confianza
- **Vehículo**: ≥ 60% de confianza

Si la confianza es menor al umbral, no se guardará como alerta.

