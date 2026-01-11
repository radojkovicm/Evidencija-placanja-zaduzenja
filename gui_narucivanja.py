import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry
from gui_vendors import VendorsWindow
from pdf_generator import PDFGenerator
import os


class NarucivanjeTab:
    """Tab za naručivanje robe (dobavljači)"""
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.pdf_generator = PDFGenerator(db)

        self.all_orders = []

        self.setup_ui()
        self.load_orders()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Nova narudžbina", command=self.add_order).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Prikaži stavke", command=self.view_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Izmeni", command=self.edit_order).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_order).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiviraj", command=self.archive_order).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Dobavljači", command=self.open_vendors).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Artikli", command=self.open_articles).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiva", command=self.open_archive).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="PDF Narudžbina", command=self.generate_pdf).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_orders).pack(side=tk.LEFT, padx=2)

        # Filter
        filter_frame = ttk.Frame(self.parent)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Pretraga:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(filter_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self.apply_filters())

        # Table
        table_container = ttk.Frame(self.parent)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('Broj narudžbine', 'Datum', 'Dobavljač', 'Broj stavki', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings')

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column('Broj narudžbine', width=120)
        self.tree.column('Datum', width=100)
        self.tree.column('Dobavljač', width=250)
        self.tree.column('Broj stavki', width=100)
        self.tree.column('Napomena', width=300)

        vsb = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=hsb.set)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Double-click za pregled stavki
        self.tree.bind('<Double-1>', lambda e: self.view_items())

        # Status bar
        self.status_bar = ttk.Label(self.parent, text="Spremno", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_orders(self):
        self.all_orders = self.db.get_all_orders(include_archived=False)
        self.apply_filters()
        self.status_bar.config(text=f"Učitano {len(self.all_orders)} narudžbina")

    def apply_filters(self):
        search_text = self.search_entry.get().lower()

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Filter and display
        for order in self.all_orders:
            # Pretraži po svim poljima
            if search_text:
                searchable = f"{order['order_number']} {order['vendor_name']} {order.get('notes', '')}".lower()
                if search_text not in searchable:
                    continue

            # Prebroj stavke
            items = self.db.get_order_items(order['id'])
            num_items = len(items)

            self.tree.insert('', tk.END, values=(
                order['order_number'],
                order['order_date'],
                order['vendor_name'],
                num_items,
                order.get('notes', '')
            ), tags=(order['id'],))

    def add_order(self):
        OrderDialog(self.parent, self.db, self.load_orders)

    def edit_order(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite narudžbinu za izmenu.")
            return

        order_id = self.tree.item(selection[0])['tags'][0]
        OrderDialog(self.parent, self.db, self.load_orders, order_id=order_id)

    def delete_order(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite narudžbinu za brisanje.")
            return

        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovu narudžbinu?"):
            order_id = self.tree.item(selection[0])['tags'][0]
            self.db.delete_order(order_id)
            self.load_orders()
            messagebox.showinfo("Uspeh", "Narudžbina je uspešno obrisana.")

    def archive_order(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite narudžbinu za arhiviranje.")
            return

        order_id = self.tree.item(selection[0])['tags'][0]
        self.db.archive_order(order_id)
        self.load_orders()
        messagebox.showinfo("Uspeh", "Narudžbina je arhivirana.")

    def view_items(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite narudžbinu.")
            return

        order_id = self.tree.item(selection[0])['tags'][0]
        OrderItemsWindow(self.parent, self.db, order_id)

    def open_vendors(self):
        VendorsWindow(self.parent, self.db, 'vendors')

    def open_articles(self):
        VendorsWindow(self.parent, self.db, 'articles')

    def open_archive(self):
        OrderArchiveWindow(self.parent, self.db, self.load_orders)

    def generate_pdf(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite narudžbinu.")
            return

        order_id = self.tree.item(selection[0])['tags'][0]
        filename = self.pdf_generator.generate_order_pdf(order_id)

        if filename:
            messagebox.showinfo("Uspeh", f"PDF narudžbine je kreiran:\n{filename}")
            if os.path.exists(filename):
                os.startfile(filename)
        else:
            messagebox.showerror("Greška", "Greška pri kreiranju PDF-a.")


class OrderDialog:
    """Dialog za kreiranje/izmenu narudžbine"""
    def __init__(self, parent, db, callback, order_id=None):
        self.db = db
        self.callback = callback
        self.order_id = order_id
        self.items = []

        self.window = tk.Toplevel(parent)
        self.window.title("Izmeni narudžbinu" if order_id else "Nova narudžbina")
        self.window.geometry("800x600")
        self.window.grab_set()

        self.setup_ui()

        if order_id:
            self.load_order_data()

    def setup_ui(self):
        # Header Frame
        header_frame = ttk.LabelFrame(self.window, text="Osnovni podaci", padding=10)
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0

        # Datum narudžbine
        ttk.Label(header_frame, text="Datum narudžbine:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.order_date_entry = DateEntry(header_frame, width=27, date_pattern='dd.mm.yyyy')
        self.order_date_entry.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # Dobavljač
        ttk.Label(header_frame, text="Dobavljač:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.vendor_combo = ttk.Combobox(header_frame, width=27, state='readonly')
        vendors = self.db.get_all_vendors()
        self.vendor_map = {v['name']: v['id'] for v in vendors}
        self.vendor_combo['values'] = list(self.vendor_map.keys())
        self.vendor_combo.grid(row=row, column=1, pady=5, sticky=tk.W)
        row += 1

        # Napomena
        ttk.Label(header_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notes_entry = ttk.Entry(header_frame, width=30)
        self.notes_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        header_frame.columnconfigure(1, weight=1)

        # Items Frame
        items_frame = ttk.LabelFrame(self.window, text="Stavke narudžbine", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Items Toolbar
        items_toolbar = ttk.Frame(items_frame)
        items_toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(items_toolbar, text="Dodaj stavku", command=self.add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_toolbar, text="Ukloni stavku", command=self.remove_item).pack(side=tk.LEFT, padx=2)

        # Items Table
        items_table_container = ttk.Frame(items_frame)
        items_table_container.pack(fill=tk.BOTH, expand=True)

        columns = ('Naziv', 'Količina', 'JM', 'Napomena')
        self.items_tree = ttk.Treeview(items_table_container, columns=columns, show='headings', height=10)

        self.items_tree.heading('Naziv', text='Naziv artikla')
        self.items_tree.heading('Količina', text='Količina')
        self.items_tree.heading('JM', text='JM')
        self.items_tree.heading('Napomena', text='Napomena')

        self.items_tree.column('Naziv', width=350)
        self.items_tree.column('Količina', width=80)
        self.items_tree.column('JM', width=60)
        self.items_tree.column('Napomena', width=310)

        vsb = ttk.Scrollbar(items_table_container, orient=tk.VERTICAL, command=self.items_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.items_tree.configure(yscrollcommand=vsb.set)

        self.items_tree.pack(fill=tk.BOTH, expand=True)

        # Button Frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)

    def load_order_data(self):
        order = self.db.get_order_by_id(self.order_id)
        if not order:
            return

        # Postavi datum
        date_obj = datetime.strptime(order['order_date'], '%d.%m.%Y')
        self.order_date_entry.set_date(date_obj)

        # Postavi dobavljača
        self.vendor_combo.set(order['vendor_name'])

        # Postavi napomenu
        if order.get('notes'):
            self.notes_entry.insert(0, order['notes'])

        # Učitaj stavke
        items = self.db.get_order_items(self.order_id)
        for item in items:
            self.items.append({
                'article_id': item['article_id'],
                'article_code': item['article_code'],
                'article_name': item['article_name'],
                'quantity': item['quantity'],
                'unit': item['unit'],
                'notes': item.get('notes', '')
            })

        self.refresh_items()

    def add_item(self):
        OrderItemDialog(self.window, self.db, self.on_item_added)

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
        self.items_tree.delete(*self.items_tree.get_children())

        for item in self.items:
            self.items_tree.insert('', tk.END, values=(
                item['article_name'],
                f"{item['quantity']:.2f}",
                item['unit'],
                item.get('notes', '')
            ))

    def save(self):
        if not self.vendor_combo.get():
            messagebox.showerror("Greška", "Molim izaberite dobavljača.")
            return

        if not self.items:
            messagebox.showerror("Greška", "Molim dodajte bar jednu stavku.")
            return

        vendor_name = self.vendor_combo.get()
        vendor_id = self.vendor_map.get(vendor_name)
        order_date = self.order_date_entry.get_date().strftime('%d.%m.%Y')
        notes = self.notes_entry.get().strip()

        order_data = {
            'order_date': order_date,
            'vendor_id': vendor_id,
            'vendor_name': vendor_name,
            'notes': notes
        }

        try:
            if self.order_id:  # Edit mode
                self.db.update_order(self.order_id, order_data, self.items)
                messagebox.showinfo("Uspeh", "Narudžbina je uspešno izmenjena.")
            else:  # Create mode
                self.db.add_order(order_data, self.items)
                messagebox.showinfo("Uspeh", "Narudžbina je uspešno kreirana.")

            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class OrderItemDialog:
    """Dialog za dodavanje artikla u narudžbinu (sa pretragom i auto-popunjavanjem)"""
    def __init__(self, parent, db, callback):
        self.db = db
        self.callback = callback
        self.search_results = []

        self.window = tk.Toplevel(parent)
        self.window.title("Dodaj artikal")
        self.window.geometry("550x480")
        self.window.grab_set()

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

        # Količina
        ttk.Label(form_frame, text="Količina:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.quantity_entry = ttk.Entry(form_frame, width=50)
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        # Jedinica mere (auto-popunjava se)
        ttk.Label(form_frame, text="Jedinica mere:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.unit_entry = ttk.Entry(form_frame, width=50)
        self.unit_entry.insert(0, "kom")
        self.unit_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        # Napomena
        ttk.Label(form_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.notes_text = tk.Text(form_frame, width=48, height=3)
        self.notes_text.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        form_frame.columnconfigure(1, weight=1)

        # Button Frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        ttk.Button(button_frame, text="Dodaj", command=self.add).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)

    def find_articles(self):
        """Pretražuje artikle po šifri ili imenu"""
        search_term = self.code_entry.get().strip()

        if len(search_term) < 3:
            self.results_frame.grid_remove()
            return

        self.search_results = self.db.search_articles(search_term)

        # Očisti listu
        self.results_listbox.delete(0, tk.END)

        if not self.search_results:
            self.results_frame.grid_remove()
            return

        if len(self.search_results) == 1:
            # Ako je samo jedan rezultat, automatski popuni i ostani na ekranu
            self.populate_article_data(self.search_results[0])
            self.results_frame.grid_remove()
            # Fokusiraj količinu da korisnik može odmah da unese
            self.quantity_entry.focus()
            self.quantity_entry.select_range(0, tk.END)
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

        # Popuni jedinicu mere
        self.unit_entry.delete(0, tk.END)
        self.unit_entry.insert(0, article['unit'])

        # Selektuj u combo box
        key = f"{article['article_code']} - {article['name']}"
        if key in self.article_map:
            self.article_combo.set(key)

    def on_article_selected(self, event):
        """Kada korisnik izabere artikal iz combo boxa"""
        selected = self.article_combo.get()
        if selected in self.article_map:
            article = self.article_map[selected]
            self.populate_article_data(article)

    def add(self):
        """Dodaje artikal u narudžbinu"""
        if not self.article_combo.get():
            messagebox.showerror("Greška", "Molim izaberite artikal.")
            return

        try:
            quantity = float(self.quantity_entry.get().strip().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validnu količinu.")
            return

        selected = self.article_combo.get()
        article = self.article_map[selected]

        item = {
            'article_id': article['id'],
            'article_code': article['article_code'],
            'article_name': article['name'],
            'quantity': quantity,
            'unit': self.unit_entry.get().strip(),
            'notes': self.notes_text.get('1.0', tk.END).strip()
        }

        self.callback(item)
        self.window.destroy()


class OrderItemsWindow:
    """Prozor za pregled stavki narudžbine (read-only)"""
    def __init__(self, parent, db, order_id):
        self.db = db
        self.order_id = order_id

        self.window = tk.Toplevel(parent)
        self.window.title("Stavke narudžbine")
        self.window.geometry("800x500")
        self.window.grab_set()

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        # Info Frame
        info_frame = ttk.LabelFrame(self.window, text="Podaci o narudžbini", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.info_label = ttk.Label(info_frame, text="", justify=tk.LEFT)
        self.info_label.pack(anchor=tk.W)

        # Items Frame
        items_frame = ttk.LabelFrame(self.window, text="Stavke", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ('Rb.', 'Naziv artikla', 'Količina', 'JM', 'Napomena')
        self.tree = ttk.Treeview(items_frame, columns=columns, show='headings')

        self.tree.heading('Rb.', text='Rb.')
        self.tree.heading('Naziv artikla', text='Naziv artikla')
        self.tree.heading('Količina', text='Količina')
        self.tree.heading('JM', text='JM')
        self.tree.heading('Napomena', text='Napomena')

        self.tree.column('Rb.', width=50)
        self.tree.column('Naziv artikla', width=300)
        self.tree.column('Količina', width=80)
        self.tree.column('JM', width=60)
        self.tree.column('Napomena', width=310)

        vsb = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(items_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=hsb.set)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Button Frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Zatvori", command=self.window.destroy).pack(side=tk.RIGHT)

    def load_data(self):
        order = self.db.get_order_by_id(self.order_id)
        if not order:
            return

        # Prikaži info
        info_text = f"Broj narudžbine: {order['order_number']}\n"
        info_text += f"Datum: {order['order_date']}\n"
        info_text += f"Dobavljač: {order['vendor_name']}\n"
        if order.get('notes'):
            info_text += f"Napomena: {order['notes']}"

        self.info_label.config(text=info_text)

        # Učitaj i prikaži stavke
        items = self.db.get_order_items(self.order_id)

        for idx, item in enumerate(items, 1):
            self.tree.insert('', tk.END, values=(
                idx,
                item['article_name'],
                f"{item['quantity']:.2f}",
                item['unit'],
                item.get('notes', '')
            ))


class OrderArchiveWindow:
    """Prozor za pregled arhiviranih narudžbina"""
    def __init__(self, parent, db, callback):
        self.db = db
        self.callback = callback

        self.window = tk.Toplevel(parent)
        self.window.title("Arhiva narudžbina")
        self.window.geometry("1000x600")
        self.window.grab_set()

        self.setup_ui()
        self.load_archive()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Vrati iz arhive", command=self.unarchive).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_archive).pack(side=tk.LEFT, padx=2)

        # Table
        table_container = ttk.Frame(self.window)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('Broj narudžbine', 'Datum', 'Dobavljač', 'Broj stavki', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column('Broj narudžbine', width=120)
        self.tree.column('Datum', width=100)
        self.tree.column('Dobavljač', width=250)
        self.tree.column('Broj stavki', width=100)
        self.tree.column('Napomena', width=400)

        vsb = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=hsb.set)

        self.tree.pack(fill=tk.BOTH, expand=True)

    def load_archive(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load archived orders
        all_orders = self.db.get_all_orders(include_archived=True)
        archived_orders = [order for order in all_orders if order.get('is_archived')]

        for order in archived_orders:
            # Prebroj stavke
            items = self.db.get_order_items(order['id'])
            num_items = len(items)

            self.tree.insert('', tk.END, values=(
                order['order_number'],
                order['order_date'],
                order['vendor_name'],
                num_items,
                order.get('notes', '')
            ), tags=(order['id'],))

    def unarchive(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite narudžbinu za vraćanje iz arhive.")
            return

        if messagebox.askyesno("Potvrda", "Da li želite da vratite ovu narudžbinu iz arhive?"):
            order_id = self.tree.item(selection[0])['tags'][0]
            self.db.unarchive_order(order_id)
            messagebox.showinfo("Uspeh", "Narudžbina je uspešno vraćena iz arhive.")
            self.load_archive()
            self.callback()

    def delete(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite narudžbinu za brisanje.")
            return

        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovu narudžbinu?\n\nOvo će trajno obrisati narudžbinu i sve njene stavke."):
            order_id = self.tree.item(selection[0])['tags'][0]
            self.db.delete_order(order_id)
            messagebox.showinfo("Uspeh", "Narudžbina je uspešno obrisana.")
            self.load_archive()
            self.callback()
