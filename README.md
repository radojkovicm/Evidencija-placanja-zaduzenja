# Evidencija Poslovanja

Desktop aplikacija za kompletno upravljanje poslovanjem malih i srednjih preduzeća. Razvijena u Python-u sa Tkinter GUI-jem i SQLite bazom podataka.

---

## Funkcionalnosti

### 1. Plaćanje zaduženja (Dobavljači)

Evidencija i praćenje faktura od dobavljača.

| Opcija | Opis |
|--------|------|
| Unos faktura | Datum fakture, datum valute, dobavljač, broj otpremnice, iznos, napomena |
| Delimično plaćanje | Više uplata po jednoj fakturi sa praćenjem preostalog iznosa |
| Filtriranje | Svi, Neplaćeni, Delimično plaćeni, Plaćeni, Ističu uskoro |
| Pretraga | Po broju otpremnice ili nazivu dobavljača |
| Sortiranje | Po datumu valute, datumu fakture, dobavljaču, iznosu |
| Arhiviranje | Logičko brisanje bez gubitka podataka |
| PDF izveštaj | Eksport svih faktura u PDF format |

---

### 2. Predračuni (Kupci)

Kreiranje i praćenje predračuna za kupce.

| Opcija | Opis |
|--------|------|
| Kreiranje predračuna | Automatsko numerisanje (PR-00001, PR-00002...) |
| Stavke predračuna | Dodavanje artikala sa količinom, cenom i popustom |
| Plaćanje stavki | Pojedinačno označavanje stavki kao plaćenih |
| Status praćenje | Neplaćeno, Delimično plaćeno, Plaćeno |
| Upravljanje kupcima | Šifra, ime, telefon, PIB, adresa, napomene |
| Upravljanje artiklima | Šifra, naziv, jedinica mere, cena, popust |
| PDF predračun | Generisanje PDF dokumenta za kupca |

---

### 3. Plaćanje komunalija

Evidencija računa za komunalne usluge.

| Opcija | Opis |
|--------|------|
| Tipovi komunalija | Struja, voda, grejanje, telefon, internet, itd. |
| Mesečno praćenje | Evidencija po mesecu i godini |
| Status plaćanja | Neplaćeno, Delimično, Plaćeno, Pretplata |
| Filtriranje | Po tipu, statusu, mesecu i godini |
| Upravljanje tipovima | Dodavanje custom tipova komunalija |
| PDF potvrda | Generisanje potvrde o plaćanju |

---

### 4. Kontrola prometa

Dnevna evidencija prometa sa raspodelom po načinu plaćanja.

| Opcija | Opis |
|--------|------|
| Unos prometa | Gotovina, kartica, virman, čekovi |
| Automatski zbir | Ukupan dnevni promet |
| Period filtriranje | Pregled prometa od-do datuma |
| Status praćenje | Označavanje pazara kao uplaćenog |
| PDF izveštaj | Eksport izveštaja o prometu |

---

### 5. Naručivanje robe

Kreiranje i praćenje narudžbina prema dobavljačima.

| Opcija | Opis |
|--------|------|
| Kreiranje narudžbina | Automatsko numerisanje (NAR-0001, NAR-0002...) |
| Stavke narudžbine | Artikli sa količinama |
| Pretraga | Po dobavljaču ili broju narudžbine |
| Arhiviranje | Čuvanje starih narudžbina |
| PDF narudžbenica | Generisanje dokumenta za slanje dobavljaču |

---

### 6. Upravljanje bazom podataka

| Entitet | Podaci |
|---------|--------|
| Dobavljači | Šifra, ime, mesto, PIB, matični broj, broj računa, telefon, email, kontakt osoba |
| Kupci | Šifra, ime, telefon, PIB, broj lične karte, matični broj, adresa |
| Artikli | Šifra, naziv, jedinica mere, cena, popust |

---

### 7. Email notifikacije (Gmail OAuth2)

Automatsko slanje upozorenja za fakture koje ističu.

| Opcija | Opis |
|--------|------|
| Gmail OAuth2 | Bezbedna autentifikacija bez čuvanja lozinki |
| Zakazano slanje | Podešavanje vremena slanja (npr. 09:00) |
| Period upozorenja | Broj dana pre isteka (1-30) |
| HTML email | Formatirana tabela sa fakturama koje ističu |
| Windows notifikacije | Toast notifikacije na desktopu |

**Podešavanje:**
1. Kreirajte OAuth2 credentials u [Google Cloud Console](https://console.cloud.google.com/)
2. Preuzmite `credentials.json` fajl
3. U aplikaciji odaberite putanju do credentials fajla
4. Kliknite "Autentifikuj se" - otvoriće se browser za prijavu
5. Token se automatski osvežava - prijava samo jednom

---

### 8. Podešavanja aplikacije

| Kategorija | Opcije |
|------------|--------|
| Firma | Naziv, adresa, PIB, broj računa, logo |
| Notifikacije | Email adresa, vreme slanja, broj dana upozorenja |
| Sistem | Autostart sa Windows-om, podrazumevano sortiranje |

---

### 9. Import/Export

| Format | Opis |
|--------|------|
| Excel import | Masovni unos artikala iz Excel fajla |
| PDF export | Fakture, predračuni, narudžbine, izveštaji |

---

## Instalacija

### Zahtevi

- Python 3.8+
- Windows 10/11

### Instalacija zavisnosti

```bash
pip install tkcalendar reportlab win10toast Pillow pystray
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Pokretanje

```bash
python main.py
```

---

## Struktura projekta

```
├── main.py              # Glavna aplikacija
├── database.py          # SQLite baza podataka
├── notifications.py     # Email i Windows notifikacije
├── pdf_generator.py     # Generisanje PDF dokumenata
├── excel_import.py      # Import iz Excel-a
├── gui_main.py          # Tab: Plaćanje zaduženja
├── gui_predracuni.py    # Tab: Predračuni
├── gui_komunalije.py    # Tab: Komunalije
├── gui_promet.py        # Tab: Kontrola prometa
├── gui_narucivanja.py   # Tab: Naručivanje
├── gui_vendors.py       # Prozor: Dobavljači/Kupci/Artikli
├── gui_settings.py      # Prozor: Podešavanja
├── system_tray.py       # System tray funkcionalnost
├── startup.py           # Windows autostart
└── invoices.db          # SQLite baza (kreira se automatski)
```

---

## Baza podataka

SQLite baza `invoices.db` sa tabelama:

| Tabela | Namena |
|--------|--------|
| invoices | Fakture od dobavljača |
| payments | Uplate za fakture |
| vendors | Dobavljači |
| proforma_invoices | Predračuni |
| proforma_items | Stavke predračuna |
| proforma_payments | Uplate na predračune |
| customers | Kupci |
| articles | Artikli |
| utility_bills | Komunalni računi |
| utility_types | Tipovi komunalija |
| revenue_entries | Dnevni promet |
| orders | Narudžbine |
| order_items | Stavke narudžbina |
| settings | Podešavanja aplikacije |

---

## Funkcije sistema

| Funkcija | Opis |
|----------|------|
| System Tray | Minimizacija u pozadinu sa quick access menijem |
| Autostart | Opciono pokretanje sa Windows-om |
| Arhiviranje | Logičko brisanje umesto fizičkog |
| Automatsko numerisanje | Šifre dobavljača, brojevi predračuna i narudžbina |
| Delimično plaćanje | Više uplata po dokumentu sa praćenjem ostatka |

---

## Licence

MIT License
