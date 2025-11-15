# 🔥 Instrucciones Completas - Ojo de Dios

## ✅ Las Alertas SÍ se están Guardando

He verificado y **las alertas SÍ se están guardando correctamente** en la base de datos. Hay **47 alertas** guardadas.

## 🔍 El Problema

Estás viendo la **página HTML estática** que lee de `data.json` (datos de ejemplo), no de la base de datos real.

## ✅ Solución: Usar el Servidor Flask

Para ver las alertas reales de la base de datos, necesitas usar el servidor Flask:

### Paso 1: Iniciar el Servidor Flask

Abre una terminal y ejecuta:

```bash
python app.py
```

Verás algo como:
```
 * Running on http://127.0.0.1:5000
```

### Paso 2: Abrir en el Navegador

Abre tu navegador y ve a:
```
http://localhost:5000
```

### Paso 3: Ver las Alertas

1. Haz clic en **"Alertas"** en el menú
2. Verás las **47 alertas reales** guardadas en la base de datos
3. Incluye fecha/hora, tipo, objeto detectado, confianza, etc.

## 📊 Verificar Alertas desde Terminal

También puedes ver las alertas desde la terminal:

```bash
python ver_alertas.py
```

Esto mostrará todas las alertas guardadas.

## 🎯 Flujo Completo

1. **Terminal 1**: `python app.py` → Servidor web (http://localhost:5000)
2. **Terminal 2**: `python camara_vivo.py` → Cámara en vivo
3. **Cámara detecta fuego** → Guarda automáticamente en `alertas.db`
4. **Recarga la página web** → Verás la alerta nueva

## 🔄 Actualización en Tiempo Real

Las alertas se actualizan cuando:
- Recargas la página (F5)
- O navegas a otra sección y vuelves

## 💡 Nota Importante

- **Páginas HTML estáticas** (`index.html`, `alertas.html`, etc.) = Solo visualización con datos de ejemplo
- **Servidor Flask** (`python app.py`) = Funcionalidad completa con base de datos real

**Para ver las alertas reales, SIEMPRE usa el servidor Flask.**

