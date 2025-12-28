from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os


class PDFGenerator:
    def __init__(self, db):
        self.db = db
        
        # Pokušaj registraciju fontova sa Unicode podrrškom
        self.has_serbian_font = False
        self.font_name = 'Helvetica'
        self.font_name_bold = 'Helvetica-Bold'
        
        # Pokušaj registraciju Arial fontova sa Windows-a (imaju Unicode podrsku za srpske znakove)
        font_paths = [
            ('C:\\Windows\\Fonts\\arial.ttf', 'C:\\Windows\\Fonts\\arialbd.ttf'),
            ('C:\\Windows\\Fonts\\ARIAL.TTF', 'C:\\Windows\\Fonts\\ARIALBD.TTF'),
        ]
        
        for regular_path, bold_path in font_paths:
            try:
                pdfmetrics.registerFont(TTFont('CustomArial', regular_path))
                pdfmetrics.registerFont(TTFont('CustomArial-Bold', bold_path))
                self.has_serbian_font = True
                self.font_name = 'CustomArial'
                self.font_name_bold = 'CustomArial-Bold'
                break
            except Exception as e:
                continue
    
    def _get_styles(self):
        styles = getSampleStyleSheet()
        
        # Uvek koristi DejaVuSans ako je dostupan, inače Helvetica
        font = self.font_name
        font_bold = self.font_name_bold
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_bold,
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_bold,
            fontSize=14,
            spaceAfter=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=font,
            fontSize=10
        )
        
        return title_style, heading_style, normal_style
    
    def _get_font(self, bold=False):
        """Vraća odgovarajući font - DejaVuSans ako je dostupan, inače Helvetica"""
        if bold:
            return self.font_name_bold
        return self.font_name
    
    # ==================== RAČUNI DOBAVLJAČA ====================
    def generate_invoice_report(self, invoices):
        """PDF izveštaj za račune dobavljača"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'racuni_izvestaj_{timestamp}.pdf'
        
        # Landscape orijentacija zbog više kolona
        from reportlab.lib.pagesizes import landscape
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        # Naslov
        elements.append(Paragraph("Izveštaj o računima dobavljača", title_style))
        elements.append(Paragraph(f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela sa SVIM kolonama
        data = [[
            'Datum\nfakture', 
            'Datum\nvalute', 
            'Dobavljač', 
            'Br.\notpremnice', 
            'Iznos\n(RSD)', 
            'Plaćeno\n(RSD)', 
            'Preostalo\n(RSD)', 
            'Status', 
            'Posl.\nuplata'
        ]]
        
        for inv in invoices:
            # Koristi nove ključeve koje si dodao u gui_zaduzenja.py
            total_paid = inv.get('total_paid', 0)
            remaining = inv.get('remaining', 0)
            status = inv.get('payment_status', 'Neplaćeno')
            
            # Datum poslednje uplate
            last_payment = self.db.get_last_payment_date(inv['id']) if hasattr(self.db, 'get_last_payment_date') else "-"
            
            data.append([
                inv['invoice_date'],
                inv['due_date'],
                inv['vendor_name'][:20],  # Skrati ime ako je predugačko
                inv['delivery_note_number'],
                f"{inv['amount']:,.2f}",
                f"{total_paid:,.2f}",
                f"{remaining:,.2f}",
                status,
                last_payment if last_payment else "-"
            ])
        
        # Prilagođene širine kolona za landscape
        table = Table(data, colWidths=[2*cm, 2*cm, 4*cm, 2.5*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Ažurirana statistika
        total = sum(inv['amount'] for inv in invoices)
        total_paid_sum = sum(inv.get('total_paid', 0) for inv in invoices)
        remaining_sum = sum(inv.get('remaining', 0) for inv in invoices)
        
        # Brojači statusa
        status_counts = {
            'Neplaćeno': sum(1 for inv in invoices if inv.get('payment_status', 'Neplaćeno') == 'Neplaćeno'),
            'Delimično': sum(1 for inv in invoices if inv.get('payment_status', 'Neplaćeno') == 'Delimično'),
            'Plaćeno': sum(1 for inv in invoices if inv.get('payment_status', 'Neplaćeno') == 'Plaćeno')
        }
        
        stats_text = (
            f"<b>Ukupan iznos:</b> {total:,.2f} RSD | "
            f"<b>Plaćeno:</b> {total_paid_sum:,.2f} RSD | "
            f"<b>Preostalo:</b> {remaining_sum:,.2f} RSD<br/>"
            f"<b>Računi:</b> Neplaćeno: {status_counts['Neplaćeno']} | "
            f"Delimično: {status_counts['Delimično']} | "
            f"Plaćeno: {status_counts['Plaćeno']}"
        )
        elements.append(Paragraph(stats_text, normal_style))
        
        doc.build(elements)
        return filename
    
    # ==================== PREDRAČUNI ====================
    # ==================== PREDRAČUNI ====================
    def generate_proforma_pdf(self, proforma_id):
        """PDF predračun za kupca"""
        proforma = self.db.get_proforma_by_id(proforma_id)
        items = self.db.get_proforma_items(proforma_id)
        customer = self.db.get_customer_by_id(proforma['customer_id']) if proforma['customer_id'] else None
        
        # Izračunaj plaćeno i preostalo iz payments tabele
        total_paid = self.db.get_total_paid_proforma(proforma_id)
        remaining = proforma['total_amount'] - total_paid
        status = self.db.get_payment_status_proforma(proforma_id)
        last_payment_date = self.db.get_last_payment_date_proforma(proforma_id)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'predracun_{proforma["proforma_number"]}_{timestamp}.pdf'
        
        doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        # Header
        elements.append(Paragraph(f"PREDRAČUN BR. {proforma['proforma_number']}", title_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Info blokovi
        info_data = [
            ['Datum izdavanja:', proforma['invoice_date'], '', 'Status plaćanja:', status],
        ]
        
        if customer:
            info_data.append(['Kupac:', customer['name'], '', 'Telefon:', customer.get('phone', '-')])
            info_data.append(['Adresa:', customer.get('address', '-'), '', 'Br. lične karte:', customer.get('id_card_number', '-')])
        else:
            info_data.append(['Kupac:', proforma['customer_name'], '', '', ''])
        
        info_table = Table(info_data, colWidths=[3*cm, 5*cm, 1*cm, 3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('FONTNAME', (0, 0), (0, -1), self._get_font(bold=True)),
            ('FONTNAME', (3, 0), (3, -1), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.8*cm))
        
        # Stavke
        elements.append(Paragraph("STAVKE PREDRAČUNA", heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Tabela BEZ "Status" kolone, šira kolona za naziv
        item_data = [['Rb.', 'Šifra', 'Naziv artikla', 'Količina', 'JM', 'Cena', 'Popust %', 'Ukupno']]
        
        for idx, item in enumerate(items, 1):
            item_data.append([
                str(idx),
                item['article_code'],
                item['article_name'],
                f"{item['quantity']:.2f}",
                item['unit'],
                f"{item['price']:,.2f}",
                f"{item['discount']:.1f}",
                f"{item['total']:,.2f}"
            ])
        
        # Ako nema stavki, dodaj praznu stavku sa porukom
        if len(item_data) == 1:
            item_data.append(['–', '–', 'Nema stavki u predračunu', '–', '–', '–', '–', '–'])
        
        # Šire kolone: naziv dobija više prostora (6.5cm umesto 5cm)
        item_table = Table(item_data, colWidths=[1*cm, 1.5*cm, 6.5*cm, 1.5*cm, 1.2*cm, 2*cm, 1.5*cm, 2.3*cm])
        item_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Naziv na levu stranu
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Ukupno - SA NOVIM PODACIMA
        total_data = [
            ['Ukupan iznos:', f"{proforma['total_amount']:,.2f} RSD"],
            ['Plaćeno:', f"{total_paid:,.2f} RSD"],
            ['Preostalo:', f"{remaining:,.2f} RSD"]
        ]
        
        total_table = Table(total_data, colWidths=[14*cm, 4*cm])
        total_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ]))
        elements.append(total_table)
        
        # Ako postoji poslednja uplata, dodaj info
        if last_payment_date:
            elements.append(Spacer(1, 0.3*cm))
            payment_info = f"<i>Poslednja uplata: {last_payment_date}</i>"
            elements.append(Paragraph(payment_info, normal_style))
        
        elements.append(Spacer(1, 1.5*cm))
        
        # Potpisi
        sig_data = [
            ['_____________________', '', '_____________________'],
            ['Prodavac', '', 'Kupac']
        ]
        
        sig_table = Table(sig_data, colWidths=[6*cm, 4*cm, 6*cm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(sig_table)
        
        if proforma.get('notes'):
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph(f"<b>Napomena:</b> {proforma['notes']}", normal_style))
        
        doc.build(elements)
        return filename
    
    # ==================== KOMUNALIJE ====================
    def generate_utility_report(self, bills):
        """PDF izveštaj za komunalije"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'komunalije_izvestaj_{timestamp}.pdf'
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        # Naslov
        elements.append(Paragraph("Izveštaj o komunalijama", title_style))
        elements.append(Paragraph(f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela
        data = [['Datum\nračuna', 'Tip\nkomunalije', 'Iznos\n(RSD)', 'Plaćeno\n(RSD)', 'Status', 'Datum\nplaćanja']]
        
        for bill in bills:
            data.append([
                bill['bill_date'],
                bill['utility_type_name'],
                f"{bill['amount']:,.2f}",
                f"{bill['paid_amount']:,.2f}",
                bill['payment_status'],
                bill['payment_date'] if bill['payment_date'] else "-"
            ])
        
        table = Table(data, colWidths=[2.5*cm, 4*cm, 3*cm, 3*cm, 2.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Statistika
        total = sum(bill['amount'] for bill in bills)
        paid = sum(bill['paid_amount'] for bill in bills)
        unpaid = total - paid
        
        stats_text = f"<b>Ukupno:</b> {total:,.2f} RSD | <b>Plaćeno:</b> {paid:,.2f} RSD | <b>Neplaćeno:</b> {unpaid:,.2f} RSD"
        elements.append(Paragraph(stats_text, normal_style))
        
        doc.build(elements)
        return filename
    
    # ==================== PROMET ====================
    def generate_revenue_report(self, entries):
        """PDF izveštaj za kontrolu prometa"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'promet_izvestaj_{timestamp}.pdf'
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        # Naslov
        elements.append(Paragraph("Izveštaj o prometu", title_style))
        elements.append(Paragraph(f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela
        data = [['Datum\nunosa', 'Period\nOD', 'Period\nDO', 'Iznos prometa\n(RSD)', 'Napomena']]
        
        for entry in entries:
            data.append([
                entry['entry_date'],
                entry['date_from'],
                entry['date_to'],
                f"{entry['amount']:,.2f}",
                entry['notes'] if entry['notes'] else "-"
            ])
        
        table = Table(data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 3.5*cm, 6*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (3, -1), 'CENTER'),
            ('ALIGN', (4, 0), (4, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Statistika
        total_revenue = sum(entry['amount'] for entry in entries)
        avg_revenue = total_revenue / len(entries) if entries else 0
        
        stats_text = f"<b>Ukupan promet:</b> {total_revenue:,.2f} RSD | <b>Prosečan promet:</b> {avg_revenue:,.2f} RSD | <b>Broj unosa:</b> {len(entries)}"
        elements.append(Paragraph(stats_text, normal_style))
        
        doc.build(elements)
        return filename