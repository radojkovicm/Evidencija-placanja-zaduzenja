import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry


class PrometTab:
    """Tab za kontrolu prometa"""
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db

        self.all_entries = []

        self.setup_ui()
        self.load_entries()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Novi unos", command=self.add_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_entry).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Osveži", command=self.load_entries).pack(side=tk.LEFT, padx=2)

        # Filter
        filter_frame = ttk.Frame(self.parent)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Period:").pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Od:").pack(side=tk.LEFT, padx=5)
        self.filter_date_from = DateEntry(filter_frame, width=12, date_pattern='dd.mm.yyyy')
        self.filter_date_from.pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Do:").pack(side=tk.LEFT, padx=5)
        self.filter_date_to = DateEntry(filter_frame, width=12, date_pattern='dd.mm.yyyy')
        self.filter_date_to.pack(side=tk.LEFT, padx=5)

        ttk.Button(filter_frame, text="Filtriraj", command=self.apply_filters).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Očisti", command=self.clear_filters).pack(side=tk.LEFT, padx=5)

        # Container za tabelu
        table_container = ttk.Frame(self.parent)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tabela
        columns = ('Datum unosa', 'Period OD', 'Period DO', 'Gotovina (RSD)', 'Kartica (RSD)', 'Virman (RSD)', 'Čekovi (RSD)', 'Ukupan Iznos (RSD)', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column('Datum unosa', width=120)
        self.tree.column('Period OD', width=120)
        self.tree.column('Period DO', width=120)
        self.tree.column('Gotovina (RSD)', width=120)
        self.tree.column('Kartica (RSD)', width=120)
        self.tree.column('Virman (RSD)', width=120)
        self.tree.column('Čekovi (RSD)', width=120)
        self.tree.column('Ukupan Iznos (RSD)', width=150)
        self.tree.column('Napomena', width=400)

        # Scrollbars
        vsb = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Status bar sa ukupnim prometom
        self.status_bar = ttk.Label(self.parent, text="Spremno", relief=tk.SUNKEN, anchor=tk.W, font=('Arial', 10, 'bold'))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_entries(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.all_entries = self.db.get_all_revenue_entries()
        self.display_entries(self.all_entries)

    def display_entries(self, entries):
        for item in self.tree.get_children():
            self.tree.delete(item)

        total_revenue = 0

        for entry in entries:
            # Pretpostavljamo da baza sada vraća cash, card, wire, checks i total_amount
            # Ako baza i dalje vraća samo 'amount', moraćete da prilagodite ovaj deo
            # ili da ažurirate bazu da čuva ove nove vrednosti.
            cash = entry.get('cash', 0)
            card = entry.get('card', 0)
            wire = entry.get('wire', 0)
            checks = entry.get('checks', 0)
            total_amount = entry.get('amount', 0) # Ukupan iznos se i dalje čuva kao 'amount'

            self.tree.insert('', tk.END, values=(
                entry['entry_date'],
                entry['date_from'],
                entry['date_to'],
                f"{entry.get('cash', 0):,.2f}",
                f"{entry.get('card', 0):,.2f}",
                f"{entry.get('wire', 0):,.2f}",
                f"{entry.get('checks', 0):,.2f}",
                f"{total_amount:,.2f}",
                entry['notes'] or ''
            ), tags=(entry['id'],))

            total_revenue += entry.get('amount', 0)

        self.status_bar.config(text=f"Ukupan promet: {total_revenue:,.2f} RSD  |  Broj unosa: {len(entries)}")

    def apply_filters(self):
        date_from = self.filter_date_from.get_date()
        date_to = self.filter_date_to.get_date()

        filtered = []

        for entry in self.all_entries:
            try:
                entry_date_from = datetime.strptime(entry['date_from'], '%d.%m.%Y').date()
                entry_date_to = datetime.strptime(entry['date_to'], '%d.%m.%Y').date()

                # Proveri da li se period preklapa sa filterom
                if entry_date_from <= date_to and entry_date_to >= date_from:
                    filtered.append(entry)
            except:
                pass

        self.display_entries(filtered)

    def clear_filters(self):
        self.display_entries(self.all_entries)

    def add_entry(self):
        RevenueDialog(self.parent, self.db, self.load_entries)

    def delete_entry(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite unos za brisanje.")
            return

        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj unos?"):
            tags = self.tree.item(selection[0])['tags']
            entry_id = tags[0]
            self.db.delete_revenue_entry(entry_id)
            messagebox.showinfo("Uspeh", "Unos je uspešno obrisan.")
            self.load_entries()


class RevenueDialog:
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Novi unos prometa")
        self.window.geometry("500x550") # Povećana visina prozora
        self.window.transient(parent)
        self.window.grab_set()

        self.db = db
        self.callback = callback

        self.setup_ui()
        self.update_total_amount() # Inicijalno postavi total na 0.00

    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)

        row = 0

        ttk.Label(form_frame, text="Datum unosa:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.entry_date_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.entry_date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1

        ttk.Label(form_frame, text="Period OD:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.date_from_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.date_from_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Period DO:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.date_to_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.date_to_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1

        # Nova polja za unos iznosa
        ttk.Label(form_frame, text="Gotovina (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.cash_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.cash_entry.insert(0, "0.00")
        self.cash_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Kartica (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.card_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.card_entry.insert(0, "0.00")
        self.card_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Virman (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.wire_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.wire_entry.insert(0, "0.00")
        self.wire_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Čekovi (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.checks_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.checks_entry.insert(0, "0.00")
        self.checks_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Ukupan Iznos (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.total_amount_label = ttk.Label(form_frame, text="0.00", font=('Arial', 10, 'bold'))
        self.total_amount_label.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        self.cash_entry.bind("<KeyRelease>", self.update_total_amount)
        self.card_entry.bind("<KeyRelease>", self.update_total_amount)
        self.wire_entry.bind("<KeyRelease>", self.update_total_amount)
        self.checks_entry.bind("<KeyRelease>", self.update_total_amount)
        
        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1

        ttk.Label(form_frame, text="Napomena:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notes_text = tk.Text(form_frame, width=40, height=5)
        self.notes_text.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        form_frame.columnconfigure(1, weight=1) # Premesteno ovde

        button_frame = ttk.Frame(self.window) # Premesteno ovde
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10) # Premesteno ovde

        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)

    def update_total_amount(self, event=None):
        try:
            cash = float(self.cash_entry.get().strip().replace(',', '.'))
            card = float(self.card_entry.get().strip().replace(',', '.'))
            wire = float(self.wire_entry.get().strip().replace(',', '.'))
            checks = float(self.checks_entry.get().strip().replace(',', '.'))
            total = cash + card + wire + checks
            self.total_amount_label.config(text=f"{total:,.2f}")
        except ValueError:
            self.total_amount_label.config(text="Nevažeći unos")
        

    def save(self):
        try:
            cash = float(self.cash_entry.get().strip().replace(',', '.'))
            card = float(self.card_entry.get().strip().replace(',', '.'))
            wire = float(self.wire_entry.get().strip().replace(',', '.'))
            checks = float(self.checks_entry.get().strip().replace(',', '.'))
            total_amount = cash + card + wire + checks
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validne iznose za sve kategorije.")
            return

        entry_date = self.entry_date_entry.get_date().strftime('%d.%m.%Y')
        date_from = self.date_from_entry.get_date().strftime('%d.%m.%Y')
        date_to = self.date_to_entry.get_date().strftime('%d.%m.%Y')
        notes = self.notes_text.get('1.0', tk.END).strip()

        # Validacija da date_from nije posle date_to
        try:
            df = datetime.strptime(date_from, '%d.%m.%Y')
            dt = datetime.strptime(date_to, '%d.%m.%Y')
            if df > dt:
                messagebox.showerror("Greška", "Datum 'OD' ne može biti posle datuma 'DO'.")
                return
        except:
            pass

        try:
            # Pretpostavljamo da vaša baza podataka ima metodu za dodavanje ovih novih polja
            # Ako ne, moraćete da ažurirate vašu db klasu da podržava ove nove parametre.
            self.db.add_revenue_entry(
                entry_date=entry_date,
                date_from=date_from,
                date_to=date_to,
                cash=cash,
                card=card,
                wire=wire,
                checks=checks,
                amount=total_amount, # Ukupan iznos se i dalje čuva kao 'amount'
                notes=notes
            )
            messagebox.showinfo("Uspeh", "Unos prometa je uspešno sačuvan.")
            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")