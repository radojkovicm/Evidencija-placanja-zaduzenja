# startup.py - NOVI FAJL
import os
import sys
import winshell
from win32com.client import Dispatch

def add_to_startup():
    """Dodaj program u Windows Startup folder"""
    try:
        # Putanja do startup foldera
        startup_folder = winshell.startup()
        
        # Putanja do programa (exe ili python script)
        if getattr(sys, 'frozen', False):
            # Ako je .exe
            target_path = sys.executable
        else:
            # Ako je .py script
            target_path = os.path.abspath(sys.argv[0])
        
        # Putanja do shortcut-a
        shortcut_path = os.path.join(startup_folder, "Evidencija Plaćanja.lnk")
        
        # Kreiraj shortcut
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.IconLocation = target_path
        shortcut.save()
        
        print(f"Program je dodat u Windows Startup: {shortcut_path}")
        return True
    except Exception as e:
        print(f"Greška pri dodavanju u startup: {e}")
        return False

def remove_from_startup():
    """Ukloni program iz Windows Startup folder-a"""
    try:
        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, "Evidencija Plaćanja.lnk")
        
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            print("Program je uklonjen iz Windows Startup-a.")
            return True
        else:
            print("Program nije u Windows Startup-u.")
            return False
    except Exception as e:
        print(f"Greška pri uklanjanju iz startup-a: {e}")
        return False

def is_in_startup():
    """Proveri da li je program u Windows Startup-u"""
    try:
        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, "Evidencija Plaćanja.lnk")
        return os.path.exists(shortcut_path)
    except:
        return False