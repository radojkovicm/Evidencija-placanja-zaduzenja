# gui_settings.py – Podešavanja sa Gmail OAuth2 podrškom
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class SettingsWindow:
    PROVIDER_DISPLAY_TO_KEY = {
        "Gmail (OAuth2)": "gmail_oauth",
    }
    PROVIDER_KEY_TO_DISPLAY = {v: k for k, v in PROVIDER_DISPLAY_TO_KEY.items()}

    def __init__(self, parent, db):
        self.window = tk.Toplevel(parent)
        self.window.title("Podešavanja")
        self.window.geometry("600x750")
        self.window.transient(parent)
        self.window.grab_set()

        self.db = db
        self.logo_path = None
        self.gmail_token_path = ""
        self.token_path_var = tk.StringVar()
        self.credentials_path_var = tk.StringVar()

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ----------------------
        # Tab 1: Opšta podešavanja
        # ----------------------
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
        self.email_minite_label = ttk.Label(time_frame, text="(format: HH:MM)")
        self.email_minute_spinbox.set("00")
        ttk.Label(time_frame, text="(format: HH:MM)").pack(side=tk.LEFT, padx=10)
        row += 1

        ttk.Label(general_frame, text="Podrazumevano sortiranje:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.default_sort_combo = ttk.Combobox(general_frame, width=37, state="readonly")
        self.default_sort_combo["values"] = ("Datum valute", "Datum fakture", "Dobavljač", "Iznos")
        self.default_sort_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Separator(general_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=15)
        row += 1

        self.autostart_var = tk.BooleanVar()
        self.autostart_check = ttk.Checkbutton(
            general_frame,
            text="Pokreni automatski pri startovanju Windows-a",
            variable=self.autostart_var,
            command=self.toggle_autostart,
        )
        self.autostart_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1

        general_frame.columnconfigure(1, weight=1)

        # ----------------------
        # Tab 2: Email podešavanja
        # ----------------------
        email_frame = ttk.Frame(notebook, padding=20)
        notebook.add(email_frame, text="Email notifikacije")

        row = 0
        ttk.Label(email_frame, text="Email servis:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
        )
        row += 1

        ttk.Label(email_frame, text="Provider:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.email_provider_combo = ttk.Combobox(email_frame, width=37, state="readonly")
        self.email_provider_combo["values"] = list(self.PROVIDER_DISPLAY_TO_KEY.keys())
        self.email_provider_combo.current(0)
        self.email_provider_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(email_frame, text="Email adresa (From):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.gmail_user_entry = ttk.Entry(email_frame, width=40)
        self.gmail_user_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(email_frame, text="Email za notifikacije (To):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notification_email_entry = ttk.Entry(email_frame, width=40)
        self.notification_email_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        ttk.Label(email_frame, text="credentials.json putanja:").grid(row=row, column=0, sticky=tk.W, pady=5)
        creds_frame = ttk.Frame(email_frame)
        creds_frame.grid(row=row, column=1, pady=5, sticky=tk.EW)
        self.gmail_credentials_entry = ttk.Entry(creds_frame, textvariable=self.credentials_path_var, width=33)
        self.gmail_credentials_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(creds_frame, text="...", width=3, command=self.browse_credentials).pack(side=tk.LEFT, padx=4)
        row += 1

        ttk.Label(email_frame, text="Token fajl (gmail_token.json):").grid(row=row, column=0, sticky=tk.W, pady=5)
        token_frame = ttk.Frame(email_frame)
        token_frame.grid(row=row, column=1, pady=5, sticky=tk.EW)
        self.gmail_token_entry = ttk.Entry(token_frame, textvariable=self.token_path_var, width=33, state="readonly")
        self.gmail_token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(token_frame, text="Otvori folder", command=self.open_token_folder).pack(side=tk.LEFT, padx=4)
        row += 1

        self.token_status_label = ttk.Label(email_frame, text="Token status: Not authorized", foreground="red")
        self.token_status_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1

        ttk.Button(email_frame, text="Autorizuj Google nalog", command=self.authorize_google).grid(
            row=row, column=0, columnspan=2, pady=5
        )
        row += 1

        ttk.Separator(email_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=15)
        row += 1

        self.enable_email_var = tk.BooleanVar()
        self.enable_email_check = ttk.Checkbutton(
            email_frame,
            text="Omogući automatske email notifikacije",
            variable=self.enable_email_var,
        )
        self.enable_email_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)
        row += 1

        info_text = (
            "Uputstvo:\n"
            "1. Klikni na „...“ i izaberi credentials.json (preuzet iz Google Cloud konzole).\n"
            "2. Klikni na „Autorizuj Google nalog“, potvrdi login u browseru -> token fajl se kreira.\n"
            "3. Popuni email polja i klikni „Sačuvaj“ nakon što završiš.\n"
            "4. Program automatski šalje email jednom dnevno u zadato vreme ako postoje računi."
        )
        ttk.Label(email_frame, text=info_text, justify=tk.LEFT, foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5)
        )
        row += 1

        ttk.Button(email_frame, text="Testiraj Email Podešavanja", command=self.test_email).grid(
            row=row, column=0, columnspan=2, pady=10
        )
        row += 1

        email_frame.columnconfigure(1, weight=1)

        # ----------------------
        # Dugmad
        # ----------------------
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)

        ttk.Button(button_frame, text="Sačuvaj", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Otkaži", command=self.window.destroy).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Logo helperi
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Gmail OAuth helperi
    # ------------------------------------------------------------------
    def browse_credentials(self):
        filename = filedialog.askopenfilename(
            title="Izaberi credentials.json",
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            self.credentials_path_var.set(filename)
            # Reset token suggestion when credentials change
            self.gmail_token_path = ""
            self.token_path_var.set("")
            self.update_token_status_label()

    def open_token_folder(self):
        path = self.token_path_var.get()
        if path and os.path.exists(path):
            os.startfile(os.path.dirname(path))
        else:
            messagebox.showinfo("Informacija", "Token fajl ne postoji još uvek.")

    def authorize_google(self):
        from notifications import GmailOAuthHelper  # lazy import to avoid circular refs

        credentials_path = self.credentials_path_var.get().strip()
        if not credentials_path or not os.path.exists(credentials_path):
            messagebox.showerror("Greška", "Molim izaberi validan credentials.json fajl.")
            return

        try:
            GmailOAuthHelper.ensure_dependencies()
        except ImportError as exc:
            messagebox.showerror("Greška", str(exc))
            return

        token_path = self.gmail_token_path or GmailOAuthHelper.default_token_path(credentials_path)

        try:
            GmailOAuthHelper.authorize(credentials_path, token_path)
        except Exception as exc:
            messagebox.showerror("Greška", f"Autorizacija nije uspela: {exc}")
            return

        self.gmail_token_path = token_path
        self.token_path_var.set(token_path)
        self.update_token_status_label()
        messagebox.showinfo(
            "Uspeh",
            "Google nalog je uspešno autorizovan.\nNe zaboravi da klikneš „Sačuvaj“ kada završiš sa podešavanjima."
        )

    def update_token_status_label(self):
        path = self.gmail_token_path or self.token_path_var.get()
        if path and os.path.exists(path):
            text = f"Token status: OK ({os.path.basename(path)})"
            color = "green"
        else:
            text = "Token status: Not authorized"
            color = "red"
        self.token_status_label.config(text=text, foreground=color)

    # ------------------------------------------------------------------
    # Autostart helperi
    # ------------------------------------------------------------------
    def toggle_autostart(self):
        try:
            from startup import add_to_startup, remove_from_startup
        except ImportError:
            messagebox.showerror("Greška", "startup.py modul nije pronađen.")
            self.autostart_var.set(False)
            return

        try:
            if self.autostart_var.get():
                if add_to_startup():
                    messagebox.showinfo("Uspeh", "Program će se automatski pokretati pri startovanju Windows-a.")
                else:
                    self.autostart_var.set(False)
                    messagebox.showerror("Greška", "Greška pri dodavanju u startup.")
            else:
                if remove_from_startup():
                    messagebox.showinfo("Uspeh", "Program je uklonjen iz automatskog pokretanja.")
                else:
                    messagebox.showerror("Greška", "Greška pri uklanjanju iz startup-a.")
        except Exception as exc:
            self.autostart_var.set(False)
            messagebox.showerror("Greška", f"Greška: {exc}")

    # ------------------------------------------------------------------
    # Učitavanje podešavanja
    # ------------------------------------------------------------------
    def load_settings(self):
        settings = self.db.get_settings()

        self.company_name_entry.insert(0, settings.get("company_name", ""))
        self.company_address_entry.insert(0, settings.get("company_address", ""))

        logo_path = settings.get("logo_path", "")
        if logo_path and os.path.exists(logo_path):
            self.logo_path = logo_path
            self.logo_label.config(text=os.path.basename(logo_path))

        self.notification_days_spinbox.set(settings.get("notification_days", 7))

        email_time = settings.get("email_notification_time", "09:00")
        try:
            hour, minute = email_time.split(":")
            self.email_hour_spinbox.set(hour)
            self.email_minute_spinbox.set(minute)
        except Exception:
            self.email_hour_spinbox.set("09")
            self.email_minute_spinbox.set("00")

        self.default_sort_combo.set(settings.get("default_sort", "Datum valute"))

        self.gmail_user_entry.insert(0, settings.get("gmail_user", ""))
        self.notification_email_entry.insert(0, settings.get("notification_email", ""))

        provider_key = settings.get("email_provider", "gmail_oauth")
        provider_display = self.PROVIDER_KEY_TO_DISPLAY.get(provider_key, "Gmail (OAuth2)")
        self.email_provider_combo.set(provider_display)

        creds_path = settings.get("gmail_credentials_path", "")
        if creds_path:
            self.credentials_path_var.set(creds_path)

        self.gmail_token_path = settings.get("gmail_token_path", "")
        if self.gmail_token_path:
            self.token_path_var.set(self.gmail_token_path)

        self.enable_email_var.set(settings.get("enable_email_notifications", False))
        self.update_token_status_label()

        try:
            from startup import is_in_startup
            self.autostart_var.set(is_in_startup())
        except Exception:
            self.autostart_var.set(False)

    # ------------------------------------------------------------------
    # Test email
    # ------------------------------------------------------------------
    def test_email(self):
        from notifications import NotificationManager, GmailOAuthHelper  # lazy import

        provider_display = self.email_provider_combo.get()
        provider_key = self.PROVIDER_DISPLAY_TO_KEY.get(provider_display, "gmail_oauth")

        if provider_key != "gmail_oauth":
            messagebox.showwarning("Upozorenje", "Test trenutno podržava samo Gmail (OAuth2).")
            return

        credentials_path = self.credentials_path_var.get().strip()
        if not credentials_path or not os.path.exists(credentials_path):
            messagebox.showwarning("Upozorenje", "Molim izaberi validan credentials.json fajl.")
            return

        try:
            GmailOAuthHelper.ensure_dependencies()
        except ImportError as exc:
            messagebox.showerror("Greška", str(exc))
            return

        gmail_user = self.gmail_user_entry.get().strip()
        notification_email = self.notification_email_entry.get().strip()
        if not gmail_user or not notification_email:
            messagebox.showwarning("Upozorenje", "Molim popuni oba email polja (From i To).")
            return

        token_path = self.gmail_token_path or GmailOAuthHelper.default_token_path(credentials_path)
        if not GmailOAuthHelper.token_exists(token_path):
            messagebox.showwarning("Upozorenje", "Najpre autorizuj Google nalog da bi se generisao token.")
            return

        test_invoice = [{
            "invoice": {
                "vendor_name": "Test Dobavljač",
                "delivery_note_number": "TEST-001",
                "amount": 10000.00,
                "due_date": "01.01.2025"
            },
            "days_until_due": 3
        }]

        original_settings = self.db.get_settings()
        temp_settings = original_settings.copy()
        temp_settings.update({
            "gmail_user": gmail_user,
            "notification_email": notification_email,
            "email_provider": provider_key,
            "gmail_credentials_path": credentials_path,
            "gmail_token_path": token_path,
            "enable_email_notifications": True
        })

        try:
            self.db.save_settings(temp_settings)
            notification_manager = NotificationManager(self.db, start_scheduler=False)
            result = notification_manager.send_email_notification(test_invoice)
        finally:
            # Keep the new token path in original settings, then restore others
            original_settings["gmail_token_path"] = token_path
            self.db.save_settings(original_settings)

        if result:
            messagebox.showinfo("Uspeh", "Test email je uspešno poslat! Proveri inbox.")
        else:
            messagebox.showerror("Greška", "Greška pri slanju test email-a. Proveri podešavanja i log poruke u konzoli.")

    # ------------------------------------------------------------------
    # Snimanje podešavanja
    # ------------------------------------------------------------------
    def save(self):
        try:
            notification_days = int(self.notification_days_spinbox.get())
            if not (1 <= notification_days <= 30):
                raise ValueError
        except ValueError:
            messagebox.showerror("Greška", "Broj dana mora biti između 1 i 30.")
            return

        try:
            hour = int(self.email_hour_spinbox.get())
            minute = int(self.email_minute_spinbox.get())
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError
            email_time = f"{hour:02d}:{minute:02d}"
        except ValueError:
            messagebox.showerror("Greška", "Vreme mora biti u formatu HH:MM (00:00 - 23:59).")
            return

        provider_display = self.email_provider_combo.get()
        provider_key = self.PROVIDER_DISPLAY_TO_KEY.get(provider_display, "gmail_oauth")
        credentials_path = self.credentials_path_var.get().strip()

        settings_payload = {
            "company_name": self.company_name_entry.get().strip(),
            "company_address": self.company_address_entry.get().strip(),
            "logo_path": self.logo_path if self.logo_path else "",
            "notification_days": notification_days,
            "email_notification_time": email_time,
            "default_sort": self.default_sort_combo.get(),
            "enable_email_notifications": self.enable_email_var.get(),
            "email_provider": provider_key,
            "gmail_user": self.gmail_user_entry.get().strip(),
            "notification_email": self.notification_email_entry.get().strip(),
            "gmail_credentials_path": credentials_path,
            "gmail_token_path": self.gmail_token_path or self.token_path_var.get().strip(),
            "gmail_password": "",  # legacy key kept empty
        }

        self.db.save_settings(settings_payload)
        messagebox.showinfo("Uspeh", "Podešavanja su uspešno sačuvana.")
        self.window.destroy()