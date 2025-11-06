# notifications.py - SAMO OUTLOOK SA APP PASSWORD
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from win10toast import ToastNotifier

class NotificationManager:
    def __init__(self, db):
        self.db = db
        self.toaster = ToastNotifier()
    
    def check_due_invoices(self):
        """Proveri račune koji ističu uskoro"""
        settings = self.db.get_settings()
        notification_days = settings.get('notification_days', 7)
        
        invoices = self.db.get_all_invoices(include_archived=False)
        due_invoices = []
        
        today = datetime.now().date()
        
        for invoice in invoices:
            if not invoice['is_paid']:
                due_date = datetime.strptime(invoice['due_date'], '%d.%m.%Y').date()
                days_until_due = (due_date - today).days
                
                if 0 <= days_until_due <= notification_days:
                    due_invoices.append({
                        'invoice': invoice,
                        'days_until_due': days_until_due
                    })
        
        return due_invoices
    
    def show_windows_notification(self, due_invoices):
        """Prikaži Windows notifikaciju"""
        if not due_invoices:
            return
        
        count = len(due_invoices)
        title = f"Upozorenje: {count} račun(a) ističe uskoro!"
        
        message_lines = []
        for item in due_invoices[:5]:
            invoice = item['invoice']
            days = item['days_until_due']
            message_lines.append(f"• {invoice['vendor_name']}: {days} dana")
        
        message = "\n".join(message_lines)
        
        if count > 5:
            message += f"\n... i još {count - 5} računa"
        
        try:
            self.toaster.show_toast(
                title,
                message,
                duration=10,
                threaded=True
            )
        except Exception as e:
            print(f"Greška pri prikazivanju notifikacije: {e}")
    
    def send_email_notification(self, due_invoices):
        """Pošalji email notifikaciju preko Outlook-a"""
        settings = self.db.get_settings()
        
        outlook_user = settings.get('gmail_user')  # Koristi isto polje
        outlook_password = settings.get('gmail_password')  # App Password
        notification_email = settings.get('notification_email')
        
        if not all([outlook_user, outlook_password, notification_email]):
            print("Email podešavanja nisu kompletna.")
            return False
        
        if not due_invoices:
            return False
        
        # Kreiraj email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Upozorenje: {len(due_invoices)} račun(a) ističe uskoro!"
        msg['From'] = outlook_user
        msg['To'] = notification_email
        
        # HTML sadržaj
        html = """
        <html>
          <head></head>
          <body>
            <h2>Računi koji ističu uskoro:</h2>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
              <tr style="background-color: #f2f2f2;">
                <th>Dobavljač</th>
                <th>Broj otpremnice</th>
                <th>Iznos (RSD)</th>
                <th>Datum valute</th>
                <th>Preostalo dana</th>
              </tr>
        """
        
        for item in due_invoices:
            invoice = item['invoice']
            days = item['days_until_due']
            
            row_color = "#ffcccc" if days <= 3 else "#ffffcc"
            
            html += f"""
              <tr style="background-color: {row_color};">
                <td>{invoice['vendor_name']}</td>
                <td>{invoice['delivery_note_number']}</td>
                <td>{invoice['amount']:,.2f}</td>
                <td>{invoice['due_date']}</td>
                <td>{days}</td>
              </tr>
            """
        
        html += """
            </table>
            <br>
            <p>Molimo vas da obratite pažnju na ove račune.</p>
          </body>
        </html>
        """
        
        part = MIMEText(html, 'html', 'utf-8')
        msg.attach(part)
        
        # Pošalji email preko Outlook SMTP
        try:
            print(f"Povezujem se sa Outlook SMTP serverom...")
            print(f"Email: {outlook_user}")
            
            # Outlook SMTP sa TLS
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.set_debuglevel(1)  # Debug mode
            server.ehlo()
            server.starttls()
            server.ehlo()
            
            print("Logujem se...")
            server.login(outlook_user, outlook_password)
            
            print("Šaljem email...")
            server.send_message(msg)
            server.quit()
            
            print("✓ Email notifikacija uspešno poslata.")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"✗ Greška autentifikacije: {e}")
            print("Proveri:")
            print("1. Da li si kreirao App Password na account.live.com/proofs/manage/additional")
            print("2. Da li koristiš App Password umesto obične lozinke")
            return False
        except Exception as e:
            print(f"✗ Greška pri slanju email-a: {e}")
            return False