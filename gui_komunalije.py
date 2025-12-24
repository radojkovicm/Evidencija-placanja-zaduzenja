import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry


class KomunalijeTab:
    """Tab za plaćanje komunalija"""
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        
        self.all_bills = []
        
        self.setup_ui()
        self.load_bills()
    
    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Novi račun", command=self.add_bill).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Izmeni plaćanje", command=self.edit_payment).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_bill).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Arhiviraj", command=self.archive_bill).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Tipovi komunalija", command=self.manage_utility_types).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Osveži", command=self.load_bills).pack(side=tk.LEFT, padx=2)
        
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
        
        ttk.Label(filter_frame, text="Tip:").pack(side=tk.LEFT, padx=5)
        self.type_combo = ttk.Combobox(filter_frame, width=15, state='readonly')
        self.type_combo['values'] = ['Svi'] + [t['name'] for t in self.db.get_all_utility_types()]
        self.type_combo.set('Svi')
        self.type_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.type_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(filter_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(filter_frame, text="Mesec/Godina:").pack(side=tk.LEFT, padx=5)
        self.month_combo = ttk.Combobox(filter_frame, width=12, state='readonly')
        months = ['Sve'] + [f"{i:02d}" for i in range(1, 13)]
        self.month_combo['values'] = months
        self.month_combo.set('Sve')
        self.month_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.month_combo.pack(side=tk.LEFT, padx=5)
        
        current_year = datetime.now().year
        self.year_combo = ttk.Combobox(filter_frame, width=10, state='readonly')
        years = ['Sve'] + [str(y) for y in range(current_year - 5, current_year + 2)]
        self.year_combo['values'] = years
        self.year_combo.set('Sve')
        self.year_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.year_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Očisti", command=self.clear_filters).pack(side=tk.LEFT, padx=5)
        
        # Container za tabelu
        table_container = ttk.Frame(self.parent)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tabela
        columns = ('Datum računa', 'Datum unosa', 'Tip', 'Iznos', 'Plaćeno', 'Status', 'Datum plaćanja', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Datum računa', width=100)
        self.tree.column('Datum unosa', width=100)
        self.tree.column('Tip', width=150)
        self.tree.column('Iznos', width=100)
        self.tree.column('Plaćeno', width=100)
        self.tree.column('Status', width=100)
        self.tree.column('Datum plaćanja', width=120)
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
        
        # Double click za izmenu plaćanja
        self.tree.bind('<Double-1>', lambda e: self.edit_payment())
        
        # Status bar
        self.status_bar = ttk.Label(self.parent, text="Spremno", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_bills(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.all_bills = self.db.get_all_utility_bills(include_archived=False)
        
        # Refresh type combo
        self.type_combo['values'] = ['Svi'] + [t['name'] for t in self.db.get_all_utility_types()]
        
        self.apply_filters()
    
    def apply_filters(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        filtered = self.all_bills.copy()
        
        # Filter po statusu
        filter_value = self.filter_combo.get()
        if filter_value != 'Svi':
            filtered = [b for b in filtered if b['payment_status'] == filter_value]
        
        # Filter po tipu
        type_value = self.type_combo.get()
        if type_value != 'Svi':
            filtered = [b for b in filtered if b['utility_type_name'] == type_value]
        
        # Filter po mesecu/godini
        month_value = self.month_combo.get()
        year_value = self.year_combo.get()
        
        if month_value != 'Sve' or year_value != 'Sve':
            temp_filtered = []
            for bill in filtered:
                try:
                    bill_date = datetime.strptime(bill['bill_date'], '%d.%m.%Y')
                    match = True
                    
                    if month_value != 'Sve' and f"{bill_date.month:02d}" != month_value:
                        match = False
                    
                    if year_value != 'Sve' and str(bill_date.year) != year_value:
                        match = False
                    
                    if match:
                        temp_filtered.append(bill)
                except:
                    pass
            
            filtered = temp_filtered
        
        # Prikaži
        for bill in filtered:
            status = bill['payment_status']
            payment_date = bill['payment_date'] if bill['payment_date'] else "-"
            
            item_id = self.tree.insert('', tk.END, values=(
                bill['bill_date'],
                bill['entry_date'],
                bill['utility_type_name'],
                f"{bill['amount']:,.2f}",
                f"{bill['paid_amount']:,.2f}",
                status,
                payment_date,
                bill['notes'] or ''
            ), tags=(bill['id'],))
            
            # Oboji red
            if status == 'Plaćeno':
                self.tree.item(item_id, tags=('paid', bill['id']))
            elif status == 'Delimično':
                self.tree.item(item_id, tags=('partial', bill['id']))
        
        self.tree.tag_configure('paid', background='#90EE90')
        self.tree.tag_configure('partial', background='#FFFF99')
        
        self.status_bar.config(text=f"Ukupno računa: {len(self.tree.get_children())}")
    
    def clear_filters(self):
        self.filter_combo.set('Svi')
        self.type_combo.set('Svi')
        self.month_combo.set('Sve')
        self.year_combo.set('Sve')
        self.apply_filters()
    
    def add_bill(self):
        BillDialog(self.parent, self.db, None, self.load_bills)
    
    def edit_payment(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        bill_id = tags[-1]
        PaymentDialog(self.parent, self.db, bill_id, self.load_bills)
    
    def delete_bill(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za brisanje.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj račun?"):
            tags = self.tree.item(selection[0])['tags']
            bill_id = tags[-1]
            self.db.delete_utility_bill(bill_id)
            messagebox.showinfo("Uspeh", "Račun je uspešno obrisan.")
            self.load_bills()
    
    def archive_bill(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite račun za arhiviranje.")
            return
        
        tags = self.tree.item(selection[0])['tags']
        bill_id = tags[-1]
        bill = self.db.get_utility_bill_by_id(bill_id)
        
        if bill['payment_status'] != 'Plaćeno':
            messagebox.showwarning("Upozorenje", "Možete arhivirati samo plaćene račune.")
            return
        
        if messagebox.askyesno("Potvrda", "Da li želite da arhivirate ovaj račun?"):
            self.db.archive_utility_bill(bill_id)
            messagebox.showinfo("Uspeh", "Račun je uspešno arhiviran.")
            self.load_bills()
    
    def manage_utility_types(self):
        UtilityTypesWindow(self.parent, self.db, self.load_bills)


class BillDialog:
    def __init__(self, parent, db, bill_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi račun komunalija")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.bill_id = bill_id
        self.callback = callback
        
        self.setup_ui()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        ttk.Label(form_frame, text="Datum računa:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.bill_date_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.bill_date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Datum unosa:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.entry_date_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.entry_date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Tip komunalije:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.type_combo = ttk.Combobox(form_frame, width=37, state='readonly')
        types = self.db.get_all_utility_types()
        self.type_map = {t['name']: t['id'] for t in types}
        self.type_combo['values'] = list(self.type_map.keys())
        self.type_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
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
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def save(self):
        if not self.type_combo.get():
            messagebox.showerror("Greška", "Molim izaberite tip komunalije.")
            return
        
        try:
            amount = float(self.amount_entry.get().strip().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validan iznos.")
            return
        
        bill_date = self.bill_date_entry.get_date().strftime('%d.%m.%Y')
        entry_date = self.entry_date_entry.get_date().strftime('%d.%m.%Y')
        type_name = self.type_combo.get()
        type_id = self.type_map.get(type_name)
        notes = self.notes_text.get('1.0', tk.END).strip()
        
        try:
            self.db.add_utility_bill(
                bill_date=bill_date,
                entry_date=entry_date,
                utility_type_id=type_id,
                utility_type_name=type_name,
                amount=amount,
                paid_amount=0,
                payment_status='Neplaćeno',
                payment_date=None,
                notes=notes
            )
            messagebox.showinfo("Uspeh", "Račun je uspešno dodat.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class PaymentDialog:
    def __init__(self, parent, db, bill_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Izmeni plaćanje")
        self.window.geometry("400x300")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.bill_id = bill_id
        self.callback = callback
        
        self.bill = self.db.get_utility_bill_by_id(bill_id)
        
        self.setup_ui()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        ttk.Label(form_frame, text=f"Tip: {self.bill['utility_type_name']}", font=('Arial', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        ttk.Label(form_frame, text=f"Ukupan iznos: {self.bill['amount']:,.2f} RSD", font=('Arial', 10)).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        
        ttk.Label(form_frame, text="Plaćeni iznos (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.paid_amount_entry = ttk.Entry(form_frame, width=30)
        self.paid_amount_entry.insert(0, str(self.bill['paid_amount']))
        self.paid_amount_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(form_frame, text="Datum plaćanja:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.payment_date_entry = DateEntry(form_frame, width=27, date_pattern='dd.mm.yyyy')
        if self.bill['payment_date']:
            self.payment_date_entry.set_date(datetime.strptime(self.bill['payment_date'], '%d.%m.%Y'))
        self.payment_date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def save(self):
        try:
            paid_amount = float(self.paid_amount_entry.get().strip().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validan iznos.")
            return
        
        if paid_amount > self.bill['amount']:
            messagebox.showerror("Greška", "Plaćeni iznos ne može biti veći od ukupnog iznosa.")
            return
        
        payment_date = self.payment_date_entry.get_date().strftime('%d.%m.%Y')
        
        try:
            self.db.update_utility_bill_payment(self.bill_id, paid_amount, payment_date)
            messagebox.showinfo("Uspeh", "Plaćanje je uspešno ažurirano.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class UtilityTypesWindow:
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Tipovi komunalija")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.callback = callback
        
        self.setup_ui()
        self.load_types()
    
    def setup_ui(self):
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Dodaj tip", command=self.add_type).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_types).pack(side=tk.LEFT, padx=2)
        
        # Listbox
        self.listbox = tk.Listbox(self.window, font=('Arial', 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Zatvori", command=self.close).pack(side=tk.RIGHT, padx=5)
    
    def load_types(self):
        self.listbox.delete(0, tk.END)
        types = self.db.get_all_utility_types()
        for t in types:
            self.listbox.insert(tk.END, t['name'])
    
    def add_type(self):
        AddTypeDialog(self.window, self.db, self.load_types)
    
    def close(self):
        self.callback()
        self.window.destroy()


class AddTypeDialog:
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Dodaj tip komunalije")
        self.window.geometry("350x150")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.callback = callback
        
        self.setup_ui()
    
    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(form_frame, text="Naziv tipa:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(form_frame, width=30)
        self.name_entry.grid(row=0, column=1, pady=5, sticky=tk.EW)
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Dodaj", command=self.add).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def add(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Greška", "Molim unesite naziv tipa.")
            return
        
        try:
            self.db.add_utility_type(name)
            messagebox.showinfo("Uspeh", "Tip je uspešno dodat.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri dodavanju: {str(e)}")