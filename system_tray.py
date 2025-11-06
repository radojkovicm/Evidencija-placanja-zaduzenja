# system_tray.py - NOVI FAJL
import pystray
from PIL import Image, ImageDraw
import threading

class SystemTrayApp:
    def __init__(self, root, on_show, on_exit):
        self.root = root
        self.on_show = on_show
        self.on_exit = on_exit
        self.icon = None
        
    def create_image(self):
        """Kreiraj ikonu za system tray"""
        # Kreiraj jednostavnu ikonu (plavi krug)
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        dc = ImageDraw.Draw(image)
        dc.ellipse([8, 8, 56, 56], fill='blue', outline='darkblue')
        return image
    
    def show_window(self, icon, item):
        """Prikaži glavni prozor"""
        self.root.after(0, self.on_show)
    
    def quit_app(self, icon, item):
        """Zatvori aplikaciju"""
        icon.stop()
        self.root.after(0, self.on_exit)
    
    def run(self):
        """Pokreni system tray ikonu"""
        menu = pystray.Menu(
            pystray.MenuItem('Otvori', self.show_window, default=True),
            pystray.MenuItem('Izlaz', self.quit_app)
        )
        
        self.icon = pystray.Icon(
            "Evidencija Plaćanja",
            self.create_image(),
            "Evidencija Plaćanja Zaduženja",
            menu
        )
        
        # Pokreni u posebnom thread-u
        threading.Thread(target=self.icon.run, daemon=True).start()
    
    def stop(self):
        """Zaustavi system tray ikonu"""
        if self.icon:
            self.icon.stop()