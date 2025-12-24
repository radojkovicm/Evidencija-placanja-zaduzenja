import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry
from gui_vendors import VendorsWindow
from pdf_generator import PDFGenerator
import os


class PredracuniTab:
    """Tab za predračune (kupci i artikli)"""
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.pdf_generator = PDFGenerator(db)
        
        self.all_proformas = []
        
        self.setup_ui()
        self.load_proformas()
    
    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Novi predračun", command=self.add_proforma).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Prikaži stavke", command=self.view_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_proforma).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiviraj", command=self.archive_proforma).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Kupci", command=self.open_customers).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Artikli", command=self.open_articles).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="PDF Predračun", command=self.generate_pdf).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_proformas).pack(side=tk.LEFT, padx=2)
        
        # Filter
        filter_frame = ttk.Frame(self.parent)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_combo = ttk.Combobox(filter_frame, width=15, state='readonly')
        self.filter_combo['values'] = ('Svi', 'Neplaćeno', 'Delimično', 'Plaćeno')
        self.filter_combo.set('Svi')
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(filter_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(filter_frame, text="Pretraga:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(filter_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self.apply_filters())
        
        ttk.Button(filter_frame, text="Očisti", command=self.clear_search).pack(side=tk.LEFT, padx=5)
        
        # Container za tabelu
        table_container = ttk.Frame(self.parent)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tabela
        columns = ('Broj predračuna', 'Datum', 'Kupac', 'Ukupan iznos', 'Plaćeno', 'Status', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Broj predračuna', width=120)
        self.tree.column('Datum', width=100)
        self.tree.column('Kupac', width=200)
        self.tree.column('Ukupan iznos', width=120)
        self.tree.column('Plaćeno', width=120)
        self.tree.column('Status', width=100)
        self.tree.column('Napomena', width=300)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Double click za prikaz stavki
        self.tree.bind('<Double-1>', lambda e: self.view_items())
        
        # Status bar
        self.status_bar = ttk.Label(self.parent, text="Spremno", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_proformas(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.all_proformas = self.db.get_all_proforma_invoices(include_archived=False)
        self.apply_filters()
    
    def apply_filters(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        filtered = self.all_proformas.copy()
        
        # Filter po statusu
        filter_value = self.filter_combo.get()
        if filter_value != 'Svi':
            filtered = [p for p in filtered if p['payment_status'] == filter_value]
        
        # Search
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            filtered = [p for p in filtered if search_text in (p['customer_name'] or '').lower() or search_text in (p['proforma_number'] or '').lower()]
        
        # Prikaži
        for proforma in filtered:
            status = proforma['payment_status']
            
            item_id = self.tree.insert('', tk.END, values=(
                proforma['proforma_number'],
                proforma['invoice_date'],
                proforma['customer_name'],
                f"{proforma['total_amount']:,.2f}",
                f"{proforma['paid_amount']:,.2f}",
                status,
                proforma['notes'] or ''
            ), tags=(proforma['id'],))
            
            # Oboji red
            if status == 'Plaćeno':
                self.tree.item(item_id, tags=('paid', proforma['id']))
            elif status == 'Delimično':
                self.tree.item(item_id, tags=('partial', proforma['id']))
        
        self.tree.tag_configure('paid', background='#90EE90')
        self.tree.tag_configure('partial', background='#FFFF99')
        
        self.status_bar.config(text=f"Ukupno predračuna: {len(self.tree.get_children())}")
    
    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.filter_combo.set('Svi')
        self.apply_filters()
    
    def add_proforma(self):
        ProformaDialog(self.parent, self.db, None, self.load_proformas)
    
    def view_items(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        proforma_id = tags[-1]
        ProformaItemsWindow(self.parent, self.db, proforma_id, self.load_proformas)
    
    def delete_proforma(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za brisanje.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj predračun?"):
            tags = self.tree.item(selection[0])['tags']
            proforma_id = tags[-1]
            self.db.delete_proforma(proforma_id)
            messagebox.showinfo("Uspeh", "Predračun je uspešno obrisan.")
            self.load_proformas()
    
    def archive_proforma(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za arhiviranje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        proforma_id = tags[-1]
        proforma = self.db.get_proforma_by_id(proforma_id)
        
        if proforma['payment_status'] != 'Plaćeno':
            messagebox.showwarning("Upozorenje", "Možete arhivirati samo potpuno plaćene predračune.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da arhivirate ovaj predračun?"):
            self.db.archive_proforma(proforma_id)
            messagebox.showinfo("Uspeh", "Predračun je uspešno arhiviran.")
            self.load_proformas()
    
    def open_customers(self):
        VendorsWindow(self.parent, self.db, 'customers')
    
    def open_articles(self):
        VendorsWindow(self.parent, self.db, 'articles')
    
    def generate_pdf(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za PDF.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        proforma_id = tags[-1]
        
        try:
            filename = self.pdf_generator.generate_proforma_pdf(proforma_id)
            messagebox.showinfo("Uspeh", f"PDF predračun je kreiran: {filename}")
            
            if messagebox.askyesno("Otvori PDF", "Da li želite da otvorite PDF?"):
                os.startfile(filename)
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri kreiranju PDF-a: {str(e)}")


class ProformaDialog:
    def __init__(self, parent, db, proforma_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi predračun")
        self.window.geometry("900x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.proforma_id = proforma_id
        self.callback = callback
        
        self.items = []
        
        self.setup_ui()
    
    def setup_ui(self):
        # Gornji deo - header info
        header_frame = ttk.LabelFrame(self.window, text="Osnovni podaci", padding=10)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        row = 0
        ttk.Label(header_frame, text="Datum:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.invoice_date_entry = DateEntry(header_frame, width=25, date_pattern='dd.mm.yyyy')
        self.invoice_date_entry.grid(row=row, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(header_frame, text="Kupac:").grid(row=row, column=2, sticky=tk.W, pady=5, padx=(20, 0))
        self.customer_combo = ttk.Combobox(header_frame, width=30, state='readonly')
        customers = self.db.get_all_customers()
        self.customer_map = {c['name']: c['id'] for c in customers}
        self.customer_combo['values'] = list(self.customer_map.keys())
        self.customer_combo.grid(row=row, column=3, pady=5, sticky=tk.W)
        
        row += 1
        ttk.Label(header_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notes_entry = ttk.Entry(header_frame, width=70)
        self.notes_entry.grid(row=row, column=1, columnspan=3, pady=5, sticky=tk.EW)
        
        # Srednji deo - artikli
        items_frame = ttk.LabelFrame(self.window, text="Stavke predračuna", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Toolbar za stavke
        items_toolbar = ttk.Frame(items_frame)
        items_toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        ttk.Button(items_toolbar, text="Dodaj stavku", command=self.add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_toolbar, text="Ukloni stavku", command=self.remove_item).pack(side=tk.LEFT, padx=2)
        
        # Tabela stavki
        columns = ('Šifra', 'Naziv', 'Količina', 'JM', 'Cena', 'Popust %', 'Ukupno')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
        
        self.items_tree.column('Šifra', width=80)
        self.items_tree.column('Naziv', width=200)
        self.items_tree.column('Količina', width=80)
        self.items_tree.column('JM', width=50)
        self.items_tree.column('Cena', width=100)
        self.items_tree.column('Popust %', width=80)
        self.items_tree.column('Ukupno', width=100)
        
        scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscroll=scrollbar.set)
        
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Donji deo - ukupno
        total_frame = ttk.Frame(self.window)
        total_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(total_frame, text="UKUPNO:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=5)
        self.total_label = ttk.Label(total_frame, text="0.00 RSD", font=('Arial', 12, 'bold'))
        self.total_label.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def add_item(self):
        ItemDialog(self.window, self.db, self.on_item_added)
    
    def on_item_added(self, item):
        self.items.append(item)
        self.refresh_items()
    
    def remove_item(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite stavku za uklanjanje.")
            return
        
        index = self.items_tree.index(selection[0])
        self.items.pop(index)
        self.refresh_items()
    
    def refresh_items(self):
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        total = 0
        for item in self.items:
            self.items_tree.insert('', tk.END, values=(
                item['article_code'],
                item['article_name'],
                f"{item['quantity']:.2f}",
                item['unit'],
                f"{item['price']:,.2f}",
                f"{item['discount']:.1f}",
                f"{item['total']:,.2f}"
            ))
            total += item['total']
        
        self.total_label.config(text=f"{total:,.2f} RSD")
    
    def save(self):
        if not self.customer_combo.get():
            messagebox.showerror("Greška", "Molim izaberite kupca.")
            return
        
        if not self.items:
            messagebox.showerror("Greška", "Molim dodajte bar jednu stavku.")
            return
        
        customer_name = self.customer_combo.get()
        customer_id = self.customer_map.get(customer_name)
        invoice_date = self.invoice_date_entry.get_date().strftime('%d.%m.%Y')
        notes = self.notes_entry.get().strip()
        
        total_amount = sum(item['total'] for item in self.items)
        
        proforma_data = {
            'invoice_date': invoice_date,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'total_amount': total_amount,
            'paid_amount': 0,
            'payment_status': 'Neplaćeno',
            'notes': notes
        }
        
        try:
            self.db.add_proforma_invoice(proforma_data, self.items)
            messagebox.showinfo("Uspeh", "Predračun je uspešno kreiran.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class ItemDialog:
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Dodaj stavku")
        self.window.geometry("500x350")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.callback = callback
        
        self.setup_ui()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        ttk.Label(form_frame, text="Artikal:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.article_combo = ttk.Combobox(form_frame, width=37, state='readonly')
        articles = self.db.get_all_articles()
        self.article_map = {f"{a['article_code']} - {a['name']}": a for a in articles}
        self.article_combo['values'] = list(self.article_map.keys())
        self.article_combo.bind('<<ComboboxSelected>>', self.on_article_selected)
        self.article_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Količina:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.quantity_entry = ttk.Entry(form_frame, width=40)
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.bind('<KeyRelease>', self.calculate_total)
        self.quantity_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Jedinica mere:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.unit_entry = ttk.Entry(form_frame, width=40)
        self.unit_entry.insert(0, "kom")
        self.unit_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Cena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.price_entry = ttk.Entry(form_frame, width=40)
        self.price_entry.bind('<KeyRelease>', self.calculate_total)
        self.price_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Popust (%):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.discount_entry = ttk.Entry(form_frame, width=40)
        self.discount_entry.insert(0, "0")
        self.discount_entry.bind('<KeyRelease>', self.calculate_total)
        self.discount_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Ukupno:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.total_label = ttk.Label(form_frame, text="0.00 RSD", font=('Arial', 10, 'bold'))
        self.total_label.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Dodaj", command=self.add).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def on_article_selected(self, event):
        selected = self.article_combo.get()
        if selected in self.article_map:
            article = self.article_map[selected]
            self.unit_entry.delete(0, tk.END)
            self.unit_entry.insert(0, article['unit'])
            self.price_entry.delete(0, tk.END)
            self.price_entry.insert(0, str(article['price']))
            self.discount_entry.delete(0, tk.END)
            self.discount_entry.insert(0, str(article['discount']))
            self.calculate_total()
    
    def calculate_total(self, event=None):
        try:
            quantity = float(self.quantity_entry.get().strip().replace(',', '.'))
            price = float(self.price_entry.get().strip().replace(',', '.'))
            discount = float(self.discount_entry.get().strip().replace(',', '.'))
            
            subtotal = quantity * price
            discount_amount = subtotal * (discount / 100)
            total = subtotal - discount_amount
            
            self.total_label.config(text=f"{total:,.2f} RSD")
        except ValueError:
            self.total_label.config(text="0.00 RSD")
    
    def add(self):
        if not self.article_combo.get():
            messagebox.showerror("Greška", "Molim izaberite artikal.")
            return
        
        try:
            quantity = float(self.quantity_entry.get().strip().replace(',', '.'))
            price = float(self.price_entry.get().strip().replace(',', '.'))
            discount = float(self.discount_entry.get().strip().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validne brojeve.")
            return
        
        selected = self.article_combo.get()
        article = self.article_map[selected]
        
        subtotal = quantity * price
        discount_amount = subtotal * (discount / 100)
        total = subtotal - discount_amount
        
        item = {
            'article_id': article['id'],
            'article_code': article['article_code'],
            'article_name': article['name'],
            'quantity': quantity,
            'unit': self.unit_entry.get().strip(),
            'price': price,
            'discount': discount,
            'total': total,
            'is_paid': 0
        }
        
        self.callback(item)
        self.window.destroy()


class ProformaItemsWindow:
    def __init__(self, parent, db, proforma_id, callback):
        print(f"DEBUG: Otvaranje ProformaItemsWindow za predračun {proforma_id}")
        
        self.window = tk.Toplevel(parent)
        self.window.title("Stavke predračuna")
        self.window.geometry("1000x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.proforma_id = proforma_id
        self.callback = callback
        
        print(f"DEBUG: Pozivam setup_ui()")
        self.setup_ui()
        print(f"DEBUG: Pozivam load_items()")
        self.load_items()
        print(f"DEBUG: Završen __init__")
    
    def setup_ui(self):
        # Header info
        proforma = self.db.get_proforma_by_id(self.proforma_id)
        
        info_frame = ttk.Frame(self.window, padding=10)
        info_frame.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(info_frame, text=f"Predračun: {proforma['proforma_number']}", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=10)
        ttk.Label(info_frame, text=f"Kupac: {proforma['customer_name']}", font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        ttk.Label(info_frame, text=f"Status: {proforma['payment_status']}", font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        
        # Tabela
        columns = ('Šifra', 'Naziv', 'Količina', 'JM', 'Cena', 'Popust %', 'Ukupno', 'Status')
        self.tree = ttk.Treeview(self.window, columns=columns, show='headings')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Šifra', width=80)
        self.tree.column('Naziv', width=200)
        self.tree.column('Količina', width=80)
        self.tree.column('JM', width=50)
        self.tree.column('Cena', width=100)
        self.tree.column('Popust %', width=80)
        self.tree.column('Ukupno', width=100)
        self.tree.column('Status', width=100)
        
        scrollbar = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        
        # Buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Označi kao plaćeno", command=self.mark_paid).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Označi kao neplaćeno", command=self.mark_unpaid).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Zatvori", command=self.close).pack(side=tk.RIGHT, padx=5)
    
    def load_items(self):
        print(f"DEBUG: load_items() je pozvan za predračun {self.proforma_id}")
        
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            items = self.db.get_proforma_items(self.proforma_id)
            print(f"DEBUG (GUI): Učitavanje stavki za predračun {self.proforma_id} - pronađeno: {len(items)}")
            
            if not items:
                print(f"  ⚠️  NEMA STAVKI U BAZI ZA OVAJ PREDRAČUN!")
            
            for item in items:
                print(f"  - Dodajem stavku: {item['article_name']}")
                status = "Plaćeno" if item['is_paid'] else "Neplaćeno"
                
                values = (
                    item['article_code'],
                    item['article_name'],
                    f"{item['quantity']:.2f}",
                    item['unit'],
                    f"{item['price']:,.2f}",
                    f"{item['discount']:.1f}",
                    f"{item['total']:,.2f}",
                    status
                )
                print(f"    Values: {values}")
                
                item_id = self.tree.insert('', tk.END, values=values, tags=(str(item['id']),))
                
                if item['is_paid']:
                    self.tree.tag_configure('paid', background='#90EE90')
            
            print(f"  ✓ Završeno učitavanje stavki")
        except Exception as e:
            print(f"  ❌ GREŠKA u load_items(): {e}")
            import traceback
            traceback.print_exc()
    
    def mark_paid(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite stavku.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        item_id = tags[-1]
        self.db.update_proforma_item_payment(item_id, 1)
        self.load_items()
        messagebox.showinfo("Uspeh", "Stavka je označena kao plaćena.")
    
    def mark_unpaid(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite stavku.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        item_id = tags[-1]
        self.db.update_proforma_item_payment(item_id, 0)
        self.load_items()
        messagebox.showinfo("Uspeh", "Stavka je označena kao neplaćena.")
    
    def close(self):
        self.callback()
        self.window.destroy()