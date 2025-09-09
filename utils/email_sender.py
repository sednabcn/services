import os, smtplib, ssl, json, time, re
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class EmailSender:
    def __init__(self, smtp_host=None, smtp_port=None, smtp_user=None, smtp_pass=None, alerts_email=None, dry_run=False):
        self.smtp_host = smtp_host or os.environ.get('SMTP_HOST')
        self.smtp_port = int(smtp_port or os.environ.get('SMTP_PORT', 587))
        self.smtp_user = smtp_user or os.environ.get('SMTP_USER')
        self.smtp_pass = smtp_pass or os.environ.get('SMTP_PASS')
        self.alerts_email = alerts_email or os.environ.get('ALERT_EMAIL')
        self.dry_run = dry_run
        
        # Enhanced features
        self.rate_limit = int(os.environ.get('EMAIL_RATE_LIMIT', '30'))  # emails per minute
        self.last_send_time = 0
        self.tracking_dir = Path(os.environ.get('TRACKING_DIR', 'tracking'))
        self.tracking_dir.mkdir(exist_ok=True)
        
        print(f"EmailSender initialized - dry_run: {dry_run}, alerts: {alerts_email}")
        if dry_run:
            print("🔍 DRY RUN MODE - No emails will be sent")
        
    def _connect(self):
        """Enhanced connection with better error handling"""
        try:
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=60)
            server.starttls(context=context)
            server.login(self.smtp_user, self.smtp_pass)
            return server
        except Exception as e:
            print(f"SMTP Connection Error: {e}")
            return None
    
    def _rate_limit_check(self):
        """Simple rate limiting to avoid overwhelming SMTP servers"""
        if self.rate_limit <= 0:
            return
            
        current_time = time.time()
        time_since_last = current_time - self.last_send_time
        min_interval = 60 / self.rate_limit  # seconds between emails
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            if not self.dry_run:  # Only sleep in real mode
                time.sleep(sleep_time)
        
        self.last_send_time = time.time()
    
    def _personalize_content(self, content: str, contact: Dict) -> str:
        """Replace placeholders in content with contact information"""
        if not isinstance(contact, dict):
            return content
            
        personalized = content
        
        # Common placeholders
        placeholders = {
            '{{name}}': contact.get('name', contact.get('email', '').split('@')[0]),
            '{{email}}': contact.get('email', ''),
            '{{first_name}}': contact.get('name', '').split(' ')[0] if contact.get('name') else '',
        }
        
        # Add custom fields from contact
        for key, value in contact.items():
            if key not in ['name', 'email'] and value:
                placeholders[f'{{{{{key}}}}}'] = str(value)
        
        # Replace placeholders
        for placeholder, value in placeholders.items():
            personalized = personalized.replace(placeholder, value)
        
        return personalized
        
    def send_email(self, to_email, subject, body_text, from_name=None, from_email=None, contact_data=None):
        """Enhanced send_email with personalization support"""
        if not to_email:
            return False
            
        # Apply rate limiting
        self._rate_limit_check()
        
        # Personalize content if contact data provided
        if contact_data:
            subject = self._personalize_content(subject, contact_data)
            body_text = self._personalize_content(body_text, contact_data)
        
        if self.dry_run:
            print(f"[DRY-RUN] Would send to {to_email}")
            print(f"Subject: {subject}")
            print(f"From: {from_name or self.smtp_user}")
            print(f"Body preview: {body_text[:100]}...")
            print(f"{'-'*50}")
            return True
            
        msg = EmailMessage()
        sender = from_email or self.smtp_user
        msg['From'] = f"{from_name} <{sender}>" if from_name else sender
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Check if content is HTML
        if '<html' in body_text.lower() or '<div' in body_text.lower() or '<p' in body_text.lower():
            # Create multipart message for HTML
            msg_multi = MIMEMultipart('alternative')
            msg_multi['From'] = msg['From']
            msg_multi['To'] = msg['To']
            msg_multi['Subject'] = msg['Subject']
            
            # Create plain text version
            text_content = re.sub('<[^<]+?>', '', body_text)
            text_content = text_content.replace('&nbsp;', ' ').strip()
            
            msg_multi.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg_multi.attach(MIMEText(body_text, 'html', 'utf-8'))
            
            try:
                server = self._connect()
                if not server:
                    return False
                server.send_message(msg_multi)
                server.quit()
                return True
            except Exception as e:
                print(f"SMTP Error: {e}")
                return False
        else:
            # Plain text email
            msg.set_content(body_text)
            try:
                server = self._connect()
                if not server:
                    return False
                server.send_message(msg)
                server.quit()
                return True
            except Exception as e:
                print(f"SMTP Error: {e}")
                return False
    
    def send_campaign(self, campaign_name: str, subject: str, content: str, 
                     recipients: List[Dict], from_name: str = "Campaign System") -> Dict:
        """Send campaign to multiple recipients with tracking"""
        start_time = datetime.now()
        results = {
            'campaign_name': campaign_name,
            'total_recipients': len(recipients),
            'sent': 0,
            'failed': 0,
            'errors': [],
            'start_time': start_time.isoformat(),
            'dry_run': self.dry_run,
            'recipients_detail': []
        }
        
        print(f"Starting campaign '{campaign_name}' to {len(recipients)} recipients")
        
        for i, contact in enumerate(recipients, 1):
            recipient_result = {
                'email': contact.get('email', ''),
                'name': contact.get('name', ''),
                'status': 'pending'
            }
            
            try:
                success = self.send_email(
                    to_email=contact['email'],
                    subject=subject,
                    body_text=content,
                    from_name=from_name,
                    contact_data=contact
                )
                
                if success:
                    results['sent'] += 1
                    recipient_result['status'] = 'sent' if not self.dry_run else 'simulated'
                    if not self.dry_run:
                        print(f"✅ Sent {i}/{len(recipients)}: {contact['email']}")
                else:
                    results['failed'] += 1
                    recipient_result['status'] = 'failed'
                    error_msg = f"Failed to send to {contact['email']}"
                    results['errors'].append(error_msg)
                    print(f"❌ Failed {i}/{len(recipients)}: {contact['email']}")
                    
            except Exception as e:
                results['failed'] += 1
                recipient_result['status'] = 'error'
                recipient_result['error'] = str(e)
                error_msg = f"Error sending to {contact['email']}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"❌ Error {i}/{len(recipients)}: {contact['email']} - {str(e)}")
            
            results['recipients_detail'].append(recipient_result)
            
            # Progress update every 10 emails
            if i % 10 == 0:
                print(f"Progress: {i}/{len(recipients)} processed")
        
        # Finalize results
        results['end_time'] = datetime.now().isoformat()
        duration = datetime.now() - start_time
        results['duration_seconds'] = duration.total_seconds()
        
        print(f"\nCampaign '{campaign_name}' completed:")
        print(f"  ✅ Sent: {results['sent']}")
        print(f"  ❌ Failed: {results['failed']}")
        print(f"  ⏱️ Duration: {duration}")
        
        # Save detailed results
        self._save_campaign_results(results)
        
        # Send alert if there were failures and not in dry run
        if results['failed'] > 0 and not self.dry_run:
            self._send_failure_alert(results)
        
        return results
    
    def _save_campaign_results(self, results: Dict):
        """Save campaign results to tracking directory"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{results['campaign_name']}_{timestamp}.json"
            filepath = self.tracking_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"Campaign results saved to: {filepath}")
            
        except Exception as e:
            print(f"Warning: Could not save campaign results: {e}")
    
    def _send_failure_alert(self, results: Dict):
        """Send alert email if there were failures"""
        if not self.alerts_email or self.dry_run:
            return
            
        failure_rate = (results['failed'] / results['total_recipients']) * 100
        
        alert_subject = f"🚨 Campaign Alert: {results['campaign_name']} - {results['failed']} failures"
        
        alert_body = f"""
Campaign Failure Report
======================

Campaign: {results['campaign_name']}
Total Recipients: {results['total_recipients']}
Successful: {results['sent']}
Failed: {results['failed']}
Failure Rate: {failure_rate:.1f}%
Duration: {results.get('duration_seconds', 0):.1f} seconds

Recent Errors:
{chr(10).join(results['errors'][-5:])}  

Check the full campaign log for detailed information.
        """.strip()
        
        try:
            self.send_alert(alert_subject, alert_body)
            print("Failure alert sent to administrators")
        except Exception as e:
            print(f"Warning: Could not send failure alert: {e}")
            
    def send_alert(self, subject, body_text):
        """Original alert method - maintained for compatibility"""
        if not self.alerts_email:
            print("No alerts email configured.")
            return False
        return self.send_email(self.alerts_email, subject, body_text, from_name="Campaign System")
    
    def get_campaign_stats(self) -> Dict:
        """Get statistics from recent campaigns"""
        stats = {
            'total_campaigns': 0,
            'total_emails_sent': 0,
            'total_failures': 0,
            'recent_campaigns': []
        }
        
        try:
            # Read recent campaign files
            campaign_files = sorted(self.tracking_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
            
            for file_path in campaign_files[:10]:  # Last 10 campaigns
                try:
                    with open(file_path, 'r') as f:
                        campaign_data = json.load(f)
                    
                    stats['total_campaigns'] += 1
                    stats['total_emails_sent'] += campaign_data.get('sent', 0)
                    stats['total_failures'] += campaign_data.get('failed', 0)
                    
                    stats['recent_campaigns'].append({
                        'name': campaign_data.get('campaign_name', 'Unknown'),
                        'date': campaign_data.get('start_time', ''),
                        'sent': campaign_data.get('sent', 0),
                        'failed': campaign_data.get('failed', 0)
                    })
                    
                except Exception as e:
                    print(f"Warning: Could not read campaign file {file_path}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Could not read campaign statistics: {e}")
        
        return stats
