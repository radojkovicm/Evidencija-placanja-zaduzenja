# gui_main.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import DateEntry
from gui_settings import SettingsWindow
from gui_vendors import VendorsWindow
from pdf_generator import PDFGenerator
import os

class MainWindow:
    def __init__(self, root, db, notification_manager):
        self.root = root
        self.db = db
        self.notification_manager = notification_manager
        self.pdf_generator = PDFGenerator(db)
        
        self.root.title("Evidencija Plaćanja Zaduženja")
        self.root.geometry("1400x700")
        
        self.current_filter = "Svi"
        self.search_text = ""
        self.search_field = "Broj otpremnice"
        
        self.setup_ui()
        self.load_invoices()
        
        # Proveri notifikacije pri pokretanju
        self.check_notifications_on_startup()
    
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fajl", menu=file_menu)
        file_menu.add_command(label="Podešavanja", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Izlaz", command=self.root.quit)
        
        data_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Podaci", menu=data_menu)
        data_menu.add_command(label="Dobavljači", command=self.open_vendors)
        data_menu.add_command(label="Arhiva", command=self.open_archive)
        
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Novi račun", command=self.add_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Izmeni", command=self.edit_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiviraj", command=self.archive_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="PDF Izveštaj", command=self.generate_pdf_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_invoices).pack(side=tk.LEFT, padx=2)
        
        # Filter i search
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_combo = ttk.Combobox(filter_frame, width=15, state='readonly')
        self.filter_combo['values'] = ('Svi', 'Neplaćeni', 'Plaćeni', 'Ističu uskoro')
        self.filter_combo.set('Svi')
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(filter_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(filter_frame, text="Pretraga:").pack(side=tk.LEFT, padx=5)
        self.search_field_combo = ttk.Combobox(filter_frame, width=15, state='readonly')
        self.search_field_combo['values'] = ('Broj otpremnice', 'Dobavljač')
        self.search_field_combo.set('Broj otpremnice')
        self.search_field_combo.pack(side=tk.LEFT, padx=5)
        
        self.search_entry = ttk.Entry(filter_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self.apply_filters())
        
        ttk.Button(filter_frame, text="Očisti", command=self.clear_search).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(filter_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(filter_frame, text="Sortiranje:").pack(side=tk.LEFT, padx=5)
        self.sort_combo = ttk.Combobox(filter_frame, width=15, state='readonly')
        self.sort_combo['values'] = ('Datum valute', 'Datum fakture', 'Dobavljač', 'Iznos')
        self.sort_combo.set('Datum valute')
        self.sort_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.sort_combo.pack(side=tk.LEFT, padx=5)
        
        # Container za tabelu
        table_container = ttk.Frame(self.root)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tabela
        columns = ('Datum fakture', 'Datum valute', 'Dobavljač', 'Br. otpremnice', 'Iznos (RSD)', 'Status', 'Datum plaćanja', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Datum fakture', width=100)
        self.tree.column('Datum valute', width=100)
        self.tree.column('Dobavljač', width=200)
        self.tree.column('Br. otpremnice', width=120)
        self.tree.column('Iznos (RSD)', width=120)
        self.tree.column('Status', width=100)
        self.tree.column('Datum plaćanja', width=120)
        self.tree.column('Napomena', width=300)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Double click za izmenu
        self.tree.bind('<Double-1>', lambda e: self.edit_invoice())
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Spremno", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_invoices(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        invoices = self.db.get_all_invoices(include_archived=False)
        self.all_invoices = invoices  # Čuvaj sve račune za filtriranje
        
        self.apply_filters()
        self.update_status_bar()
    
    def apply_filters(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filtriraj
        filtered = self.all_invoices.copy()
        
        # Filter po statusu
        filter_value = self.filter_combo.get()
        if filter_value == 'Neplaćeni':
            filtered = [inv for inv in filtered if not inv['is_paid']]
        elif filter_value == 'Plaćeni':
            filtered = [inv for inv in filtered if inv['is_paid']]
        elif filter_value == 'Ističu uskoro':
            settings = self.db.get_settings()
            notification_days = settings.get('notification_days', 7)
            today = datetime.now().date()
            filtered = [inv for inv in filtered if not inv['is_paid'] and 
                       0 <= (datetime.strptime(inv['due_date'], '%d.%m.%Y').date() - today).days <= notification_days]
        
        # Search
        search_text = self.search_entry.get().strip().lower()
        search_field = self.search_field_combo.get()
        
        if search_text:
            if search_field == 'Broj otpremnice':
                filtered = [inv for inv in filtered if search_text in (inv['delivery_note_number'] or '').lower()]
            elif search_field == 'Dobavljač':
                filtered = [inv for inv in filtered if search_text in (inv['vendor_name'] or '').lower()]
        
        # Sortiranje
        sort_field = self.sort_combo.get()
        sort_map = {
            'Datum valute': 'due_date',
            'Datum fakture': 'invoice_date',
            'Dobavljač': 'vendor_name',
            'Iznos': 'amount'
        }
        sort_key = sort_map.get(sort_field, 'due_date')
        
        if sort_key in ['due_date', 'invoice_date']:
            filtered.sort(key=lambda x: datetime.strptime(x[sort_key], '%d.%m.%Y'))
        else:
            filtered.sort(key=lambda x: x[sort_key] if x[sort_key] else '')
        
        # Prikaži
        settings = self.db.get_settings()
        notification_days = settings.get('notification_days', 7)
        today = datetime.now().date()
        
        for invoice in filtered:
            status = "Plaćeno" if invoice['is_paid'] else "Neplaćeno"
            payment_date = invoice['payment_date'] if invoice['payment_date'] else "-"
            
            item_id = self.tree.insert('', tk.END, values=(
                invoice['invoice_date'],
                invoice['due_date'],
                invoice['vendor_name'],
                invoice['delivery_note_number'],
                f"{invoice['amount']:,.2f}",
                status,
                payment_date,
                invoice['notes'] or ''
            ), tags=(invoice['id'],))
            
            # Oboji red
            if invoice['is_paid']:
                self.tree.item(item_id, tags=('paid', invoice['id']))
            else:
                due_date = datetime.strptime(invoice['due_date'], '%d.%m.%Y').date()
                days_until_due = (due_date - today).days
                
                if 0 <= days_until_due <= notification_days:
                    self.tree.item(item_id, tags=('due_soon', invoice['id']))
        
        # Primeni boje
        self.tree.tag_configure('paid', background='#90EE90')  # Svetlo zelena
        self.tree.tag_configure('due_soon', background='#FFFF99')  # Svetlo žuta
        
        self.update_status_bar()
    
    def update_status_bar(self):
        total = len(self.tree.get_children())
        self.status_bar.config(text=f"Ukupno računa: {total}")
    
    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.filter_combo.set('Svi')
        self.apply_filters()
    
    def add_invoice(self):
        InvoiceDialog(self.root, self.db, None, self.load_invoices)
    
    def edit_invoice(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za izmenu.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        id = tags[-1]  # Poslednji tag je uvek id
        InvoiceDialog(self.root, self.db, id, self.load_invoices)
    
    def delete_invoice(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za brisanje.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj račun?"):
            tags = self.tree.item(selection[0])['tags']
            id = tags[-1]
            self.db.delete_invoice(id)
            messagebox.showinfo("Uspeh", "Račun je uspešno obrisan.")
            self.load_invoices()
    
    def archive_invoice(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za arhiviranje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        id = tags[-1]
        invoice = self.db.get_invoice_by_id(id)
        
        if not invoice['is_paid']:
            messagebox.showwarning("Upozorenje", "Možete arhivirati samo plaćene račune.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da arhivirate ovaj račun?"):
            self.db.archive_invoice(id)
            messagebox.showinfo("Uspeh", "Račun je uspešno arhiviran.")
            self.load_invoices()
    
    def open_archive(self):
        ArchiveWindow(self.root, self.db, self.load_invoices)
    
    def open_settings(self):
        SettingsWindow(self.root, self.db)
    
    def open_vendors(self):
        VendorsWindow(self.root, self.db)
    
    def generate_pdf_report(self):
        # Uzmi trenutno prikazane račune
        displayed_invoices = []
        for item in self.tree.get_children():
            tags = self.tree.item(item)['tags']
            id = tags[-1]
            invoice = self.db.get_invoice_by_id(id)
            if invoice:
                displayed_invoices.append(invoice)
        
        if not displayed_invoices:
            messagebox.showwarning("Upozorenje", "Nema računa za prikaz u PDF-u.")
            return
        
        try:
            filename = self.pdf_generator.generate_invoice_report(displayed_invoices)
            messagebox.showinfo("Uspeh", f"PDF izveštaj je kreiran: {filename}")
            
            # Otvori PDF
            if messagebox.askyesno("Otvori PDF", "Da li želite da otvorite PDF?"):
                os.startfile(filename)
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri kreiranju PDF-a: {str(e)}")
    
    # gui_main.py - ZAMENI check_notifications_on_startup metodu

    def check_notifications_on_startup(self):
        """Prikaži samo Windows notifikaciju pri pokretanju (email šalje scheduler)"""
        due_invoices = self.notification_manager.check_due_invoices()
        if due_invoices:
            # Samo Windows notifikacija
            self.notification_manager.show_windows_notification(due_invoices)


class InvoiceDialog:
    def __init__(self, parent, db, id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi račun" if id is None else "Izmeni račun")
        self.window.geometry("600x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.id = id
        self.callback = callback
        
        self.setup_ui()
        
        if id:
            self.load_invoice_data()
    
    def setup_ui(self):
        # Form
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        ttk.Label(form_frame, text="Datum fakture:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.invoice_date_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.invoice_date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Datum valute:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.due_date_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.due_date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Dobavljač:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.vendor_combo = ttk.Combobox(form_frame, width=37, state='readonly')
        vendors = self.db.get_all_vendors()
        # vendor name može biti pod ključem 'name' ili 'vendor_name'; vendor id može biti 'vendor_id' ili 'id'
        self.vendor_map = {
            (v.get('name') or v.get('vendor_name') or '').strip(): (v.get('vendor_id') or v.get('id') or None)
            for v in vendors
        }
        self.vendor_combo['values'] = [k for k in self.vendor_map.keys() if k]
        self.vendor_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Broj otpremnice:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.delivery_note_entry = ttk.Entry(form_frame, width=40)
        self.delivery_note_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Iznos (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.amount_entry = ttk.Entry(form_frame, width=40)
        self.amount_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notes_text = tk.Text(form_frame, width=40, height=5)
        self.notes_text.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        # Checkbox za plaćeno
        self.is_paid_var = tk.BooleanVar()
        self.paid_check = ttk.Checkbutton(form_frame, text="Plaćeno", variable=self.is_paid_var, command=self.on_paid_changed)
        self.paid_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1
        
        ttk.Label(form_frame, text="Datum plaćanja:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.payment_date_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.payment_date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        self.payment_date_entry.config(state='disabled')
        row += 1
        
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def on_paid_changed(self):
        if self.is_paid_var.get():
            self.payment_date_entry.config(state='normal')
            # Postavi današnji datum ako nije već postavljen
            if not self.id:
                self.payment_date_entry.set_date(datetime.now())
        else:
            self.payment_date_entry.config(state='disabled')
    
    def load_invoice_data(self):
        invoice = self.db.get_invoice_by_id(self.id)
        if not invoice:
            return

        self.invoice_date_entry.set_date(datetime.strptime(invoice['invoice_date'], '%d.%m.%Y'))
        self.due_date_entry.set_date(datetime.strptime(invoice['due_date'], '%d.%m.%Y'))

        # Pokušaj da dobijemo vendor po vendor_id; ako ne postoji, fallback na vendor_name
        vid = invoice.get('vendor_id')
        vendor = None
        try:
            if vid is not None:
                try:
                    vendor = self.db.get_vendor_by_id(int(vid))
                except Exception:
                    vendor = self.db.get_vendor_by_id(vid)
        except Exception:
            vendor = None

        if vendor:
            self.vendor_combo.set(vendor.get('name') or vendor.get('vendor_name') or '')
        else:
            # fallback na vendor_name iz invoice-a
            self.vendor_combo.set(invoice.get('vendor_name') or '')

        self.delivery_note_entry.delete(0, tk.END)
        self.delivery_note_entry.insert(0, invoice.get('delivery_note_number') or '')
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, str(invoice.get('amount') or ''))
        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', invoice.get('notes') or '')

        self.is_paid_var.set(bool(invoice.get('is_paid')))
        if invoice.get('is_paid') and invoice.get('payment_date'):
            self.payment_date_entry.config(state='normal')
            self.payment_date_entry.set_date(datetime.strptime(invoice['payment_date'], '%d.%m.%Y'))
        else:
            self.payment_date_entry.config(state='disabled')
    
    def save(self):
        # Validacija
        if not self.vendor_combo.get():
            messagebox.showerror("Greška", "Molim izaberite dobavljača.")
            return

        if not self.delivery_note_entry.get().strip():
            messagebox.showerror("Greška", "Molim unesite broj otpremnice.")
            return

        try:
            amount = float(self.amount_entry.get().strip().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validan iznos.")
            return

        invoice_date = self.invoice_date_entry.get_date().strftime('%d.%m.%Y')
        due_date = self.due_date_entry.get_date().strftime('%d.%m.%Y')
        vendor_name = self.vendor_combo.get()
        vendor_id = self.vendor_map.get(vendor_name)  # može biti None
        delivery_note = self.delivery_note_entry.get().strip()
        notes = self.notes_text.get('1.0', tk.END).strip()
        is_paid = 1 if self.is_paid_var.get() else 0
        payment_date = self.payment_date_entry.get_date().strftime('%d.%m.%Y') if is_paid else None

        invoice_data = {
            'invoice_date': invoice_date,
            'due_date': due_date,
            'vendor_id': vendor_id,
            'vendor_name': vendor_name,
            'delivery_note_number': delivery_note,
            'amount': amount,
            'notes': notes
        }

        try:
            if self.id:
                # update_invoice očekuje (invoice_id, invoice_data)
                self.db.update_invoice(self.id, invoice_data)
                # update is_paid status separately
                if is_paid:
                    self.db.mark_as_paid(self.id, payment_date)
                else:
                    self.db.mark_as_unpaid(self.id)
                messagebox.showinfo("Uspeh", "Račun je uspešno izmenjen.")
            else:
                new_id = self.db.add_invoice(invoice_data)
                if is_paid:
                    self.db.mark_as_paid(new_id, payment_date)
                messagebox.showinfo("Uspeh", "Račun je uspešno dodat.")

            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class ArchiveWindow:
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Arhiva")
        self.window.geometry("1200x600")
        self.db = db
        self.callback = callback
        
        self.setup_ui()
        self.load_archive()
    
    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Vrati iz arhive", command=self.unarchive).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_archive).pack(side=tk.LEFT, padx=2)
        
        # Tabela
        columns = ('Datum fakture', 'Datum valute', 'Dobavljač', 'Br. otpremnice', 'Iznos (RSD)', 'Datum plaćanja', 'Napomena')
        self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Datum fakture', width=100)
        self.tree.column('Datum valute', width=100)
        self.tree.column('Dobavljač', width=200)
        self.tree.column('Br. otpremnice', width=120)
        self.tree.column('Iznos (RSD)', width=120)
        self.tree.column('Datum plaćanja', width=120)
        self.tree.column('Napomena', width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
    
    def load_archive(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Pokušaj da dobijemo arhivirane fakture koristeći get_all_invoices(include_archived=True)
        invoices = None
        try:
            invoices = self.db.get_all_invoices(include_archived=True)
        except TypeError:
            # fallback: možda metoda prima pozicioni arg
            try:
                invoices = self.db.get_all_invoices(True)
            except Exception:
                invoices = None
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri dohvatanju arhive: {e}")
            return

        if invoices is None:
            messagebox.showerror("Greška", "Funkcija za dohvatanje arhiviranih računa nije dostupna u Database objektu.")
            return

        # Filtriraj SAMO arhivirane račune
        archived_invoices = [inv for inv in invoices if inv.get('is_archived')]
        
        for invoice in archived_invoices:
            try:
                inv = dict(invoice)
            except Exception:
                inv = invoice

            invoice_date = inv.get('invoice_date') or inv.get('date') or ''
            due_date = inv.get('due_date') or ''
            vendor_name = inv.get('vendor_name') or inv.get('vendor') or ''
            delivery_note = inv.get('delivery_note_number') or inv.get('delivery_note') or ''
            amount = inv.get('amount') or 0.0
            payment_date = inv.get('payment_date') or ''
            notes = inv.get('notes') or ''

            try:
                amount_str = f"{float(amount):,.2f}"
            except Exception:
                amount_str = str(amount)

            self.tree.insert('', tk.END, values=(
                invoice_date,
                due_date,
                vendor_name,
                delivery_note,
                amount_str,
                payment_date,
                notes
            ), tags=(inv.get('id') or inv.get('invoice_id') or ''))
            
    def unarchive(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za vraćanje iz arhive.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da vratite ovaj račun iz arhive?"):
            id = self.tree.item(selection[0])['tags'][0]
            self.db.unarchive_invoice(id)
            messagebox.showinfo("Uspeh", "Račun je uspešno vraćen iz arhive.")
            self.load_archive()
            self.callback()
    
    def delete(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za brisanje.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj račun iz arhive?"):
            id = self.tree.item(selection[0])['tags'][0]
            self.db.delete_invoice(id)
            messagebox.showinfo("Uspeh", "Račun je uspešno obrisan.")
            self.load_archive()