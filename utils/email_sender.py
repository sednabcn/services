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

# Add this code to your email_sender.py file

import tempfile
import yaml

class GitHubActionsEmailSender(EmailSender):
    """Enhanced EmailSender that works with GitHub Actions email extension"""
    
    def __init__(self, smtp_host=None, smtp_port=None, smtp_user=None, smtp_pass=None, alerts_email=None, dry_run=False):
        super().__init__(smtp_host, smtp_port, smtp_user, smtp_pass, alerts_email, dry_run)
        self.github_actions_mode = os.getenv('GITHUB_ACTIONS') is not None
        self.emails_to_send = []
        
        if self.github_actions_mode:
            print("GitHub Actions mode - emails will be processed by workflow action")
    
    def send_email(self, to_email, subject, body_text, from_name=None, from_email=None, contact_data=None):
        """Override to queue emails for GitHub Actions instead of sending via SMTP"""
        
        if not to_email:
            return False
            
        # Apply rate limiting (for logging purposes)
        self._rate_limit_check()
        
        # Personalize content if contact data provided
        if contact_data:
            subject = self._personalize_content(subject, contact_data)
            body_text = self._personalize_content(body_text, contact_data)
        
        # In GitHub Actions mode, save email data instead of sending
        if self.github_actions_mode:
            email_data = {
                'to': to_email,
                'subject': subject,
                'body': body_text,
                'from_name': from_name or 'Campaign System',
                'from_email': from_email or self.smtp_user,
                'contact': contact_data or {},
                'timestamp': datetime.now().isoformat()
            }
            self.emails_to_send.append(email_data)
            
            print(f"[QUEUED] {to_email}: {subject}")
            return True
        
        # Otherwise use original SMTP sending logic
        return super().send_email(to_email, subject, body_text, from_name, from_email, contact_data)
    
    def send_campaign(self, campaign_name: str, subject: str, content: str, 
                     recipients: List[Dict], from_name: str = "Campaign System") -> Dict:
        """Enhanced campaign sending with GitHub Actions support"""
        
        # Run the campaign (this will queue emails in GitHub Actions mode)
        results = super().send_campaign(campaign_name, subject, content, recipients, from_name)
        
        # In GitHub Actions mode, save emails for the workflow to process
        if self.github_actions_mode and self.emails_to_send:
            self._save_emails_for_github_actions(campaign_name)
            results['github_actions_emails_saved'] = len(self.emails_to_send)
            
        return results
    
    def _save_emails_for_github_actions(self, campaign_name):
        """Save email queue to files for GitHub Actions workflow"""
        try:
            # Create individual email files for batch processing
            batch_dir = Path(f'./github_actions_emails/{campaign_name}')
            batch_dir.mkdir(parents=True, exist_ok=True)
            
            # Save individual emails
            for i, email in enumerate(self.emails_to_send):
                email_file = batch_dir / f'email_{i+1:03d}.json'
                with open(email_file, 'w') as f:
                    json.dump(email, f, indent=2)
            
            # Create summary file for the workflow
            summary = {
                'campaign_name': campaign_name,
                'total_emails': len(self.emails_to_send),
                'smtp_config': {
                    'host': self.smtp_host,
                    'port': self.smtp_port,
                    'user': self.smtp_user
                },
                'created_at': datetime.now().isoformat(),
                'batch_directory': str(batch_dir)
            }
            
            summary_file = Path('./github_actions_email_summary.json')
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            # Create a simple workflow step file
            workflow_step = {
                'name': f'Send {len(self.emails_to_send)} personalized emails',
                'uses': 'dawidd6/action-send-mail@v3',
                'strategy': {
                    'matrix': {
                        'email_file': [f'{batch_dir}/email_{i+1:03d}.json' for i in range(len(self.emails_to_send))]
                    }
                }
            }
            
            with open('./github_actions_email_step.yml', 'w') as f:
                yaml.safe_dump(workflow_step, f, default_flow_style=False)
            
            print(f"Saved {len(self.emails_to_send)} emails for GitHub Actions processing")
            print(f"Summary: {summary_file}")
            print(f"Batch directory: {batch_dir}")
            
        except Exception as e:
            print(f"Warning: Could not save emails for GitHub Actions: {e}")
    
    def send_batch_summary(self, campaigns_processed, total_sent, total_failed, campaign_results):
        """Send a summary email using GitHub Actions (bypasses SMTP timeout issues)"""
        
        summary_subject = f"Campaign Batch Summary: {campaigns_processed} campaigns, {total_sent + total_failed} emails"
        
        summary_body = f"""
CAMPAIGN EXECUTION SUMMARY
========================

Total Campaigns: {campaigns_processed}
Total Emails: {total_sent + total_failed}
Successfully Sent: {total_sent}
Failed: {total_failed}
Success Rate: {(total_sent / max(1, total_sent + total_failed)) * 100:.1f}%
Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CAMPAIGN DETAILS:
"""
        
        for result in campaign_results:
            summary_body += f"\n• {result['campaign_name']}: {result['sent']}/{result['total_recipients']}"
            if result['failed'] > 0:
                summary_body += f" ({result['failed']} failed)"
        
        summary_body += f"\n\nMode: {'GitHub Actions (SMTP bypass)' if self.github_actions_mode else 'Direct SMTP'}"
        summary_body += f"\nPersonalization: ENABLED"
        
        # Create summary email file for GitHub Actions
        if self.github_actions_mode:
            summary_email = {
                'to': self.alerts_email or self.smtp_user,
                'subject': summary_subject,
                'body': summary_body,
                'from_name': 'Campaign System',
                'from_email': self.smtp_user,
                'priority': 'high',
                'timestamp': datetime.now().isoformat()
            }
            
            summary_file = Path('./campaign_summary_email.json')
            with open(summary_file, 'w') as f:
                json.dump(summary_email, f, indent=2)
            
            print(f"Campaign summary saved for GitHub Actions: {summary_file}")
            return True
        else:
            # Fall back to direct SMTP
            return self.send_alert(summary_subject, summary_body)
