import os, smtplib, ssl
from email.message import EmailMessage

class EmailSender:
    def __init__(self, smtp_host=None, smtp_port=None, smtp_user=None, smtp_pass=None, alerts_email=None, dry_run=False):
        self.smtp_host = smtp_host or os.environ.get('SMTP_HOST')
        self.smtp_port = int(smtp_port or os.environ.get('SMTP_PORT', 587))
        self.smtp_user = smtp_user or os.environ.get('SMTP_USER')
        self.smtp_pass = smtp_pass or os.environ.get('SMTP_PASS')
        self.alerts_email = alerts_email or os.environ.get('ALERT_EMAIL')
        self.dry_run = dry_run
        
    def _connect(self):
        context = ssl.create_default_context()
        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=60)
        server.starttls(context=context)
        server.login(self.smtp_user, self.smtp_pass)
        return server
        
    def send_email(self, to_email, subject, body_text, from_name=None, from_email=None):
        if not to_email:
            return False
        if self.dry_run:
            print(f"[DRY-RUN] Would send to {to_email} | Subject: {subject}\n{body_text}\n{'-'*40}")
            return True
        msg = EmailMessage()
        sender = from_email or self.smtp_user
        msg['From'] = f"{from_name} <{sender}>" if from_name else sender
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.set_content(body_text)
        try:
            server = self._connect()
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print("SMTP Error:", e)
            return False
            
    def send_alert(self, subject, body_text):
        if not self.alerts_email:
            print("No alerts email configured.")
            return False
        return self.send_email(self.alerts_email, subject, body_text, from_name="Campaign System")
