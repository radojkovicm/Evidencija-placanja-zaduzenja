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
        
        self.has_serbian_font = False
        self.font_name = 'Helvetica'
        self.font_name_bold = 'Helvetica-Bold'
        
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
        if bold:
            return self.font_name_bold
        return self.font_name
    
    def _wrap_text(self, text, font_size=8, align=TA_CENTER, max_width=None):
        if not text or text == "-":
            return text
        
        text_str = str(text)
        
        if max_width and len(text_str) <= max_width:
            return text_str
        
        style = ParagraphStyle(
            'cell_wrap',
            fontName=self._get_font(),
            fontSize=font_size,
            leading=font_size + 1,
            alignment=align
        )
        return Paragraph(text_str, style)
    
    def _format_month_year(self, date_str):
        months_sr = [
            "Januar", "Februar", "Mart", "April", "Maj", "Jun",
            "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"
        ]
        try:
            date_obj = datetime.strptime(date_str, '%d.%m.%Y')
            return f"{months_sr[date_obj.month - 1]} {date_obj.year}"
        except:
            return date_str
    
    def generate_invoice_report(self, invoices):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'racuni_izvestaj_{timestamp}.pdf'
        
        from reportlab.lib.pagesizes import landscape
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        elements.append(Paragraph("Izveštaj o računima dobavljača", title_style))
        elements.append(Paragraph(f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.5*cm))
        
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
            total_paid = inv.get('total_paid', 0)
            remaining = inv.get('remaining', 0)
            status = inv.get('payment_status', 'Neplaćeno')
            
            last_payment = self.db.get_last_payment_date(inv['id']) if hasattr(self.db, 'get_last_payment_date') else "-"
            
            vendor_paragraph = Paragraph(inv['vendor_name'], ParagraphStyle(
                'cell',
                fontName=self._get_font(),
                fontSize=8,
                leading=9,
                alignment=TA_LEFT
            ))
            
            delivery_note_paragraph = Paragraph(inv['delivery_note_number'], ParagraphStyle(
                'cell',
                fontName=self._get_font(),
                fontSize=7,
                leading=8,
                alignment=TA_CENTER
            ))
            
            data.append([
                inv['invoice_date'],
                inv['due_date'],
                vendor_paragraph,
                delivery_note_paragraph,
                f"{inv['amount']:,.2f}",
                f"{total_paid:,.2f}",
                f"{remaining:,.2f}",
                status,
                last_payment if last_payment else "-"
            ])
        
        table = Table(data, colWidths=[2*cm, 2*cm, 4*cm, 2.5*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        total = sum(inv['amount'] for inv in invoices)
        total_paid_sum = sum(inv.get('total_paid', 0) for inv in invoices)
        remaining_sum = sum(inv.get('remaining', 0) for inv in invoices)
        
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
    
    def generate_proforma_pdf(self, proforma_id):
        proforma = self.db.get_proforma_by_id(proforma_id)
        items = self.db.get_proforma_items(proforma_id)
        customer = self.db.get_customer_by_id(proforma['customer_id']) if proforma['customer_id'] else None
        
        total_paid = self.db.get_total_paid_proforma(proforma_id)
        remaining = proforma['total_amount'] - total_paid
        status = self.db.get_payment_status_proforma(proforma_id)
        last_payment_date = self.db.get_last_payment_date_proforma(proforma_id)
        
        settings = self.db.get_settings()
        company_name = settings.get('company_name', '')
        company_address = settings.get('company_address', '')
        company_pib = settings.get('company_pib', '')
        company_bank_account = settings.get('company_bank_account', '')
        logo_path = settings.get('logo_path', '')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'predracun_{proforma["proforma_number"]}_{timestamp}.pdf'
        
        doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        if company_name or company_address:
            logo_image = None
            if logo_path and os.path.exists(logo_path):
                try:
                    from reportlab.platypus import Image
                    logo_image = Image(logo_path, width=2*cm, height=2*cm)
                except Exception as e:
                    print(f"Greška pri učitavanju loga: {e}")
                    logo_image = None
            
            company_info_lines = []
            if company_name:
                company_info_lines.append(Paragraph(f"<b>{company_name}</b>", 
                    ParagraphStyle('company', fontName=self._get_font(bold=True), fontSize=12, leading=14)))
            if company_address:
                company_info_lines.append(Paragraph(company_address, 
                    ParagraphStyle('address', fontName=self._get_font(), fontSize=9, leading=11)))
            if company_pib:
                company_info_lines.append(Paragraph(f"PIB: {company_pib}", 
                    ParagraphStyle('pib', fontName=self._get_font(), fontSize=9, leading=11)))
            if company_bank_account:
                company_info_lines.append(Paragraph(f"Broj računa: {company_bank_account}", 
                    ParagraphStyle('bank', fontName=self._get_font(), fontSize=9, leading=11)))
            
            if logo_image:
                header_table = Table([[company_info_lines, logo_image]], colWidths=[14*cm, 3*cm])
            else:
                header_table = Table([[company_info_lines, '']], colWidths=[14*cm, 3*cm])
            
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            
            elements.append(header_table)
            elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph(f"PREDRAČUN BR. {proforma['proforma_number']}", title_style))
        elements.append(Spacer(1, 0.3*cm))
        
        info_data = [
            ['Datum izdavanja:', proforma['invoice_date'], '', 'Status plaćanja:', status],
        ]
        
        if customer:
            info_data.append([
                'Kupac:', 
                self._wrap_text(customer['name'], font_size=9, align=TA_LEFT),
                '', 
                'Telefon:', 
                customer.get('phone', '-')
            ])
            info_data.append([
                'Adresa:', 
                self._wrap_text(customer.get('address', '-'), font_size=9, align=TA_LEFT),
                '', 
                'Br. lične karte:', 
                customer.get('id_card_number', '-')
            ])
        else:
            info_data.append([
                'Kupac:', 
                self._wrap_text(proforma['customer_name'], font_size=9, align=TA_LEFT),
                '', 
                '', 
                ''
            ])
        
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
        
        elements.append(Paragraph("STAVKE PREDRAČUNA", heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        item_data = [['Rb.', 'Šifra', 'Naziv artikla', 'Količina', 'JM', 'Cena', 'Popust %', 'Ukupno']]
        
        for idx, item in enumerate(items, 1):
            item_data.append([
                str(idx),
                self._wrap_text(item['article_code'], font_size=7, align=TA_CENTER),
                self._wrap_text(item['article_name'], font_size=8, align=TA_LEFT),
                f"{item['quantity']:.2f}",
                item['unit'],
                f"{item['price']:,.2f}",
                f"{item['discount']:.1f}",
                f"{item['total']:,.2f}"
            ])
        
        if len(item_data) == 1:
            item_data.append(['–', '–', 'Nema stavki u predračunu', '–', '–', '–', '–', '–'])
        
        item_table = Table(item_data, colWidths=[1*cm, 1.5*cm, 6.5*cm, 1.5*cm, 1.2*cm, 2*cm, 1.5*cm, 2.3*cm])
        item_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 0.5*cm))
        
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
        
        if last_payment_date:
            elements.append(Spacer(1, 0.3*cm))
            payment_info = f"<i>Poslednja uplata: {last_payment_date}</i>"
            elements.append(Paragraph(payment_info, normal_style))
        
        elements.append(Spacer(1, 1.5*cm))
        
        sig_data = [
            ['_____________________', '', '_____________________'],
            ['Potpis prodavca', '', 'Potpis kupca']
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
            elements.append(Paragraph("<b>Napomena:</b>", normal_style))
            elements.append(Spacer(1, 0.1*cm))
            note_para = Paragraph(proforma['notes'], ParagraphStyle(
                'note',
                fontName=self._get_font(),
                fontSize=9,
                leading=11,
                alignment=TA_LEFT
            ))
            elements.append(note_para)
        
        doc.build(elements)
        return filename
    
    def generate_utility_report(self, bills):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'komunalije_izvestaj_{timestamp}.pdf'
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        elements.append(Paragraph("Izveštaj o komunalijama", title_style))
        elements.append(Paragraph(f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.5*cm))
        
        data = [['Datum\nračuna', 'Tip\nkomunalije', 'Iznos\n(RSD)', 'Plaćeno\n(RSD)', 'Status', 'Datum\nplaćanja']]
        
        for bill in bills:
            data.append([
                bill['bill_date'],
                self._wrap_text(bill['utility_type_name'], font_size=8, align=TA_LEFT),
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
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        total = sum(bill['amount'] for bill in bills)
        paid = sum(bill['paid_amount'] for bill in bills)
        unpaid = total - paid
        
        stats_text = f"<b>Ukupno:</b> {total:,.2f} RSD | <b>Plaćeno:</b> {paid:,.2f} RSD | <b>Neplaćeno:</b> {unpaid:,.2f} RSD"
        elements.append(Paragraph(stats_text, normal_style))
        
        doc.build(elements)
        return filename
    
    def generate_revenue_report(self, entries, filter_info=None):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'promet_izvestaj_{timestamp}.pdf'
        
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                               topMargin=1.5*cm, bottomMargin=1.5*cm,
                               leftMargin=1.5*cm, rightMargin=1.5*cm)
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        elements.append(Paragraph("Izveštaj o kontroli prometa", title_style))
        elements.append(Paragraph(f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        
        if filter_info:
            filter_text = f"Period: {filter_info['date_from']} - {filter_info['date_to']}"
            elements.append(Paragraph(filter_text, ParagraphStyle(
                'filter',
                fontName=self._get_font(),
                fontSize=9,
                leading=11,
                alignment=TA_CENTER,
                textColor=colors.grey
            )))
        
        elements.append(Spacer(1, 0.5*cm))
        
        data = [['Datum', 'Gotovina\n(RSD)', 'Kartica\n(RSD)', 'Virman\n(RSD)', 'Čekovi\n(RSD)', 'Ukupno\n(RSD)', 'Status', 'Napomena']]
        
        for entry in entries:
            payment_status = entry.get('payment_status', 'Neplaćeno')
            
            data.append([
                entry['date_from'],
                f"{entry.get('cash', 0):,.2f}",
                f"{entry.get('card', 0):,.2f}",
                f"{entry.get('wire', 0):,.2f}",
                f"{entry.get('checks', 0):,.2f}",
                f"{entry['amount']:,.2f}",
                payment_status,
                self._wrap_text(entry['notes'] if entry['notes'] else "-", font_size=7, align=TA_LEFT)
            ])
        
        table = Table(data, colWidths=[2*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.3*cm, 1.7*cm, 4*cm])
        
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (7, 0), (7, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self._get_font(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        for idx, entry in enumerate(entries, start=1):
            if entry.get('payment_status') == 'Plaćeno':
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, idx), (-1, idx), colors.lightgreen)
                ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph("─" * 100, normal_style))
        elements.append(Spacer(1, 0.3*cm))
        
        total_cash = sum(e.get('cash', 0) for e in entries)
        total_card = sum(e.get('card', 0) for e in entries)
        total_wire = sum(e.get('wire', 0) for e in entries)
        total_checks = sum(e.get('checks', 0) for e in entries)
        total_revenue = sum(entry['amount'] for entry in entries)
        
        paid_entries = [e for e in entries if e.get('payment_status') == 'Plaćeno']
        unpaid_entries = [e for e in entries if e.get('payment_status') == 'Neplaćeno']
        
        paid_amount = sum(e.get('amount', 0) for e in paid_entries)
        unpaid_amount = sum(e.get('amount', 0) for e in unpaid_entries)
        
        stats_text = (
            f"<b>STATISTIKA</b><br/>"
            f"<b>Ukupno unosa:</b> {len(entries)} | "
            f"<b>Ukupan promet:</b> {total_revenue:,.2f} RSD<br/>"
            f"<b>Promet po vrstama:</b><br/>"
            f"&nbsp;&nbsp;• Gotovina: {total_cash:,.2f} RSD<br/>"
            f"&nbsp;&nbsp;• Kartica: {total_card:,.2f} RSD<br/>"
            f"&nbsp;&nbsp;• Virman: {total_wire:,.2f} RSD<br/>"
            f"&nbsp;&nbsp;• Čekovi: {total_checks:,.2f} RSD<br/><br/>"
            f"<b>Status plaćanja:</b><br/>"
            f"&nbsp;&nbsp;• ✅ Plaćeno: {paid_amount:,.2f} RSD ({len(paid_entries)} unosa)<br/>"
            f"&nbsp;&nbsp;• ⚪ Neplaćeno: {unpaid_amount:,.2f} RSD ({len(unpaid_entries)} unosa)"
        )
        
        stats_style = ParagraphStyle(
            'stats',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=0,
            spaceAfter=6
        )
        
        elements.append(Paragraph(stats_text, stats_style))
        
        elements.append(Spacer(1, 0.5*cm))
        legend_text = "<i>Napomena: Zelena boja označava plaćene stavke.</i>"
        elements.append(Paragraph(legend_text, ParagraphStyle(
            'legend',
            fontName=self._get_font(),
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )))
        
        doc.build(elements)
        return filename
    
    def generate_utility_payment_receipt(self, bill_id):
        bill = self.db.get_utility_bill_by_id(bill_id)
        
        if not bill:
            raise Exception("Račun nije pronađen")
        
        settings = self.db.get_settings()
        company_name = settings.get('company_name', '')
        company_address = settings.get('company_address', '')
        company_pib = settings.get('company_pib', '')
        company_bank_account = settings.get('company_bank_account', '')
        logo_path = settings.get('logo_path', '')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        utility_type = bill['utility_type_name'].replace(' ', '_')
        filename = f'{utility_type}_potvrda_{timestamp}.pdf'
        
        doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        title_style, heading_style, normal_style = self._get_styles()
        
        if company_name or company_address:
            logo_image = None
            if logo_path and os.path.exists(logo_path):
                try:
                    from reportlab.platypus import Image
                    logo_image = Image(logo_path, width=2*cm, height=2*cm)
                except Exception as e:
                    print(f"Greška pri učitavanju loga: {e}")
                    logo_image = None
            
            company_info_lines = []
            if company_name:
                company_info_lines.append(Paragraph(f"<b>{company_name}</b>", 
                    ParagraphStyle('company', fontName=self._get_font(bold=True), fontSize=12, leading=14)))
            if company_address:
                company_info_lines.append(Paragraph(company_address, 
                    ParagraphStyle('address', fontName=self._get_font(), fontSize=9, leading=11)))
            if company_pib:
                company_info_lines.append(Paragraph(f"PIB: {company_pib}", 
                    ParagraphStyle('pib', fontName=self._get_font(), fontSize=9, leading=11)))
            if company_bank_account:
                company_info_lines.append(Paragraph(f"Broj računa: {company_bank_account}", 
                    ParagraphStyle('bank', fontName=self._get_font(), fontSize=9, leading=11)))
            
            if logo_image:
                header_table = Table([[company_info_lines, logo_image]], colWidths=[14*cm, 3*cm])
            else:
                header_table = Table([[company_info_lines, '']], colWidths=[14*cm, 3*cm])
            
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            
            elements.append(header_table)
            elements.append(Spacer(1, 0.5*cm))
        
        title_text = f"{bill['utility_type_name'].upper()} - POTVRDA O PLAĆANJU"
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        month_year_display = self._format_month_year(bill['bill_date'])
        
        info_data = [
            ['Period:', month_year_display],
            ['Iznos:', f"{bill['amount']:,.2f} RSD"],
            ['Plaćeno:', f"{bill['paid_amount']:,.2f} RSD"],
            ['Status:', bill['payment_status']],
            ['Datum plaćanja:', bill['payment_date'] if bill['payment_date'] else '-'],
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 13*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), self._get_font(bold=True)),
            ('FONTNAME', (1, 0), (1, -1), self._get_font()),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 1*cm))
        
        if bill.get('notes'):
            elements.append(Paragraph("<b>Napomena:</b>", heading_style))
            elements.append(Spacer(1, 0.2*cm))
            notes_para = Paragraph(bill['notes'], normal_style)
            elements.append(notes_para)
            elements.append(Spacer(1, 1*cm))
        
        elements.append(Spacer(1, 2*cm))
        
        sig_data = [
            ['_____________________', '', '_____________________'],
            ['Potpis platioca', '', 'Potpis primaoca uplate']
        ]
        
        sig_table = Table(sig_data, colWidths=[6*cm, 4*cm, 6*cm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self._get_font()),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(sig_table)
        
        elements.append(Spacer(1, 1*cm))
        footer_text = f"<i>Datum kreiranja potvrde: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
        elements.append(Paragraph(footer_text, ParagraphStyle(
            'footer',
            fontName=self._get_font(),
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )))
        
        doc.build(elements)
        return filename