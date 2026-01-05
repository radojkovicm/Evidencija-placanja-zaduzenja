import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import calendar


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
        ttk.Button(toolbar, text="Plaćanje pazara", command=self.pazar_payment).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Izmeni", command=self.edit_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Obriši", command=self.delete_entry).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="PDF Izvoz", command=self.generate_pdf).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Osveži", command=self.load_entries).pack(side=tk.LEFT, padx=2)

        # Filter
        filter_frame = ttk.Frame(self.parent)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Period:").pack(side=tk.LEFT, padx=5)
        ttk.Label(filter_frame, text="Od:").pack(side=tk.LEFT, padx=5)
        self.filter_date_from = DateEntry(filter_frame, width=12, date_pattern='dd.mm.yyyy')
        self.filter_date_from.set_date(datetime.now().replace(day=1).date())
        self.filter_date_from.pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Do:").pack(side=tk.LEFT, padx=5)
        self.filter_date_to = DateEntry(filter_frame, width=12, date_pattern='dd.mm.yyyy')
        last_day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
        self.filter_date_to.set_date(datetime.now().replace(day=last_day).date())
        self.filter_date_to.pack(side=tk.LEFT, padx=5)

        ttk.Button(filter_frame, text="Filtriraj", command=self.apply_filters).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Očisti", command=self.clear_filters).pack(side=tk.LEFT, padx=5)

        # Container za tabelu
        table_container = ttk.Frame(self.parent)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tabela
        columns = ('Datum', 'Gotovina (RSD)', 'Kartica (RSD)', 'Virman (RSD)', 'Čekovi (RSD)', 'Ukupno (RSD)', 'Status', 'Napomena')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='browse')

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column('Datum', width=100)
        self.tree.column('Gotovina (RSD)', width=120)
        self.tree.column('Kartica (RSD)', width=120)
        self.tree.column('Virman (RSD)', width=120)
        self.tree.column('Čekovi (RSD)', width=120)
        self.tree.column('Ukupno (RSD)', width=130)
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

        # Double-click za izmenu
        self.tree.bind('<Double-1>', lambda e: self.edit_entry())

        # Status bar
        self.status_bar = ttk.Label(self.parent, text="Spremno", relief=tk.SUNKEN, anchor=tk.W, font=('Arial', 9))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Statistički panel
        self.setup_statistics_panel()

    def setup_statistics_panel(self):
        """Panel za statistiku prikazanih podataka"""
        stats_frame = ttk.LabelFrame(self.parent, text="📊 STATISTIKA ZA PRIKAZANI PERIOD", padding=10)
        stats_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5, before=self.status_bar)

        self.stats_container = ttk.Frame(stats_frame)
        self.stats_container.pack(fill=tk.BOTH, expand=True)

    def update_statistics_panel(self, entries):
        """Ažuriraj statistički panel"""
        for widget in self.stats_container.winfo_children():
            widget.destroy()

        if not entries:
            ttk.Label(self.stats_container, text="Nema podataka za prikaz", 
                     font=('Arial', 10, 'italic')).pack(pady=10)
            return

        # Izračunaj totale
        total_cash = sum(e.get('cash', 0) for e in entries)
        total_card = sum(e.get('card', 0) for e in entries)
        total_wire = sum(e.get('wire', 0) for e in entries)
        total_checks = sum(e.get('checks', 0) for e in entries)
        total_amount = sum(e.get('amount', 0) for e in entries)

        # Podela po statusu
        paid_entries = [e for e in entries if e.get('payment_status') == 'Plaćeno']
        unpaid_entries = [e for e in entries if e.get('payment_status') == 'Neplaćeno']

        paid_amount = sum(e.get('amount', 0) for e in paid_entries)
        unpaid_amount = sum(e.get('amount', 0) for e in unpaid_entries)

        # Red 1: Osnovne info
        row1 = ttk.Frame(self.stats_container)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text=f"Ukupno unosa: {len(entries)}", 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        ttk.Label(row1, text="|", foreground="gray").pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text=f"Ukupan promet: {total_amount:,.2f} RSD", 
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        # Red 2: Promet po tipu
        row2 = ttk.Frame(self.stats_container)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text="Promet po:", font=('Arial', 9)).pack(side=tk.LEFT, padx=10)
        ttk.Label(row2, text=f"Gotovina: {total_cash:,.2f} RSD", 
                 font=('Arial', 9), foreground='green').pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="|", foreground="gray").pack(side=tk.LEFT, padx=2)
        ttk.Label(row2, text=f"Kartica: {total_card:,.2f} RSD", 
                 font=('Arial', 9), foreground='blue').pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="|", foreground="gray").pack(side=tk.LEFT, padx=2)
        ttk.Label(row2, text=f"Virman: {total_wire:,.2f} RSD", 
                 font=('Arial', 9), foreground='purple').pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="|", foreground="gray").pack(side=tk.LEFT, padx=2)
        ttk.Label(row2, text=f"Čekovi: {total_checks:,.2f} RSD", 
                 font=('Arial', 9), foreground='orange').pack(side=tk.LEFT, padx=5)

        # Red 3: Status plaćanja
        row3 = ttk.Frame(self.stats_container)
        row3.pack(fill=tk.X, pady=5)

        ttk.Label(row3, text="Status plaćanja:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=10)
        ttk.Label(row3, text=f"✅ Plaćeno: {paid_amount:,.2f} RSD ({len(paid_entries)} unosa)", 
                 font=('Arial', 9), foreground='green').pack(side=tk.LEFT, padx=5)
        ttk.Label(row3, text="|", foreground="gray").pack(side=tk.LEFT, padx=2)
        ttk.Label(row3, text=f"⚪ Neplaćeno: {unpaid_amount:,.2f} RSD ({len(unpaid_entries)} unosa)", 
                 font=('Arial', 9), foreground='red').pack(side=tk.LEFT, padx=5)

    def load_entries(self):
        """Učitaj sve unose i sortuj od najnovijeg"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.all_entries = self.db.get_all_revenue_entries()

        # Sortiranje po date_from (najnoviji prvi)
        self.all_entries.sort(key=lambda x: datetime.strptime(x['date_from'], '%d.%m.%Y'), reverse=True)

        self.apply_filters()

    def display_entries(self, entries):
        """Prikaži unose u tabeli"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for entry in entries:
            payment_status = entry.get('payment_status', 'Neplaćeno')

            item_id = self.tree.insert('', tk.END, values=(
                entry['date_from'],
                f"{entry.get('cash', 0):,.2f}",
                f"{entry.get('card', 0):,.2f}",
                f"{entry.get('wire', 0):,.2f}",
                f"{entry.get('checks', 0):,.2f}",
                f"{entry.get('amount', 0):,.2f}",
                payment_status,
                entry['notes'] or ''
            ), tags=(entry['id'],))

            # Oboji red prema statusu
            if payment_status == 'Plaćeno':
                self.tree.item(item_id, tags=('paid', entry['id']))

        # Konfiguracija boja
        self.tree.tag_configure('paid', background='#90EE90')

        # Ažuriraj statistiku
        self.update_statistics_panel(entries)

        # Status bar
        self.status_bar.config(text=f"Prikazano: {len(entries)} unosa")

    def apply_filters(self):
        """Primeni filtere"""
        filtered = self.all_entries.copy()

        # Filter po datumu
        date_from = self.filter_date_from.get_date()
        date_to = self.filter_date_to.get_date()

        temp_filtered = []
        for entry in filtered:
            try:
                entry_date = datetime.strptime(entry['date_from'], '%d.%m.%Y').date()

                if date_from <= entry_date <= date_to:
                    temp_filtered.append(entry)
            except:
                pass

        self.display_entries(temp_filtered)

    def clear_filters(self):
        """Očisti filtere i vrati na tekući mesec"""
        self.filter_date_from.set_date(datetime.now().replace(day=1).date())
        last_day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
        self.filter_date_to.set_date(datetime.now().replace(day=last_day).date())
        self.apply_filters()

    def add_entry(self):
        """Dodaj novi unos"""
        RevenueDialog(self.parent, self.db, None, self.load_entries)

    def edit_entry(self):
        """Izmeni postojeći unos"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite unos za izmenu.")
            return

        tags = self.tree.item(selection[0])['tags']
        entry_id = tags[-1]
        RevenueDialog(self.parent, self.db, entry_id, self.load_entries)

    def delete_entry(self):
        """Obriši unos"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Molim izaberite unos za brisanje.")
            return

        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite da obrišete ovaj unos?"):
            tags = self.tree.item(selection[0])['tags']
            entry_id = tags[-1]
            self.db.delete_revenue_entry(entry_id)
            messagebox.showinfo("Uspeh", "Unos je uspešno obrisan.")
            self.load_entries()

    def pazar_payment(self):
        """Otvori prozor za plaćanje pazara"""
        PazarPaymentDialog(self.parent, self.db, self.load_entries)

    def generate_pdf(self):
        """Generiši PDF izvoz"""
        # Uzmi prikazane unose (filtrirane)
        filtered_entries = []
        for item in self.tree.get_children():
            entry_id = self.tree.item(item)['tags'][-1]
            entry = next((e for e in self.all_entries if e['id'] == entry_id), None)
            if entry:
                filtered_entries.append(entry)

        if not filtered_entries:
            messagebox.showwarning("Upozorenje", "Nema podataka za izvoz.")
            return

        try:
            from pdf_generator import PDFGenerator
            pdf_gen = PDFGenerator(self.db)
            
            # Prosleđuj filter period
            filter_info = {
                'date_from': self.filter_date_from.get_date().strftime('%d.%m.%Y'),
                'date_to': self.filter_date_to.get_date().strftime('%d.%m.%Y')
            }
            
            filename = pdf_gen.generate_revenue_report(filtered_entries, filter_info)
            
            # Ponudi otvaranje PDF-a
            response = messagebox.askyesno(
                "Uspeh", 
                f"PDF je uspešno kreiran:\n{filename}\n\nDa li želite da otvorite PDF?"
            )
            
            if response:
                import os
                os.startfile(filename)
                
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri kreiranju PDF-a: {str(e)}")


class RevenueDialog:
    """Dialog za dodavanje/izmenu unosa prometa"""
    def __init__(self, parent, db, entry_id, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Unos prometa" if not entry_id else "Izmena unosa prometa")
        self.window.geometry("500x520")
        self.window.transient(parent)
        self.window.grab_set()

        self.db = db
        self.entry_id = entry_id
        self.callback = callback

        # Ako je izmena, učitaj postojeće podatke
        self.existing_entry = None
        if entry_id:
            self.existing_entry = self.db.get_revenue_entry_by_id(entry_id)

        self.setup_ui()

        # Ako je izmena, popuni polja
        if self.existing_entry:
            self.load_existing_data()
        else:
            self.update_total_amount()

    def setup_ui(self):
        form_frame = ttk.Frame(self.window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)

        row = 0

        ttk.Label(form_frame, text="Datum prometa:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=5)
        self.date_entry = DateEntry(form_frame, width=37, date_pattern='dd.mm.yyyy')
        self.date_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1

        # Iznosi
        ttk.Label(form_frame, text="Gotovina (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.cash_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.cash_entry.insert(0, "0.00")
        self.cash_entry.bind("<KeyRelease>", self.update_total_amount)
        self.cash_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Kartica (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.card_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.card_entry.insert(0, "0.00")
        self.card_entry.bind("<KeyRelease>", self.update_total_amount)
        self.card_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Virman (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.wire_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.wire_entry.insert(0, "0.00")
        self.wire_entry.bind("<KeyRelease>", self.update_total_amount)
        self.wire_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Čekovi (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.checks_entry = ttk.Entry(form_frame, width=40, font=('Arial', 10))
        self.checks_entry.insert(0, "0.00")
        self.checks_entry.bind("<KeyRelease>", self.update_total_amount)
        self.checks_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(form_frame, text="Ukupan Iznos (RSD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.total_amount_label = ttk.Label(form_frame, text="0.00", font=('Arial', 10, 'bold'))
        self.total_amount_label.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
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

    def update_total_amount(self, event=None):
        """Ažuriraj ukupan iznos"""
        try:
            cash = float(self.cash_entry.get().strip().replace(',', '.'))
            card = float(self.card_entry.get().strip().replace(',', '.'))
            wire = float(self.wire_entry.get().strip().replace(',', '.'))
            checks = float(self.checks_entry.get().strip().replace(',', '.'))
            total = cash + card + wire + checks
            self.total_amount_label.config(text=f"{total:,.2f}")
        except ValueError:
            self.total_amount_label.config(text="Nevažeći unos")

    def load_existing_data(self):
        """Popuni polja sa postojećim podacima"""
        entry = self.existing_entry

        self.date_entry.set_date(datetime.strptime(entry['date_from'], '%d.%m.%Y'))

        self.cash_entry.delete(0, tk.END)
        self.cash_entry.insert(0, str(entry.get('cash', 0)))

        self.card_entry.delete(0, tk.END)
        self.card_entry.insert(0, str(entry.get('card', 0)))

        self.wire_entry.delete(0, tk.END)
        self.wire_entry.insert(0, str(entry.get('wire', 0)))

        self.checks_entry.delete(0, tk.END)
        self.checks_entry.insert(0, str(entry.get('checks', 0)))

        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', entry.get('notes', ''))

        self.update_total_amount()

    def check_date_overlap(self, date_str, exclude_id=None):
        """Proveri da li postoji unos za isti datum"""
        all_entries = self.db.get_all_revenue_entries()
        
        for entry in all_entries:
            if exclude_id and entry['id'] == exclude_id:
                continue
            
            if entry['date_from'] == date_str:
                return True
        
        return False

    def save(self):
        """Sačuvaj unos"""
        try:
            cash = float(self.cash_entry.get().strip().replace(',', '.'))
            card = float(self.card_entry.get().strip().replace(',', '.'))
            wire = float(self.wire_entry.get().strip().replace(',', '.'))
            checks = float(self.checks_entry.get().strip().replace(',', '.'))
            total_amount = cash + card + wire + checks
        except ValueError:
            messagebox.showerror("Greška", "Molim unesite validne iznose za sve kategorije.")
            return

        date_str = self.date_entry.get_date().strftime('%d.%m.%Y')

        # Validacija duplikata
        if self.check_date_overlap(date_str, exclude_id=self.entry_id):
            messagebox.showerror("Greška", 
                f"Već postoji unos za datum {date_str}!\n\n"
                f"Molim izaberite drugi datum ili izmenite postojeći unos.")
            return

        notes = self.notes_text.get('1.0', tk.END).strip()

        try:
            if self.entry_id:
                # Izmena postojećeg unosa
                self.db.update_revenue_entry(
                    entry_id=self.entry_id,
                    entry_date=date_str,
                    date_from=date_str,
                    date_to=date_str,
                    cash=cash,
                    card=card,
                    wire=wire,
                    checks=checks,
                    amount=total_amount,
                    notes=notes
                )
                messagebox.showinfo("Uspeh", "Unos prometa je uspešno ažuriran.")
            else:
                # Novi unos
                self.db.add_revenue_entry(
                    entry_date=date_str,
                    date_from=date_str,
                    date_to=date_str,
                    cash=cash,
                    card=card,
                    wire=wire,
                    checks=checks,
                    amount=total_amount,
                    notes=notes
                )
                messagebox.showinfo("Uspeh", "Unos prometa je uspešno sačuvan.")

            self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čuvanju: {str(e)}")


class PazarPaymentDialog:
    """Dialog za plaćanje pazara"""
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Plaćanje pazara")
        self.window.geometry("700x700")
        self.window.transient(parent)
        self.window.grab_set()

        self.db = db
        self.callback = callback

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Period izbor
        period_frame = ttk.LabelFrame(main_frame, text="Izaberi period", padding=10)
        period_frame.pack(fill=tk.X, pady=10)

        ttk.Label(period_frame, text="Od:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.date_from_entry = DateEntry(period_frame, width=15, date_pattern='dd.mm.yyyy')
        self.date_from_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(period_frame, text="Do:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.date_to_entry = DateEntry(period_frame, width=15, date_pattern='dd.mm.yyyy')
        self.date_to_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(period_frame, text="Prikaži pregled", command=self.load_preview).grid(row=0, column=4, padx=10)

        # Pregled
        preview_frame = ttk.LabelFrame(main_frame, text="📊 PREGLED", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Scrollable lista
        list_container = ttk.Frame(preview_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.preview_text = tk.Text(list_container, width=60, height=15, 
                                     yscrollcommand=scrollbar.set, font=('Courier', 10))
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.preview_text.yview)

        # Ukupno
        self.total_label = ttk.Label(preview_frame, text="UKUPNO: 0.00 RSD", 
                                     font=('Arial', 12, 'bold'))
        self.total_label.pack(pady=10)

        # Dugmad
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)

        self.pay_button = ttk.Button(button_frame, text="Potvrdi plaćanje", 
                                     command=self.confirm_payment, state='disabled')
        self.pay_button.pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)

    def load_preview(self):
        """Učitaj pregled unosa za izabrani period"""
        date_from = self.date_from_entry.get_date()
        date_to = self.date_to_entry.get_date()

        if date_from > date_to:
            messagebox.showerror("Greška", "Datum 'Od' ne može biti posle datuma 'Do'.")
            return

        # Učitaj sve unose
        all_entries = self.db.get_all_revenue_entries()

        # Filtriraj po periodu
        self.filtered_entries = []
        for entry in all_entries:
            try:
                entry_date = datetime.strptime(entry['date_from'], '%d.%m.%Y').date()
                if date_from <= entry_date <= date_to:
                    self.filtered_entries.append(entry)
            except:
                pass

        if not self.filtered_entries:
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', "Nema unosa u izabranom periodu.")
            self.total_label.config(text="UKUPNO: 0.00 RSD")
            self.pay_button.config(state='disabled')
            return

        # Sortiraj po datumu
        self.filtered_entries.sort(key=lambda x: datetime.strptime(x['date_from'], '%d.%m.%Y'))

        # Prikaži pregled
        self.preview_text.delete('1.0', tk.END)
        total_amount = 0

        for entry in self.filtered_entries:
            payment_status = entry.get('payment_status', 'Neplaćeno')
            status_icon = "✅" if payment_status == 'Plaćeno' else "⚪"
            
            line = f"- {entry['date_from']}: {entry['amount']:>10,.2f} RSD  {status_icon} {payment_status}\n"
            self.preview_text.insert(tk.END, line)
            
            total_amount += entry['amount']

        # Separator
        self.preview_text.insert(tk.END, "\n" + "─" * 60 + "\n")

        # Ukupno
        self.total_label.config(text=f"UKUPNO: {total_amount:,.2f} RSD")

        # Omogući dugme ako ima neplaćenih unosa
        unpaid_count = sum(1 for e in self.filtered_entries if e.get('payment_status') == 'Neplaćeno')
        if unpaid_count > 0:
            self.pay_button.config(state='normal')
        else:
            self.pay_button.config(state='disabled')
            messagebox.showinfo("Informacija", "Svi unosi u ovom periodu su već plaćeni.")

    def confirm_payment(self):
        """Potvrdi plaćanje pazara"""
        unpaid_entries = [e for e in self.filtered_entries if e.get('payment_status') == 'Neplaćeno']

        if not unpaid_entries:
            messagebox.showinfo("Informacija", "Nema neplaćenih unosa u ovom periodu.")
            return

        # Potvrda
        total_unpaid = sum(e['amount'] for e in unpaid_entries)
        confirm_msg = (
            f"Da li želite da potvrdite plaćanje pazara?\n\n"
            f"Broj unosa: {len(unpaid_entries)}\n"
            f"Ukupan iznos: {total_unpaid:,.2f} RSD\n\n"
            f"Period: {self.date_from_entry.get_date().strftime('%d.%m.%Y')} - "
            f"{self.date_to_entry.get_date().strftime('%d.%m.%Y')}"
        )

        if not messagebox.askyesno("Potvrda plaćanja", confirm_msg):
            return

        # Označi sve kao plaćeno
        payment_date = datetime.now().strftime('%d.%m.%Y')
        
        try:
            for entry in unpaid_entries:
                self.db.mark_revenue_as_paid(entry['id'], payment_date)

            messagebox.showinfo("Uspeh", 
                f"Plaćanje pazara je uspešno evidentirano!\n\n"
                f"Plaćeno unosa: {len(unpaid_entries)}\n"
                f"Ukupan iznos: {total_unpaid:,.2f} RSD")

            self.callback()
            self.window.destroy()

        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri evidentiranju plaćanja: {str(e)}")