# gui_settings.py - KOMPLETAN NOVI FAJL
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

class SettingsWindow:
    def __init__(self, parent, db):
        self.window = tk.Toplevel(parent)
        self.window.title("Podešavanja")
        self.window.geometry("600x700")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.db = db
        self.logo_path = None
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        # Notebook za tabove
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Opšta podešavanja
        general_frame = ttk.Frame(notebook, padding=20)
        notebook.add(general_frame, text="Opšte")
        
        row = 0
        
        ttk.Label(general_frame, text="Naziv firme:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.company_name_entry = ttk.Entry(general_frame, width=40)
        self.company_name_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(general_frame, text="Adresa firme:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.company_address_entry = ttk.Entry(general_frame, width=40)
        self.company_address_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(general_frame, text="Logo firme:").grid(row=row, column=0, sticky=tk.W, pady=5)
        logo_frame = ttk.Frame(general_frame)
        logo_frame.grid(row=row, column=1, pady=5, sticky=tk.EW)
        
        self.logo_label = ttk.Label(logo_frame, text="Nije izabran")
        self.logo_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(logo_frame, text="Izaberi", command=self.select_logo).pack(side=tk.RIGHT, padx=5)
        ttk.Button(logo_frame, text="Ukloni", command=self.remove_logo).pack(side=tk.RIGHT)
        row += 1
        
        ttk.Separator(general_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=15)
        row += 1
        
        ttk.Label(general_frame, text="Broj dana za upozorenje:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notification_days_spinbox = ttk.Spinbox(general_frame, from_=1, to=30, width=38)
        self.notification_days_spinbox.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(general_frame, text="Vreme slanja email-a:").grid(row=row, column=0, sticky=tk.W, pady=5)
        time_frame = ttk.Frame(general_frame)
        time_frame.grid(row=row, column=1, pady=5, sticky=tk.EW)
        
        self.email_hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, width=5, format="%02.0f")
        self.email_hour_spinbox.pack(side=tk.LEFT)
        self.email_hour_spinbox.set("09")
        
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT, padx=2)
        
        self.email_minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, width=5, format="%02.0f")
        self.email_minute_spinbox.pack(side=tk.LEFT)
        self.email_minute_spinbox.set("00")
        
        ttk.Label(time_frame, text="(format: HH:MM)").pack(side=tk.LEFT, padx=10)
        row += 1
        
        ttk.Label(general_frame, text="Podrazumevano sortiranje:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.default_sort_combo = ttk.Combobox(general_frame, width=37, state='readonly')
        self.default_sort_combo['values'] = ('Datum valute', 'Datum fakture', 'Dobavljač', 'Iznos')
        self.default_sort_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        general_frame.columnconfigure(1, weight=1)
        
        # Tab 2: Email podešavanja
        email_frame = ttk.Frame(notebook, padding=20)
        notebook.add(email_frame, text="Email notifikacije")
        
        row = 0
        
        ttk.Label(email_frame, text="Email servis:", font=('Arial', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1
        
        ttk.Label(email_frame, text="Email adresa (Gmail/Outlook):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.gmail_user_entry = ttk.Entry(email_frame, width=40)
        self.gmail_user_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(email_frame, text="Lozinka:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.gmail_password_entry = ttk.Entry(email_frame, width=40, show="*")
        self.gmail_password_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Label(email_frame, text="Email za notifikacije:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notification_email_entry = ttk.Entry(email_frame, width=40)
        self.notification_email_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1
        
        ttk.Separator(email_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=15)
        row += 1
        
        # Checkbox za omogućavanje email notifikacija
        self.enable_email_var = tk.BooleanVar()
        self.enable_email_check = ttk.Checkbutton(email_frame, text="Omogući automatske email notifikacije", variable=self.enable_email_var)
        self.enable_email_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1
        
        # Info tekst
        info_text = """
Uputstvo za podešavanje:

Gmail:
1. Koristi App Password (preporučeno)
2. Ili isključi 2-Step Verification

Outlook/Hotmail:
1. Koristi običnu lozinku
2. Jednostavnije za podešavanje

Email se šalje automatski jednom dnevno u podešeno vreme
ako postoje računi koji ističu uskoro.
        """
        
        info_label = ttk.Label(email_frame, text=info_text, justify=tk.LEFT, foreground="gray")
        info_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1
        
        # Test email dugme
        ttk.Button(email_frame, text="Testiraj Email Podešavanja", command=self.test_email).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1
        
        email_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)
        
        # gui_settings.py - DODAJ U setup_ui metodu (u general_frame, posle email_time)

        ttk.Separator(general_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=15)
        row += 1
        
        # Automatski start
        self.autostart_var = tk.BooleanVar()
        self.autostart_check = ttk.Checkbutton(general_frame, text="Pokreni automatski pri startovanju Windows-a", variable=self.autostart_var, command=self.toggle_autostart)
        self.autostart_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1
    
    def select_logo(self):
        filename = filedialog.askopenfilename(
            title="Izaberi logo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if filename:
            self.logo_path = filename
            self.logo_label.config(text=os.path.basename(filename))
    
    def remove_logo(self):
        self.logo_path = ""
        self.logo_label.config(text="Nije izabran")
    
    # gui_settings.py - DODAJ OVE METODE u SettingsWindow klasu

    def toggle_autostart(self):
        """Omogući/onemogući automatski start"""
        try:
            from startup import add_to_startup, remove_from_startup
            
            if self.autostart_var.get():
                # Dodaj u startup
                if add_to_startup():
                    messagebox.showinfo("Uspeh", "Program će se automatski pokretati pri startovanju Windows-a.")
                else:
                    self.autostart_var.set(False)
                    messagebox.showerror("Greška", "Greška pri dodavanju u startup.")
            else:
                # Ukloni iz startup-a
                if remove_from_startup():
                    messagebox.showinfo("Uspeh", "Program je uklonjen iz automatskog pokretanja.")
                else:
                    messagebox.showerror("Greška", "Greška pri uklanjanju iz startup-a.")
        except Exception as e:
            messagebox.showerror("Greška", f"Greška: {e}")
            self.autostart_var.set(False)
    
    def load_settings(self):
        settings = self.db.get_settings()
        
        self.company_name_entry.insert(0, settings.get('company_name', ''))
        self.company_address_entry.insert(0, settings.get('company_address', ''))
        
        logo_path = settings.get('logo_path', '')
        if logo_path and os.path.exists(logo_path):
            self.logo_path = logo_path
            self.logo_label.config(text=os.path.basename(logo_path))
        
        self.notification_days_spinbox.set(settings.get('notification_days', 7))
        
        # Učitaj vreme slanja
        email_time = settings.get('email_notification_time', '09:00')
        try:
            hour, minute = email_time.split(':')
            self.email_hour_spinbox.set(hour)
            self.email_minute_spinbox.set(minute)
        except:
            self.email_hour_spinbox.set("09")
            self.email_minute_spinbox.set("00")
        
        self.default_sort_combo.set(settings.get('default_sort', 'Datum valute'))
        
        self.gmail_user_entry.insert(0, settings.get('gmail_user', ''))
        self.gmail_password_entry.insert(0, settings.get('gmail_password', ''))
        self.notification_email_entry.insert(0, settings.get('notification_email', ''))
        
        self.enable_email_var.set(settings.get('enable_email_notifications', False))
        
        # gui_settings.py - DODAJ U load_settings metodu

        # Proveri da li je u startup-u
        try:
            from startup import is_in_startup
            self.autostart_var.set(is_in_startup())
        except:
            self.autostart_var.set(False)
    
    def test_email(self):
        """Testiraj email podešavanja"""
        from notifications import NotificationManager
        
        # Privremeno sačuvaj podešavanja
        temp_settings = {
            'gmail_user': self.gmail_user_entry.get().strip(),
            'gmail_password': self.gmail_password_entry.get().strip(),
            'notification_email': self.notification_email_entry.get().strip()
        }
        
        if not all(temp_settings.values()):
            messagebox.showwarning("Upozorenje", "Molim popuni sva email polja.")
            return
        
        # Kreiraj test email
        notification_manager = NotificationManager(self.db)
        
        test_invoice = [{
            'invoice': {
                'vendor_name': 'Test Dobavljač',
                'delivery_note_number': 'TEST-001',
                'amount': 10000.00,
                'due_date': '01.01.2025'
            },
            'days_until_due': 3
        }]
        
        # Privremeno postavi podešavanja
        original_settings = self.db.get_settings()
        self.db.save_settings(temp_settings)
        
        result = notification_manager.send_email_notification(test_invoice)
        
        # Vrati originalna podešavanja
        self.db.save_settings(original_settings)
        
        if result:
            messagebox.showinfo("Uspeh", "Test email je uspešno poslat! Proveri inbox.")
        else:
            messagebox.showerror("Greška", "Greška pri slanju test email-a. Proveri podešavanja.")
    
    def save(self):
        # Validacija
        try:
            notification_days = int(self.notification_days_spinbox.get())
            if notification_days < 1 or notification_days > 30:
                raise ValueError
        except ValueError:
            messagebox.showerror("Greška", "Broj dana mora biti između 1 i 30.")
            return
        
        # Validacija vremena
        try:
            hour = int(self.email_hour_spinbox.get())
            minute = int(self.email_minute_spinbox.get())
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError
            email_time = f"{hour:02d}:{minute:02d}"
        except ValueError:
            messagebox.showerror("Greška", "Vreme mora biti u formatu HH:MM (00:00 - 23:59).")
            return
        
        settings = {
            'company_name': self.company_name_entry.get().strip(),
            'company_address': self.company_address_entry.get().strip(),
            'logo_path': self.logo_path if self.logo_path else '',
            'notification_days': notification_days,
            'email_notification_time': email_time,
            'default_sort': self.default_sort_combo.get(),
            'gmail_user': self.gmail_user_entry.get().strip(),
            'gmail_password': self.gmail_password_entry.get().strip(),
            'notification_email': self.notification_email_entry.get().strip(),
            'enable_email_notifications': self.enable_email_var.get()
        }
        
        self.db.save_settings(settings)
        messagebox.showinfo("Uspeh", "Podešavanja su uspešno sačuvana.")
        self.window.destroy()