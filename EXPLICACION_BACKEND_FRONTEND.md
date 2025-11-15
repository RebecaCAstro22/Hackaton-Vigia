# 🔄 Backend vs Frontend - Explicación Simple

## ¿Qué es Backend y Frontend?

### 🔧 BACKEND (app.py)
- **Es el servidor** que corre en tu computadora
- **Lee de la base de datos** (`alertas.db`)
- **Procesa las peticiones** del navegador
- **Genera las páginas HTML** con datos reales

### 🎨 FRONTEND (templates/*.html)
- **Son las páginas** que ves en el navegador
- **Se generan dinámicamente** por el backend
- **Muestran los datos** que el backend lee de la BD

## 🔗 Cómo Funcionan Juntos

```
NAVEGADOR → http://localhost:5000/alertas
                ↓
         BACKEND (app.py)
                ↓
         Lee de alertas.db
                ↓
         Genera HTML con datos
                ↓
         FRONTEND (templates/alertas.html)
                ↓
         NAVEGADOR muestra la página
```

## ⚠️ IMPORTANTE: Reiniciar el Servidor

Cuando cambias el código de `app.py`, **DEBES reiniciar el servidor**:

1. **Detén el servidor**: Presiona `Ctrl + C` en la terminal donde está corriendo
2. **Vuelve a iniciarlo**: `python app.py`
3. **Recarga la página** en el navegador (F5)

## ✅ Pasos Correctos

1. **Terminal**: `python app.py` (debe estar corriendo)
2. **Navegador**: `http://localhost:5000/alertas` (NO abrir el archivo HTML directamente)
3. **Si cambias código**: Detén y reinicia el servidor

## ❌ Errores Comunes

- ❌ Abrir `alertas.html` directamente → No funciona (datos de ejemplo)
- ❌ No reiniciar el servidor después de cambios → Sigue con código viejo
- ✅ Usar `http://localhost:5000` → Funciona correctamente

