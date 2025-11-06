# test_old_db.py - NAPRAVI OVAJ FAJL I POKRENI
import sqlite3

conn = sqlite3.connect('evidencija_placanja.db')
cursor = conn.cursor()

# Proveri broj računa
cursor.execute('SELECT COUNT(*) FROM invoices')
count = cursor.fetchone()[0]
print(f"Broj računa u evidencija_placanja.db: {count}")

# Prikaži sve račune
cursor.execute('SELECT * FROM invoices')
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()