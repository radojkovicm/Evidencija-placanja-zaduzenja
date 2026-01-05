import sqlite3
from datetime import datetime, timedelta
import os
import shutil


class Database:
    def __init__(self, db_name='invoices.db'):
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.create_tables()
        self._ensure_all_columns()
        self._ensure_vendor_codes()
        
        try:
            cursor = self.conn.cursor()  
            cursor.execute('ALTER TABLE revenue_entries ADD COLUMN period_type TEXT DEFAULT "Custom"')
            self.conn.commit()
        except:
            pass  # Kolona već postoji
        
        # Migracija: Dodaj payment_status i payment_date kolone ako ne postoje
        try:
            cursor = self.conn.cursor()
            cursor.execute('ALTER TABLE revenue_entries ADD COLUMN payment_status TEXT DEFAULT "Neplaćeno"')
            self.conn.commit()
        except:
            pass  # Kolona već postoji

        try:
            cursor = self.conn.cursor()
            cursor.execute('ALTER TABLE revenue_entries ADD COLUMN payment_date TEXT')
            self.conn.commit()
        except:
            pass  # Kolona već postoji
    
    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            print(f"Connection to '{self.db_name}' opened.")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # ==================== POSTOJEĆE TABELE ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                vendor_code TEXT,
                address TEXT,
                city TEXT,
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                vendor_id INTEGER,
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
        
        # ==================== NOVA TABELA ZA PLAĆANJA ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                payment_amount REAL NOT NULL,
                payment_date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # ==================== NOVE TABELE ZA KUPCE I ARTIKLE ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_code TEXT,
                name TEXT NOT NULL,
                phone TEXT,
                pib TEXT,
                id_card_number TEXT,
                registration_number TEXT,
                address TEXT,
                city TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                unit TEXT,
                price REAL NOT NULL,
                discount REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ==================== TABELE ZA PREDRAČUNE ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proforma_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proforma_number TEXT UNIQUE NOT NULL,
                invoice_date TEXT NOT NULL,
                customer_id INTEGER,
                customer_name TEXT,
                total_amount REAL NOT NULL,
                paid_amount REAL DEFAULT 0,
                payment_status TEXT DEFAULT 'Neplaćeno',
                notes TEXT,
                is_archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proforma_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proforma_id INTEGER NOT NULL,
                article_id INTEGER,
                article_name TEXT NOT NULL,
                article_code TEXT,
                quantity REAL NOT NULL,
                unit TEXT,
                price REAL NOT NULL,
                discount REAL DEFAULT 0,
                total REAL NOT NULL,
                is_paid INTEGER DEFAULT 0,
                FOREIGN KEY (proforma_id) REFERENCES proforma_invoices(id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== NOVA TABELA ZA PLAĆANJA PREDRAČUNA ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proforma_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proforma_id INTEGER NOT NULL,
                payment_amount REAL NOT NULL,
                payment_date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proforma_id) REFERENCES proforma_invoices(id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== TABELE ZA KOMUNALIJE ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utility_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utility_bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_date TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                utility_type_id INTEGER,
                utility_type_name TEXT NOT NULL,
                amount REAL NOT NULL,
                paid_amount REAL DEFAULT 0,
                payment_status TEXT DEFAULT 'Neplaćeno',
                payment_date TEXT,
                is_archived INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (utility_type_id) REFERENCES utility_types(id)
            )
        ''')
        
        # ==================== TABELA ZA PROMET ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL,
                date_from TEXT NOT NULL,
                date_to TEXT NOT NULL,
                cash REAL DEFAULT 0,
                card REAL DEFAULT 0,
                wire REAL DEFAULT 0,
                checks REAL DEFAULT 0,
                amount REAL NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        print("All tables ensured.")
    
    def _ensure_all_columns(self):
        cursor = self.conn.cursor()
        
        # Proveri vendors tabelu
        cursor.execute("PRAGMA table_info(vendors)")
        vendor_cols = [row['name'] for row in cursor.fetchall()]
        if 'vendor_code' not in vendor_cols:
            cursor.execute("ALTER TABLE vendors ADD COLUMN vendor_code TEXT")
        
        # Proveri invoices tabelu
        cursor.execute("PRAGMA table_info(invoices)")
        invoice_cols = [row['name'] for row in cursor.fetchall()]
        if 'vendor_id' not in invoice_cols:
            cursor.execute("ALTER TABLE invoices ADD COLUMN vendor_id INTEGER")
        if 'vendor_name' not in invoice_cols:
            cursor.execute("ALTER TABLE invoices ADD COLUMN vendor_name TEXT")
        
        # Proveri revenue_entries tabelu
        cursor.execute("PRAGMA table_info(revenue_entries)")
        revenue_cols = [row['name'] for row in cursor.fetchall()]
        if 'cash' not in revenue_cols:
            cursor.execute("ALTER TABLE revenue_entries ADD COLUMN cash REAL DEFAULT 0")
        if 'card' not in revenue_cols:
            cursor.execute("ALTER TABLE revenue_entries ADD COLUMN card REAL DEFAULT 0")
        if 'wire' not in revenue_cols:
            cursor.execute("ALTER TABLE revenue_entries ADD COLUMN wire REAL DEFAULT 0")
        if 'checks' not in revenue_cols:
            cursor.execute("ALTER TABLE revenue_entries ADD COLUMN checks REAL DEFAULT 0")
        
        self.conn.commit()
    
    def _ensure_vendor_codes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, vendor_code FROM vendors ORDER BY id")
        rows = cursor.fetchall()
        
        if not rows:
            return
        
        max_numeric = 0
        updates = []
        
        for row in rows:
            vendor_id = row['id']
            raw_code = (row['vendor_code'] or '').strip()
            
            if raw_code.isdigit():
                numeric = int(raw_code)
                max_numeric = max(max_numeric, numeric)
                padded = f"{numeric:04d}"
                if padded != raw_code:
                    updates.append((padded, vendor_id))
            else:
                updates.append((None, vendor_id))
        
        next_number = max_numeric + 1
        for new_code, vendor_id in updates:
            if new_code is None:
                new_code = f"{next_number:04d}"
                next_number += 1
            cursor.execute("UPDATE vendors SET vendor_code = ? WHERE id = ?", (new_code, vendor_id))
        
        if updates:
            self.conn.commit()
    
    def _generate_next_vendor_code(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT vendor_code FROM vendors")
        rows = cursor.fetchall()
        
        max_code = 0
        for row in rows:
            code = (row['vendor_code'] or '').strip()
            if code.isdigit():
                max_code = max(max_code, int(code))
        
        return f"{max_code + 1:04d}"
    
    # ==================== INVOICE METHODS (POSTOJEĆE) ====================
    def add_invoice(self, invoice_data):
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
        cursor = self.conn.cursor()
        if include_archived:
            cursor.execute('SELECT * FROM invoices ORDER BY due_date DESC')
        else:
            cursor.execute('SELECT * FROM invoices WHERE is_archived = 0 ORDER BY due_date DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_invoice_by_id(self, invoice_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_invoice(self, invoice_id, invoice_data):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE invoices SET invoice_date = ?, due_date = ?, vendor_name = ?,
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
        """Legacy metoda - koristi add_payment umesto ove"""
        if payment_date is None:
            payment_date = datetime.now().strftime('%d.%m.%Y')
        
        # Proveri da li već postoje uplate
        existing_paid = self.get_total_paid(invoice_id)
        invoice = self.get_invoice_by_id(invoice_id)
        
        if existing_paid == 0 and invoice:
            # Dodaj punu uplatu ako nema prethodnih
            self.add_payment(invoice_id, invoice['amount'], payment_date, "Potpuno plaćanje")
        
        cursor = self.conn.cursor()
        cursor.execute('UPDATE invoices SET is_paid = 1, payment_date = ? WHERE id = ?', (payment_date, invoice_id))
        self.conn.commit()
    
    def mark_as_unpaid(self, invoice_id):
        """Briše sve uplate i vraća račun na neplaćen status"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM payments WHERE invoice_id = ?', (invoice_id,))
        cursor.execute('UPDATE invoices SET is_paid = 0, payment_date = NULL WHERE id = ?', (invoice_id,))
        self.conn.commit()
    
    def archive_invoice(self, invoice_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE invoices SET is_archived = 1 WHERE id = ?', (invoice_id,))
        self.conn.commit()
    
    def unarchive_invoice(self, invoice_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE invoices SET is_archived = 0 WHERE id = ?', (invoice_id,))
        self.conn.commit()
    
    def delete_invoice(self, invoice_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
        self.conn.commit()
        
    # ==================== PAYMENT METHODS (NOVO) ====================
    
    def add_payment(self, invoice_id, payment_amount, payment_date, notes=None):
        """Dodaje novu uplatu za račun"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO payments (invoice_id, payment_amount, payment_date, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (invoice_id, payment_amount, payment_date, notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_payments(self, invoice_id):
        """Vraća sve uplate za određeni račun"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM payments WHERE invoice_id = ? ORDER BY payment_date DESC', (invoice_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_total_paid(self, invoice_id):
        """Vraća ukupan plaćeni iznos za račun"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT SUM(payment_amount) as total FROM payments WHERE invoice_id = ?', (invoice_id,))
        row = cursor.fetchone()
        return row['total'] if row['total'] else 0.0
    
    def get_remaining_amount(self, invoice_id):
        """Vraća preostali iznos za plaćanje"""
        invoice = self.get_invoice_by_id(invoice_id)
        if not invoice:
            return 0.0
        total_paid = self.get_total_paid(invoice_id)
        return invoice['amount'] - total_paid
    
    def get_payment_status(self, invoice_id):
        """Vraća status plaćanja: 'Neplaćeno', 'Delimično', 'Plaćeno'"""
        invoice = self.get_invoice_by_id(invoice_id)
        if not invoice:
            return 'Neplaćeno'
        
        total_paid = self.get_total_paid(invoice_id)
        total_amount = invoice['amount']
        
        if total_paid == 0:
            return 'Neplaćeno'
        elif total_paid >= total_amount:
            return 'Plaćeno'
        else:
            return 'Delimično'
    
    def delete_payment(self, payment_id):
        """Briše uplatu"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM payments WHERE id = ?', (payment_id,))
        self.conn.commit()
    
    def get_last_payment_date(self, invoice_id):
        """Vraća datum poslednje uplate"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT payment_date FROM payments WHERE invoice_id = ? ORDER BY payment_date DESC LIMIT 1', (invoice_id,))
        row = cursor.fetchone()
        return row['payment_date'] if row else None
    
    # ==================== VENDOR METHODS (POSTOJEĆE) ====================
    def get_all_vendors(self, with_details=True, include_orphan_invoice_names=True):
        cursor = self.conn.cursor()
        if with_details:
            cursor.execute("SELECT * FROM vendors ORDER BY name COLLATE NOCASE")
            results = []
            for row in cursor.fetchall():
                vendor_id = row['id']
                vendor_code = (row['vendor_code'] or '').strip()
                if vendor_code.isdigit():
                    vendor_code = f"{int(vendor_code):04d}"
                results.append({
                    'vendor_id': vendor_id,
                    'id': vendor_id,
                    'vendor_code': vendor_code,
                    'vendor_name': row['name'],
                    'name': row['name'],
                    'address': row['address'] or '',
                    'city': row['city'] or '',
                    'pib': row['pib'] or '',
                    'registration_number': row['registration_number'] or '',
                    'bank_account': row['bank_account'] or '',
                    'contact_person': row['contact_person'] or '',
                    'phone': row['phone'] or '',
                    'email': row['email'] or '',
                    'notes': row['notes'] or ''
                })
            return results
        else:
            cursor.execute("SELECT DISTINCT name AS vendor_name FROM vendors WHERE name IS NOT NULL AND name != '' ORDER BY vendor_name COLLATE NOCASE")
            return [row['vendor_name'] for row in cursor.fetchall()]
    
    def get_vendor_by_id(self, vendor_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM vendors WHERE id = ?', (vendor_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            'vendor_id': row['id'],
            'id': row['id'],
            'vendor_code': row['vendor_code'] or '',
            'vendor_name': row['name'],
            'name': row['name'],
            'address': row['address'] or '',
            'city': row['city'] or '',
            'pib': row['pib'] or '',
            'registration_number': row['registration_number'] or '',
            'bank_account': row['bank_account'] or '',
            'contact_person': row['contact_person'] or '',
            'phone': row['phone'] or '',
            'email': row['email'] or '',
            'notes': row['notes'] or ''
        }
    
    def add_vendor(self, *args, **kwargs):
        name = kwargs.get('name') or kwargs.get('vendor_name')
        if not name and args:
            name = args[0] if isinstance(args[0], str) else args[0].get('name')
        
        if not name:
            raise ValueError("Vendor name is required.")
        
        address = kwargs.get('address', '')
        city = kwargs.get('city', '')
        pib = kwargs.get('pib', '')
        registration_number = kwargs.get('registration_number', '')
        bank_account = kwargs.get('bank_account', '')
        contact_person = kwargs.get('contact_person', '')
        phone = kwargs.get('phone', '')
        email = kwargs.get('email', '')
        notes = kwargs.get('notes', '')
        vendor_code = self._generate_next_vendor_code()
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO vendors (name, vendor_code, address, city, pib, registration_number, bank_account, contact_person, phone, email, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, vendor_code, address, city, pib, registration_number, bank_account, contact_person, phone, email, notes))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_vendor(self, vendor_id, **kwargs):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        for key in ['name', 'vendor_code', 'address', 'city', 'pib', 'registration_number', 'bank_account', 'contact_person', 'phone', 'email', 'notes']:
            if key in kwargs and kwargs[key] is not None:
                updates.append(f'{key} = ?')
                params.append(kwargs[key])
        
        if updates:
            params.append(vendor_id)
            cursor.execute(f"UPDATE vendors SET {', '.join(updates)} WHERE id = ?", tuple(params))
            self.conn.commit()
    
    def delete_vendor_by_id(self, vendor_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM vendors WHERE id = ?', (vendor_id,))
        self.conn.commit()
    
    # ==================== CUSTOMER METHODS ====================
    def _generate_next_customer_code(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT customer_code FROM customers")
        rows = cursor.fetchall()
        max_code = 0
        for row in rows:
            code = (row['customer_code'] or '').strip()
            if code.isdigit():
                max_code = max(max_code, int(code))
        return f"{max_code + 1:04d}"
    
    def add_customer(self, **kwargs):
        name = kwargs.get('name')
        if not name:
            raise ValueError("Customer name is required.")
        
        customer_code = self._generate_next_customer_code()
        phone = kwargs.get('phone', '')
        pib = kwargs.get('pib', '')
        id_card_number = kwargs.get('id_card_number', '')
        registration_number = kwargs.get('registration_number', '')
        address = kwargs.get('address', '')
        city = kwargs.get('city', '')
        notes = kwargs.get('notes', '')
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO customers (customer_code, name, phone, pib, id_card_number, registration_number, address, city, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_code, name, phone, pib, id_card_number, registration_number, address, city, notes))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_customers(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM customers ORDER BY name COLLATE NOCASE")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_customer_by_id(self, customer_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_customer(self, customer_id, **kwargs):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        for key in ['name', 'customer_code', 'phone', 'pib', 'id_card_number', 'registration_number', 'address', 'city', 'notes']:
            if key in kwargs and kwargs[key] is not None:
                updates.append(f'{key} = ?')
                params.append(kwargs[key])
        
        if updates:
            params.append(customer_id)
            cursor.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id = ?", tuple(params))
            self.conn.commit()
    
    def delete_customer(self, customer_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        self.conn.commit()
    
    # ==================== ARTICLE METHODS ====================
    def add_article(self, **kwargs):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO articles (article_code, name, unit, price, discount, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            kwargs.get('article_code'),
            kwargs.get('name'),
            kwargs.get('unit', 'kom'),
            kwargs.get('price', 0),
            kwargs.get('discount', 0),
            kwargs.get('notes', '')
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def upsert_article(self, **kwargs):
        """
        Dodaje ili ažurira artikal na osnovu article_code.
        Koristi se za Excel uvoz.
        """
        article_code = (kwargs.get('article_code') or '').strip()
        if not article_code:
            return None

        existing = self.get_article_by_code(article_code)

        cursor = self.conn.cursor()

        if existing:
            # UPDATE
            cursor.execute('''
                UPDATE articles
                SET name = ?,
                    unit = ?,
                    price = ?,
                    discount = ?,
                    notes = ?
                WHERE article_code = ?
            ''', (
                kwargs.get('name', existing['name']),
                kwargs.get('unit', existing['unit']),
                kwargs.get('price', existing['price']),
                kwargs.get('discount', existing['discount']),
                kwargs.get('notes', existing['notes']),
                article_code
            ))
            self.conn.commit()
            return existing['id']
        else:
            # INSERT
            cursor.execute('''
                INSERT INTO articles (article_code, name, unit, price, discount, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                article_code,
                kwargs.get('name'),
                kwargs.get('unit', 'kom'),
                kwargs.get('price', 0),
                kwargs.get('discount', 0),
                kwargs.get('notes', '')
            ))
            self.conn.commit()
            return cursor.lastrowid

    
    def get_all_articles(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles ORDER BY name COLLATE NOCASE")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_article_by_id(self, article_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_article(self, article_id, **kwargs):
        cursor = self.conn.cursor()
        updates = []
        params = []
        
        for key in ['article_code', 'name', 'unit', 'price', 'discount', 'notes']:
            if key in kwargs and kwargs[key] is not None:
                updates.append(f'{key} = ?')
                params.append(kwargs[key])
        
        if updates:
            params.append(article_id)
            cursor.execute(f"UPDATE articles SET {', '.join(updates)} WHERE id = ?", tuple(params))
            self.conn.commit()
    
    def delete_article(self, article_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM articles WHERE id = ?', (article_id,))
        self.conn.commit()
    
    # ==================== PROFORMA INVOICE METHODS ====================
    def _generate_next_proforma_number(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT proforma_number FROM proforma_invoices ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            last_num = row['proforma_number'].split('-')[-1]
            if last_num.isdigit():
                return f"PR-{int(last_num) + 1:05d}"
        return "PR-00001"
    
    def add_proforma_invoice(self, proforma_data, items):
        cursor = self.conn.cursor()
        proforma_number = self._generate_next_proforma_number()
        
        cursor.execute('''
            INSERT INTO proforma_invoices (proforma_number, invoice_date, customer_id, customer_name, total_amount, paid_amount, payment_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            proforma_number,
            proforma_data['invoice_date'],
            proforma_data.get('customer_id'),
            proforma_data['customer_name'],
            proforma_data['total_amount'],
            proforma_data.get('paid_amount', 0),
            proforma_data.get('payment_status', 'Neplaćeno'),
            proforma_data.get('notes', '')
        ))
        proforma_id = cursor.lastrowid
        
        for item in items:
            cursor.execute('''
                INSERT INTO proforma_items (proforma_id, article_id, article_name, article_code, quantity, unit, price, discount, total, is_paid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                proforma_id,
                item.get('article_id'),
                item['article_name'],
                item.get('article_code', ''),
                item['quantity'],
                item.get('unit', 'kom'),
                item['price'],
                item.get('discount', 0),
                item['total'],
                item.get('is_paid', 0)
            ))
        
        self.conn.commit()
        return proforma_id
    
    def get_all_proforma_invoices(self, include_archived=False):
        cursor = self.conn.cursor()
        if include_archived:
            cursor.execute('SELECT * FROM proforma_invoices ORDER BY invoice_date DESC')
        else:
            cursor.execute('SELECT * FROM proforma_invoices WHERE is_archived = 0 ORDER BY invoice_date DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_proforma_by_id(self, proforma_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM proforma_invoices WHERE id = ?', (proforma_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_proforma_items(self, proforma_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM proforma_items WHERE proforma_id = ?', (proforma_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def update_proforma_payment_status(self, proforma_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT SUM(total) as total, SUM(CASE WHEN is_paid = 1 THEN total ELSE 0 END) as paid FROM proforma_items WHERE proforma_id = ?', (proforma_id,))
        row = cursor.fetchone()
        total = row['total'] or 0
        paid = row['paid'] or 0
        
        if paid >= total:
            status = 'Plaćeno'
        elif paid > 0:
            status = 'Delimično'
        else:
            status = 'Neplaćeno'
        
        cursor.execute('UPDATE proforma_invoices SET paid_amount = ?, payment_status = ? WHERE id = ?', (paid, status, proforma_id))
        self.conn.commit()
    
    def update_proforma_item_payment(self, item_id, is_paid):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE proforma_items SET is_paid = ? WHERE id = ?', (is_paid, item_id))
        cursor.execute('SELECT proforma_id FROM proforma_items WHERE id = ?', (item_id,))
        proforma_id = cursor.fetchone()['proforma_id']
        self.conn.commit()
        self.update_proforma_payment_status(proforma_id)
    
    def archive_proforma(self, proforma_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE proforma_invoices SET is_archived = 1 WHERE id = ?', (proforma_id,))
        self.conn.commit()
    
    def delete_proforma(self, proforma_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM proforma_items WHERE proforma_id = ?', (proforma_id,))
        cursor.execute('DELETE FROM proforma_invoices WHERE id = ?', (proforma_id,))
        self.conn.commit()
    
    # ==================== UTILITY BILLS METHODS ====================
    def add_utility_type(self, name):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO utility_types (name) VALUES (?)', (name,))
        self.conn.commit()
    
    def get_all_utility_types(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM utility_types ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]
    
    def add_utility_bill(self, **kwargs):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO utility_bills (bill_date, entry_date, utility_type_id, utility_type_name, amount, paid_amount, payment_status, payment_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            kwargs['bill_date'],
            kwargs['entry_date'],
            kwargs.get('utility_type_id'),
            kwargs['utility_type_name'],
            kwargs['amount'],
            kwargs.get('paid_amount', 0),
            kwargs.get('payment_status', 'Neplaćeno'),
            kwargs.get('payment_date'),
            kwargs.get('notes', '')
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_utility_bills(self, include_archived=False):
        cursor = self.conn.cursor()
        if include_archived:
            cursor.execute('SELECT * FROM utility_bills ORDER BY bill_date DESC')
        else:
            cursor.execute('SELECT * FROM utility_bills WHERE is_archived = 0 ORDER BY bill_date DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_utility_bill_by_id(self, bill_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM utility_bills WHERE id = ?', (bill_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_utility_bill_payment(self, bill_id, paid_amount, payment_date=None):
        cursor = self.conn.cursor()
        cursor.execute('SELECT amount FROM utility_bills WHERE id = ?', (bill_id,))
        total = cursor.fetchone()['amount']
        
        if paid_amount >= total:
            status = 'Plaćeno'
        elif paid_amount > 0:
            status = 'Delimično'
        else:
            status = 'Neplaćeno'
        
        if payment_date is None and paid_amount > 0:
            payment_date = datetime.now().strftime('%d.%m.%Y')
        
        cursor.execute('UPDATE utility_bills SET paid_amount = ?, payment_status = ?, payment_date = ? WHERE id = ?', 
                      (paid_amount, status, payment_date, bill_id))
        self.conn.commit()
    
    def archive_utility_bill(self, bill_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE utility_bills SET is_archived = 1 WHERE id = ?', (bill_id,))
        self.conn.commit()
    
    def delete_utility_bill(self, bill_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM utility_bills WHERE id = ?', (bill_id,))
        self.conn.commit()
    
    # ==================== REVENUE ENTRY METHODS ====================
    def add_revenue_entry(self, **kwargs):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO revenue_entries (entry_date, date_from, date_to, cash, card, wire, checks, amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            kwargs['entry_date'],
            kwargs['date_from'],
            kwargs['date_to'],
            kwargs.get('cash', 0),
            kwargs.get('card', 0),
            kwargs.get('wire', 0),
            kwargs.get('checks', 0),
            kwargs['amount'],
            kwargs.get('notes', '')
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_revenue_entries(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM revenue_entries ORDER BY date_from DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_revenue_entry(self, entry_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM revenue_entries WHERE id = ?', (entry_id,))
        self.conn.commit()
        
    # U sekciji REVENUE ENTRY METHODS, dodaj:

    def mark_revenue_as_paid(self, entry_id, payment_date):
        """Označi unos prometa kao plaćen"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE revenue_entries 
            SET payment_status = 'Plaćeno',
                payment_date = ?
            WHERE id = ?
        ''', (payment_date, entry_id))
        self.conn.commit()
        
    def get_revenue_entry_by_id(self, entry_id):
        """Vraća jedan unos prometa po ID-u"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM revenue_entries WHERE id = ?', (entry_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def update_revenue_entry(self, entry_id, **kwargs):
        """Ažurira postojeći unos prometa (NE dira payment_status)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE revenue_entries 
            SET entry_date = ?, 
                date_from = ?, 
                date_to = ?, 
                cash = ?,
                card = ?,
                wire = ?,
                checks = ?,
                amount = ?, 
                notes = ?
            WHERE id = ?
        ''', (
            kwargs['entry_date'],
            kwargs['date_from'],
            kwargs['date_to'],
            kwargs.get('cash', 0),
            kwargs.get('card', 0),
            kwargs.get('wire', 0),
            kwargs.get('checks', 0),
            kwargs['amount'],
            kwargs.get('notes', ''),
            entry_id
        ))
        self.conn.commit()
    
    # ==================== SETTINGS & STATS ====================
    def get_settings(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        settings = {}
        for row in cursor.fetchall():
            key = row['key']
            value = row['value']
            if value == 'True':
                value = True
            elif value == 'False':
                value = False
            elif value is not None and value.isdigit():
                value = int(value)
            settings[key] = value
        return settings
    
    def save_settings(self, settings):
        cursor = self.conn.cursor()
        for key, value in settings.items():
            cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value) if value is not None else ''))
        self.conn.commit()
    
    def update_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
        self.conn.commit()
    
    # ==================== PROFORMA PAYMENT METHODS (NOVO) ====================
    
    def add_proforma_payment(self, proforma_id, payment_amount, payment_date, notes=None):
        """Dodaje novu uplatu za predračun"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO proforma_payments (proforma_id, payment_amount, payment_date, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (proforma_id, payment_amount, payment_date, notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
        
        # Ažuriraj paid_amount i status u proforma_invoices
        self.update_proforma_payment_status_new(proforma_id)
        
        return cursor.lastrowid
    
    def get_proforma_payments(self, proforma_id):
        """Vraća sve uplate za određeni predračun"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM proforma_payments WHERE proforma_id = ? ORDER BY payment_date DESC', (proforma_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_total_paid_proforma(self, proforma_id):
        """Vraća ukupan plaćeni iznos za predračun"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT SUM(payment_amount) as total FROM proforma_payments WHERE proforma_id = ?', (proforma_id,))
        row = cursor.fetchone()
        return row['total'] if row['total'] else 0.0
    
    def get_remaining_amount_proforma(self, proforma_id):
        """Vraća preostali iznos za plaćanje predračuna"""
        proforma = self.get_proforma_by_id(proforma_id)
        if not proforma:
            return 0.0
        total_paid = self.get_total_paid_proforma(proforma_id)
        return proforma['total_amount'] - total_paid
    
    def get_payment_status_proforma(self, proforma_id):
        """Vraća status plaćanja predračuna: 'Neplaćeno', 'Delimično', 'Plaćeno'"""
        proforma = self.get_proforma_by_id(proforma_id)
        if not proforma:
            return 'Neplaćeno'
        
        total_paid = self.get_total_paid_proforma(proforma_id)
        total_amount = proforma['total_amount']
        
        if total_paid == 0:
            return 'Neplaćeno'
        elif total_paid >= total_amount:
            return 'Plaćeno'
        else:
            return 'Delimično'
    
    def get_last_payment_date_proforma(self, proforma_id):
        """Vraća datum poslednje uplate za predračun"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT payment_date FROM proforma_payments WHERE proforma_id = ? ORDER BY payment_date DESC LIMIT 1', (proforma_id,))
        row = cursor.fetchone()
        return row['payment_date'] if row else None
    
    def update_proforma_payment_status_new(self, proforma_id):
        """Ažurira paid_amount i payment_status u proforma_invoices tabeli"""
        total_paid = self.get_total_paid_proforma(proforma_id)
        status = self.get_payment_status_proforma(proforma_id)
        
        cursor = self.conn.cursor()
        cursor.execute('UPDATE proforma_invoices SET paid_amount = ?, payment_status = ? WHERE id = ?', 
                      (total_paid, status, proforma_id))
        self.conn.commit()
    
    def delete_proforma_payment(self, payment_id):
        """Briše uplatu predračuna"""
        cursor = self.conn.cursor()
        # Prvo uzmi proforma_id pre brisanja
        cursor.execute('SELECT proforma_id FROM proforma_payments WHERE id = ?', (payment_id,))
        row = cursor.fetchone()
        if row:
            proforma_id = row['proforma_id']
            cursor.execute('DELETE FROM proforma_payments WHERE id = ?', (payment_id,))
            self.conn.commit()
            # Ažuriraj status
            self.update_proforma_payment_status_new(proforma_id)
    
    def get_article_by_code(self, article_code):
        """Pronalazi artikal po šifri"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM articles WHERE article_code = ?', (article_code,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_proforma_invoice(self, proforma_id, proforma_data, items):
        """Ažurira predračun i njegove stavke"""
        cursor = self.conn.cursor()
        
        # Ažuriraj header
        cursor.execute('''
            UPDATE proforma_invoices 
            SET invoice_date = ?, customer_id = ?, customer_name = ?, total_amount = ?, notes = ?
            WHERE id = ?
        ''', (
            proforma_data['invoice_date'],
            proforma_data.get('customer_id'),
            proforma_data['customer_name'],
            proforma_data['total_amount'],
            proforma_data.get('notes', ''),
            proforma_id
        ))
        
        # Obriši stare stavke
        cursor.execute('DELETE FROM proforma_items WHERE proforma_id = ?', (proforma_id,))
        
        # Dodaj nove stavke
        for item in items:
            cursor.execute('''
                INSERT INTO proforma_items (proforma_id, article_id, article_name, article_code, quantity, unit, price, discount, total, is_paid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                proforma_id,
                item.get('article_id'),
                item['article_name'],
                item.get('article_code', ''),
                item['quantity'],
                item.get('unit', 'kom'),
                item['price'],
                item.get('discount', 0),
                item['total'],
                0  # Nove stavke su neplaćene
            ))
        
        self.conn.commit()
    
    def unarchive_proforma(self, proforma_id):
        """Vraća predračun iz arhive"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE proforma_invoices SET is_archived = 0 WHERE id = ?', (proforma_id,))
        self.conn.commit()
    
    def __del__(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass