import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd


class ExcelImporter:
    """Prozor za import artikala iz Excel fajla"""
    def __init__(self, parent, db, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("Uvezi artikle iz Excel-a")
        self.window.geometry("800x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.callback = callback
        self.df = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Instrukcije
        instructions = ttk.LabelFrame(self.window, text="Uputstvo", padding=10)
        instructions.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(instructions, text="Excel fajl mora imati sledeće kolone:").pack(anchor=tk.W)
        ttk.Label(instructions, text="• Šifra - jedinstvena šifra artikla (obavezno)").pack(anchor=tk.W, padx=20)
        ttk.Label(instructions, text="• Naziv - naziv artikla (obavezno)").pack(anchor=tk.W, padx=20)
        ttk.Label(instructions, text="• Jedinica - jedinica mere (npr. kom, kg, l)").pack(anchor=tk.W, padx=20)
        ttk.Label(instructions, text="• Cena - cena u RSD (obavezno)").pack(anchor=tk.W, padx=20)
        ttk.Label(instructions, text="• Popust - popust u procentima (opciono)").pack(anchor=tk.W, padx=20)
        ttk.Label(instructions, text="• Napomena - dodatne napomene (opciono)").pack(anchor=tk.W, padx=20)
        
        # File selection
        file_frame = ttk.Frame(self.window, padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(file_frame, text="Excel fajl:").pack(side=tk.LEFT, padx=5)
        self.file_entry = ttk.Entry(file_frame, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Izaberi fajl", command=self.select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Uvezi", command=self.import_data).pack(side=tk.LEFT, padx=5)
        
        # Preview
        preview_frame = ttk.LabelFrame(self.window, text="Pregled podataka", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('Šifra', 'Naziv', 'Jedinica', 'Cena', 'Popust', 'Napomena')
        self.tree = ttk.Treeview(preview_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('Šifra', width=100)
        self.tree.column('Naziv', width=250)
        self.tree.column('Jedinica', width=80)
        self.tree.column('Cena', width=100)
        self.tree.column('Popust', width=80)
        self.tree.column('Napomena', width=150)
        
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status
        self.status_label = ttk.Label(self.window, text="Izaberite Excel fajl...", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
    
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Izaberite Excel fajl",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.load_preview(filename)
    
    def load_preview(self, filename):
        try:
            self.df = pd.read_excel(filename)
            
            # Očisti preview
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Proveri kolone
            required_cols = ['Šifra', 'Naziv', 'Cena']
            missing_cols = [col for col in required_cols if col not in self.df.columns]
            
            if missing_cols:
                messagebox.showerror("Greška", f"Nedostaju obavezne kolone: {', '.join(missing_cols)}")
                self.status_label.config(text="Greška: Nedostaju obavezne kolone!")
                return
            
            # Prikazi podatke
            for idx, row in self.df.iterrows():
                self.tree.insert('', tk.END, values=(
                    row.get('Šifra', ''),
                    row.get('Naziv', ''),
                    row.get('Jedinica', 'kom'),
                    f"{row.get('Cena', 0):,.2f}",
                    f"{row.get('Popust', 0):.1f}",
                    row.get('Napomena', '')
                ))
            
            self.status_label.config(text=f"Učitano {len(self.df)} artikala. Klikni 'Uvezi' za import.")
        
        except Exception as e:
            messagebox.showerror("Greška", f"Greška pri čitanju fajla: {str(e)}")
            self.status_label.config(text="Greška pri učitavanju fajla!")
    
    def import_data(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("Upozorenje", "Nema podataka za import.")
            return
        
        if not messagebox.askyesno("Potvrda", f"Da li želite da uvezete {len(self.df)} artikala?"):
            return
        
        success_count = 0
        error_count = 0
        errors = []
        
        for idx, row in self.df.iterrows():
            try:
                article_code = str(row.get('Šifra', '')).strip()
                name = str(row.get('Naziv', '')).strip()
                unit = str(row.get('Jedinica', 'kom')).strip()
                
                if not article_code or not name:
                    raise ValueError("Šifra i naziv su obavezni")
                
                try:
                    price = float(str(row.get('Cena', 0)).replace(',', '.'))
                except:
                    price = 0
                
                try:
                    discount = float(str(row.get('Popust', 0)).replace(',', '.'))
                except:
                    discount = 0
                
                notes = str(row.get('Napomena', '')).strip()
                
                self.db.add_article(
                    article_code=article_code,
                    name=name,
                    unit=unit,
                    price=price,
                    discount=discount,
                    notes=notes
                )
                
                success_count += 1
            
            except Exception as e:
                error_count += 1
                errors.append(f"Red {idx + 2}: {str(e)}")
        
        # Prikazi rezultate
        result_msg = f"Uspešno uvezeno: {success_count} artikala"
        if error_count > 0:
            result_msg += f"\nGreške: {error_count}"
            if errors:
                result_msg += f"\n\nDetalji:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    result_msg += f"\n... i još {len(errors) - 10} grešaka"
        
        if success_count > 0:
            messagebox.showinfo("Rezultat importa", result_msg)
            self.callback()
            self.window.destroy()
        else:
            messagebox.showerror("Greška", result_msg)