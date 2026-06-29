"""
eSYNAPSE 360 — Script de migración única: renombra la app 'sgi' a 'sig'
conservando todos los datos. Ejecutar UNA sola vez con el servidor APAGADO,
desde la carpeta backend:

    python renombrar_sgi_a_sig.py
    python manage.py migrate
"""
import os
import sqlite3

if not os.path.exists('db.sqlite3'):
    print('No existe db.sqlite3 en esta carpeta. Ejecuta desde backend/.')
    raise SystemExit(1)

con = sqlite3.connect('db.sqlite3')
cur = con.cursor()
tablas = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sgi_%'")]
if not tablas:
    print('Nada que renombrar: no hay tablas sgi_* (¿ya se ejecutó este script?)')
else:
    for t in tablas:
        nuevo = 'sig_' + t[len('sgi_'):]
        cur.execute(f'ALTER TABLE {t} RENAME TO {nuevo}')
        print(f'  {t} → {nuevo}')
    cur.execute("UPDATE django_migrations SET app='sig' WHERE app='sgi'")
    print(f'  django_migrations: {cur.rowcount} registros')
    cur.execute("UPDATE django_content_type SET app_label='sig' WHERE app_label='sgi'")
    print(f'  django_content_type: {cur.rowcount} registros')
    con.commit()
    print('\nListo. Ahora ejecuta: python manage.py migrate')
con.close()
