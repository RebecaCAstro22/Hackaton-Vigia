import sqlite3
<<<<<<< HEAD
<<<<<<< HEAD
from datetime import datetime
=======
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
=======
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5

# Abrir la base de datos
conn = sqlite3.connect("alertas.db")
cur = conn.cursor()

<<<<<<< HEAD
<<<<<<< HEAD
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
=======
=======
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
# Leer todas las alertas ordenadas por ID (últimas primero)
cur.execute("SELECT * FROM alertas ORDER BY id DESC")

alertas = cur.fetchall()

print("\n=== ALERTAS REGISTRADAS ===\n")
<<<<<<< HEAD
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
=======
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5

if len(alertas) == 0:
    print("No hay alertas guardadas aún.")
else:
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
    for alerta in alertas:
        print(alerta)
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5
=======
    for alerta in alertas:
        print(alerta)
>>>>>>> 31aa1689f52723d656035f6577cb8212810169d5

conn.close()
