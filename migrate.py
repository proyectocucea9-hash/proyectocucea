"""
Script de migración: agrega la columna imagen_url a la tabla presupuestos.
Ejecutar con: python migrate.py
(Cierra la aplicación Flask antes de ejecutarlo)
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'instance', 'transparencia.db')

if not os.path.exists(db_path):
    print('No existe la base de datos. La aplicación la creará al iniciar.')
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(presupuestos)")
columns = [row[1] for row in cursor.fetchall()]

if 'imagen_url' not in columns:
    cursor.execute("ALTER TABLE presupuestos ADD COLUMN imagen_url VARCHAR(500)")
    conn.commit()
    print('Columna imagen_url agregada correctamente.')
else:
    print('La columna imagen_url ya existe.')

conn.close()
print('Migración completada.')
