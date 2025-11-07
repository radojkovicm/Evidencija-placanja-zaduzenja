import sqlite3
from datetime import datetime
import os
import shutil


class Database:
    def __init__(self, db_name: str = 'invoices.db'):
        self.db_name = db_name
        self.conn: sqlite3.Connection | None = None

        self.connect()
        self.create_tables()
        self._ensure_vendors_primary_key()
        self._ensure_vendors_columns()
        self._ensure_invoices_columns()
        self._ensure_vendor_codes()

    # ------------------------------------------------------------------
    # Connection & schema helpers
    # ------------------------------------------------------------------
    def connect(self):
        """Open a database connection."""
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            print(f"Connection to '{self.db_name}' opened.")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise

    def create_tables(self):
        """Create base tables if they do not exist."""
        cursor = self.conn.cursor()

        cursor.execute(
            '''
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
            '''
        )

        cursor.execute(
            '''
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
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            '''
        )

        self.conn.commit()
        print("Tables ensured.")

    def _get_table_columns(self, table_name: str) -> list[str]:
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row['name'] for row in cursor.fetchall()]

    def _get_table_info(self, table_name: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [dict(row) for row in cursor.fetchall()]

    def _ensure_vendors_primary_key(self):
        """
        Make sure the vendors table has an INTEGER PRIMARY KEY column named 'id'.
        If not, migrate the existing table into a new structure.
        """
        info = self._get_table_info('vendors')
        column_names = [col['name'] for col in info]
        has_id = any(col['name'] == 'id' for col in info)
        id_is_pk = any(col['name'] == 'id' and col['pk'] for col in info)

        if has_id and id_is_pk:
            return  # everything OK

        cursor = self.conn.cursor()
        backup_table = 'vendors__old_schema'

        cursor.execute(f"DROP TABLE IF EXISTS {backup_table}")
        cursor.execute(f"ALTER TABLE vendors RENAME TO {backup_table}")

        cursor.execute(
            '''
            CREATE TABLE vendors (
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
            '''
        )

        # Determine which columns can be copied from the old table
        old_columns = self._get_table_columns(backup_table)
        new_columns = [
            'name',
            'vendor_code',
            'address',
            'city',
            'pib',
            'registration_number',
            'bank_account',
            'contact_person',
            'phone',
            'email',
            'notes',
            'created_at',
        ]
        copy_columns = [col for col in new_columns if col in old_columns]

        if copy_columns:
            col_list = ', '.join(copy_columns)
            cursor.execute(
                f'''
                INSERT INTO vendors ({col_list})
                SELECT {col_list} FROM {backup_table}
                '''
            )

        cursor.execute(f"DROP TABLE IF EXISTS {backup_table}")
        self.conn.commit()
        print("Vendors table migrated to include primary key 'id'.")

    def _ensure_vendors_columns(self):
        """Ensure all vendor columns expected by the GUI exist."""
        cursor = self.conn.cursor()
        existing = self._get_table_columns('vendors')
        needed = {
            'vendor_code': 'vendor_code TEXT',
            'address': 'address TEXT',
            'city': 'city TEXT',
            'pib': 'pib TEXT',
            'registration_number': 'registration_number TEXT',
            'bank_account': 'bank_account TEXT',
            'contact_person': 'contact_person TEXT',
            'phone': 'phone TEXT',
            'email': 'email TEXT',
            'notes': 'notes TEXT',
            'created_at': "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        }

        altered = False
        for col, col_sql in needed.items():
            if col not in existing:
                try:
                    cursor.execute(f"ALTER TABLE vendors ADD COLUMN {col_sql}")
                    altered = True
                except Exception:
                    pass

        if altered:
            self.conn.commit()

    def _ensure_invoices_columns(self):
        """Ensure invoices table has required columns."""
        cursor = self.conn.cursor()
        existing = self._get_table_columns('invoices')
        altered = False

        if 'vendor_id' not in existing:
            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN vendor_id INTEGER')
                altered = True
            except Exception:
                pass

        if 'vendor_name' not in existing:
            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN vendor_name TEXT')
                altered = True
            except Exception:
                pass

        if 'created_at' not in existing:
            try:
                cursor.execute("ALTER TABLE invoices ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
                altered = True
            except Exception:
                pass

        if altered:
            self.conn.commit()
            print("Invoices table updated with missing columns.")

    def _ensure_vendor_codes(self):
        """
        Ensure every vendor has a numeric, zero-padded vendor_code.
        Existing numeric codes are padded, missing/non-numeric codes are reassigned.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, vendor_code FROM vendors ORDER BY id")
        rows = cursor.fetchall()

        if not rows:
            return

        max_numeric = 0
        updates: list[tuple[str, int]] = []

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

    def _generate_next_vendor_code(self) -> str:
        """Generate the next sequential vendor code (zero-padded)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT vendor_code FROM vendors")
        rows = cursor.fetchall()

        max_code = 0
        for row in rows:
            code = (row['vendor_code'] or '').strip()
            if code.isdigit():
                max_code = max(max_code, int(code))

        return f"{max_code + 1:04d}"

    def _row_to_vendor_dict(self, row: dict) -> dict:
        """Normalize vendor row into a dict structure GUI expects."""
        vendor_id = row.get('id')
        vendor_code = (row.get('vendor_code') or '').strip()
        if vendor_code.isdigit():
            vendor_code = f"{int(vendor_code):04d}"
        elif not vendor_code and vendor_id is not None:
            vendor_code = f"{vendor_id:04d}"

        vendor_name = (row.get('name') or '').strip()
        return {
            'vendor_id': vendor_id,
            'vendor_code': vendor_code,
            'vendor_name': vendor_name,
            'name': vendor_name,
            'address': (row.get('address') or '').strip(),
            'city': (row.get('city') or '').strip(),
            'pib': (row.get('pib') or '').strip(),
            'registration_number': (row.get('registration_number') or '').strip(),
            'bank_account': (row.get('bank_account') or '').strip(),
            'contact_person': (row.get('contact_person') or '').strip(),
            'phone': (row.get('phone') or '').strip(),
            'email': (row.get('email') or '').strip(),
            'notes': (row.get('notes') or '').strip(),
        }

    # ------------------------------------------------------------------
    # Invoice methods
    # ------------------------------------------------------------------
    def add_invoice(self, invoice_data: dict) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            INSERT INTO invoices (
                invoice_date, due_date, vendor_name,
                delivery_note_number, amount, notes, vendor_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                invoice_data.get('invoice_date'),
                invoice_data.get('due_date'),
                invoice_data.get('vendor_name'),
                invoice_data.get('delivery_note_number'),
                invoice_data.get('amount'),
                invoice_data.get('notes'),
                invoice_data.get('vendor_id'),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_invoices(self, include_archived: bool = False) -> list[dict]:
        cursor = self.conn.cursor()
        if include_archived:
            cursor.execute('SELECT * FROM invoices ORDER BY due_date DESC')
        else:
            cursor.execute('SELECT * FROM invoices WHERE is_archived = 0 ORDER BY due_date DESC')
        return [dict(row) for row in cursor.fetchall()]

    def get_invoice_by_id(self, invoice_id: int) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_invoice(self, invoice_id: int, invoice_data: dict):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            UPDATE invoices
            SET invoice_date = ?, due_date = ?, vendor_name = ?,
                delivery_note_number = ?, amount = ?, notes = ?, vendor_id = ?
            WHERE id = ?
            ''',
            (
                invoice_data.get('invoice_date'),
                invoice_data.get('due_date'),
                invoice_data.get('vendor_name'),
                invoice_data.get('delivery_note_number'),
                invoice_data.get('amount'),
                invoice_data.get('notes'),
                invoice_data.get('vendor_id'),
                invoice_id,
            ),
        )
        self.conn.commit()

    def mark_as_paid(self, invoice_id: int, payment_date: str | None = None):
        if payment_date is None:
            payment_date = datetime.now().strftime('%d.%m.%Y')

        cursor = self.conn.cursor()
        cursor.execute(
            '''
            UPDATE invoices
            SET is_paid = 1, payment_date = ?
            WHERE id = ?
            ''',
            (payment_date, invoice_id),
        )
        self.conn.commit()

    def mark_as_unpaid(self, invoice_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            UPDATE invoices
            SET is_paid = 0, payment_date = NULL
            WHERE id = ?
            ''',
            (invoice_id,),
        )
        self.conn.commit()

    def archive_invoice(self, invoice_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            UPDATE invoices
            SET is_archived = 1
            WHERE id = ?
            ''',
            (invoice_id,),
        )
        self.conn.commit()

    def unarchive_invoice(self, invoice_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            UPDATE invoices
            SET is_archived = 0
            WHERE id = ?
            ''',
            (invoice_id,),
        )
        self.conn.commit()

    def delete_invoice(self, invoice_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Vendor methods
    # ------------------------------------------------------------------
    def get_all_vendors(
        self,
        with_details: bool = True,
        include_orphan_invoice_names: bool = True,
    ) -> list:
        cursor = self.conn.cursor()

        if with_details:
            cursor.execute("SELECT * FROM vendors ORDER BY name COLLATE NOCASE")
            rows = cursor.fetchall()

            results = [self._row_to_vendor_dict(dict(row)) for row in rows]
            seen_names = {vendor['vendor_name'] for vendor in results if vendor['vendor_name']}

            if include_orphan_invoice_names:
                cursor.execute(
                    '''
                    SELECT DISTINCT vendor_name
                    FROM invoices
                    WHERE vendor_name IS NOT NULL AND vendor_name != ''
                    ORDER BY vendor_name COLLATE NOCASE
                    '''
                )
                for row in cursor.fetchall():
                    name = (row['vendor_name'] or '').strip()
                    if name and name not in seen_names:
                        results.append(
                            {
                                'vendor_id': None,
                                'vendor_code': '',
                                'vendor_name': name,
                                'name': name,
                                'address': '',
                                'city': '',
                                'pib': '',
                                'registration_number': '',
                                'bank_account': '',
                                'contact_person': '',
                                'phone': '',
                                'email': '',
                                'notes': '',
                            }
                        )
                        seen_names.add(name)
            return results

        cursor.execute(
            '''
            SELECT DISTINCT name AS vendor_name
            FROM vendors
            WHERE name IS NOT NULL AND name != ''
            UNION
            SELECT DISTINCT vendor_name
            FROM invoices
            WHERE vendor_name IS NOT NULL AND vendor_name != ''
            ORDER BY vendor_name COLLATE NOCASE
            '''
        )
        return [row['vendor_name'] for row in cursor.fetchall()]

    def get_vendor_by_id(self, vendor_id: int) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM vendors WHERE id = ?', (vendor_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_vendor_dict(dict(row))

    def add_vendor(self, *args, **kwargs) -> int:
        """
        Insert a new vendor. Supports both positional and keyword arguments
        for backward compatibility.
        """
        name = None
        address = ''
        city = ''
        pib = ''
        registration_number = ''
        bank_account = ''
        vendor_code = ''
        contact_person = ''
        phone = ''
        email = ''
        notes = ''

        if kwargs:
            name = kwargs.get('name') or kwargs.get('vendor_name') or kwargs.get('vendor')
            address = kwargs.get('address', '')
            city = kwargs.get('city', '')
            pib = kwargs.get('pib', '')
            registration_number = kwargs.get('registration_number', '')
            bank_account = kwargs.get('bank_account', '')
            vendor_code = kwargs.get('vendor_code', '')
            contact_person = kwargs.get('contact_person', '')
            phone = kwargs.get('phone', '')
            email = kwargs.get('email', '')
            notes = kwargs.get('notes', '')

        if args:
            if len(args) == 1 and isinstance(args[0], dict):
                data = args[0]
                name = data.get('name') or data.get('vendor_name') or name
                address = data.get('address', address)
                city = data.get('city', city)
                pib = data.get('pib', pib)
                registration_number = data.get('registration_number', registration_number)
                bank_account = data.get('bank_account', bank_account)
                vendor_code = data.get('vendor_code', vendor_code)
                contact_person = data.get('contact_person', contact_person)
                phone = data.get('phone', phone)
                email = data.get('email', email)
                notes = data.get('notes', notes)
            else:
                try:
                    name = name or args[0]
                    city = args[1] if len(args) > 1 else city
                    pib = args[2] if len(args) > 2 else pib
                    registration_number = args[3] if len(args) > 3 else registration_number
                    bank_account = args[4] if len(args) > 4 else bank_account
                    vendor_code = args[5] if len(args) > 5 else vendor_code
                    address = args[6] if len(args) > 6 else address
                    contact_person = args[7] if len(args) > 7 else contact_person
                    phone = args[8] if len(args) > 8 else phone
                    email = args[9] if len(args) > 9 else email
                    notes = args[10] if len(args) > 10 else notes
                except Exception:
                    pass

        name = str(name).strip() if name is not None else ''
        if not name:
            raise ValueError("Vendor name is required.")

        address = str(address or '').strip()
        city = str(city or '').strip()
        pib = str(pib or '').strip()
        registration_number = str(registration_number or '').strip()
        bank_account = str(bank_account or '').strip()
        contact_person = str(contact_person or '').strip()
        phone = str(phone or '').strip()
        email = str(email or '').strip()
        notes = str(notes or '').strip()

        auto_code = self._generate_next_vendor_code()
        vendor_code = str(vendor_code or '').strip()
        if vendor_code.isdigit():
            vendor_code = f"{int(vendor_code):04d}"
        else:
            vendor_code = auto_code

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO vendors (
                    name, vendor_code, address, city, pib, registration_number,
                    bank_account, contact_person, phone, email, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    name,
                    vendor_code,
                    address,
                    city,
                    pib,
                    registration_number,
                    bank_account,
                    contact_person,
                    phone,
                    email,
                    notes,
                ),
            )
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting vendor: {e}")
            self.conn.rollback()
            raise

    def update_vendor(
        self,
        vendor_id: int,
        name: str | None = None,
        vendor_code: str | None = None,
        address: str | None = None,
        city: str | None = None,
        pib: str | None = None,
        registration_number: str | None = None,
        bank_account: str | None = None,
        contact_person: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        notes: str | None = None,
    ):
        cursor = self.conn.cursor()
        updates = []
        params = []

        if name is not None:
            updates.append('name = ?')
            params.append(name.strip())
        if vendor_code is not None:
            code = vendor_code.strip()
            if code.isdigit():
                code = f"{int(code):04d}"
            updates.append('vendor_code = ?')
            params.append(code)
        if address is not None:
            updates.append('address = ?')
            params.append(address.strip())
        if city is not None:
            updates.append('city = ?')
            params.append(city.strip())
        if pib is not None:
            updates.append('pib = ?')
            params.append(pib.strip())
        if registration_number is not None:
            updates.append('registration_number = ?')
            params.append(registration_number.strip())
        if bank_account is not None:
            updates.append('bank_account = ?')
            params.append(bank_account.strip())
        if contact_person is not None:
            updates.append('contact_person = ?')
            params.append(contact_person.strip())
        if phone is not None:
            updates.append('phone = ?')
            params.append(phone.strip())
        if email is not None:
            updates.append('email = ?')
            params.append(email.strip())
        if notes is not None:
            updates.append('notes = ?')
            params.append(notes.strip())

        if not updates:
            return

        params.append(vendor_id)
        sql = f"UPDATE vendors SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, tuple(params))
        self.conn.commit()

    def update_vendor_name(self, old_name: str, new_name: str):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            UPDATE invoices
            SET vendor_name = ?
            WHERE vendor_name = ?
            ''',
            (new_name, old_name),
        )
        cursor.execute(
            '''
            UPDATE vendors
            SET name = ?
            WHERE name = ?
            ''',
            (new_name, old_name),
        )
        self.conn.commit()

    def delete_vendor(self, vendor_name: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute('DELETE FROM invoices WHERE vendor_name = ?', (vendor_name,))
            cursor.execute('DELETE FROM vendors WHERE name = ?', (vendor_name,))
            self.conn.commit()
        except Exception as e:
            print(f"Error deleting vendor: {e}")
            self.conn.rollback()
            raise

    def delete_vendor_by_id(self, vendor_id: int):
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT name FROM vendors WHERE id = ?', (vendor_id,))
            row = cursor.fetchone()
            vendor_name = row['name'] if row else None

            if vendor_name:
                cursor.execute('DELETE FROM invoices WHERE vendor_name = ?', (vendor_name,))
            cursor.execute('DELETE FROM vendors WHERE id = ?', (vendor_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Error deleting vendor by id: {e}")
            self.conn.rollback()
            raise

    def get_vendor_invoices(self, vendor_name: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM invoices
            WHERE vendor_name = ?
            ORDER BY due_date DESC
            ''',
            (vendor_name,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_vendor_stats(self, vendor_name: str) -> dict:
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) AS count FROM invoices WHERE vendor_name = ?', (vendor_name,))
        total_invoices = cursor.fetchone()['count']

        cursor.execute('SELECT SUM(amount) AS total FROM invoices WHERE vendor_name = ?', (vendor_name,))
        total_amount = cursor.fetchone()['total'] or 0

        cursor.execute(
            'SELECT COUNT(*) AS count FROM invoices WHERE vendor_name = ? AND is_paid = 1',
            (vendor_name,),
        )
        paid_invoices = cursor.fetchone()['count']

        cursor.execute(
            'SELECT SUM(amount) AS total FROM invoices WHERE vendor_name = ? AND is_paid = 1',
            (vendor_name,),
        )
        paid_amount = cursor.fetchone()['total'] or 0

        return {
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'paid_invoices': paid_invoices,
            'paid_amount': paid_amount,
            'unpaid_invoices': total_invoices - paid_invoices,
            'unpaid_amount': total_amount - paid_amount,
        }

    # ------------------------------------------------------------------
    # Settings & stats
    # ------------------------------------------------------------------
    def get_settings(self) -> dict:
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
            elif value is not None and value.isdigit():
                value = int(value)

            settings[key] = value

        return settings

    def save_settings(self, settings: dict):
        cursor = self.conn.cursor()
        for key, value in settings.items():
            cursor.execute(
                '''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
                ''',
                (key, str(value) if value is not None else ''),
            )
        self.conn.commit()

    def update_setting(self, key: str, value):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
            ''',
            (key, str(value)),
        )
        self.conn.commit()

    def get_statistics(self) -> dict:
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) AS count FROM invoices WHERE is_archived = 0')
        total_invoices = cursor.fetchone()['count']

        cursor.execute('SELECT SUM(amount) AS total FROM invoices WHERE is_archived = 0')
        total_amount = cursor.fetchone()['total'] or 0

        cursor.execute('SELECT COUNT(*) AS count FROM invoices WHERE is_paid = 1 AND is_archived = 0')
        paid_invoices = cursor.fetchone()['count']

        cursor.execute('SELECT SUM(amount) AS total FROM invoices WHERE is_paid = 1 AND is_archived = 0')
        paid_amount = cursor.fetchone()['total'] or 0

        cursor.execute('SELECT COUNT(*) AS count FROM invoices WHERE is_paid = 0 AND is_archived = 0')
        unpaid_invoices = cursor.fetchone()['count']

        cursor.execute('SELECT SUM(amount) AS total FROM invoices WHERE is_paid = 0 AND is_archived = 0')
        unpaid_amount = cursor.fetchone()['total'] or 0

        return {
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'paid_invoices': paid_invoices,
            'paid_amount': paid_amount,
            'unpaid_invoices': unpaid_invoices,
            'unpaid_amount': unpaid_amount,
        }

    def search_invoices(self, search_term: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT * FROM invoices
            WHERE (vendor_name LIKE ? OR delivery_note_number LIKE ?)
              AND is_archived = 0
            ORDER BY due_date DESC
            ''',
            (f'%{search_term}%', f'%{search_term}%'),
        )
        return [dict(row) for row in cursor.fetchall()]

    def filter_invoices(self, filter_type: str = 'all') -> list[dict]:
        cursor = self.conn.cursor()

        if filter_type == 'paid':
            cursor.execute('SELECT * FROM invoices WHERE is_paid = 1 AND is_archived = 0 ORDER BY due_date DESC')
        elif filter_type == 'unpaid':
            cursor.execute('SELECT * FROM invoices WHERE is_paid = 0 AND is_archived = 0 ORDER BY due_date DESC')
        elif filter_type == 'overdue':
            today = datetime.now().strftime('%d.%m.%Y')
            cursor.execute(
                '''
                SELECT * FROM invoices
                WHERE is_paid = 0 AND due_date < ? AND is_archived = 0
                ORDER BY due_date DESC
                ''',
                (today,),
            )
        else:
            cursor.execute('SELECT * FROM invoices WHERE is_archived = 0 ORDER BY due_date DESC')

        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Backup & restore
    # ------------------------------------------------------------------
    def backup_database(self, backup_path: str | None = None) -> str:
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f'invoices_backup_{timestamp}.db'

        shutil.copy2(self.db_name, backup_path)
        print(f"Backup created: {backup_path}")
        return backup_path

    def restore_database(self, backup_path: str) -> bool:
        if not os.path.exists(backup_path):
            print(f"Backup file does not exist: {backup_path}")
            return False

        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

        shutil.copy2(backup_path, self.db_name)
        self.connect()
        self.create_tables()
        self._ensure_vendors_primary_key()
        self._ensure_vendors_columns()
        self._ensure_invoices_columns()
        self._ensure_vendor_codes()
        print(f"Database restored from: {backup_path}")
        return True

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def __del__(self):
        if self.conn:
            try:
                self.conn.close()
                print("Database connection closed.")
            except Exception:
                pass