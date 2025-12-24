#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kompletan test - proverite šta se dešava sa stavkama
"""
import os
import sys

os.chdir(r'C:\Users\KATA\Documents\Python\Evidencija-placanja-zaduzenja')
sys.path.insert(0, os.getcwd())

from database import Database
from pdf_generator import PDFGenerator

print("=" * 80)
print("KOMPLETAN TEST - PRONALAŽENJE PROBLEMA SA STAVKAMA")
print("=" * 80)
print()

# Inicijalizuj bazu i PDF generator
db = Database()
pdf_gen = PDFGenerator(db)

print(f"Font korišćen: {pdf_gen.font_name}")
print(f"Arial font registrovan: {pdf_gen.has_serbian_font}")
print()

# Pronađi sve predračune
proformas = db.get_all_proforma_invoices(include_archived=False)
print(f"Pronađeno predračuna: {len(proformas)}")
print()

if not proformas:
    print("❌ NEMA PREDRAČUNA U BAZI!")
    sys.exit(1)

# Testiraj prvi predračun
pf = proformas[0]
pf_id = pf['id']
pf_number = pf['proforma_number']

print(f"Testiram predračun: {pf_number} (ID: {pf_id})")
print(f"  Kupac: {pf['customer_name']}")
print()

# 1. Pronađi stavke direktno iz baze
print("KORAK 1: Pronalaženje stavki u bazi...")
items_from_db = db.get_proforma_items(pf_id)
print(f"  Pronađeno stavki: {len(items_from_db)}")

if items_from_db:
    for idx, item in enumerate(items_from_db[:3], 1):
        print(f"    {idx}. {item['article_name']} - Kol: {item['quantity']}, Cena: {item['price']}")
    if len(items_from_db) > 3:
        print(f"    ... i još {len(items_from_db) - 3} stavke")
else:
    print("  ❌ NEMA STAVKI U BAZI!")
    print()
    print("  ZAKLJUČAK: Problem je u bazi - stavke nisu sačuvane!")
    sys.exit(1)

print()

# 2. Generiši PDF i vidi debug ispis
print("KORAK 2: Generisanje PDF-a sa debug ispis...")
print()
print("-" * 80)

try:
    filename = pdf_gen.generate_proforma_pdf(pf_id)
    print("-" * 80)
    print()
    print(f"✓ PDF je uspešno generiisan: {filename}")
    print()
    print("=" * 80)
    print("ZAKLJUČAK: Ako vidite stavke u PDF-u, problem je REŠEN!")
    print("=" * 80)
except Exception as e:
    print("-" * 80)
    print()
    print(f"❌ GREŠKA pri generisanju PDF-a: {e}")
    print()
    import traceback
    traceback.print_exc()
