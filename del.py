# migrate_vendors.py
import sqlite3
import shutil
from datetime import datetime
import os
import sys

DB = 'invoices.db'

def backup_db():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'invoices_backup_{timestamp}.db'
    shutil.copy2(DB, backup_name)
    print(f'✓ Backup kreiran: {backup_name}')
    return backup_name

def table_exists(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]

def add_column(conn, table, column_sql):
    cur = conn.cursor()
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")
        conn.commit()
        print(f"✓ Dodata kolona: {column_sql}")
    except Exception as e:
        print(f"✗ Ne mogu dodati kolonu {column_sql}: {e}")

def main():
    if not os.path.exists(DB):
        print(f"Datoteka baze '{DB}' ne postoji u trenutnom direktorijumu.")
        sys.exit(1)

    backup_db()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Ako vendors tabela ne postoji, kreiraj je i popuni iz invoices (ako ima imena)
    if not table_exists(conn, 'vendors'):
        print("Tabela 'vendors' ne postoji — kreiram novu tabelu 'vendors' i popunjavam iz invoices.")
        cur.execute('''
            CREATE TABLE vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        # Popuni iz invoices (jedinstvena imena)
        cur.execute("SELECT DISTINCT vendor_name FROM invoices WHERE vendor_name IS NOT NULL AND vendor_name != ''")
        names = [r[0] for r in cur.fetchall()]
        for n in names:
            cur.execute("INSERT INTO vendors (name, created_at) VALUES (?, datetime('now'))", (n,))
        conn.commit()
        print(f"✓ Kreirano vendors i ubačeno {len(names)} dobavljača iz invoices (ako ih je bilo).")
    else:
        # Ako postoji, dodaj nedostajuće kolone
        cols = get_columns(conn, 'vendors')
        print("Postojeće kolone u vendors:", cols)

        needed = {
            'address': "address TEXT",
            'contact_person': "contact_person TEXT",
            'phone': "phone TEXT",
            'email': "email TEXT",
            'notes': "notes TEXT",
            'created_at': "created_at TEXT"
        }

        for col, sql in needed.items():
            if col not in cols:
                add_column(conn, 'vendors', sql)

        # Ako created_at je dodat, postavi vrednost za postojeće redove
        cols_after = get_columns(conn, 'vendors')
        if 'created_at' in cols_after:
            cur.execute("UPDATE vendors SET created_at = datetime('now') WHERE created_at IS NULL OR created_at = ''")
            conn.commit()
            print("✓ Ažuriran created_at za postojeće redove (ako je bilo praznih).")

    conn.close()
    print("Migracija vendors tabele završena. Pokreni aplikaciju i testiraj dodavanje dobavljača.")
    print("Ako se pojave greške, pošalji tačan stack trace ili poruku greške.")

if __name__ == '__main__':
    main()