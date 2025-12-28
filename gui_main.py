import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry
from gui_settings import SettingsWindow
from gui_vendors import VendorsWindow
from pdf_generator import PDFGenerator
import os


class ZaduzenjaTab:
    """Tab za plaćanje zaduženja (dobavljači)"""
    def __init__(self, parent, db, notification_manager):
        self.parent = parent
        self.db = db
        self.notification_manager = notification_manager
        self.pdf_generator = PDFGenerator(db)
        
        self.all_invoices = []
        
        self.setup_ui()
        self.load_invoices()
        self.check_notifications_on_startup()
    
    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Novi račun", command=self.add_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Plati", command=self.pay_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Izmeni", command=self.edit_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiviraj", command=self.archive_invoice).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Dobavljači", command=self.open_vendors).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiva", command=self.open_archive).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="PDF Izveštaj", command=self.generate_pdf_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_invoices).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Podešavanja", command=self.open_settings).pack(side=tk.LEFT, padx=2)
        
        # Filter i search
        filter_frame = ttk.Frame(self.parent)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_combo = ttk.Combobox(filter_frame, width=18, state='readonly')
        self.filter_combo['values'] = ('Svi', 'Neplaćeni', 'Delimično plaćeni', 'Plaćeni', 'Ističu uskoro')
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
        table_container = ttk.Frame(self.parent)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tabela sa novim kolonama
        columns = ('Datum fakture', 'Datum valute', 'Dobavljač', 'Br. otpremnice', 
                'Iznos (RSD)', 'Plaćeno (RSD)', 'Preostalo (RSD)', 'Status', 'Posl. uplata', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Datum fakture', width=100)
        self.tree.column('Datum valute', width=100)
        self.tree.column('Dobavljač', width=180)
        self.tree.column('Br. otpremnice', width=110)
        self.tree.column('Iznos (RSD)', width=110)
        self.tree.column('Plaćeno (RSD)', width=110)
        self.tree.column('Preostalo (RSD)', width=110)
        self.tree.column('Status', width=100)
        self.tree.column('Posl. uplata', width=100)
        self.tree.column('Napomena', width=250)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Double click za plaćanje
        self.tree.bind('<Double-1>', lambda e: self.pay_invoice())
        
        # Status bar
        self.status_bar = ttk.Label(self.parent, text="Spremno", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_invoices(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.all_invoices = self.db.get_all_invoices(include_archived=False)
        self.apply_filters()
        self.update_status_bar()
    
    def apply_filters(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        filtered = self.all_invoices.copy()
        
        # Filter po statusu
        filter_value = self.filter_combo.get()
        
        if filter_value == 'Neplaćeni':
            filtered = [inv for inv in filtered if self.db.get_payment_status(inv['id']) == 'Neplaćeno']
        elif filter_value == 'Delimično plaćeni':
            filtered = [inv for inv in filtered if self.db.get_payment_status(inv['id']) == 'Delimično']
        elif filter_value == 'Plaćeni':
            filtered = [inv for inv in filtered if self.db.get_payment_status(inv['id']) == 'Plaćeno']
        elif filter_value == 'Ističu uskoro':
            settings = self.db.get_settings()
            notification_days = settings.get('notification_days', 7)
            today = datetime.now().date()
            temp = []
            for inv in filtered:
                status = self.db.get_payment_status(inv['id'])
                if status in ['Neplaćeno', 'Delimično']:
                    due_date = datetime.strptime(inv['due_date'], '%d.%m.%Y').date()
                    days_until_due = (due_date - today).days
                    if 0 <= days_until_due <= notification_days:
                        temp.append(inv)
            filtered = temp
        
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
            invoice_id = invoice['id']
            total_paid = self.db.get_total_paid(invoice_id)
            remaining = invoice['amount'] - total_paid
            status = self.db.get_payment_status(invoice_id)
            last_payment_date = self.db.get_last_payment_date(invoice_id) or "-"
            
            item_id = self.tree.insert('', tk.END, values=(
                invoice['invoice_date'],
                invoice['due_date'],
                invoice['vendor_name'],
                invoice['delivery_note_number'],
                f"{invoice['amount']:,.2f}",
                f"{total_paid:,.2f}",
                f"{remaining:,.2f}",
                status,
                last_payment_date,
                invoice['notes'] or ''
            ), tags=(invoice['id'],))
            
            # Oboji red
            if status == 'Plaćeno':
                self.tree.item(item_id, tags=('paid', invoice['id']))
            elif status == 'Delimično':
                self.tree.item(item_id, tags=('partial', invoice['id']))
            else:
                due_date = datetime.strptime(invoice['due_date'], '%d.%m.%Y').date()
                days_until_due = (due_date - today).days
                
                if 0 <= days_until_due <= notification_days:
                    self.tree.item(item_id, tags=('due_soon', invoice['id']))
        
        self.tree.tag_configure('paid', background='#90EE90')
        self.tree.tag_configure('partial', background='#FFFFE0')
        self.tree.tag_configure('due_soon', background='#FFB6C1')
        
        self.update_status_bar()
    
    def update_status_bar(self):
        total = len(self.tree.get_children())
        self.status_bar.config(text=f"Ukupno računa: {total}")
    
    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.filter_combo.set('Svi')
        self.apply_filters()
    
    def add_invoice(self):
        InvoiceDialog(self.parent, self.db, None, self.load_invoices)
    
    def pay_invoice(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za plaćanje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        invoice_id = tags[-1]
        
        # Otvori dialog za sve statuse (readonly ako je plaćeno)
        status = self.db.get_payment_status(invoice_id)
        readonly = (status == 'Plaćeno')
        
        PaymentDialog(self.parent, self.db, invoice_id, self.load_invoices, readonly=readonly)
    
    def edit_invoice(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za izmenu.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        invoice_id = tags[-1]
        InvoiceDialog(self.parent, self.db, invoice_id, self.load_invoices)
    
    def archive_invoice(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za arhiviranje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        invoice_id = tags[-1]
        
        status = self.db.get_payment_status(invoice_id)
        
        if status != 'Plaćeno':
            remaining = self.db.get_remaining_amount(invoice_id)
            messagebox.showwarning(
                "Upozorenje", 
                f"Možete arhivirati samo potpuno plaćene račune.\n\n"
                f"Preostalo za plaćanje: {remaining:,.2f} RSD"
            )
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da arhivirate ovaj račun?"):
            self.db.archive_invoice(invoice_id)
            messagebox.showinfo("Uspeh", "Račun je uspešno arhiviran.")
            self.load_invoices()
    
    def open_archive(self):
        ArchiveWindow(self.parent, self.db, self.load_invoices)
    
    def open_settings(self):
        SettingsWindow(self.parent, self.db)
    
    def open_vendors(self):
        VendorsWindow(self.parent, self.db, 'vendors')
    
    def generate_pdf_report(self):
        displayed_invoices = []
        for item in self.tree.get_children():
            tags = self.tree.item(item)['tags']
            invoice_id = tags[-1]
            invoice = self.db.get_invoice_by_id(invoice_id)
            if invoice:
                invoice['total_paid'] = self.db.get_total_paid(invoice_id)
                invoice['remaining'] = invoice['amount'] - invoice['total_paid']
                invoice['payment_status'] = self.db.get_payment_status(invoice_id)
                displayed_invoices.append(invoice)
        
        if not displayed_invoices:
            messagebox.showwarning("Upozorenje", "Nema računa za prikaz u PDF-u.")
            return
        
        try:
            filename = self.pdf_generator.generate_invoice_report(displayed_invoices)
            messagebox.showinfo("Uspeh", f"PDF izveštaj je kreiran: {filename}")
            
            if messagebox.askyesno("Otvori PDF", "Da li želite da otvorite PDF?"):
                os.startfile(filename)
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri kreiranju PDF-a: {str(e)}")
    
    def check_notifications_on_startup(self):
        due_invoices = self.notification_manager.check_due_invoices()
        if due_invoices:
            self.notification_manager.show_windows_notification(due_invoices)


class PaymentDialog:
    """Dialog za plaćanje računa"""
    def __init__(self, parent, db, invoice_id, callback, readonly=False):
        self.window = tk.Toplevel(parent)
        self.window.title("Plaćanje računa")
        self.window.geometry("850x750")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.invoice_id = invoice_id
        self.callback = callback
        self.invoice = db.get_invoice_by_id(invoice_id)
        
        if not self.invoice:
            messagebox.showerror("Greška", "Račun nije pronađen.")
            self.window.destroy()
            return
        
        self.total_paid = db.get_total_paid(invoice_id)
        self.remaining = self.invoice['amount'] - self.total_paid
        self.readonly = readonly

        self.setup_ui()
        self.load_payments()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text=" 📄 Informacije o računu ", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = (
            f"Dobavljač: {self.invoice['vendor_name']}\n"
            f"Broj otpremnice: {self.invoice['delivery_note_number']}\n"
            f"Datum fakture: {self.invoice['invoice_date']}\n"
            f"Datum valute: {self.invoice['due_date']}"
        )
        
        ttk.Label(info_frame, text=info_text, font=('Arial', 10)).pack(anchor=tk.W)
        
        # Finance frame
        finance_frame = ttk.LabelFrame(main_frame, text=" 💰 Finansijski pregled ", padding=10)
        finance_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(finance_frame, text="UKUPAN IZNOS:", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(finance_frame, text=f"{self.invoice['amount']:,.2f} RSD", font=('Arial', 10)).grid(row=0, column=1, sticky=tk.E, pady=2)
        
        ttk.Label(finance_frame, text="Plaćeno do sada:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(finance_frame, text=f"{self.total_paid:,.2f} RSD", font=('Arial', 10)).grid(row=1, column=1, sticky=tk.E, pady=2)
        
        ttk.Separator(finance_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        
        ttk.Label(finance_frame, text="PREOSTALO ZA PLAĆANJE:", font=('Arial', 11, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.remaining_label = ttk.Label(finance_frame, text=f"{self.remaining:,.2f} RSD", font=('Arial', 11, 'bold'), foreground='#D32F2F')
        self.remaining_label.grid(row=3, column=1, sticky=tk.E, pady=2)
        
        finance_frame.columnconfigure(0, weight=1)
        finance_frame.columnconfigure(1, weight=1)
        
        # Payment frame
        payment_frame = ttk.LabelFrame(main_frame, text=" 📝 Nova uplata ", padding=10)
        payment_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.payment_type = tk.StringVar(value='full')
        
        ttk.Radiobutton(
            payment_frame, 
            text=f"Potpuno plaćanje ({self.remaining:,.2f} RSD)", 
            variable=self.payment_type, 
            value='full',
            command=self.on_payment_type_changed
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            payment_frame, 
            text="Delimično plaćanje", 
            variable=self.payment_type, 
            value='partial',
            command=self.on_payment_type_changed
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(payment_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Amount
        amount_frame = ttk.Frame(payment_frame)
        amount_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(amount_frame, text="Iznos uplate:", width=15).pack(side=tk.LEFT)
        self.amount_entry = ttk.Entry(amount_frame, width=20)
        self.amount_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(amount_frame, text="RSD").pack(side=tk.LEFT)
        self.max_label = ttk.Label(amount_frame, text=f"(max: {self.remaining:,.2f})", foreground='gray')
        self.max_label.pack(side=tk.LEFT, padx=5)
        
        # Date
        date_frame = ttk.Frame(payment_frame)
        date_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(date_frame, text="Datum uplate:", width=15).pack(side=tk.LEFT)
        self.payment_date_entry = DateEntry(date_frame, width=17, date_pattern='dd.mm.yyyy')
        self.payment_date_entry.pack(side=tk.LEFT, padx=5)
        
        # Notes
        notes_frame = ttk.Frame(payment_frame)
        notes_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(notes_frame, text="Napomena:", width=15).pack(side=tk.LEFT, anchor=tk.N)
        self.notes_entry = tk.Text(notes_frame, width=40, height=3)
        self.notes_entry.pack(side=tk.LEFT, padx=5)
        
        # History frame
        history_frame = ttk.LabelFrame(main_frame, text=" 📋 Istorija uplata ", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ('Datum', 'Iznos (RSD)', 'Napomena')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=6)
        
        self.history_tree.heading('Datum', text='Datum')
        self.history_tree.heading('Iznos (RSD)', text='Iznos (RSD)')
        self.history_tree.heading('Napomena', text='Napomena')
        
        self.history_tree.column('Datum', width=100)
        self.history_tree.column('Iznos (RSD)', width=100)
        self.history_tree.column('Napomena', width=300)
        
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Sačuvaj uplatu", command=self.save_payment).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Zatvori", command=self.window.destroy).pack(side=tk.RIGHT)
        
        self.on_payment_type_changed()
    
    def on_payment_type_changed(self):
        if self.payment_type.get() == 'full':
            self.amount_entry.delete(0, tk.END)
            self.amount_entry.insert(0, f"{self.remaining:.2f}")
            self.amount_entry.config(state='disabled')
        else:
            self.amount_entry.config(state='normal')
            self.amount_entry.delete(0, tk.END)
    
    def load_payments(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        payments = self.db.get_payments(self.invoice_id)
        
        for payment in payments:
            self.history_tree.insert('', tk.END, values=(
                payment['payment_date'],
                f"{payment['payment_amount']:,.2f}",
                payment['notes'] or ''
            ))
    
    def save_payment(self):
        try:
            amount_str = self.amount_entry.get().strip().replace(',', '.')
            amount = float(amount_str)
        except ValueError:
            messagebox.showerror("Greška", "Unesite validan iznos.")
            return
        
        if amount <= 0:
            messagebox.showerror("Greška", "Iznos mora biti veći od 0.")
            return
        
        if amount > self.remaining:
            messagebox.showerror("Greška", f"Iznos ne može biti veći od preostalog ({self.remaining:,.2f} RSD).")
            return
        
        payment_date = self.payment_date_entry.get_date().strftime('%d.%m.%Y')
        notes = self.notes_entry.get('1.0', tk.END).strip()
        
        try:
            self.db.add_payment(self.invoice_id, amount, payment_date, notes)
            
            # Ažuriraj is_paid ako je potpuno plaćeno
            new_total_paid = self.db.get_total_paid(self.invoice_id)
            if new_total_paid >= self.invoice['amount']:
                self.db.mark_as_paid(self.invoice_id, payment_date)
            
            messagebox.showinfo("Uspeh", "Uplata je uspešno evidentirana.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class InvoiceDialog:
    """Dialog za dodavanje/izmenu računa"""
    def __init__(self, parent, db, invoice_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi račun" if invoice_id is None else "Izmeni račun")
        self.window.geometry("600x450")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.invoice_id = invoice_id
        self.callback = callback
        
        self.setup_ui()
        
        if invoice_id:
            self.load_invoice_data()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text=" 📄 Informacije o računu ", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = (
            f"Dobavljač: {self.invoice['vendor_name']}\n"
            f"Broj otpremnice: {self.invoice['delivery_note_number']}\n"
            f"Datum fakture: {self.invoice['invoice_date']}\n"
            f"Datum valute: {self.invoice['due_date']}"
        )
        
        ttk.Label(info_frame, text=info_text, font=('Arial', 10)).pack(anchor=tk.W)
        
        # Finance frame
        finance_frame = ttk.LabelFrame(main_frame, text=" 💰 Finansijski pregled ", padding=10)
        finance_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(finance_frame, text="UKUPAN IZNOS:", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(finance_frame, text=f"{self.invoice['amount']:,.2f} RSD", font=('Arial', 10)).grid(row=0, column=1, sticky=tk.E, pady=2)
        
        ttk.Label(finance_frame, text="Plaćeno do sada:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(finance_frame, text=f"{self.total_paid:,.2f} RSD", font=('Arial', 10)).grid(row=1, column=1, sticky=tk.E, pady=2)
        
        ttk.Separator(finance_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        
        ttk.Label(finance_frame, text="PREOSTALO ZA PLAĆANJE:", font=('Arial', 11, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.remaining_label = ttk.Label(finance_frame, text=f"{self.remaining:,.2f} RSD", font=('Arial', 11, 'bold'), foreground='#D32F2F')
        self.remaining_label.grid(row=3, column=1, sticky=tk.E, pady=2)
        
        finance_frame.columnconfigure(0, weight=1)
        finance_frame.columnconfigure(1, weight=1)
        
        # Payment frame
        payment_frame = ttk.LabelFrame(main_frame, text=" 📝 Nova uplata ", padding=10)
        payment_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.payment_type = tk.StringVar(value='full')
        
        ttk.Radiobutton(
            payment_frame, 
            text=f"Potpuno plaćanje ({self.remaining:,.2f} RSD)", 
            variable=self.payment_type, 
            value='full',
            command=self.on_payment_type_changed
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            payment_frame, 
            text="Delimično plaćanje", 
            variable=self.payment_type, 
            value='partial',
            command=self.on_payment_type_changed
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(payment_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Amount
        amount_frame = ttk.Frame(payment_frame)
        amount_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(amount_frame, text="Iznos uplate:", width=15).pack(side=tk.LEFT)
        self.amount_entry = ttk.Entry(amount_frame, width=20)
        self.amount_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(amount_frame, text="RSD").pack(side=tk.LEFT)
        self.max_label = ttk.Label(amount_frame, text=f"(max: {self.remaining:,.2f})", foreground='gray')
        self.max_label.pack(side=tk.LEFT, padx=5)
        
        # Date
        date_frame = ttk.Frame(payment_frame)
        date_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(date_frame, text="Datum uplate:", width=15).pack(side=tk.LEFT)
        self.payment_date_entry = DateEntry(date_frame, width=17, date_pattern='dd.mm.yyyy')
        self.payment_date_entry.pack(side=tk.LEFT, padx=5)
        
        # Notes
        notes_frame = ttk.Frame(payment_frame)
        notes_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(notes_frame, text="Napomena:", width=15).pack(side=tk.LEFT, anchor=tk.N)
        self.notes_entry = tk.Text(notes_frame, width=40, height=3)
        self.notes_entry.pack(side=tk.LEFT, padx=5)
        
        # History frame
        history_frame = ttk.LabelFrame(main_frame, text=" 📋 Istorija uplata ", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ('Datum', 'Iznos (RSD)', 'Napomena')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=6)
        
        self.history_tree.heading('Datum', text='Datum')
        self.history_tree.heading('Iznos (RSD)', text='Iznos (RSD)')
        self.history_tree.heading('Napomena', text='Napomena')
        
        self.history_tree.column('Datum', width=100)
        self.history_tree.column('Iznos (RSD)', width=100)
        self.history_tree.column('Napomena', width=300)
        
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Sačuvaj uplatu", command=self.save_payment).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Zatvori", command=self.window.destroy).pack(side=tk.RIGHT)
        
        self.on_payment_type_changed()
    
    def on_payment_type_changed(self):
        if self.payment_type.get() == 'full':
            self.amount_entry.delete(0, tk.END)
            self.amount_entry.insert(0, f"{self.remaining:.2f}")
            self.amount_entry.config(state='disabled')
        else:
            self.amount_entry.config(state='normal')
            self.amount_entry.delete(0, tk.END)
    
    def load_payments(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        payments = self.db.get_payments(self.invoice_id)
        
        for payment in payments:
            self.history_tree.insert('', tk.END, values=(
                payment['payment_date'],
                f"{payment['payment_amount']:,.2f}",
                payment['notes'] or ''
            ))
    
    def save_payment(self):
        try:
            amount_str = self.amount_entry.get().strip().replace(',', '.')
            amount = float(amount_str)
        except ValueError:
            messagebox.showerror("Greška", "Unesite validan iznos.")
            return
        
        if amount <= 0:
            messagebox.showerror("Greška", "Iznos mora biti veći od 0.")
            return
        
        if amount > self.remaining:
            messagebox.showerror("Greška", f"Iznos ne može biti veći od preostalog ({self.remaining:,.2f} RSD).")
            return
        
        payment_date = self.payment_date_entry.get_date().strftime('%d.%m.%Y')
        notes = self.notes_entry.get('1.0', tk.END).strip()
        
        try:
            self.db.add_payment(self.invoice_id, amount, payment_date, notes)
            
            # Ažuriraj is_paid ako je potpuno plaćeno
            new_total_paid = self.db.get_total_paid(self.invoice_id)
            if new_total_paid >= self.invoice['amount']:
                self.db.mark_as_paid(self.invoice_id, payment_date)
            
            messagebox.showinfo("Uspeh", "Uplata je uspešno evidentirana.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class InvoiceDialog:
    """Dialog za dodavanje/izmenu računa"""
    def __init__(self, parent, db, invoice_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi račun" if invoice_id is None else "Izmeni račun")
        self.window.geometry("600x450")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.invoice_id = invoice_id
        self.callback = callback
        
        self.setup_ui()
        
        if invoice_id:
            self.load_invoice_data()
    
    def setup_ui(self):
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
        self.vendor_map = {v.get('name', ''): v.get('id') for v in vendors}
        self.vendor_combo['values'] = list(self.vendor_map.keys())
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
        
        form_frame.columnconfigure(1, weight=1)
        
        # Button frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        if self.invoice_id:
            ttk.Button(button_frame, text="Obriši račun", command=self.delete_invoice).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Sačuvaj izmene" if self.invoice_id else "Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
    
    def load_invoice_data(self):
        invoice = self.db.get_invoice_by_id(self.invoice_id)
        if not invoice:
            return
        
        self.invoice_date_entry.set_date(datetime.strptime(invoice['invoice_date'], '%d.%m.%Y'))
        self.due_date_entry.set_date(datetime.strptime(invoice['due_date'], '%d.%m.%Y'))
        
        self.vendor_combo.set(invoice.get('vendor_name', ''))
        
        self.delivery_note_entry.delete(0, tk.END)
        self.delivery_note_entry.insert(0, invoice.get('delivery_note_number', ''))
        
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, str(invoice.get('amount', '')))
        
        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', invoice.get('notes', ''))
    
    def delete_invoice(self):
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj račun?\n\nOvo će obrisati i sve uplate vezane za ovaj račun."):
            try:
                self.db.delete_invoice(self.invoice_id)
                messagebox.showinfo("Uspeh", "Račun je uspešno obrisan.")
                self.callback()
                self.window.destroy()
            except Exception as e:
                messagebox.showerror("Greška", f"Greška pri brisanju: {str(e)}")
    
    def save(self):
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
        
        if amount <= 0:
            messagebox.showerror("Greška", "Iznos mora biti veći od 0.")
            return
        
        invoice_date = self.invoice_date_entry.get_date().strftime('%d.%m.%Y')
        due_date = self.due_date_entry.get_date().strftime('%d.%m.%Y')
        vendor_name = self.vendor_combo.get()
        vendor_id = self.vendor_map.get(vendor_name)
        delivery_note = self.delivery_note_entry.get().strip()
        notes = self.notes_text.get('1.0', tk.END).strip()
        
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
            if self.invoice_id:
                self.db.update_invoice(self.invoice_id, invoice_data)
                messagebox.showinfo("Uspeh", "Račun je uspešno izmenjen.")
            else:
                self.db.add_invoice(invoice_data)
                messagebox.showinfo("Uspeh", "Račun je uspešno dodat.")
            
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class ArchiveWindow:
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Arhiva")
        self.window.geometry("1400x600")
        self.db = db
        self.callback = callback
        
        self.setup_ui()
        self.load_archive()
    
    def setup_ui(self):
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Vrati iz arhive", command=self.unarchive).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_archive).pack(side=tk.LEFT, padx=2)
        
        columns = ('Datum fakture', 'Datum valute', 'Dobavljač', 'Br. otpremnice', 
                   'Iznos (RSD)', 'Plaćeno (RSD)', 'Status', 'Posl. uplata', 'Napomena')
        self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Datum fakture', width=100)
        self.tree.column('Datum valute', width=100)
        self.tree.column('Dobavljač', width=200)
        self.tree.column('Br. otpremnice', width=120)
        self.tree.column('Iznos (RSD)', width=120)
        self.tree.column('Plaćeno (RSD)', width=120)
        self.tree.column('Status', width=100)
        self.tree.column('Posl. uplata', width=120)
        self.tree.column('Napomena', width=300)
        
        scrollbar = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
    
    def load_archive(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        invoices = self.db.get_all_invoices(include_archived=True)
        archived_invoices = [inv for inv in invoices if inv.get('is_archived')]
        
        for invoice in archived_invoices:
            invoice_id = invoice['id']
            total_paid = self.db.get_total_paid(invoice_id)
            status = self.db.get_payment_status(invoice_id)
            last_payment_date = self.db.get_last_payment_date(invoice_id) or "-"
            
            self.tree.insert('', tk.END, values=(
                invoice.get('invoice_date', ''),
                invoice.get('due_date', ''),
                invoice.get('vendor_name', ''),
                invoice.get('delivery_note_number', ''),
                f"{invoice.get('amount', 0):,.2f}",
                f"{total_paid:,.2f}",
                status,
                last_payment_date,
                invoice.get('notes', '')
            ), tags=(invoice.get('id', ''),))
    
    def unarchive(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za vraćanje iz arhive.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da vratite ovaj račun iz arhive?"):
            invoice_id = self.tree.item(selection[0])['tags'][0]
            self.db.unarchive_invoice(invoice_id)
            messagebox.showinfo("Uspeh", "Račun je uspešno vraćen iz arhive.")
            self.load_archive()
            self.callback()
    
    def delete(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za brisanje.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj račun iz arhive?\n\nOvo će obrisati i sve uplate vezane za ovaj račun."):
            invoice_id = self.tree.item(selection[0])['tags'][0]
            self.db.delete_invoice(invoice_id)
            messagebox.showinfo("Uspeh", "Račun je uspešno obrisan.")
            self.load_archive()