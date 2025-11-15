import sqlite3
from datetime import datetime

# Abrir la base de datos
conn = sqlite3.connect("alertas.db")
cur = conn.cursor()

# Verificar si existe la columna 'tipo'
try:
    cur.execute("SELECT tipo FROM alertas LIMIT 1")
    tiene_tipo = True
except sqlite3.OperationalError:
    tiene_tipo = False

# Leer todas las alertas ordenadas por ID (últimas primero)
if tiene_tipo:
    cur.execute("SELECT id, fecha_hora, imagen, tipo, objeto, confianza, x1, y1, x2, y2 FROM alertas ORDER BY id DESC")
else:
    cur.execute("SELECT id, fecha_hora, imagen, objeto, confianza, x1, y1, x2, y2 FROM alertas ORDER BY id DESC")

alertas = cur.fetchall()

print("\n" + "="*80)
print(" " * 25 + "ALERTAS REGISTRADAS")
print("="*80 + "\n")

if len(alertas) == 0:
    print("No hay alertas guardadas aún.")
else:
    # Iconos por tipo
    iconos = {
        'arma': '🔫',
        'incendio': '🔥',
        'vehiculo': '🚗',
        'otro': '⚠️'
    }
    
    for alerta in alertas:
        if tiene_tipo:
            id_alerta, fecha_hora, imagen, tipo, objeto, confianza, x1, y1, x2, y2 = alerta
        else:
            id_alerta, fecha_hora, imagen, objeto, confianza, x1, y1, x2, y2 = alerta
            tipo = 'otro'  # Valor por defecto si no existe la columna
        
        icono = iconos.get(tipo, '⚠️')
        
        print(f"{icono} ALERTA #{id_alerta}")
        print(f"   Fecha/Hora: {fecha_hora}")
        print(f"   Imagen: {imagen}")
        print(f"   Tipo: {tipo.upper()}")
        print(f"   Objeto: {objeto}")
        print(f"   Confianza: {confianza:.2%}")
        
        if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            print(f"   Coordenadas: ({x1:.3f}, {y1:.3f}) → ({x2:.3f}, {y2:.3f})")
        else:
            print(f"   Coordenadas: No disponible")
        
        print("-" * 80)

print(f"\nTotal de alertas: {len(alertas)}")
print("="*80 + "\n")

conn.close()
