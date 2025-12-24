#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test generisanja PDF sa debug ispis
"""
import os
import sys

os.chdir(r'C:\Users\KATA\Documents\Python\Evidencija-placanja-zaduzenja')
sys.path.insert(0, os.getcwd())

from database import Database
from pdf_generator import PDFGenerator

print("=" * 70)
print("TEST GENERISANJA PDF - TRAŽIMO STAVKE")
print("=" * 70)
print()

# Inicijalizuj bazu
db = Database()
pdf_gen = PDFGenerator(db)

# Pronađi sve predračune
proformas = db.get_all_proforma_invoices(include_archived=False)
print(f"Pronađeno predračuna: {len(proformas)}\n")

if proformas:
    for pf in proformas[:1]:  # Samo prvi
        print(f"Testiram predračun: {pf['proforma_number']} (ID: {pf['id']})\n")
        
        # Prvo proverim stavke direktno iz baze
        items = db.get_proforma_items(pf['id'])
        print(f"Stavke u bazi: {len(items)}")
        if items:
            for item in items:
                print(f"  - {item}")
        print()
        
        # Sada generiši PDF - videćemo debug ispis
        print("Generiši PDF...")
        try:
            filename = pdf_gen.generate_proforma_pdf(pf['id'])
            print(f"\n✓ PDF kreiran: {filename}\n")
        except Exception as e:
            print(f"\n✗ Greška: {e}\n")
            import traceback
            traceback.print_exc()
else:
    print("Nema predračuna u bazi")
