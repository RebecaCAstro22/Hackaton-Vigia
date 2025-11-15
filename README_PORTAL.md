# Portal Web - Ojo de Dios

Portal web profesional para el sistema de detección de amenazas de seguridad nacional.

## 🚀 Características

- **Análisis de Imágenes**: Sube imágenes y analízalas en tiempo real
- **Dashboard Interactivo**: Visualiza estadísticas y métricas del sistema
- **Historial de Alertas**: Revisa todas las alertas registradas con filtros avanzados
- **API REST**: Endpoints para integración con otros sistemas
- **Interfaz Moderna**: Diseño responsive y profesional

## 📋 Requisitos

- Python 3.8+
- Flask
- Google Cloud Vision API configurado
- Base de datos SQLite (se crea automáticamente)

## 🛠️ Instalación

1. Instala las dependencias:
```bash
pip install -r requirements.txt
```

2. Asegúrate de tener el archivo de credenciales de Google Cloud:
   - `hackaton-segiridad-500d7a7a5a64.json` (o el que corresponda)

3. Inicia el servidor:
```bash
python app.py
```

4. Abre tu navegador en:
```
http://localhost:5000
```

## 📁 Estructura del Proyecto

```
Hackaton-OjoDeDios/
├── app.py                 # Aplicación Flask principal
├── analizador.py         # Módulo de detección de amenazas
├── camara_vivo.py        # Detección en tiempo real
├── templates/            # Plantillas HTML
│   ├── base.html
│   ├── index.html
│   ├── analizar.html
│   ├── dashboard.html
│   └── alertas.html
├── static/               # Archivos estáticos
│   ├── css/
│   │   └── style.css
│   └── js/
├── uploads/             # Imágenes subidas
└── alertas_frames/      # Frames de alertas
```

## 🔌 API Endpoints

### GET `/api/alertas`
Obtiene alertas en formato JSON.

**Parámetros:**
- `limit` (opcional): Número máximo de alertas (default: 50)
- `tipo` (opcional): Filtrar por tipo (arma, incendio, vehiculo)

**Ejemplo:**
```
GET /api/alertas?limit=10&tipo=arma
```

### GET `/api/estadisticas`
Obtiene estadísticas del sistema.

**Respuesta:**
```json
{
  "por_tipo": {
    "arma": 15,
    "incendio": 8,
    "vehiculo": 3
  },
  "ultimas_24h": 26
}
```

## 🎯 Uso

### Analizar una Imagen

1. Ve a la sección "Analizar Imagen"
2. Selecciona una imagen (JPG, PNG, GIF, WEBP)
3. Haz clic en "Analizar Imagen"
4. Revisa los resultados

### Ver Dashboard

1. Accede al Dashboard desde el menú
2. Visualiza estadísticas en tiempo real
3. Revisa alertas recientes
4. Observa gráficos de tendencias

### Filtrar Alertas

1. Ve a la sección "Alertas"
2. Usa los filtros para buscar por:
   - Tipo de alerta
   - Rango de fechas
3. Haz clic en "Filtrar"

## 🔒 Seguridad

- Las imágenes se guardan de forma segura
- Validación de tipos de archivo
- Límite de tamaño de archivo (16MB)
- Sanitización de nombres de archivo

## 📊 Funcionalidades Futuras

- [ ] Autenticación de usuarios
- [ ] Notificaciones en tiempo real
- [ ] Exportación de reportes
- [ ] Integración con cámaras IP
- [ ] Panel de administración avanzado

## 🤝 Contribución

Este es un proyecto de hackathon para seguridad nacional. Para mejoras o sugerencias, contacta al equipo de desarrollo.

## 📝 Licencia

Ver archivo LICENSE para más detalles.

