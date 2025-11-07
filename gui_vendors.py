import tkinter as tk
from tkinter import ttk, messagebox


class VendorsWindow:
    def __init__(self, parent, db):
        self.window = tk.Toplevel(parent)
        self.window.title("Dobavljači")
        self.window.geometry("900x600")
        self.db = db

        self.setup_ui()
        self.load_vendors()

    def setup_ui(self):
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Novi dobavljač", command=self.add_vendor).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Izmeni", command=self.edit_vendor).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_vendor).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Osveži", command=self.load_vendors).pack(side=tk.LEFT, padx=2)

        columns = ('Šifra', 'Ime', 'Mesto', 'PIB', 'Matični broj', 'Broj računa')
        self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column('Šifra', width=80)
        self.tree.column('Ime', width=200)
        self.tree.column('Mesto', width=150)
        self.tree.column('PIB', width=120)
        self.tree.column('Matični broj', width=120)
        self.tree.column('Broj računa', width=180)

        scrollbar = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)

        self.tree.bind('<Double-1>', lambda e: self.edit_vendor())

    def load_vendors(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        vendors = self.db.get_all_vendors(with_details=True, include_orphan_invoice_names=False)
        for vendor in vendors:
            vendor_id = vendor.get('vendor_id')
            if vendor_id is None:
                continue  # skip invoice-only names

            vendor_code = vendor.get('vendor_code') or ''
            name = vendor.get('vendor_name') or ''
            address = vendor.get('address') or ''
            pib = vendor.get('pib') or ''
            reg_number = vendor.get('registration_number') or ''
            bank_account = vendor.get('bank_account') or ''

            self.tree.insert(
                '',
                tk.END,
                values=(vendor_code, name, address, pib, reg_number, bank_account),
                tags=(vendor_id,),
            )

    def add_vendor(self):
        VendorDialog(self.window, self.db, None, self.load_vendors)

    def edit_vendor(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite dobavljača za izmenu.")
            return

        vendor_id = self.tree.item(selection[0])['tags'][0]
        VendorDialog(self.window, self.db, vendor_id, self.load_vendors)

    def delete_vendor(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite dobavljača za brisanje.")
            return

        if not messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovog dobavljača?"):
            return

        vendor_tag = self.tree.item(selection[0])['tags'][0]
        try:
            vendor_id = int(vendor_tag)
        except Exception:
            vendor_id = None

        try:
            if vendor_id:
                if hasattr(self.db, 'delete_vendor_by_id'):
                    self.db.delete_vendor_by_id(vendor_id)
                else:
                    vals = self.tree.item(selection[0])['values']
                    name = vals[1] if len(vals) > 1 else ''
                    self.db.delete_vendor(name)
            else:
                vals = self.tree.item(selection[0])['values']
                name = vals[1] if len(vals) > 1 else ''
                self.db.delete_vendor(name)

            messagebox.showinfo("Uspeh", "Dobavljač je uspešno obrisan.")
            self.load_vendors()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri brisanju dobavljača: {e}")


class VendorDialog:
    def __init__(self, parent, db, vendor_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi dobavljač" if vendor_id is None else "Izmeni dobavljača")
        self.window.geometry("500x370")
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

        ttk.Label(form_frame, text="Ime:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.vendor_name_entry = ttk.Entry(form_frame, width=40)
        self.vendor_name_entry.grid(row=0, column=1, pady=5, sticky=tk.EW)

        ttk.Label(form_frame, text="Mesto:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.address_entry = ttk.Entry(form_frame, width=40)
        self.address_entry.grid(row=1, column=1, pady=5, sticky=tk.EW)

        ttk.Label(form_frame, text="PIB:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.pib_entry = ttk.Entry(form_frame, width=40)
        self.pib_entry.grid(row=2, column=1, pady=5, sticky=tk.EW)

        ttk.Label(form_frame, text="Matični broj:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.reg_entry = ttk.Entry(form_frame, width=40)
        self.reg_entry.grid(row=3, column=1, pady=5, sticky=tk.EW)

        ttk.Label(form_frame, text="Broj računa:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.bank_entry = ttk.Entry(form_frame, width=40)
        self.bank_entry.grid(row=4, column=1, pady=5, sticky=tk.EW)

        form_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)

        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)

    def load_vendor_data(self):
        try:
            vendor_id = int(self.vendor_id)
        except Exception:
            vendor_id = self.vendor_id

        vendor = None
        try:
            vendor = self.db.get_vendor_by_id(vendor_id)
        except Exception:
            vendor = None

        if not vendor:
            return

        self.vendor_name_entry.delete(0, tk.END)
        self.vendor_name_entry.insert(0, vendor.get('name') or '')

        self.address_entry.delete(0, tk.END)
        self.address_entry.insert(0, vendor.get('address') or '')

        self.pib_entry.delete(0, tk.END)
        self.pib_entry.insert(0, vendor.get('pib') or '')

        self.reg_entry.delete(0, tk.END)
        self.reg_entry.insert(0, vendor.get('registration_number') or '')

        self.bank_entry.delete(0, tk.END)
        self.bank_entry.insert(0, vendor.get('bank_account') or '')

    def save(self):
        vendor_name = self.vendor_name_entry.get().strip()
        if not vendor_name:
            messagebox.showerror("Greška", "Ime dobavljača je obavezno.")
            return

        address = self.address_entry.get().strip()
        pib = self.pib_entry.get().strip()
        reg_number = self.reg_entry.get().strip()
        bank_account = self.bank_entry.get().strip()

        try:
            if self.vendor_id:
                try:
                    vendor_id = int(self.vendor_id)
                except Exception:
                    vendor_id = self.vendor_id

                self.db.update_vendor(
                    vendor_id,
                    name=vendor_name,
                    address=address,
                    pib=pib,
                    registration_number=reg_number,
                    bank_account=bank_account,
                )
                messagebox.showinfo("Uspeh", "Dobavljač je uspešno izmenjen.")
            else:
                self.db.add_vendor(
                    name=vendor_name,
                    address=address,
                    pib=pib,
                    registration_number=reg_number,
                    bank_account=bank_account,
                )
                messagebox.showinfo("Uspeh", "Dobavljač je uspešno dodat.")

            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {e}")