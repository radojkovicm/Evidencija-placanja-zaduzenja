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
        ttk.Button(toolbar, text="Plati", command=self.pay_proforma).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Izmeni", command=self.edit_proforma).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiviraj", command=self.archive_proforma).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_proforma).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Kupci", command=self.open_customers).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Artikli", command=self.open_articles).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiva", command=self.open_archive).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="PDF Predračun", command=self.generate_pdf).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_proformas).pack(side=tk.LEFT, padx=2)
        
        # Filter
        filter_frame = ttk.Frame(self.parent)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_combo = ttk.Combobox(filter_frame, width=18, state='readonly')
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
        
        # Tabela sa novim kolonama
        columns = ('Broj predračuna', 'Datum', 'Kupac', 'Ukupan iznos', 'Plaćeno', 'Preostalo', 'Status', 'Posl. uplata', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Broj predračuna', width=120)
        self.tree.column('Datum', width=100)
        self.tree.column('Kupac', width=180)
        self.tree.column('Ukupan iznos', width=110)
        self.tree.column('Plaćeno', width=110)
        self.tree.column('Preostalo', width=110)
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
        self.tree.bind('<Double-1>', lambda e: self.pay_proforma())
        
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
            filtered = [p for p in filtered if self.db.get_payment_status_proforma(p['id']) == filter_value]
        
        # Search
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            filtered = [p for p in filtered if search_text in (p['customer_name'] or '').lower() or search_text in (p['proforma_number'] or '').lower()]
        
        # Prikaži
        for proforma in filtered:
            proforma_id = proforma['id']
            total_paid = self.db.get_total_paid_proforma(proforma_id)
            remaining = proforma['total_amount'] - total_paid
            status = self.db.get_payment_status_proforma(proforma_id)
            last_payment_date = self.db.get_last_payment_date_proforma(proforma_id) or "-"
            
            notes = proforma['notes'] or ''
            notes_display = notes[:50] + '...' if len(notes) > 50 else notes

            item_id = self.tree.insert('', tk.END, values=(
                proforma['proforma_number'],
                proforma['invoice_date'],
                proforma['customer_name'],
                f"{proforma['total_amount']:,.2f}",
                f"{total_paid:,.2f}",
                f"{remaining:,.2f}",
                status,
                last_payment_date,
                notes_display
            ), tags=(proforma['id'],))
            
            # Oboji red
            if status == 'Plaćeno':
                self.tree.item(item_id, tags=('paid', proforma['id']))
            elif status == 'Delimično':
                self.tree.item(item_id, tags=('partial', proforma['id']))
        
        self.tree.tag_configure('paid', background='#90EE90')
        self.tree.tag_configure('partial', background='#FFFFE0')
        
        self.status_bar.config(text=f"Ukupno predračuna: {len(self.tree.get_children())}")
    
    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.filter_combo.set('Svi')
        self.apply_filters()
    
    def add_proforma(self):
        ProformaDialog(self.parent, self.db, None, self.load_proformas)
    
    def pay_proforma(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za plaćanje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        proforma_id = tags[-1]
        
        # Otvori dialog za sve statuse (readonly ako je plaćeno)
        status = self.db.get_payment_status_proforma(proforma_id)
        readonly = (status == 'Plaćeno')
        
        ProformaPaymentDialog(self.parent, self.db, proforma_id, self.load_proformas, readonly=readonly)
    
    def edit_proforma(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za izmenu.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        proforma_id = tags[-1]
        ProformaEditDialog(self.parent, self.db, proforma_id, self.load_proformas)

    def delete_proforma(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za brisanje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        proforma_id = tags[-1]
        
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj predračun?\n\nOvo će obrisati i sve uplate vezane za ovaj predračun."):
            try:
                self.db.delete_proforma(proforma_id)
                messagebox.showinfo("Uspeh", "Predračun je uspešno obrisan.")
                self.load_proformas()
            except Exception as e:
                messagebox.showerror("Greška", f"Greška pri brisanju: {str(e)}")
    
    def archive_proforma(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za arhiviranje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        proforma_id = tags[-1]
        
        status = self.db.get_payment_status_proforma(proforma_id)
        
        if status != 'Plaćeno':
            remaining = self.db.get_remaining_amount_proforma(proforma_id)
            messagebox.showwarning(
                "Upozorenje", 
                f"Možete arhivirati samo potpuno plaćene predračune.\n\n"
                f"Preostalo za plaćanje: {remaining:,.2f} RSD"
            )
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da arhivirate ovaj predračun?"):
            self.db.archive_proforma(proforma_id)
            messagebox.showinfo("Uspeh", "Predračun je uspešno arhiviran.")
            self.load_proformas()
    
    def open_archive(self):
        ProformaArchiveWindow(self.parent, self.db, self.load_proformas)
    
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


class ProformaPaymentDialog:
    """Dialog za plaćanje predračuna"""
    def __init__(self, parent, db, proforma_id, callback, readonly=False):
        self.window = tk.Toplevel(parent)
        self.window.title("Plaćanje predračuna")
        
        # Maksimiziraj prozor (full screen)
        self.window.state('zoomed')
        
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.proforma_id = proforma_id
        self.callback = callback
        self.proforma = db.get_proforma_by_id(proforma_id)
        self.readonly = readonly
        
        if not self.proforma:
            messagebox.showerror("Greška", "Predračun nije pronađen.")
            self.window.destroy()
            return
        
        self.total_paid = db.get_total_paid_proforma(proforma_id)
        self.remaining = self.proforma['total_amount'] - self.total_paid
        
        self.setup_ui()
        self.load_items()
        self.load_payments()
    
    def setup_ui(self):
        # Konfiguriši window za grid layout
        self.window.grid_rowconfigure(0, weight=0)  # Gornji deo
        self.window.grid_rowconfigure(1, weight=1)  # Srednji deo - ekspanduje se
        self.window.grid_rowconfigure(2, weight=0)  # Donji deo - dugmići
        self.window.grid_columnconfigure(0, weight=1)
        
        # Gornji deo - info i finance frame-ovi
        top_frame = ttk.Frame(self.window, padding=15)
        top_frame.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        
        # Info frame
        info_frame = ttk.LabelFrame(top_frame, text=" 📄 Informacije o predračunu ", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = (
            f"Broj predračuna: {self.proforma['proforma_number']}\n"
            f"Kupac: {self.proforma['customer_name']}\n"
            f"Datum: {self.proforma['invoice_date']}"
        )
        
        ttk.Label(info_frame, text=info_text, font=('Arial', 10)).pack(anchor=tk.W)
        
        # Finance frame
        finance_frame = ttk.LabelFrame(top_frame, text=" 💰 Finansijski pregled ", padding=10)
        finance_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(finance_frame, text="UKUPAN IZNOS:", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(finance_frame, text=f"{self.proforma['total_amount']:,.2f} RSD", font=('Arial', 10)).grid(row=0, column=1, sticky=tk.E, pady=2)
        
        ttk.Label(finance_frame, text="Plaćeno do sada:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(finance_frame, text=f"{self.total_paid:,.2f} RSD", font=('Arial', 10)).grid(row=1, column=1, sticky=tk.E, pady=2)
        
        ttk.Separator(finance_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        
        ttk.Label(finance_frame, text="PREOSTALO ZA PLAĆANJE:", font=('Arial', 11, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=2)
        remaining_color = '#4CAF50' if self.remaining == 0 else '#D32F2F'
        self.remaining_label = ttk.Label(finance_frame, text=f"{self.remaining:,.2f} RSD", font=('Arial', 11, 'bold'), foreground=remaining_color)
        self.remaining_label.grid(row=3, column=1, sticky=tk.E, pady=2)
        
        finance_frame.columnconfigure(0, weight=1)
        finance_frame.columnconfigure(1, weight=1)
        
        # Srednji deo - items, payment i history frame-ovi
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)
        main_frame.grid_rowconfigure(3, weight=1)  # History frame se ekspanduje
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Items frame - tabela stavki
        items_frame = ttk.LabelFrame(main_frame, text=" 📦 Stavke predračuna ", padding=10)
        items_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))

        # Toolbar za stavke
        items_toolbar = ttk.Frame(items_frame)
        items_toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        ttk.Button(items_toolbar, text="✓ Plaćeno", command=self.toggle_item_paid).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_toolbar, text="Osveži", command=self.load_items).pack(side=tk.LEFT, padx=2)

        # Dodaj kolonu "Status"
        columns = ('Šifra', 'Naziv', 'Količina', 'JM', 'Cena', 'Popust %', 'Ukupno', 'Status')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=6, selectmode='browse')

        for col in columns:
            self.items_tree.heading(col, text=col)

        self.items_tree.column('Šifra', width=80)
        self.items_tree.column('Naziv', width=250)
        self.items_tree.column('Količina', width=80)
        self.items_tree.column('JM', width=50)
        self.items_tree.column('Cena', width=100)
        self.items_tree.column('Popust %', width=80)
        self.items_tree.column('Ukupno', width=100)
        self.items_tree.column('Status', width=80)  # Nova kolona

        scrollbar_items = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscroll=scrollbar_items.set)

        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_items.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_items.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Payment frame - sakri ako je readonly
        if not self.readonly:
            payment_frame = ttk.LabelFrame(main_frame, text=" 📝 Nova uplata ", padding=10)
            payment_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))
            
            # Koristi grid layout za bolju organizaciju
            left_frame = ttk.Frame(payment_frame)
            left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
            
            right_frame = ttk.Frame(payment_frame)
            right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Radiobutoni na levoj strani
            self.payment_type = tk.StringVar(value='full')
            
            ttk.Radiobutton(
                left_frame, 
                text=f"Potpuno plaćanje\n({self.remaining:,.2f} RSD)", 
                variable=self.payment_type, 
                value='full',
                command=self.on_payment_type_changed
            ).pack(anchor=tk.W, pady=5)
            
            ttk.Radiobutton(
                left_frame, 
                text="Delimično plaćanje", 
                variable=self.payment_type, 
                value='partial',
                command=self.on_payment_type_changed
            ).pack(anchor=tk.W, pady=5)
            
            # Desna strana - Amount, Date, Notes u grid-u
            row = 0
            ttk.Label(right_frame, text="Iznos uplate:").grid(row=row, column=0, sticky=tk.W, pady=5)
            self.amount_entry = ttk.Entry(right_frame, width=20)
            self.amount_entry.grid(row=row, column=1, padx=5, sticky=tk.W)
            ttk.Label(right_frame, text="RSD").grid(row=row, column=2, sticky=tk.W)
            self.max_label = ttk.Label(right_frame, text=f"(max: {self.remaining:,.2f})", foreground='gray')
            self.max_label.grid(row=row, column=3, padx=5, sticky=tk.W)
            
            row += 1
            ttk.Label(right_frame, text="Datum uplate:").grid(row=row, column=0, sticky=tk.W, pady=5)
            self.payment_date_entry = DateEntry(right_frame, width=17, date_pattern='dd.mm.yyyy')
            self.payment_date_entry.grid(row=row, column=1, padx=5, sticky=tk.W)
            
            row += 1
            ttk.Label(right_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.NW, pady=5)
            self.notes_entry = tk.Text(right_frame, width=40, height=1, wrap=tk.WORD)
            self.notes_entry.grid(row=row, column=1, columnspan=3, padx=5, sticky=tk.EW)

            # Automatsko prilagođavanje visine
            def adjust_height(event=None):
                lines = int(self.notes_entry.index('end-1c').split('.')[0])
                self.notes_entry.config(height=max(3, min(lines, 10)))  # Min 3, max 10 redova

            self.notes_entry.bind('<KeyRelease>', adjust_height)
            
            # Dugmadi desno od polja
            row += 1
            buttons_frame = ttk.Frame(right_frame)
            buttons_frame.grid(row=row, column=0, columnspan=4, sticky=tk.E, pady=10)
            
            ttk.Button(buttons_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.LEFT, padx=5)
            ttk.Button(buttons_frame, text="Sačuvaj uplatu", command=self.save_payment).pack(side=tk.LEFT, padx=5)
            
            self.on_payment_type_changed()
            
            history_row = 2
        else:
            # Readonly info
            readonly_frame = ttk.LabelFrame(main_frame, text=" ✅ Predračun je potpuno plaćen ", padding=10)
            readonly_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))
            
            ttk.Label(
                readonly_frame, 
                text="Ovaj predračun je u potpunosti plaćen. Pregled uplata je dostupan ispod.",
                font=('Arial', 10),
                foreground='#4CAF50'
            ).pack(anchor=tk.W)
            
            history_row = 2
        
        # History frame
        history_frame = ttk.LabelFrame(main_frame, text=" 📋 Istorija uplata ", padding=10)
        history_frame.grid(row=history_row, column=0, sticky='nsew', pady=(0, 10))
        
        columns = ('Datum', 'Iznos (RSD)', 'Napomena')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=8)
        
        self.history_tree.heading('Datum', text='Datum')
        self.history_tree.heading('Iznos (RSD)', text='Iznos (RSD)')
        self.history_tree.heading('Napomena', text='Napomena')
        
        self.history_tree.column('Datum', width=100)
        self.history_tree.column('Iznos (RSD)', width=120)
        self.history_tree.column('Napomena', width=500)
        
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def toggle_item_paid(self):
        """Toggle status plaćenosti izabrane stavke"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite stavku.")
            return
        
        # Uzmi item_id iz tags
        tags = self.items_tree.item(selection[0])['tags']
        if not tags:
            return
        
        item_id = tags[0]
        
        # Uzmi trenutni status
        values = self.items_tree.item(selection[0])['values']
        current_status = values[-1]  # Poslednja kolona je Status
        
        # Toggle status
        new_status = 0 if current_status == 'Plaćeno' else 1
        
        try:
            self.db.mark_proforma_item_paid(item_id, new_status)
            self.load_items()  # Osveži prikaz
            
            # ZAMENI ovu liniju:
            # self.status_label.config(text=f"Stavka označena kao {status_text}")
            
            # SA:
            status_text = "plaćenom" if new_status == 1 else "neplaćenom"
            messagebox.showinfo("Uspeh", f"Stavka označena kao {status_text}")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri označavanju: {str(e)}")
    
    def on_payment_type_changed(self):
        """Hendluj promenu tipa plaćanja"""
        if self.payment_type.get() == 'full':
            self.amount_entry.delete(0, tk.END)
            self.amount_entry.insert(0, f"{self.remaining:.2f}")
            self.amount_entry.config(state='disabled')
        else:
            self.amount_entry.config(state='normal')
            self.amount_entry.delete(0, tk.END)
    
    def load_items(self):
        """Učitaj stavke predračuna u tabelu"""
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        # Koristi novu metodu koja vraća i ID
        items = self.db.get_proforma_items_with_id(self.proforma_id)
        
        for item in items:
            is_paid = item.get('is_paid', 0)
            status_text = 'Plaćeno' if is_paid else 'Neplaćeno'
            
            item_id = self.items_tree.insert('', tk.END, values=(
                item['article_code'],
                item['article_name'],
                f"{item['quantity']:.2f}",
                item['unit'],
                f"{item['price']:,.2f}",
                f"{item['discount']:.1f}",
                f"{item['total']:,.2f}",
                status_text
            ), tags=(item['id'],))
            
            # Oboji plaćene stavke zeleno
            if is_paid:
                self.items_tree.item(item_id, tags=('paid', item['id']))
        
        # Dodaj tag konfiguraciju
        self.items_tree.tag_configure('paid', background='#90EE90')
    
    def load_payments(self):
        """Učitaj istoriju uplata u tabelu"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        payments = self.db.get_proforma_payments(self.proforma_id)
        
        for payment in payments:
            notes = payment['notes'] or ''
            notes_display = notes[:50] + '...' if len(notes) > 50 else notes
            
            self.history_tree.insert('', tk.END, values=(
                payment['payment_date'],
                f"{payment['payment_amount']:,.2f}",
                notes_display
            ))
    
    def save_payment(self):
        """Sačuvaj uplatu"""
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
            self.db.add_proforma_payment(self.proforma_id, amount, payment_date, notes)
            messagebox.showinfo("Uspeh", "Uplata je uspešno evidentirana.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")
    
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


class ProformaEditDialog:
    """Dialog za izmenu predračuna"""
    def __init__(self, parent, db, proforma_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Izmeni predračun")
        self.window.geometry("1000x700")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.proforma_id = proforma_id
        self.callback = callback
        self.proforma = db.get_proforma_by_id(proforma_id)
        
        if not self.proforma:
            messagebox.showerror("Greška", "Predračun nije pronađen.")
            self.window.destroy()
            return
        
        self.items = [dict(item) for item in db.get_proforma_items(proforma_id)]
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        # Header info
        header_frame = ttk.LabelFrame(self.window, text="Osnovni podaci", padding=10)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        row = 0
        ttk.Label(header_frame, text="Broj predračuna:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(header_frame, text=self.proforma['proforma_number'], font=('Arial', 10, 'bold')).grid(row=row, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(header_frame, text="Datum:").grid(row=row, column=2, sticky=tk.W, pady=5, padx=(20, 0))
        self.invoice_date_entry = DateEntry(header_frame, width=25, date_pattern='dd.mm.yyyy')
        self.invoice_date_entry.grid(row=row, column=3, pady=5, sticky=tk.W)
        
        row += 1
        ttk.Label(header_frame, text="Kupac:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.customer_combo = ttk.Combobox(header_frame, width=30, state='readonly')
        customers = self.db.get_all_customers()
        self.customer_map = {c['name']: c['id'] for c in customers}
        self.customer_combo['values'] = list(self.customer_map.keys())
        self.customer_combo.grid(row=row, column=1, columnspan=3, pady=5, sticky=tk.W)
        
        ttk.Label(header_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.notes_entry = tk.Text(header_frame, width=70, height=1, wrap=tk.WORD)
        self.notes_entry.grid(row=row, column=1, columnspan=3, pady=5, sticky=tk.EW)

        # Automatsko prilagođavanje visine
        def adjust_height(event=None):
            lines = int(self.notes_entry.index('end-1c').split('.')[0])
            self.notes_entry.config(height=max(3, min(lines, 10)))  # Min 3, max 10 redova

        self.notes_entry.bind('<KeyRelease>', adjust_height)
        
        # Items frame
        items_frame = ttk.LabelFrame(self.window, text="Stavke predračuna", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Toolbar
        items_toolbar = ttk.Frame(items_frame)
        items_toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        ttk.Button(items_toolbar, text="Dodaj stavku", command=self.add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_toolbar, text="Ukloni stavku", command=self.remove_item).pack(side=tk.LEFT, padx=2)
        
        # Tabela
        columns = ('Šifra', 'Naziv', 'Količina', 'JM', 'Cena', 'Popust %', 'Ukupno')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
        
        self.items_tree.column('Šifra', width=80)
        self.items_tree.column('Naziv', width=250)
        self.items_tree.column('Količina', width=80)
        self.items_tree.column('JM', width=60)
        self.items_tree.column('Cena', width=100)
        self.items_tree.column('Popust %', width=80)
        self.items_tree.column('Ukupno', width=100)
        
        scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscroll=scrollbar.set)
        
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Total frame
        total_frame = ttk.Frame(self.window)
        total_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(total_frame, text="UKUPNO:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=5)
        self.total_label = ttk.Label(total_frame, text="0.00 RSD", font=('Arial', 12, 'bold'))
        self.total_label.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Obriši predračun", command=self.delete_proforma).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Sačuvaj izmene", command=self.save).pack(side=tk.RIGHT, padx=5)
        
        # Status bar (ako već ne postoji)
        if not hasattr(self, 'status_label'):
            self.status_label = ttk.Label(self.window, text="", relief=tk.SUNKEN, anchor=tk.W)
            self.status_label.grid(row=3, column=0, sticky='ew', padx=15, pady=(0, 10))
    
    def load_data(self):
        self.invoice_date_entry.set_date(datetime.strptime(self.proforma['invoice_date'], '%d.%m.%Y'))
        self.customer_combo.set(self.proforma['customer_name'])
        self.notes_entry.insert('1.0', self.proforma['notes'] or '')
        self.refresh_items()
    
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
    
    def delete_proforma(self):
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj predračun?\n\nOvo će obrisati i sve uplate vezane za ovaj predračun."):
            try:
                self.db.delete_proforma(self.proforma_id)
                messagebox.showinfo("Uspeh", "Predračun je uspešno obrisan.")
                self.callback()
                self.window.destroy()
            except Exception as e:
                messagebox.showerror("Greška", f"Greška pri brisanju: {str(e)}")
    
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
        notes = self.notes_entry.get('1.0', tk.END).strip()
        
        total_amount = sum(item['total'] for item in self.items)
        
        proforma_data = {
            'invoice_date': invoice_date,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'total_amount': total_amount,
            'notes': notes
        }
        
        try:
            self.db.update_proforma_invoice(self.proforma_id, proforma_data, self.items)
            messagebox.showinfo("Uspeh", "Predračun je uspešno izmenjen.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class ItemDialog:
    """Dialog za dodavanje stavke"""
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Dodaj stavku")
        self.window.geometry("550x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.callback = callback
        self.search_results = []
        
        self.setup_ui()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        # Pretraga po šifri ili imenu
        ttk.Label(form_frame, text="Šifra/Naziv:").grid(row=row, column=0, sticky=tk.W, pady=5)
        search_frame = ttk.Frame(form_frame)
        search_frame.grid(row=row, column=1, pady=5, sticky=tk.EW)
        
        self.code_entry = ttk.Entry(search_frame, width=20)
        self.code_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.code_entry.bind('<Return>', lambda e: self.find_articles())
        
        ttk.Button(search_frame, text="Pronađi", command=self.find_articles).pack(side=tk.LEFT)
        row += 1
        
        # Dropdown za rezultate pretrage
        self.results_frame = ttk.Frame(form_frame)
        self.results_frame.grid(row=row, column=1, pady=5, sticky=tk.EW)
        
        self.results_listbox = tk.Listbox(self.results_frame, height=8, width=47)
        self.results_scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.results_listbox.yview)
        self.results_listbox.config(yscrollcommand=self.results_scrollbar.set)
        
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_listbox.bind('<<ListboxSelect>>', self.on_search_result_selected)
        self.results_listbox.bind('<Double-Button-1>', lambda e: self.on_search_result_selected(e, auto_add=False))
        
        self.results_frame.grid_remove()  # Sakrij na početku
        row += 1
        
        ttk.Label(form_frame, text="ILI", font=('Arial', 9, 'italic')).grid(row=row, column=0, columnspan=2, pady=5)
        row += 1
        
        # Izbor iz liste
        ttk.Label(form_frame, text="Artikal:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.article_combo = ttk.Combobox(form_frame, width=47, state='readonly')
        articles = self.db.get_all_articles()
        self.article_map = {f"{a['article_code']} - {a['name']}": a for a in articles}
        self.article_combo['values'] = list(self.article_map.keys())
        self.article_combo.bind('<<ComboboxSelected>>', self.on_article_selected)
        self.article_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        
        ttk.Label(form_frame, text="Količina:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.quantity_entry = ttk.Entry(form_frame, width=50)
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.bind('<KeyRelease>', self.calculate_total)
        self.quantity_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Jedinica mere:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.unit_entry = ttk.Entry(form_frame, width=50)
        self.unit_entry.insert(0, "kom")
        self.unit_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Cena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.price_entry = ttk.Entry(form_frame, width=50)
        self.price_entry.insert(0, "0")
        self.price_entry.bind('<KeyRelease>', self.calculate_total)
        self.price_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Popust (%):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.discount_entry = ttk.Entry(form_frame, width=50)
        self.discount_entry.insert(0, "0")
        self.discount_entry.bind('<KeyRelease>', self.calculate_total)
        self.discount_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Ukupno:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.total_label = ttk.Label(form_frame, text="0.00 RSD", font=('Arial', 11, 'bold'))
        self.total_label.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Dodaj", command=self.add).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def find_articles(self):
        """Pretražuje artikle po šifri ili imenu"""
        search_term = self.code_entry.get().strip()
        
        if len(search_term) < 3:
            messagebox.showwarning("Pretraga", "Molim unesite minimum 3 karaktera za pretragu.")
            self.results_frame.grid_remove()
            return
        
        self.search_results = self.db.search_articles(search_term)
        
        # Očisti listu
        self.results_listbox.delete(0, tk.END)
        
        if not self.search_results:
            messagebox.showinfo("Pretraga", f"Nisu pronađeni artikli sa '{search_term}'.")
            self.results_frame.grid_remove()
            return
        
        if len(self.search_results) == 1:
            # Ako je samo jedan rezultat, automatski popuni
            self.populate_article_data(self.search_results[0])
            self.results_frame.grid_remove()
            messagebox.showinfo("Pronađeno", f"Artikal: {self.search_results[0]['name']}")
        else:
            # Prikaži dropdown sa rezultatima
            for article in self.search_results:
                display_text = f"{article['article_code']} - {article['name']}"
                self.results_listbox.insert(tk.END, display_text)
            
            self.results_frame.grid()
    
    def on_search_result_selected(self, event, auto_add=True):
        """Kada korisnik izabere artikal iz rezultata pretrage"""
        selection = self.results_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        article = self.search_results[index]
        
        self.populate_article_data(article)
        self.results_frame.grid_remove()
        
        # Postavi fokus na količinu
        self.quantity_entry.focus()
    
    def populate_article_data(self, article):
        """Popunjava formu podacima o artiklu"""
        # Popuni šifru
        self.code_entry.delete(0, tk.END)
        self.code_entry.insert(0, article['article_code'])
        
        # Popuni jedinicu, cenu i popust
        self.unit_entry.delete(0, tk.END)
        self.unit_entry.insert(0, article['unit'])
        
        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, str(article['price']))
        
        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(0, str(article['discount']))
        
        # Selektuj u combo box
        key = f"{article['article_code']} - {article['name']}"
        if key in self.article_map:
            self.article_combo.set(key)
        
        self.calculate_total()
    
    def on_article_selected(self, event):
        """Kada korisnik izabere artikal iz combo boxa"""
        selected = self.article_combo.get()
        if selected in self.article_map:
            article = self.article_map[selected]
            self.populate_article_data(article)
    
    def calculate_total(self, event=None):
        """Izračunava ukupnu cenu"""
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
        """Dodaje stavku u predračun"""
        selected = self.article_combo.get()
        if not selected:
            messagebox.showerror("Greška", "Molim izaberite artikal.")
            return
        
        try:
            quantity = float(self.quantity_entry.get().strip().replace(',', '.'))
            price = float(self.price_entry.get().strip().replace(',', '.'))
            discount = float(self.discount_entry.get().strip().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validne brojeve.")
            return
        
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

class ProformaArchiveWindow:
    """Prozor za arhivu predračuna"""
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Arhiva predračuna")
        self.window.geometry("1400x600")
        self.window.transient(parent)
        self.window.grab_set()
        
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
        
        columns = ('Broj predračuna', 'Datum', 'Kupac', 'Ukupan iznos', 'Plaćeno', 'Status', 'Posl. uplata', 'Napomena')
        self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Broj predračuna', width=120)
        self.tree.column('Datum', width=100)
        self.tree.column('Kupac', width=200)
        self.tree.column('Ukupan iznos', width=120)
        self.tree.column('Plaćeno', width=120)
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
        
        proformas = self.db.get_all_proforma_invoices(include_archived=True)
        archived = [p for p in proformas if p.get('is_archived')]
        
        for proforma in archived:
            proforma_id = proforma['id']
            total_paid = self.db.get_total_paid_proforma(proforma_id)
            status = self.db.get_payment_status_proforma(proforma_id)
            last_payment_date = self.db.get_last_payment_date_proforma(proforma_id) or "-"
            
            notes = proforma['notes'] or ''
            notes_display = notes[:50] + '...' if len(notes) > 50 else notes

            self.tree.insert('', tk.END, values=(
                proforma['proforma_number'],
                proforma['invoice_date'],
                proforma['customer_name'],
                f"{proforma['total_amount']:,.2f}",
                f"{total_paid:,.2f}",
                status,
                last_payment_date,
                notes_display
            ), tags=(proforma['id'],))
    
    def unarchive(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za vraćanje iz arhive.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da vratite ovaj predračun iz arhive?"):
            proforma_id = self.tree.item(selection[0])['tags'][0]
            self.db.unarchive_proforma(proforma_id)
            messagebox.showinfo("Uspeh", "Predračun je uspešno vraćen iz arhive.")
            self.load_archive()
            self.callback()
    
    def delete(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite predračun za brisanje.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj predračun iz arhive?\n\nOvo će obrisati i sve uplate vezane za ovaj predračun."):
            proforma_id = self.tree.item(selection[0])['tags'][0]
            self.db.delete_proforma(proforma_id)
            messagebox.showinfo("Uspeh", "Predračun je uspešno obrisan.")
            self.load_archive()
            self.callback()
        
        payments = self.db.get_proforma_payments(self.proforma_id)
        
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
            self.db.add_proforma_payment(self.proforma_id, amount, payment_date, notes)
            messagebox.showinfo("Uspeh", "Uplata je uspešno evidentirana.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class ProformaDialog:
    """Dialog za kreiranje novog predračuna"""
    def __init__(self, parent, db, proforma_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi predračun" if proforma_id is None else "Izmena predračuna")
        self.window.geometry("1000x700")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.proforma_id = proforma_id
        self.callback = callback
        
        self.items = []
        self.customer_map = {}
        
        # Ako je edit mode, učitaj postojeće podatke
        if proforma_id is not None:
            self.proforma = db.get_proforma_by_id(proforma_id)
            if self.proforma:
                items_from_db = db.get_proforma_items(proforma_id)
                self.items = [dict(item) for item in items_from_db]
        
        self.setup_ui()
        
        if proforma_id is not None and self.proforma:
            self.load_proforma_data()
    
    def setup_ui(self):
        # Header info
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
        ttk.Label(header_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.notes_entry = tk.Text(header_frame, width=70, height=1, wrap=tk.WORD)
        self.notes_entry.grid(row=row, column=1, columnspan=3, pady=5, sticky=tk.EW)

        # Automatsko prilagođavanje visine
        def adjust_height(event=None):
            lines = int(self.notes_entry.index('end-1c').split('.')[0])
            self.notes_entry.config(height=max(3, min(lines, 10)))  # Min 3, max 10 redova

        self.notes_entry.bind('<KeyRelease>', adjust_height)
        
        # Items frame
        items_frame = ttk.LabelFrame(self.window, text="Stavke predračuna", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Toolbar
        items_toolbar = ttk.Frame(items_frame)
        items_toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        ttk.Button(items_toolbar, text="Dodaj stavku", command=self.add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_toolbar, text="Ukloni stavku", command=self.remove_item).pack(side=tk.LEFT, padx=2)
        
        # Tabela
        columns = ('Šifra', 'Naziv', 'Količina', 'JM', 'Cena', 'Popust %', 'Ukupno')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
        
        self.items_tree.column('Šifra', width=80)
        self.items_tree.column('Naziv', width=250)
        self.items_tree.column('Količina', width=80)
        self.items_tree.column('JM', width=60)
        self.items_tree.column('Cena', width=100)
        self.items_tree.column('Popust %', width=80)
        self.items_tree.column('Ukupno', width=100)
        
        scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscroll=scrollbar.set)
        
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Total frame
        total_frame = ttk.Frame(self.window)
        total_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(total_frame, text="UKUPNO:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=5)
        self.total_label = ttk.Label(total_frame, text="0.00 RSD", font=('Arial', 12, 'bold'))
        self.total_label.pack(side=tk.LEFT, padx=5)
        
        # Button frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def load_proforma_data(self):
        """Učitaj podatke postojećeg predračuna u formu"""
        if self.proforma:
            # Postavi datum
            invoice_date = self.proforma['invoice_date']
            try:
                date_obj = datetime.strptime(invoice_date, '%d.%m.%Y')
                self.invoice_date_entry.set_date(date_obj)
            except:
                pass
            
            # Postavi kupca
            customer_name = self.proforma['customer_name']
            self.customer_combo.set(customer_name)
            
            # Postavi napomenu
            self.notes_entry.delete('1.0', tk.END)
            if self.proforma.get('notes'):
                self.notes_entry.insert('1.0', self.proforma['notes'])
            
            # Prikaži stavke
            self.refresh_items()
    
    def add_item(self):
        """Otvori dialog za dodavanje stavke"""
        ItemDialog(self.window, self.db, self.on_item_added)
    
    def on_item_added(self, item):
        """Callback kada je stavka dodata"""
        self.items.append(item)
        self.refresh_items()
    
    def remove_item(self):
        """Ukloni izabranu stavku"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite stavku za uklanjanje.")
            return
        
        index = self.items_tree.index(selection[0])
        self.items.pop(index)
        self.refresh_items()
    
    def refresh_items(self):
        """Osveži prikaz stavki u tabeli"""
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        total = 0
        for item in self.items:
            self.items_tree.insert('', tk.END, values=(
                item.get('article_code', ''),
                item['article_name'],
                f"{item['quantity']:.2f}",
                item.get('unit', 'kom'),
                f"{item['price']:,.2f}",
                f"{item.get('discount', 0):.1f}",
                f"{item['total']:,.2f}"
            ))
            total += item['total']
        
        self.total_label.config(text=f"{total:,.2f} RSD")
    
    def save(self):
        """Sačuvaj predračun"""
        if not self.customer_combo.get():
            messagebox.showerror("Greška", "Molim izaberite kupca.")
            return
        
        if not self.items:
            messagebox.showerror("Greška", "Molim dodajte bar jednu stavku.")
            return
        
        customer_name = self.customer_combo.get()
        customer_id = self.customer_map.get(customer_name)
        invoice_date = self.invoice_date_entry.get_date().strftime('%d.%m.%Y')
        notes = self.notes_entry.get('1.0', tk.END).strip()
        
        total_amount = sum(item['total'] for item in self.items)
        
        proforma_data = {
            'invoice_date': invoice_date,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'total_amount': total_amount,
            'notes': notes
        }
        
        try:
            if self.proforma_id is None:
                # Novo kreiranje
                self.db.add_proforma_invoice(proforma_data, self.items)
                messagebox.showinfo("Uspeh", "Predračun je uspešno kreiran.")
            else:
                # Update postojećeg
                self.db.update_proforma_invoice(self.proforma_id, proforma_data, self.items)
                messagebox.showinfo("Uspeh", "Predračun je uspešno ažuriran.")
            
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class ProformaEditDialog(ProformaDialog):
    """Dialog za izmenu predračuna - nasledjuje ProformaDialog"""
    def __init__(self, parent, db, proforma_id, callback):
        super().__init__(parent, db, proforma_id, callback)