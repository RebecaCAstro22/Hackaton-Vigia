# Configuración para Producción

## ⚠️ Advertencia del Servidor de Desarrollo

El mensaje que ves:
```
WARNING: This is a development server. Do not use it in a production deployment.
```

Es **normal** y puedes **ignorarlo** si estás:
- ✅ Desarrollando localmente
- ✅ Haciendo pruebas
- ✅ En un hackathon/demostración
- ✅ Usando solo tú o tu equipo

## 🚀 Para Producción Real

Si necesitas desplegar en producción (servidor público, muchos usuarios), usa:

### Opción 1: Waitress (Recomendado para Windows)

```bash
# Instalar
pip install waitress

# Ejecutar
python run_production.py
```

### Opción 2: Gunicorn (Linux/Mac)

```bash
# Instalar
pip install gunicorn

# Ejecutar
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### Opción 3: uWSGI (Avanzado)

```bash
pip install uwsgi
uwsgi --http 0.0.0.0:5000 --wsgi-file wsgi.py --callable app
```

## 📝 Diferencias

| Característica | Desarrollo (Flask) | Producción (Waitress/Gunicorn) |
|---------------|-------------------|-------------------------------|
| Rendimiento | Básico | Optimizado |
| Múltiples usuarios | Limitado | Mejor |
| Seguridad | Básica | Mejorada |
| Recarga automática | Sí (debug=True) | No |
| Uso recomendado | Desarrollo | Producción |

## 💡 Recomendación

**Para tu hackathon/demostración:**
- ✅ Usa `python app.py` (el warning es normal, ignóralo)
- ✅ Funciona perfectamente para mostrar el proyecto

**Si vas a desplegar públicamente:**
- ✅ Usa `python run_production.py` con Waitress
- ✅ O despliega en servicios como Heroku, Railway, o AWS

