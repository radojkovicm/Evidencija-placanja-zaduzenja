# notifications.py – Gmail OAuth2 slanje + dnevni scheduler
import os
import base64
import threading
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from win10toast import ToastNotifier

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    GOOGLE_LIBRARIES_AVAILABLE = True
except ImportError:
    build = InstalledAppFlow = Credentials = Request = None
    GOOGLE_LIBRARIES_AVAILABLE = False


class GmailOAuthHelper:
    """Utility helpers for Gmail OAuth2 flow."""
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    @staticmethod
    def ensure_dependencies():
        if not GOOGLE_LIBRARIES_AVAILABLE:
            raise ImportError(
                "Missing Google libraries. Install with:\n"
                "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )

    @staticmethod
    def default_token_path(credentials_path: str) -> str:
        directory = os.path.dirname(os.path.abspath(credentials_path))
        return os.path.join(directory, "gmail_token.json")

    @staticmethod
    def token_exists(token_path: str) -> bool:
        return bool(token_path and os.path.exists(token_path))

    @staticmethod
    def authorize(credentials_path: str, token_path: str):
        GmailOAuthHelper.ensure_dependencies()
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, GmailOAuthHelper.SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        return creds

    @staticmethod
    def load_credentials(credentials_path: str, token_path: str):
        GmailOAuthHelper.ensure_dependencies()

        creds = None
        if GmailOAuthHelper.token_exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, GmailOAuthHelper.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save the refreshed token back to file
                with open(token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
            else:
                creds = GmailOAuthHelper.authorize(credentials_path, token_path)

        return creds


class GmailSender:
    """Handles email sending through Gmail API."""
    def __init__(self, settings: dict):
        self.settings = settings
        self.credentials_path = settings.get("gmail_credentials_path") or ""
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise FileNotFoundError("Gmail credentials.json path is missing or invalid.")

        self.token_path = settings.get("gmail_token_path") or GmailOAuthHelper.default_token_path(
            self.credentials_path
        )
        self.from_address = settings.get("gmail_user") or "me"

    def send(self, subject: str, html_body: str, recipient: str):
        creds = GmailOAuthHelper.load_credentials(self.credentials_path, self.token_path)
        service = build("gmail", "v1", credentials=creds)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.from_address
        message["To"] = recipient
        message.attach(MIMEText(html_body, "html", "utf-8"))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw_message}).execute()


class NotificationManager:
    """Manages invoice notifications (Windows toast + Gmail email)."""

    def __init__(self, db, *, start_scheduler: bool = True):
        self.db = db
        self.toaster = ToastNotifier()
        self._scheduler_thread = None
        self._scheduler_lock = threading.Lock()
        settings = self.db.get_settings()
        self._last_email_sent_date = settings.get("last_email_notification_date", "")
        if start_scheduler:
            self._ensure_scheduler_thread()

    def _ensure_scheduler_thread(self):
        with self._scheduler_lock:
            if self._scheduler_thread is None:
                self._scheduler_thread = threading.Thread(
                    target=self._scheduler_loop, name="DailyEmailScheduler", daemon=True
                )
                self._scheduler_thread.start()

    def _scheduler_loop(self):
        while True:
            try:
                self._run_scheduler_iteration()
            except Exception as exc:
                print(f"Scheduler iteration failed: {exc}")
            time.sleep(60)  # check every minute

    def _run_scheduler_iteration(self):
        settings = self.db.get_settings()
        if not settings.get("enable_email_notifications", False):
            return

        schedule_time = settings.get("email_notification_time", "09:00")
        try:
            schedule_hour, schedule_minute = [int(part) for part in schedule_time.split(":")]
        except ValueError:
            schedule_hour, schedule_minute = 9, 0

        now = datetime.now()
        today = now.date()
        target_datetime = now.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)

        # Wait until configured time arrives
        if now < target_datetime:
            return

        today_iso = today.isoformat()
        if self._last_email_sent_date == today_iso:
            return  # already sent today

        due_invoices = self.check_due_invoices()
        if not due_invoices:
            return  # nothing to send

        sent = self.send_email_notification(due_invoices)
        if sent:
            self._last_email_sent_date = today_iso
            try:
                self.db.update_setting("last_email_notification_date", today_iso)
            except Exception as exc:
                print(f"Unable to persist last_email_notification_date: {exc}")

    def check_due_invoices(self):
        """Return list of invoices with due dates inside notification window."""
        settings = self.db.get_settings()
        notification_days = settings.get("notification_days", 7)
        try:
            notification_days = int(notification_days)
        except (TypeError, ValueError):
            notification_days = 7

        invoices = self.db.get_all_invoices(include_archived=False)
        due_invoices = []

        today = datetime.now().date()
        for invoice in invoices:
            if invoice.get("is_paid"):
                continue

            due_date_str = invoice.get("due_date")
            if not due_date_str:
                continue

            try:
                due_date = datetime.strptime(due_date_str, "%d.%m.%Y").date()
            except ValueError:
                continue

            days_until_due = (due_date - today).days
            if 0 <= days_until_due <= notification_days:
                due_invoices.append(
                    {"invoice": invoice, "days_until_due": days_until_due}
                )

        return due_invoices

    def show_windows_notification(self, due_invoices):
        """Show Windows toast notification for due invoices."""
        if not due_invoices:
            return

        count = len(due_invoices)
        title = f"Upozorenje: {count} račun(a) ističe uskoro!"
        message_lines = []

        for item in due_invoices[:5]:
            invoice = item["invoice"]
            days = item["days_until_due"]
            message_lines.append(f"• {invoice.get('vendor_name', 'N/A')}: {days} dana")

        message = "\n".join(message_lines)
        if count > 5:
            message += f"\n... i još {count - 5} računa"

        try:
            self.toaster.show_toast(title, message, duration=10, threaded=True)
        except Exception as exc:
            print(f"Greška pri prikazivanju notifikacije: {exc}")

    def _render_email_html(self, due_invoices):
        """Build HTML body for the email."""
        rows_html = ""
        for item in due_invoices:
            invoice = item["invoice"]
            days = item["days_until_due"]
            row_color = "#ffcccc" if days <= 3 else "#ffffcc"
            amount = invoice.get("amount") or 0
            try:
                amount_str = f"{float(amount):,.2f}"
            except (TypeError, ValueError):
                amount_str = str(amount)

            rows_html += f"""
                <tr style="background-color: {row_color};">
                    <td>{invoice.get('vendor_name', '')}</td>
                    <td>{invoice.get('delivery_note_number', '')}</td>
                    <td>{amount_str}</td>
                    <td>{invoice.get('due_date', '')}</td>
                    <td>{days}</td>
                </tr>
            """

        html_body = f"""
            <html>
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
                        {rows_html}
                    </table>
                    <br>
                    <p>Molimo vas da obratite pažnju na ove račune.</p>
                </body>
            </html>
        """
        return html_body

    def send_email_notification(self, due_invoices):
        """Send notification email via Gmail API."""
        if not due_invoices:
            return False

        settings = self.db.get_settings()
        if not settings.get("enable_email_notifications", False):
            print("Email notifications are disabled.")
            return False

        provider_key = settings.get("email_provider", "gmail_oauth")
        if provider_key != "gmail_oauth":
            print(f"Email provider '{provider_key}' is not supported.")
            return False

        notification_email = settings.get("notification_email")
        if not notification_email:
            print("Notification recipient email is not configured.")
            return False

        if not GOOGLE_LIBRARIES_AVAILABLE:
            print(
                "Google libraries are missing. Install required packages and try again."
            )
            return False

        try:
            sender = GmailSender(settings)
        except Exception as exc:
            print(f"Unable to initialize Gmail sender: {exc}")
            return False

        subject = f"Upozorenje: {len(due_invoices)} račun(a) ističe uskoro!"
        html_body = self._render_email_html(due_invoices)

        try:
            sender.send(subject, html_body, notification_email)
            print("✓ Email notification sent successfully.")
            return True
        except Exception as exc:
            print(f"✗ Error sending email: {exc}")
            return False