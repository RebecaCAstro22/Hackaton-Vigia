"""
Archivo WSGI para producción.
Usa este archivo con un servidor WSGI como Gunicorn o Waitress.
"""

from app import app

if __name__ == "__main__":
    app.run()

