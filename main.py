import tkinter as tk
from tkinter import ttk, messagebox
import traceback
import sys
from datetime import datetime
import threading
import time

try:
    from database import Database
    from notifications import NotificationManager
    from gui_main import ZaduzenjaTab
    from gui_predracuni import PredracuniTab
    from gui_komunalije import KomunalijeTab
    from gui_promet import PrometTab
    from gui_narucivanja import NarucivanjeTab
    from system_tray import SystemTrayApp
    
    class EmailScheduler:
        """Background task za automatsko slanje email-a"""
        def __init__(self, db, notification_manager):
            self.db = db
            self.notification_manager = notification_manager
            self.running = True
            self.thread = threading.Thread(target=self.check_time, daemon=True)
            self.thread.start()
        
        def check_time(self):
            CHECK_INTERVAL = 900  # 15 minuta
            
            while self.running:
                try:
                    settings = self.db.get_settings()
                    
                    if not settings.get('enable_email_notifications', False):
                        time.sleep(CHECK_INTERVAL)
                        continue
                    
                    if not all([settings.get('gmail_user'), settings.get('gmail_password'), settings.get('notification_email')]):
                        time.sleep(CHECK_INTERVAL)
                        continue
                    
                    last_email_date = settings.get('last_email_notification_date', '')
                    today = datetime.now().strftime('%d.%m.%Y')
                    
                    if last_email_date == today:
                        now = datetime.now()
                        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                        seconds_until_tomorrow = (tomorrow - now).total_seconds()
                        wait_time = min(seconds_until_tomorrow, CHECK_INTERVAL)
                        time.sleep(wait_time)
                        continue
                    
                    email_time = settings.get('email_notification_time', '09:00')
                    target_hour, target_minute = map(int, email_time.split(':'))
                    
                    now = datetime.now()
                    current_time_minutes = now.hour * 60 + now.minute
                    target_time_minutes = target_hour * 60 + target_minute
                    
                    if current_time_minutes >= target_time_minutes:
                        due_invoices = self.notification_manager.check_due_invoices()
                        
                        if due_invoices:
                            result = self.notification_manager.send_email_notification(due_invoices)
                            if result:
                                self.db.update_setting('last_email_notification_date', today)
                        else:
                            self.db.update_setting('last_email_notification_date', today)
                    
                    time.sleep(CHECK_INTERVAL)
                    
                except Exception as e:
                    print(f"Greška u email scheduler-u: {e}")
                    time.sleep(CHECK_INTERVAL)
        
        def stop(self):
            self.running = False
    
    class MainApp:
        def __init__(self):
            self.db = None
            self.notification_manager = None
            self.email_scheduler = None
            self.root = None
            self.tray_app = None
            self.is_minimized_to_tray = False
            
            # Tab reference
            self.zaduzenja_tab = None
            self.predracuni_tab = None
            self.komunalije_tab = None
            self.promet_tab = None
            self.narucivanje_tab = None
        
        def show_window(self):
            if self.root:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.is_minimized_to_tray = False
        
        def hide_window(self):
            if self.root:
                self.root.withdraw()
                self.is_minimized_to_tray = True
        
        def on_closing(self):
            if messagebox.askyesno("Potvrda", "Da li želite da minimizirate program u pozadinu?\n\n(Program će nastaviti da radi)\n\nKlikni 'Ne' za potpuno zatvaranje."):
                self.hide_window()
            else:
                self.quit_app()
        
        def quit_app(self):
            if self.email_scheduler:
                self.email_scheduler.stop()
            if self.tray_app:
                self.tray_app.stop()
            if self.root:
                self.root.quit()
                self.root.destroy()
        
        def run(self):
            try:
                print("Pokrećem program...")
                
                # Inicijalizuj bazu
                self.db = Database()
                
                # Inicijalizuj notification manager
                self.notification_manager = NotificationManager(self.db)
                
                # Pokreni email scheduler
                self.email_scheduler = EmailScheduler(self.db, self.notification_manager)
                
                # Kreiraj glavni prozor
                self.root = tk.Tk()
                self.root.title("Evidencija Poslovanja")
                self.root.geometry("1400x750")
                
                # Kreiraj notebook (tabove)
                notebook = ttk.Notebook(self.root)
                notebook.pack(fill=tk.BOTH, expand=True)
                
                # Tab 1: Plaćanje zaduženja
                zaduzenja_frame = ttk.Frame(notebook)
                notebook.add(zaduzenja_frame, text="Plaćanje zaduženja")
                self.zaduzenja_tab = ZaduzenjaTab(zaduzenja_frame, self.db, self.notification_manager)
                
                # Tab 2: Predračun zaduženje
                predracuni_frame = ttk.Frame(notebook)
                notebook.add(predracuni_frame, text="Predračun zaduženje")
                self.predracuni_tab = PredracuniTab(predracuni_frame, self.db)
                
                # Tab 3: Plaćanje komunalija
                komunalije_frame = ttk.Frame(notebook)
                notebook.add(komunalije_frame, text="Plaćanje troškova")
                self.komunalije_tab = KomunalijeTab(komunalije_frame, self.db)
                
                # Tab 4: Kontrola prometa
                promet_frame = ttk.Frame(notebook)
                notebook.add(promet_frame, text="Kontrola prometa")
                self.promet_tab = PrometTab(promet_frame, self.db)

                # Tab 5: Naručivanje robe
                narucivanje_frame = ttk.Frame(notebook)
                notebook.add(narucivanje_frame, text="Naručivanje robe")
                self.narucivanje_tab = NarucivanjeTab(narucivanje_frame, self.db)

                # Postavi handler za zatvaranje
                self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
                
                # Pokreni system tray
                self.tray_app = SystemTrayApp(self.root, self.show_window, self.quit_app)
                self.tray_app.run()
                
                print("Program je pokrenut uspešno!")
                
                # Pokreni aplikaciju
                self.root.mainloop()
                
            except Exception as e:
                print(f"GREŠKA: {str(e)}")
                traceback.print_exc()
                messagebox.showerror("Greška", f"Greška pri pokretanju programa:\n\n{str(e)}")
                sys.exit(1)
    
    def main():
        app = MainApp()
        app.run()
    
    if __name__ == "__main__":
        main()
        
except Exception as e:
    print(f"GREŠKA PRI IMPORTU: {str(e)}")
    traceback.print_exc()
    input("Pritisnite Enter za izlaz...")