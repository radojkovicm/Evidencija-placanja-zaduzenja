import tkinter as tk
from tkinter import ttk, messagebox
from excel_import import ExcelImporter


class VendorsWindow:
    """Univerzalni prozor za Dobavljače, Kupce i Artikle"""
    def __init__(self, parent, db, mode='vendors'):
        self.window = tk.Toplevel(parent)
        self.db = db
        self.mode = mode  # 'vendors', 'customers', 'articles'
        
        # Podesi naslov i dimenzije prema modu
        if mode == 'vendors':
            self.window.title("Dobavljači")
            self.window.geometry("1000x600")
        elif mode == 'customers':
            self.window.title("Kupci")
            self.window.geometry("1000x600")
        elif mode == 'articles':
            self.window.title("Artikli")
            self.window.geometry("900x600")
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        if self.mode == 'vendors':
            ttk.Button(toolbar, text="Novi dobavljač", command=self.add_item).pack(side=tk.LEFT, padx=2)
        elif self.mode == 'customers':
            ttk.Button(toolbar, text="Novi kupac", command=self.add_item).pack(side=tk.LEFT, padx=2)
        elif self.mode == 'articles':
            ttk.Button(toolbar, text="Novi artikal", command=self.add_item).pack(side=tk.LEFT, padx=2)
            ttk.Button(toolbar, text="Uvezi iz Excel-a", command=self.import_excel).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(toolbar, text="Izmeni", command=self.edit_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_data).pack(side=tk.LEFT, padx=2)
        
        # Tabela prema modu
        if self.mode == 'vendors':
            columns = ('Šifra', 'Ime', 'Mesto', 'PIB', 'Matični broj', 'Broj računa')
            self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')
            
            for col in columns:
                self.tree.heading(col, text=col)
            
            self.tree.column('Šifra', width=80)
            self.tree.column('Ime', width=250)
            self.tree.column('Mesto', width=150)
            self.tree.column('PIB', width=120)
            self.tree.column('Matični broj', width=120)
            self.tree.column('Broj računa', width=180)
        
        elif self.mode == 'customers':
            columns = ('Šifra', 'Ime', 'Telefon', 'PIB', 'Br. lične karte', 'Matični broj', 'Adresa')
            self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')
            
            for col in columns:
                self.tree.heading(col, text=col)
            
            self.tree.column('Šifra', width=80)
            self.tree.column('Ime', width=200)
            self.tree.column('Telefon', width=120)
            self.tree.column('PIB', width=120)
            self.tree.column('Br. lične karte', width=120)
            self.tree.column('Matični broj', width=120)
            self.tree.column('Adresa', width=200)
        
        elif self.mode == 'articles':
            columns = ('Šifra', 'Naziv', 'Jedinica mere', 'Cena', 'Popust %', 'Napomena')
            self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')
            
            for col in columns:
                self.tree.heading(col, text=col)
            
            self.tree.column('Šifra', width=100)
            self.tree.column('Naziv', width=300)
            self.tree.column('Jedinica mere', width=100)
            self.tree.column('Cena', width=120)
            self.tree.column('Popust %', width=80)
            self.tree.column('Napomena', width=200)
        
        scrollbar = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        self.tree.bind('<Double-1>', lambda e: self.edit_item())
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if self.mode == 'vendors':
            items = self.db.get_all_vendors(with_details=True, include_orphan_invoice_names=False)
            for vendor in items:
                if vendor.get('vendor_id') is None:
                    continue
                self.tree.insert('', tk.END, values=(
                    vendor.get('vendor_code', ''),
                    vendor.get('vendor_name', ''),
                    vendor.get('city', ''),
                    vendor.get('pib', ''),
                    vendor.get('registration_number', ''),
                    vendor.get('bank_account', '')
                ), tags=(vendor['vendor_id'],))
        
        elif self.mode == 'customers':
            items = self.db.get_all_customers()
            for customer in items:
                self.tree.insert('', tk.END, values=(
                    customer.get('customer_code', ''),
                    customer.get('name', ''),
                    customer.get('phone', ''),
                    customer.get('pib', ''),
                    customer.get('id_card_number', ''),
                    customer.get('registration_number', ''),
                    customer.get('address', '')
                ), tags=(customer['id'],))
        
        elif self.mode == 'articles':
            items = self.db.get_all_articles()
            for article in items:
                self.tree.insert('', tk.END, values=(
                    article.get('article_code', ''),
                    article.get('name', ''),
                    article.get('unit', ''),
                    f"{article.get('price', 0):,.2f}",
                    f"{article.get('discount', 0):.1f}",
                    article.get('notes', '')
                ), tags=(article['id'],))
    
    def add_item(self):
        if self.mode == 'vendors':
            VendorDialog(self.window, self.db, None, self.load_data)
        elif self.mode == 'customers':
            CustomerDialog(self.window, self.db, None, self.load_data)
        elif self.mode == 'articles':
            ArticleDialog(self.window, self.db, None, self.load_data)
    
    def edit_item(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", f"Molim izaberite stavku za izmenu.")
            return
        
        item_id = self.tree.item(selection[0])['tags'][0]
        
        if self.mode == 'vendors':
            VendorDialog(self.window, self.db, item_id, self.load_data)
        elif self.mode == 'customers':
            CustomerDialog(self.window, self.db, item_id, self.load_data)
        elif self.mode == 'articles':
            ArticleDialog(self.window, self.db, item_id, self.load_data)
    
    def delete_item(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", f"Molim izaberite stavku za brisanje.")
            return
        
        if not messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovu stavku?"):
            return
        
        item_id = self.tree.item(selection[0])['tags'][0]
        
        try:
            if self.mode == 'vendors':
                self.db.delete_vendor_by_id(item_id)
                messagebox.showinfo("Uspeh", "Dobavljač je uspešno obrisan.")
            elif self.mode == 'customers':
                self.db.delete_customer(item_id)
                messagebox.showinfo("Uspeh", "Kupac je uspešno obrisan.")
            elif self.mode == 'articles':
                self.db.delete_article(item_id)
                messagebox.showinfo("Uspeh", "Artikal je uspešno obrisan.")
            
            self.load_data()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri brisanju: {str(e)}")
    
    def import_excel(self):
        if self.mode == 'articles':
            ExcelImporter(self.window, self.db, self.load_data)


class VendorDialog:
    def __init__(self, parent, db, vendor_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi dobavljač" if vendor_id is None else "Izmeni dobavljača")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.vendor_id = vendor_id
        self.callback = callback
        
        self.setup_ui()
        
        if vendor_id:
            self.load_vendor_data()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        ttk.Label(form_frame, text="Ime:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(form_frame, width=40)
        self.name_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Mesto:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.city_entry = ttk.Entry(form_frame, width=40)
        self.city_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Adresa:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.address_entry = ttk.Entry(form_frame, width=40)
        self.address_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="PIB:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pib_entry = ttk.Entry(form_frame, width=40)
        self.pib_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Matični broj:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.reg_entry = ttk.Entry(form_frame, width=40)
        self.reg_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Broj računa:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.bank_entry = ttk.Entry(form_frame, width=40)
        self.bank_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def load_vendor_data(self):
        vendor = self.db.get_vendor_by_id(self.vendor_id)
        if not vendor:
            return
        
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, vendor.get('name', ''))
        
        self.city_entry.delete(0, tk.END)
        self.city_entry.insert(0, vendor.get('city', ''))
        
        self.address_entry.delete(0, tk.END)
        self.address_entry.insert(0, vendor.get('address', ''))
        
        self.pib_entry.delete(0, tk.END)
        self.pib_entry.insert(0, vendor.get('pib', ''))
        
        self.reg_entry.delete(0, tk.END)
        self.reg_entry.insert(0, vendor.get('registration_number', ''))
        
        self.bank_entry.delete(0, tk.END)
        self.bank_entry.insert(0, vendor.get('bank_account', ''))
    
    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Greška", "Ime dobavljača je obavezno.")
            return
        
        city = self.city_entry.get().strip()
        address = self.address_entry.get().strip()
        pib = self.pib_entry.get().strip()
        reg_number = self.reg_entry.get().strip()
        bank_account = self.bank_entry.get().strip()
        
        try:
            if self.vendor_id:
                self.db.update_vendor(
                    self.vendor_id,
                    name=name,
                    city=city,
                    address=address,
                    pib=pib,
                    registration_number=reg_number,
                    bank_account=bank_account
                )
                messagebox.showinfo("Uspeh", "Dobavljač je uspešno izmenjen.")
            else:
                self.db.add_vendor(
                    name=name,
                    city=city,
                    address=address,
                    pib=pib,
                    registration_number=reg_number,
                    bank_account=bank_account
                )
                messagebox.showinfo("Uspeh", "Dobavljač je uspešno dodat.")
            
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class CustomerDialog:
    def __init__(self, parent, db, customer_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi kupac" if customer_id is None else "Izmeni kupca")
        self.window.geometry("500x450")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.customer_id = customer_id
        self.callback = callback
        
        self.setup_ui()
        
        if customer_id:
            self.load_customer_data()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        ttk.Label(form_frame, text="Ime:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(form_frame, width=40)
        self.name_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Telefon:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.phone_entry = ttk.Entry(form_frame, width=40)
        self.phone_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="PIB:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.pib_entry = ttk.Entry(form_frame, width=40)
        self.pib_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Broj lične karte:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.id_card_entry = ttk.Entry(form_frame, width=40)
        self.id_card_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Matični broj:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.reg_entry = ttk.Entry(form_frame, width=40)
        self.reg_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Adresa:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.address_entry = ttk.Entry(form_frame, width=40)
        self.address_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Grad:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.city_entry = ttk.Entry(form_frame, width=40)
        self.city_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notes_text = tk.Text(form_frame, width=40, height=3)
        self.notes_text.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def load_customer_data(self):
        customer = self.db.get_customer_by_id(self.customer_id)
        if not customer:
            return
        
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, customer.get('name', ''))
        
        self.phone_entry.delete(0, tk.END)
        self.phone_entry.insert(0, customer.get('phone', ''))
        
        self.pib_entry.delete(0, tk.END)
        self.pib_entry.insert(0, customer.get('pib', ''))
        
        self.id_card_entry.delete(0, tk.END)
        self.id_card_entry.insert(0, customer.get('id_card_number', ''))
        
        self.reg_entry.delete(0, tk.END)
        self.reg_entry.insert(0, customer.get('registration_number', ''))
        
        self.address_entry.delete(0, tk.END)
        self.address_entry.insert(0, customer.get('address', ''))
        
        self.city_entry.delete(0, tk.END)
        self.city_entry.insert(0, customer.get('city', ''))
        
        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', customer.get('notes', ''))
    
    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Greška", "Ime kupca je obavezno.")
            return
        
        phone = self.phone_entry.get().strip()
        pib = self.pib_entry.get().strip()
        id_card = self.id_card_entry.get().strip()
        reg_number = self.reg_entry.get().strip()
        address = self.address_entry.get().strip()
        city = self.city_entry.get().strip()
        notes = self.notes_text.get('1.0', tk.END).strip()
        
        try:
            if self.customer_id:
                self.db.update_customer(
                    self.customer_id,
                    name=name,
                    phone=phone,
                    pib=pib,
                    id_card_number=id_card,
                    registration_number=reg_number,
                    address=address,
                    city=city,
                    notes=notes
                )
                messagebox.showinfo("Uspeh", "Kupac je uspešno izmenjen.")
            else:
                self.db.add_customer(
                    name=name,
                    phone=phone,
                    pib=pib,
                    id_card_number=id_card,
                    registration_number=reg_number,
                    address=address,
                    city=city,
                    notes=notes
                )
                messagebox.showinfo("Uspeh", "Kupac je uspešno dodat.")
            
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class ArticleDialog:
    def __init__(self, parent, db, article_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi artikal" if article_id is None else "Izmeni artikal")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.article_id = article_id
        self.callback = callback
        
        self.setup_ui()
        
        if article_id:
            self.load_article_data()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        ttk.Label(form_frame, text="Šifra artikla:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.code_entry = ttk.Entry(form_frame, width=40)
        self.code_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Naziv:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(form_frame, width=40)
        self.name_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Jedinica mere:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.unit_entry = ttk.Entry(form_frame, width=40)
        self.unit_entry.insert(0, "kom")
        self.unit_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Cena (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.price_entry = ttk.Entry(form_frame, width=40)
        self.price_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Popust (%):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.discount_entry = ttk.Entry(form_frame, width=40)
        self.discount_entry.insert(0, "0")
        self.discount_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notes_text = tk.Text(form_frame, width=40, height=4)
        self.notes_text.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def load_article_data(self):
        article = self.db.get_article_by_id(self.article_id)
        if not article:
            return
        
        self.code_entry.delete(0, tk.END)
        self.code_entry.insert(0, article.get('article_code', ''))
        self.code_entry.config(state='disabled')  # Ne može se menjati šifra
        
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, article.get('name', ''))
        
        self.unit_entry.delete(0, tk.END)
        self.unit_entry.insert(0, article.get('unit', ''))
        
        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, str(article.get('price', '')))
        
        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(0, str(article.get('discount', '')))
        
        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', article.get('notes', ''))
    
    def save(self):
        code = self.code_entry.get().strip()
        name = self.name_entry.get().strip()
        unit = self.unit_entry.get().strip()
        
        if not code:
            messagebox.showerror("Greška", "Šifra artikla je obavezna.")
            return
        
        if not name:
            messagebox.showerror("Greška", "Naziv artikla je obavezan.")
            return
        
        try:
            price = float(self.price_entry.get().strip().replace(',', '.'))
            discount = float(self.discount_entry.get().strip().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validne brojeve za cenu i popust.")
            return
        
        notes = self.notes_text.get('1.0', tk.END).strip()
        
        try:
            if self.article_id:
                self.db.update_article(
                    self.article_id,
                    name=name,
                    unit=unit,
                    price=price,
                    discount=discount,
                    notes=notes
                )
                messagebox.showinfo("Uspeh", "Artikal je uspešno izmenjen.")
            else:
                self.db.add_article(
                    article_code=code,
                    name=name,
                    unit=unit,
                    price=price,
                    discount=discount,
                    notes=notes
                )
                messagebox.showinfo("Uspeh", "Artikal je uspešno dodat.")
            
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")