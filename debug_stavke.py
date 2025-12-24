#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script - pronađi zašto se stavke ne vide
"""
import os
import sys

os.chdir(r'C:\Users\KATA\Documents\Python\Evidencija-placanja-zaduzenja')
sys.path.insert(0, os.getcwd())

from database import Database

print("=" * 70)
print("DEBUG - PRONALAŽENJE STAVKI PREDRAČUNA")
print("=" * 70)
print()

# Inicijalizuj bazu
db = Database()

# Pronađi sve predračune
proformas = db.get_all_proforma_invoices(include_archived=False)
print(f"Pronađeno predračuna: {len(proformas)}")
print()

if proformas:
    for pf in proformas:
        print(f"Predračun: {pf['proforma_number']} (ID: {pf['id']})")
        print(f"  Datum: {pf['invoice_date']}")
        print(f"  Kupac: {pf['customer_name']}")
        print(f"  Status: {pf['payment_status']}")
        print()
        
        # Pronađi stavke za ovaj predračun
        items = db.get_proforma_items(pf['id'])
        print(f"  Stavke: {len(items)}")
        
        if items:
            for idx, item in enumerate(items, 1):
                print(f"    {idx}. {item.get('article_name', 'N/A')} - Količina: {item.get('quantity', 0)}, Cena: {item.get('price', 0)}")
        else:
            print(f"    ⚠️  NEMA STAVKI!")
        
        print()
else:
    print("Nema predračuna u bazi")
