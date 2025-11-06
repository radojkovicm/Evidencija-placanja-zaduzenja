# main.py - KOMPLETAN NOVI FAJL
import tkinter as tk
from tkinter import messagebox
import traceback
import sys
from datetime import datetime, timedelta
import threading
import time
import os

try:
    from database import Database
    from notifications import NotificationManager
    from gui_main import MainWindow
    from system_tray import SystemTrayApp
    
    class EmailScheduler:
        """Background task za automatsko slanje email-a u određeno vreme"""
        def __init__(self, db, notification_manager):
            self.db = db
            self.notification_manager = notification_manager
            self.running = True
            self.thread = threading.Thread(target=self.check_time, daemon=True)
            self.thread.start()
        
        def check_time(self):
            """Proveri vreme svakih 15 minuta"""
            CHECK_INTERVAL = 900  # 15 minuta = 900 sekundi
            
            while self.running:
                try:
                    settings = self.db.get_settings()
                    
                    # Proveri da li su email notifikacije omogućene
                    if not settings.get('enable_email_notifications', False):
                        print("Email notifikacije su onemogućene. Čekam 15 minuta...")
                        time.sleep(CHECK_INTERVAL)
                        continue
                    
                    # Proveri da li su email podešavanja kompletna
                    if not all([settings.get('gmail_user'), settings.get('gmail_password'), settings.get('notification_email')]):
                        print("Email podešavanja nisu kompletna. Čekam 15 minuta...")
                        time.sleep(CHECK_INTERVAL)
                        continue
                    
                    # Proveri da li je već poslat danas
                    last_email_date = settings.get('last_email_notification_date', '')
                    today = datetime.now().strftime('%d.%m.%Y')
                    
                    if last_email_date == today:
                        # Već poslat danas - NE ŠALJI VIŠE, čekaj sutra
                        print(f"Email već poslat danas ({today}). Čekam sutradan...")
                        
                        # Izračunaj koliko treba čekati do ponoći
                        now = datetime.now()
                        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                        seconds_until_tomorrow = (tomorrow - now).total_seconds()
                        
                        # Čekaj do ponoći (ili maksimalno 15 minuta ako je to kraće)
                        wait_time = min(seconds_until_tomorrow, CHECK_INTERVAL)
                        time.sleep(wait_time)
                        continue
                    
                    # Uzmi podešeno vreme
                    email_time = settings.get('email_notification_time', '09:00')
                    target_hour, target_minute = map(int, email_time.split(':'))
                    
                    now = datetime.now()
                    current_hour = now.hour
                    current_minute = now.minute
                    
                    # Proveri da li je prošlo podešeno vreme
                    current_time_minutes = current_hour * 60 + current_minute
                    target_time_minutes = target_hour * 60 + target_minute
                    
                    if current_time_minutes >= target_time_minutes:
                        # Vreme je prošlo ili je tačno sada - pošalji email
                        print(f"Vreme za slanje email-a ({email_time}) je prošlo. Šaljem...")
                        
                        due_invoices = self.notification_manager.check_due_invoices()
                        
                        if due_invoices:
                            # Pošalji email
                            result = self.notification_manager.send_email_notification(due_invoices)
                            
                            if result:
                                # Sačuvaj datum slanja
                                self.db.update_setting('last_email_notification_date', today)
                                print(f"✓ Email notifikacija automatski poslata u {now.strftime('%H:%M')} (podešeno vreme: {email_time})")
                            else:
                                print(f"✗ Greška pri slanju email-a u {now.strftime('%H:%M')}")
                        else:
                            # Nema računa koji ističu, ali označi da je provera obavljena danas
                            self.db.update_setting('last_email_notification_date', today)
                            print(f"Nema računa koji ističu - email nije poslat ({now.strftime('%H:%M')})")
                    else:
                        # Vreme još nije prošlo
                        time_left = target_time_minutes - current_time_minutes
                        print(f"Čekam podešeno vreme {email_time} (još {time_left} minuta). Sledeća provera za 15 minuta.")
                    
                    # Čekaj 15 minuta pre sledeće provere
                    time.sleep(CHECK_INTERVAL)
                    
                except Exception as e:
                    print(f"Greška u email scheduler-u: {e}")
                    traceback.print_exc()
                    time.sleep(CHECK_INTERVAL)
        
        def stop(self):
            """Zaustavi background task"""
            self.running = False
    
    class App:
        def __init__(self):
            self.db = None
            self.notification_manager = None
            self.email_scheduler = None
            self.root = None
            self.main_window = None
            self.tray_app = None
            self.is_minimized_to_tray = False
        
        def show_window(self):
            """Prikaži glavni prozor"""
            if self.root:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.is_minimized_to_tray = False
        
        def hide_window(self):
            """Sakrij prozor u system tray"""
            if self.root:
                self.root.withdraw()
                self.is_minimized_to_tray = True
        
        def on_closing(self):
            """Kada korisnik zatvori prozor - minimiziraj u tray"""
            if messagebox.askyesno("Potvrda", "Da li želite da minimizirate program u pozadinu?\n\n(Program će nastaviti da radi i slati email notifikacije)\n\nKlikni 'Ne' za potpuno zatvaranje."):
                self.hide_window()
            else:
                self.quit_app()
        
        def quit_app(self):
            """Potpuno zatvori aplikaciju"""
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
                
                # Inicijalizuj bazu podataka
                print("Inicijalizujem bazu podataka...")
                self.db = Database()
                
                # Inicijalizuj notification manager
                print("Inicijalizujem notification manager...")
                self.notification_manager = NotificationManager(self.db)
                
                # Pokreni email scheduler (background task)
                print("Pokrećem email scheduler...")
                self.email_scheduler = EmailScheduler(self.db, self.notification_manager)
                
                # Kreiraj glavni prozor
                print("Kreiram glavni prozor...")
                self.root = tk.Tk()
                self.main_window = MainWindow(self.root, self.db, self.notification_manager)
                
                # Postavi handler za zatvaranje prozora
                self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
                
                # Pokreni system tray
                print("Pokrećem system tray...")
                self.tray_app = SystemTrayApp(self.root, self.show_window, self.quit_app)
                self.tray_app.run()
                
                print("Program je pokrenut uspešno!")
                print("Program će raditi u pozadini i slati email notifikacije automatski.")
                
                # Pokreni aplikaciju
                self.root.mainloop()
                
            except Exception as e:
                print(f"GREŠKA: {str(e)}")
                traceback.print_exc()
                messagebox.showerror("Greška", f"Greška pri pokretanju programa:\n\n{str(e)}")
                sys.exit(1)
    
    def main():
        app = App()
        app.run()
    
    if __name__ == "__main__":
        main()
        
except Exception as e:
    print(f"GREŠKA PRI IMPORTU: {str(e)}")
    traceback.print_exc()
    input("Pritisnite Enter za izlaz...")