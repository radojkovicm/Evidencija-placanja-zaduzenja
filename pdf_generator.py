# pdf_generator.py - SA LOGOM I FIRMOM
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
import sys

class PDFGenerator:
    def __init__(self, db):
        self.db = db
        self.font_name = 'Helvetica'
        self.font_name_bold = 'Helvetica-Bold'
        self._register_font()
    
    def _register_font(self):
        """Automatski pronađi i registruj font koji podržava srpska slova"""
        possible_fonts = [
            ('Arial', 'arial.ttf', 'arialbd.ttf'),
            ('Calibri', 'calibri.ttf', 'calibrib.ttf'),
            ('Verdana', 'verdana.ttf', 'verdanab.ttf'),
            ('Tahoma', 'tahoma.ttf', 'tahomabd.ttf'),
            ('Times New Roman', 'times.ttf', 'timesbd.ttf'),
        ]
        
        if sys.platform == 'win32':
            fonts_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
        else:
            fonts_dir = '/usr/share/fonts/truetype'
        
        for font_name, regular_file, bold_file in possible_fonts:
            try:
                regular_path = os.path.join(fonts_dir, regular_file)
                bold_path = os.path.join(fonts_dir, bold_file)
                
                if os.path.exists(regular_path):
                    pdfmetrics.registerFont(TTFont(font_name, regular_path))
                    self.font_name = font_name
                    
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont(f"{font_name}-Bold", bold_path))
                        self.font_name_bold = f"{font_name}-Bold"
                    else:
                        self.font_name_bold = font_name
                    
                    print(f"Registrovan font: {font_name}")
                    return
            except Exception as e:
                continue
        
        print("Koristi se default font (Helvetica)")
    
    def generate_invoice_report(self, invoices, filename="izvestaj_racuni.pdf"):
        """Generiši PDF izveštaj sa računima"""
        settings = self.db.get_settings()
        
        doc = SimpleDocTemplate(filename, pagesize=A4,
                                rightMargin=1*cm, leftMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom stilovi
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=self.font_name_bold,
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10
        )
        
        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Normal'],
            fontName=self.font_name_bold,
            fontSize=12,
            textColor=colors.HexColor('#333333')
        )
        
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            alignment=TA_RIGHT
        )
        
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Normal'],
            fontName=self.font_name_bold,
            fontSize=10,
            alignment=TA_RIGHT
        )
        
        # HEADER - Logo levo, firma desno
        logo_path = settings.get('logo_path')
        company_name = settings.get('company_name', 'Moja Firma')
        company_address = settings.get('company_address', '')
        
        header_data = []
        
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=4*cm, height=4*cm)
                company_info = f"<b>{company_name}</b><br/>{company_address}"
                company_para = Paragraph(company_info, company_style)
                header_data = [[logo, company_para]]
                
                header_table = Table(header_data, colWidths=[5*cm, 14*cm])
                header_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(header_table)
            except Exception as e:
                print(f"Greška pri učitavanju loga: {e}")
                company_para = Paragraph(f"<b>{company_name}</b><br/>{company_address}", company_style)
                elements.append(company_para)
        else:
            company_para = Paragraph(f"<b>{company_name}</b><br/>{company_address}", company_style)
            elements.append(company_para)
        
        elements.append(Spacer(1, 0.8*cm))
        
        # Naslov
        elements.append(Paragraph("IZVEŠTAJ O RAČUNIMA", title_style))
        
        # Datum izveštaja
        elements.append(Paragraph(f"Datum: {datetime.now().strftime('%d.%m.%Y')}", date_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela sa računima
        if invoices:
            data = [[
                Paragraph('<b>Datum<br/>fakture</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER)),
                Paragraph('<b>Datum<br/>valute</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER)),
                Paragraph('<b>Dobavljač</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER)),
                Paragraph('<b>Br.<br/>otpremnice</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER)),
                Paragraph('<b>Iznos<br/>(RSD)</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER)),
                Paragraph('<b>Status</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER)),
                Paragraph('<b>Datum<br/>plaćanja</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER)),
                Paragraph('<b>Napomena</b>', ParagraphStyle('HeaderStyle', parent=normal_style, fontName=self.font_name_bold, fontSize=8, alignment=TA_CENTER))
            ]]
            
            cell_style = ParagraphStyle('CellStyle', parent=normal_style, fontName=self.font_name, fontSize=7, alignment=TA_LEFT)
            cell_style_center = ParagraphStyle('CellStyleCenter', parent=normal_style, fontName=self.font_name, fontSize=7, alignment=TA_CENTER)
            cell_style_right = ParagraphStyle('CellStyleRight', parent=normal_style, fontName=self.font_name, fontSize=7, alignment=TA_RIGHT)
            
            row_colors = []
            
            for idx, invoice in enumerate(invoices):
                status = "Plaćeno" if invoice['is_paid'] else "Neplaćeno"
                payment_date = invoice['payment_date'] if invoice['payment_date'] else "-"
                notes = invoice['notes'] if invoice['notes'] else "-"
                
                if len(notes) > 80:
                    notes = notes[:77] + "..."
                
                data.append([
                    Paragraph(invoice['invoice_date'], cell_style_center),
                    Paragraph(invoice['due_date'], cell_style_center),
                    Paragraph(invoice['vendor_name'] or '-', cell_style),
                    Paragraph(invoice['delivery_note_number'] or '-', cell_style_center),
                    Paragraph(f"{invoice['amount']:,.2f}", cell_style_right),
                    Paragraph(status, cell_style_center),
                    Paragraph(payment_date, cell_style_center),
                    Paragraph(notes, cell_style)
                ])
                
                if invoice['is_paid']:
                    row_colors.append((idx + 1, colors.lightgreen))
                else:
                    due_date = datetime.strptime(invoice['due_date'], '%d.%m.%Y').date()
                    today = datetime.now().date()
                    days_until_due = (due_date - today).days
                    notification_days = settings.get('notification_days', 7)
                    
                    if 0 <= days_until_due <= notification_days:
                        row_colors.append((idx + 1, colors.yellow))
                    else:
                        row_colors.append((idx + 1, colors.beige))
            
            table = Table(data, colWidths=[1.8*cm, 1.8*cm, 3*cm, 1.8*cm, 2*cm, 1.8*cm, 1.8*cm, 5*cm])
            
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), self.font_name_bold),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]
            
            for row_idx, color in row_colors:
                table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), color))
            
            table.setStyle(TableStyle(table_style))
            elements.append(table)
            
            # Ukupan iznos
            total_amount = sum(inv['amount'] for inv in invoices)
            total_paid = sum(inv['amount'] for inv in invoices if inv['is_paid'])
            total_unpaid = total_amount - total_paid
            
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph(f"<b>Ukupno:</b> {total_amount:,.2f} RSD", summary_style))
            elements.append(Paragraph(f"<b>Plaćeno:</b> {total_paid:,.2f} RSD", summary_style))
            elements.append(Paragraph(f"<b>Neplaćeno:</b> {total_unpaid:,.2f} RSD", summary_style))
        else:
            elements.append(Paragraph("Nema računa za prikaz.", normal_style))
        
        doc.build(elements)
        return filename