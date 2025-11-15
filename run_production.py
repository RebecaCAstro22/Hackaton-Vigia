"""
Script para ejecutar el servidor en modo producción con Waitress.
Waitress es compatible con Windows.

Instalación:
    pip install waitress

Ejecución:
    python run_production.py
"""

from waitress import serve
from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("  Ojo de Dios - Servidor de Producción")
    print("=" * 60)
    print("\nServidor iniciado en: http://0.0.0.0:5000")
    print("Presiona Ctrl+C para detener\n")
    
    # Servir en todas las interfaces, puerto 5000
    serve(app, host='0.0.0.0', port=5000, threads=4)

