# 🔴 Cómo Activar la Cámara en Vivo

## Paso 1: Abrir una Terminal/PowerShell

Abre PowerShell o CMD en la carpeta del proyecto:
```
C:\Users\miche\OneDrive\Escritorio\Hackaton-OjoDeDios
```

## Paso 2: Ejecutar el Script de Cámara

Escribe este comando:

```bash
python camara_vivo.py
```

## Paso 3: La Cámara se Abrirá Automáticamente

- Se abrirá una ventana con el video en vivo
- La cámara analizará cada 2 segundos
- Si detecta **fuego, arma, agresión o vehículo**, mostrará una alerta

## Controles

- **Presiona 'q'** → Cerrar la cámara
- **Presiona 's'** → Guardar frame actual
- **Presiona 'd'** → Activar/desactivar modo debug (ver todas las etiquetas detectadas)

## ¿Qué Detecta la Cámara?

### 🔥 Incendio
- Fuego, llamas, humo, encendedores
- **Para probar**: Enciende un encendedor o vela frente a la cámara

### 🔫 Armas
- Pistolas, cuchillos, rifles, armas blancas
- **Para probar**: Muestra un cuchillo o arma de juguete

### ⚔️ Agresión
- Peleas, violencia, conflictos físicos
- **Para probar**: Simula una pelea con otra persona (puños, golpes, forcejeo)
- También detecta: wrestling, lucha, forcejeo

### 🚗 Vehículos Sospechosos
- Carros, camionetas, vehículos

## ¿Qué Pasa Cuando Detecta una Amenaza?

1. ✅ Muestra alerta en la ventana de la cámara (texto rojo "ALERTA")
2. ✅ Dibuja un rectángulo alrededor de la amenaza (si es arma/vehículo)
3. ✅ Guarda el frame en `alertas_frames/`
4. ✅ Guarda en la base de datos `alertas.db` con fecha/hora
5. ✅ Aparece en la página web cuando recargas el dashboard
6. ✅ Si confianza ≥ 80%, envía automáticamente a Policía/Bomberos

## Problemas Comunes

### Error: "No se pudo abrir la cámara"
- Verifica que la cámara no esté siendo usada por otra app
- Cierra otras aplicaciones que usen la cámara (Zoom, Teams, etc.)

### Error: "ModuleNotFoundError: No module named 'cv2'"
- Instala OpenCV: `pip install opencv-python`

### La cámara no detecta nada
- Activa modo debug con 'd' para ver qué está detectando
- Asegúrate de tener buena iluminación
- Acerca el objeto a la cámara

