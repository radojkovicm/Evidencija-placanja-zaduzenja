# database.py - Kompletan i kompatibilan fajl
import sqlite3
from datetime import datetime
import os
import shutil

class Database:
    def __init__(self, db_name='invoices.db'):
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.create_tables()
        self._ensure_invoices_columns()  # osiguraj kompatibilnost stare strukture
    
    def connect(self):
        """Otvori konekciju sa bazom"""
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            print(f"Konekcija sa bazom '{self.db_name}' uspešno otvorena.")
        except sqlite3.Error as e:
            print(f"Greška pri povezivanju sa bazom: {e}")
            raise
    
    def create_tables(self):
        """Kreiraj tabele ako ne postoje"""
        cursor = self.conn.cursor()
        
        # Tabela za dobavljače
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendors (
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
        
        # Tabela za račune (sa vendor_name radi kompatibilnosti)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                vendor_name TEXT,
                delivery_note_number TEXT,
                amount REAL NOT NULL,
                is_paid INTEGER DEFAULT 0,
                payment_date TEXT,
                notes TEXT,
                is_archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela za podešavanja
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        self.conn.commit()
        print("Tabele su kreirane ili već postoje.")
    
    def _get_table_columns(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [row['name'] for row in cursor.fetchall()]
        return cols
    
    def _ensure_vendors_columns(self):
        """
        Ensure vendors table has columns needed by GUI:
        vendor_code, pib, registration_number, bank_account, plus keep existing ones.
        Adds missing columns if necessary.
        """
        cursor = self.conn.cursor()
        # ensure vendors table exists (in case older DB had none)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                vendor_code TEXT,
                address TEXT,
                pib TEXT,
                registration_number TEXT,
                bank_account TEXT,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

        # Add any missing columns (safe if already present)
        existing = self._get_table_columns('vendors')
        needed = {
            'vendor_code': 'vendor_code TEXT',
            'pib': 'pib TEXT',
            'registration_number': 'registration_number TEXT',
            'bank_account': 'bank_account TEXT',
            'contact_person': 'contact_person TEXT',
            'phone': 'phone TEXT',
            'email': 'email TEXT',
            'notes': 'notes TEXT',
            'created_at': "created_at TEXT DEFAULT CURRENT_TIMESTAMP"
        }
        for col, col_sql in needed.items():
            if col not in existing:
                try:
                    cursor.execute(f"ALTER TABLE vendors ADD COLUMN {col_sql}")
                except Exception:
                    # ignore if cannot add (edge cases)
                    pass
        self.conn.commit()
    
    def _ensure_invoices_columns(self):
        """
        Osigura da invoices tabela ima često potrebne kolone (vendor_id, vendor_name, created_at).
        Ako kolona ne postoji, dodaće je (nullable) kako bi se izbegle greške.
        """
        cursor = self.conn.cursor()
        cols = self._get_table_columns('invoices')
        altered = False
        
        if 'vendor_id' not in cols:
            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN vendor_id INTEGER')
                altered = True
            except Exception:
                pass
        
        if 'vendor_name' not in cols:
            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN vendor_name TEXT')
                altered = True
            except Exception:
                pass
        
        if 'created_at' not in cols:
            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP')
                altered = True
            except Exception:
                pass
        
        if altered:
            self.conn.commit()
            print("Ažurirana struktura invoices tabele (dodate nedostajuće kolone).")
    
    # ==================== INVOICE METODE ====================
    
    def add_invoice(self, invoice_data):
        """Dodaj novi račun"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO invoices (invoice_date, due_date, vendor_name, delivery_note_number, amount, notes, vendor_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_data.get('invoice_date'),
            invoice_data.get('due_date'),
            invoice_data.get('vendor_name'),
            invoice_data.get('delivery_note_number'),
            invoice_data.get('amount'),
            invoice_data.get('notes'),
            invoice_data.get('vendor_id')
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_invoices(self, include_archived=False):
        """Uzmi sve račune"""
        cursor = self.conn.cursor()
        if include_archived:
            cursor.execute('SELECT * FROM invoices ORDER BY due_date DESC')
        else:
            cursor.execute('SELECT * FROM invoices WHERE is_archived = 0 ORDER BY due_date DESC')
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_invoice_by_id(self, invoice_id):
        """Uzmi račun po ID-u"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_invoice(self, invoice_id, invoice_data):
        """Ažuriraj račun"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE invoices
            SET invoice_date = ?, due_date = ?, vendor_name = ?, 
                delivery_note_number = ?, amount = ?, notes = ?, vendor_id = ?
            WHERE id = ?
        ''', (
            invoice_data.get('invoice_date'),
            invoice_data.get('due_date'),
            invoice_data.get('vendor_name'),
            invoice_data.get('delivery_note_number'),
            invoice_data.get('amount'),
            invoice_data.get('notes'),
            invoice_data.get('vendor_id'),
            invoice_id
        ))
        self.conn.commit()
    
    def mark_as_paid(self, invoice_id, payment_date=None):
        """Označi račun kao plaćen"""
        if payment_date is None:
            payment_date = datetime.now().strftime('%d.%m.%Y')
        
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE invoices
            SET is_paid = 1, payment_date = ?
            WHERE id = ?
        ''', (payment_date, invoice_id))
        self.conn.commit()
    
    def mark_as_unpaid(self, invoice_id):
        """Označi račun kao neplaćen"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE invoices
            SET is_paid = 0, payment_date = NULL
            WHERE id = ?
        ''', (invoice_id,))
        self.conn.commit()
    
    def archive_invoice(self, invoice_id):
        """Arhiviraj račun"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE invoices
            SET is_archived = 1
            WHERE id = ?
        ''', (invoice_id,))
        self.conn.commit()
    
    def delete_invoice(self, invoice_id):
        """Obriši račun"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
        self.conn.commit()
    
    # ==================== VENDOR METODE ====================
    
    def get_all_vendors(self, with_details=True):
        """
        Return vendors in a format expected by the GUI.
        - with_details=True  -> list of dicts with keys:
            vendor_id, vendor_code, vendor_name, address, pib, registration_number, bank_account, ...
        - with_details=False -> list of vendor_name strings (backwards compat).
        """
        cursor = self.conn.cursor()

        if with_details:
            cursor.execute("SELECT * FROM vendors ORDER BY name")
            rows = cursor.fetchall()
            results = []
            seen_names = set()
            for r in rows:
                d = dict(r)
                vendor = {
                    'vendor_id': d.get('id'),
                    'vendor_code': d.get('vendor_code') or d.get('id'),
                    'vendor_name': d.get('name') or '',
                    'address': d.get('address') or '',
                    'pib': d.get('pib') or '',
                    'registration_number': d.get('registration_number') or '',
                    'bank_account': d.get('bank_account') or '',
                    # include extras so other GUIs can use them
                    'contact_person': d.get('contact_person') or '',
                    'phone': d.get('phone') or '',
                    'email': d.get('email') or '',
                    'notes': d.get('notes') or ''
                }
                results.append(vendor)
                seen_names.add(vendor['vendor_name'])

            # Also include unique names that exist only in invoices (keeps compatibility)
            cursor.execute("SELECT DISTINCT vendor_name FROM invoices WHERE vendor_name IS NOT NULL AND vendor_name != ''")
            for row in cursor.fetchall():
                name = row['vendor_name']
                if name not in seen_names:
                    results.append({
                        'vendor_id': None,
                        'vendor_code': None,
                        'vendor_name': name,
                        'address': '',
                        'pib': '',
                        'registration_number': '',
                        'bank_account': '',
                        'contact_person': '',
                        'phone': '',
                        'email': '',
                        'notes': ''
                    })
                    seen_names.add(name)

            return results
        else:
            cursor.execute('''
                SELECT DISTINCT name as vendor_name FROM vendors
                WHERE name IS NOT NULL AND name != ''
                UNION
                SELECT DISTINCT vendor_name FROM invoices
                WHERE vendor_name IS NOT NULL AND vendor_name != ''
                ORDER BY 1
            ''')
            rows = cursor.fetchall()
            return [row['vendor_name'] for row in rows]
    
    def add_vendor(self, *args, **kwargs):
        """
        Add vendor. Accepts:
        - add_vendor(name, address='', pib='', registration_number='', bank_account='', vendor_code='', contact_person='', phone='', email='', notes='')
        - add_vendor({'name':..., 'pib':..., ...})
        - add_vendor(name='...', ...)
        Returns new vendor id.
        """
        # debug print to see what GUI passes (remove later)
        try:
            print("DEBUG add_vendor called with args:", args, "kwargs:", kwargs)
        except Exception:
            pass

        # defaults
        name = None
        vendor_code = ''
        address = ''
        pib = ''
        registration_number = ''
        bank_account = ''
        contact_person = ''
        phone = ''
        email = ''
        notes = ''

        # kwargs first
        if kwargs:
            name = kwargs.get('name') or kwargs.get('vendor_name') or kwargs.get('vendor')
            vendor_code = kwargs.get('vendor_code', '')
            address = kwargs.get('address', '')
            pib = kwargs.get('pib', '')
            registration_number = kwargs.get('registration_number', '')
            bank_account = kwargs.get('bank_account', '')
            contact_person = kwargs.get('contact_person', '')
            phone = kwargs.get('phone', '')
            email = kwargs.get('email', '')
            notes = kwargs.get('notes', '')

        # args handling
        if args:
            if len(args) == 1:
                first = args[0]
                if isinstance(first, dict):
                    name = first.get('name') or first.get('vendor_name') or name
                    vendor_code = first.get('vendor_code', vendor_code)
                    address = first.get('address', address)
                    pib = first.get('pib', pib)
                    registration_number = first.get('registration_number', registration_number)
                    bank_account = first.get('bank_account', bank_account)
                    contact_person = first.get('contact_person', contact_person)
                    phone = first.get('phone', phone)
                    email = first.get('email', email)
                    notes = first.get('notes', notes)
                elif isinstance(first, str):
                    if not name:
                        name = first
            else:
                # map positional args in expected order
                # order: name, address, pib, registration_number, bank_account, vendor_code, contact_person, phone, email, notes
                try:
                    name = name or args[0]
                    address = args[1] if len(args) > 1 else address
                    pib = args[2] if len(args) > 2 else pib
                    registration_number = args[3] if len(args) > 3 else registration_number
                    bank_account = args[4] if len(args) > 4 else bank_account
                    vendor_code = args[5] if len(args) > 5 else vendor_code
                    contact_person = args[6] if len(args) > 6 else contact_person
                    phone = args[7] if len(args) > 7 else phone
                    email = args[8] if len(args) > 8 else email
                    notes = args[9] if len(args) > 9 else notes
                except Exception:
                    pass

        # normalize to strings
        if name is not None:
            name = str(name).strip()
        if vendor_code is not None:
            vendor_code = str(vendor_code).strip()
        address = str(address or '').strip()
        pib = str(pib or '').strip()
        registration_number = str(registration_number or '').strip()
        bank_account = str(bank_account or '').strip()
        contact_person = str(contact_person or '').strip()
        phone = str(phone or '').strip()
        email = str(email or '').strip()
        notes = str(notes or '').strip()

        if not name:
            raise ValueError("Vendor name is required.")

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO vendors (name, vendor_code, address, pib, registration_number, bank_account, contact_person, phone, email, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, vendor_code, address, pib, registration_number, bank_account, contact_person, phone, email, notes))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Greška pri dodavanju dobavljača u DB: {e}")
            raise
        
    def delete_vendor(self, vendor_name):
        """
        Obriši dobavljača po imenu:
        - obriši sve račune koji imaju vendor_name
        - obriši unos iz vendors tabele (ako postoji)
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute('DELETE FROM invoices WHERE vendor_name = ?', (vendor_name,))
            cursor.execute('DELETE FROM vendors WHERE name = ?', (vendor_name,))
            self.conn.commit()
        except Exception as e:
            print(f"Greška pri brisanju dobavljača: {e}")
            raise
    
    def delete_vendor_by_id(self, vendor_id):
        """Obriši dobavljača po id-u i sve njegove račune (ako su povezani putem vendor_name)"""
        cursor = self.conn.cursor()
        try:
            # prvo pronađi ime da bismo obrisali račune koji imaju vendor_name
            cursor.execute('SELECT name FROM vendors WHERE id = ?', (vendor_id,))
            row = cursor.fetchone()
            name = row['name'] if row else None
            if name:
                cursor.execute('DELETE FROM invoices WHERE vendor_name = ?', (name,))
            cursor.execute('DELETE FROM vendors WHERE id = ?', (vendor_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Greška pri brisanju dobavljača po id: {e}")
            raise
    
    def update_vendor(self, vendor_id, name=None, address=None, contact_person=None, phone=None, email=None, notes=None):
        """Ažuriraj podatke o dobavljaču po id-u"""
        cursor = self.conn.cursor()
        # Sastavi dinamički UPDATE na poljima koja nisu None
        updates = []
        params = []
        if name is not None:
            updates.append('name = ?'); params.append(name)
        if address is not None:
            updates.append('address = ?'); params.append(address)
        if contact_person is not None:
            updates.append('contact_person = ?'); params.append(contact_person)
        if phone is not None:
            updates.append('phone = ?'); params.append(phone)
        if email is not None:
            updates.append('email = ?'); params.append(email)
        if notes is not None:
            updates.append('notes = ?'); params.append(notes)
        
        if not updates:
            return
        
        params.append(vendor_id)
        sql = f"UPDATE vendors SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, tuple(params))
        self.conn.commit()
    
    def update_vendor_name(self, old_name, new_name):
        """Promeni ime dobavljača u svim računima i u vendors tabeli"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE invoices
            SET vendor_name = ?
            WHERE vendor_name = ?
        ''', (new_name, old_name))
        cursor.execute('''
            UPDATE vendors
            SET name = ?
            WHERE name = ?
        ''', (new_name, old_name))
        self.conn.commit()
    
    def get_vendor_invoices(self, vendor_name):
        """Uzmi sve račune za određenog dobavljača"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM invoices 
            WHERE vendor_name = ? 
            ORDER BY due_date DESC
        ''', (vendor_name,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_vendor_stats(self, vendor_name):
        """Uzmi statistiku za dobavljača"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM invoices WHERE vendor_name = ?', (vendor_name,))
        total_invoices = cursor.fetchone()['count']
        
        cursor.execute('SELECT SUM(amount) as total FROM invoices WHERE vendor_name = ?', (vendor_name,))
        total_amount = cursor.fetchone()['total'] or 0
        
        cursor.execute('SELECT COUNT(*) as count FROM invoices WHERE vendor_name = ? AND is_paid = 1', (vendor_name,))
        paid_invoices = cursor.fetchone()['count']
        
        cursor.execute('SELECT SUM(amount) as total FROM invoices WHERE vendor_name = ? AND is_paid = 1', (vendor_name,))
        paid_amount = cursor.fetchone()['total'] or 0
        
        return {
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'paid_invoices': paid_invoices,
            'paid_amount': paid_amount,
            'unpaid_invoices': total_invoices - paid_invoices,
            'unpaid_amount': total_amount - paid_amount
        }
    
    # ==================== SETTINGS METODE ====================
    
    def get_settings(self):
        """Uzmi sva podešavanja"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        rows = cursor.fetchall()
        
        settings = {}
        for row in rows:
            key = row['key']
            value = row['value']
            
            if value == 'True':
                value = True
            elif value == 'False':
                value = False
            elif value and value.isdigit():
                # ako je čitav broj -> int
                value = int(value)
            
            settings[key] = value
        
        return settings
    
    def save_settings(self, settings):
        """Sačuvaj sva podešavanja odjednom"""
        cursor = self.conn.cursor()
        for key, value in settings.items():
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            ''', (key, str(value) if value is not None else ''))
        self.conn.commit()
    
    def update_setting(self, key, value):
        """Ažuriraj pojedinačno podešavanje"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', (key, str(value)))
        self.conn.commit()
    
    # ==================== STATISTICS METODE ====================
    
    def get_statistics(self):
        """Uzmi opštu statistiku"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM invoices WHERE is_archived = 0')
        total_invoices = cursor.fetchone()['count']
        
        cursor.execute('SELECT SUM(amount) as total FROM invoices WHERE is_archived = 0')
        total_amount = cursor.fetchone()['total'] or 0
        
        cursor.execute('SELECT COUNT(*) as count FROM invoices WHERE is_paid = 1 AND is_archived = 0')
        paid_invoices = cursor.fetchone()['count']
        
        cursor.execute('SELECT SUM(amount) as total FROM invoices WHERE is_paid = 1 AND is_archived = 0')
        paid_amount = cursor.fetchone()['total'] or 0
        
        cursor.execute('SELECT COUNT(*) as count FROM invoices WHERE is_paid = 0 AND is_archived = 0')
        unpaid_invoices = cursor.fetchone()['count']
        
        cursor.execute('SELECT SUM(amount) as total FROM invoices WHERE is_paid = 0 AND is_archived = 0')
        unpaid_amount = cursor.fetchone()['total'] or 0
        
        return {
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'paid_invoices': paid_invoices,
            'paid_amount': paid_amount,
            'unpaid_invoices': unpaid_invoices,
            'unpaid_amount': unpaid_amount
        }
    
    # ==================== SEARCH & FILTER METODE ====================
    
    def search_invoices(self, search_term):
        """Pretraži račune po dobavljaču ili broju otpremnice"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM invoices 
            WHERE (vendor_name LIKE ? OR delivery_note_number LIKE ?)
            AND is_archived = 0
            ORDER BY due_date DESC
        ''', (f'%{search_term}%', f'%{search_term}%'))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def filter_invoices(self, filter_type='all'):
        """Filtriraj račune po statusu"""
        cursor = self.conn.cursor()
        
        if filter_type == 'paid':
            cursor.execute('SELECT * FROM invoices WHERE is_paid = 1 AND is_archived = 0 ORDER BY due_date DESC')
        elif filter_type == 'unpaid':
            cursor.execute('SELECT * FROM invoices WHERE is_paid = 0 AND is_archived = 0 ORDER BY due_date DESC')
        elif filter_type == 'overdue':
            today = datetime.now().strftime('%d.%m.%Y')
            cursor.execute('SELECT * FROM invoices WHERE is_paid = 0 AND due_date < ? AND is_archived = 0 ORDER BY due_date DESC', (today,))
        else:
            cursor.execute('SELECT * FROM invoices WHERE is_archived = 0 ORDER BY due_date DESC')
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ==================== BACKUP & RESTORE ====================
    
    def backup_database(self, backup_path=None):
        """Napravi backup baze podataka"""
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f'invoices_backup_{timestamp}.db'
        
        shutil.copy2(self.db_name, backup_path)
        print(f"Backup kreiran: {backup_path}")
        return backup_path
    
    def restore_database(self, backup_path):
        """Vrati bazu iz backup-a"""
        if not os.path.exists(backup_path):
            print(f"Backup fajl ne postoji: {backup_path}")
            return False
        
        self.conn.close()
        shutil.copy2(backup_path, self.db_name)
        self.connect()
        # Ponovo osiguraj tabele/kolone
        self.create_tables()
        self._ensure_invoices_columns()
        print(f"Baza vraćena iz: {backup_path}")
        return True
    
    def __del__(self):
        """Zatvori konekciju pri uništavanju objekta"""
        if self.conn:
            try:
                self.conn.close()
                print("Konekcija sa bazom zatvorena.")
            except Exception:
                pass