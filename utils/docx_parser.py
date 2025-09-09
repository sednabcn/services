import argparse
import os
import sys
import traceback
import json
import csv
import re
from datetime import datetime

# Environment detection and library availability checks
IS_REMOTE = os.getenv('GITHUB_ACTIONS') is not None or os.getenv('CI') is not None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests library not available")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas library not available")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("Warning: python-docx library not available")

# Simple EmailSender fallback if module not available
try:
    from email_sender import EmailSender
except ImportError:
    print("Warning: email_sender module not found, using fallback")
    class EmailSender:
        def __init__(self, alerts_email=None, dry_run=False):
            self.alerts_email = alerts_email
            self.dry_run = dry_run
            print(f"EmailSender initialized - dry_run: {dry_run}, alerts: {alerts_email}")

class ContactParser:
    """Handle parsing of contact data from various file formats"""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.docx', '.txt', '.url']
    
    def parse_csv_file(self, file_path):
        """Parse CSV file and extract contact information"""
        contacts = []
        try:
            if PANDAS_AVAILABLE:
                # Try with pandas first for better handling of various CSV formats
                df = pd.read_csv(file_path, encoding='utf-8')
                
                # Common column name variations for email
                email_columns = ['email', 'Email', 'EMAIL', 'email_address', 'Email Address', 'e-mail']
                name_columns = ['name', 'Name', 'NAME', 'full_name', 'Full Name', 'first_name', 'last_name']
                
                email_col = None
                name_col = None
                
                # Find email column
                for col in df.columns:
                    if col in email_columns or 'email' in col.lower():
                        email_col = col
                        break
                
                # Find name column
                for col in df.columns:
                    if col in name_columns or 'name' in col.lower():
                        name_col = col
                        break
                
                if not email_col:
                    print(f"Warning: No email column found in {file_path}. Available columns: {list(df.columns)}")
                    return []
                
                for index, row in df.iterrows():
                    email = str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
                    name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""
                    
                    # Validate email format
                    if email and self.is_valid_email(email):
                        contact = {
                            'email': email,
                            'name': name if name else email.split('@')[0],
                            'source': file_path,
                            'row': index + 2  # +2 because pandas is 0-indexed and CSV has header
                        }
                        
                        # Add any additional columns as custom fields
                        for col in df.columns:
                            if col not in [email_col, name_col] and pd.notna(row[col]):
                                contact[col.lower().replace(' ', '_')] = str(row[col]).strip()
                        
                        contacts.append(contact)
                
                print(f"Parsed {len(contacts)} valid contacts from CSV: {file_path}")
                return contacts
            else:
                # Fallback to basic csv parsing
                return self.parse_csv_fallback(file_path)
            
        except Exception as e:
            print(f"Error parsing CSV file {file_path}: {str(e)}")
            # Fallback to basic csv module
            return self.parse_csv_fallback(file_path)
    
    def parse_csv_fallback(self, file_path):
        """Fallback CSV parsing using basic csv module"""
        contacts = []
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):
                    # Find email in any column
                    email = None
                    name = None
                    
                    for key, value in row.items():
                        if value and 'email' in key.lower():
                            email = value.strip()
                        elif value and 'name' in key.lower():
                            name = value.strip()
                    
                    if email and self.is_valid_email(email):
                        contacts.append({
                            'email': email,
                            'name': name if name else email.split('@')[0],
                            'source': file_path,
                            'row': row_num,
                            **{k.lower().replace(' ', '_'): v for k, v in row.items() if v}
                        })
            
            print(f"Parsed {len(contacts)} contacts from CSV (fallback): {file_path}")
            return contacts
            
        except Exception as e:
            print(f"Error in CSV fallback parsing {file_path}: {str(e)}")
            return []
    
    def parse_docx_file(self, file_path):
        """Parse DOCX file and extract contact information"""
        contacts = []
        
        if not DOCX_AVAILABLE:
            print(f"Warning: python-docx not available, skipping {file_path}")
            return contacts
            
        try:
            doc = Document(file_path)
            text_content = ""
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_content += cell.text + "\t"
                    text_content += "\n"
            
            # Extract emails using regex
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text_content)
            
            # Try to extract names (text before emails or on same line)
            lines = text_content.split('\n')
            
            for email in set(emails):  # Remove duplicates
                if self.is_valid_email(email):
                    name = self.extract_name_for_email(email, lines)
                    contacts.append({
                        'email': email,
                        'name': name if name else email.split('@')[0],
                        'source': file_path,
                        'extracted_from': 'docx_content'
                    })
            
            print(f"Parsed {len(contacts)} contacts from DOCX: {file_path}")
            return contacts
            
        except Exception as e:
            print(f"Error parsing DOCX file {file_path}: {str(e)}")
            return []
    
    def extract_name_for_email(self, email, lines):
        """Try to find a name associated with an email in the text"""
        for line in lines:
            if email in line:
                # Look for name patterns in the same line
                words = line.replace(email, '').split()
                # Filter out common non-name words
                potential_names = [w for w in words if len(w) > 1 and w.isalpha()]
                if potential_names:
                    return ' '.join(potential_names[:2])  # Take first two words as name
        return None
    
    def parse_txt_file(self, file_path):
        """Parse plain text file and extract email addresses"""
        contacts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract emails using regex
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, content)
            
            lines = content.split('\n')
            
            for email in set(emails):  # Remove duplicates
                if self.is_valid_email(email):
                    name = self.extract_name_for_email(email, lines)
                    contacts.append({
                        'email': email,
                        'name': name if name else email.split('@')[0],
                        'source': file_path,
                        'extracted_from': 'txt_content'
                    })
            
            print(f"Parsed {len(contacts)} contacts from TXT: {file_path}")
            return contacts
            
        except Exception as e:
            print(f"Error parsing TXT file {file_path}: {str(e)}")
            return []
    
    def is_valid_email(self, email):
        """Validate email format"""
        email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    def parse_url_file(self, file_path):
        """Parse .url file containing Google Sheets or other URLs"""
        contacts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            print(f"Processing URL file: {file_path}")
            
            # Check if it's a Google Sheets URL
            if 'docs.google.com/spreadsheets' in content:
                return self.parse_google_sheets_url(content, file_path)
            elif content.startswith('http'):
                return self.parse_web_url(content, file_path)
            else:
                print(f"Warning: Unrecognized URL format in {file_path}")
                return []
                
        except Exception as e:
            print(f"Error parsing URL file {file_path}: {str(e)}")
            return []

    def parse_google_sheets_url(self, url, source_file):
        """Parse Google Sheets URL and extract contacts"""
        contacts = []
        
        if not REQUESTS_AVAILABLE:
            print("Warning: requests library not available for Google Sheets parsing")
            return []
        
        try:
            print(f"Processing Google Sheets URL: {url}")
            
            # Convert viewing URL to CSV export URL
            if '/edit' in url:
                sheet_id = url.split('/d/')[1].split('/')[0]
                gid = '0'  # Default sheet
                
                # Extract gid if present
                if 'gid=' in url:
                    gid = url.split('gid=')[1].split('#')[0].split('&')[0]
                
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                print(f"Converted to CSV URL: {csv_url}")
                
                # Try to fetch the data
                response = requests.get(csv_url, timeout=30)
                if response.status_code == 200:
                    print("Successfully fetched Google Sheets data")
                    
                    # Save temporarily and parse as CSV
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                        temp_file.write(response.text)
                        temp_path = temp_file.name
                    
                    try:
                        contacts = self.parse_csv_file(temp_path)
                        # Update source info
                        for contact in contacts:
                            contact['source'] = f"{source_file} -> Google Sheets"
                            contact['sheets_url'] = url
                    finally:
                        os.unlink(temp_path)
                        
                elif response.status_code == 403:
                    print("Error: Google Sheets access denied. Sheet may be private or sharing settings need to be updated.")
                    print("Make sure the sheet is shared with 'Anyone with the link can view'")
                else:
                    print(f"Error fetching Google Sheets: HTTP {response.status_code}")
                    
            else:
                print("Warning: Google Sheets URL format not recognized")
                
        except Exception as e:
            print(f"Error processing Google Sheets: {str(e)}")
            
        return contacts

    def parse_web_url(self, url, source_file):
        """Parse general web URL for contact data"""
        contacts = []
        
        if not REQUESTS_AVAILABLE:
            print("Warning: requests library not available for web URL parsing")
            return []
        
        try:
            print(f"Fetching data from URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                if 'text/csv' in content_type or url.endswith('.csv'):
                    # Handle CSV response
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                        temp_file.write(response.text)
                        temp_path = temp_file.name
                    
                    try:
                        contacts = self.parse_csv_file(temp_path)
                        for contact in contacts:
                            contact['source'] = f"{source_file} -> {url}"
                    finally:
                        os.unlink(temp_path)
                        
                else:
                    # Try to extract emails from HTML/text content
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, response.text)
                    
                    for email in set(emails):
                        if self.is_valid_email(email):
                            contacts.append({
                                'email': email,
                                'name': email.split('@')[0],
                                'source': f"{source_file} -> {url}",
                                'extracted_from': 'web_content'
                            })
            else:
                print(f"Error fetching URL: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"Error processing web URL: {str(e)}")
            
        return contacts

    def parse_excel_file(self, file_path):
        """Parse Excel file (.xlsx) and extract contact information"""
        contacts = []
        
        if not PANDAS_AVAILABLE:
            print(f"Warning: pandas not available, skipping Excel file {file_path}")
            return contacts
            
        try:
            df = pd.read_excel(file_path)
            
            # Common column name variations for email
            email_columns = ['email', 'Email', 'EMAIL', 'email_address', 'Email Address', 'e-mail']
            name_columns = ['name', 'Name', 'NAME', 'full_name', 'Full Name', 'first_name', 'last_name']
            
            email_col = None
            name_col = None
            
            # Find email column
            for col in df.columns:
                if col in email_columns or 'email' in col.lower():
                    email_col = col
                    break
            
            # Find name column
            for col in df.columns:
                if col in name_columns or 'name' in col.lower():
                    name_col = col
                    break
            
            if not email_col:
                print(f"Warning: No email column found in {file_path}. Available columns: {list(df.columns)}")
                return []
            
            for index, row in df.iterrows():
                email = str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
                name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""
                
                if email and self.is_valid_email(email):
                    contact = {
                        'email': email,
                        'name': name if name else email.split('@')[0],
                        'source': file_path,
                        'row': index + 2
                    }
                    
                    # Add any additional columns as custom fields
                    for col in df.columns:
                        if col not in [email_col, name_col] and pd.notna(row[col]):
                            contact[col.lower().replace(' ', '_')] = str(row[col]).strip()
                    
                    contacts.append(contact)
            
            print(f"Parsed {len(contacts)} valid contacts from Excel: {file_path}")
            return contacts
            
        except Exception as e:
            print(f"Error parsing Excel file {file_path}: {str(e)}")
            return []
    
    def parse_contacts_directory(self, contacts_directory):
        """Parse all supported files in the contacts directory"""
        all_contacts = []
        
        if not os.path.exists(contacts_directory):
            print(f"Contacts directory does not exist: {contacts_directory}")
            return all_contacts
        
        print(f"Scanning contacts directory: {contacts_directory}")
        
        for filename in os.listdir(contacts_directory):
            file_path = os.path.join(contacts_directory, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            file_ext = os.path.splitext(filename)[1].lower()
            
            try:
                if file_ext == '.csv':
                    contacts = self.parse_csv_file(file_path)
                elif file_ext == '.xlsx':
                    contacts = self.parse_excel_file(file_path)
                elif file_ext == '.docx':
                    contacts = self.parse_docx_file(file_path)
                elif file_ext == '.txt':
                    contacts = self.parse_txt_file(file_path)
                elif file_ext == '.url':
                    contacts = self.parse_url_file(file_path)
                else:
                    print(f"Unsupported file format: {filename}")
                    continue
                
                if contacts:
                    print(f"Loaded {len(contacts)} contacts from {filename}")
                    all_contacts.extend(contacts)
                else:
                    print(f"No contacts found in {filename}")
                
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                continue
        
        # Remove duplicates based on email
        unique_contacts = {}
        for contact in all_contacts:
            email = contact['email'].lower()
            if email not in unique_contacts:
                unique_contacts[email] = contact
            else:
                # Merge contact info if duplicate found
                existing = unique_contacts[email]
                for key, value in contact.items():
                    if key not in existing and value:
                        existing[key] = value
        
        final_contacts = list(unique_contacts.values())
        print(f"\nContact Summary:")
        print(f"   Total files processed: {len([f for f in os.listdir(contacts_directory) if os.path.isfile(os.path.join(contacts_directory, f))])}")
        print(f"   Total contacts found: {len(all_contacts)}")
        print(f"   Unique contacts: {len(final_contacts)}")
        
        return final_contacts

def count_recipients_from_url(contacts_url):
    """Count recipients from a Google Sheets URL or other contact source"""
    if not REQUESTS_AVAILABLE:
        print("Warning: requests library not available for URL parsing")
        return 25
        
    try:
        if not contacts_url:
            return 0
            
        # Handle Google Sheets URLs
        if 'docs.google.com/spreadsheets' in contacts_url:
            # Convert to CSV export URL
            if '/edit' in contacts_url:
                sheet_id = contacts_url.split('/d/')[1].split('/')[0]
                gid = '0'  # Default sheet
                if 'gid=' in contacts_url:
                    gid = contacts_url.split('gid=')[1].split('#')[0].split('&')[0]
                
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                
                # Try to get the CSV data
                response = requests.get(csv_url, timeout=10)
                if response.status_code == 200:
                    # Count non-empty rows (subtract 1 for header)
                    lines = response.text.strip().split('\n')
                    return max(0, len([line for line in lines if line.strip()]) - 1)
                else:
                    print(f"Could not access Google Sheets (status: {response.status_code}), using default count")
                    return 50  # Default fallback
            
        # Handle other URL types or file paths
        elif contacts_url.endswith('.csv'):
            if os.path.exists(contacts_url):
                with open(contacts_url, 'r') as f:
                    lines = f.readlines()
                return max(0, len([line for line in lines if line.strip()]) - 1)
        
        # Default fallback
        return 25
        
    except Exception as e:
        print(f"Error counting recipients from {contacts_url}: {str(e)}")
        return 25  # Default fallback

def load_campaign_content(campaign_path):
    """Load campaign content from various file formats including JSON"""
    try:
        file_ext = os.path.splitext(campaign_path)[1].lower()
        
        if file_ext == '.json':
            return load_json_campaign(campaign_path)
        elif file_ext == '.docx':
            if not DOCX_AVAILABLE:
                print(f"Warning: python-docx not available, skipping {campaign_path}")
                return None
                
            doc = Document(campaign_path)
            content = ""
            
            # Extract all text content
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
            
            # Extract table content
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        content += cell.text + " "
                    content += "\n"
            
            return content.strip()
        
        elif file_ext in ['.txt', '.html', '.md']:
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(campaign_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    return content
                except UnicodeDecodeError:
                    continue
            
            # If all encodings failed, try binary mode
            print(f"Warning: Could not decode {campaign_path} with standard encodings, trying binary")
            with open(campaign_path, 'rb') as f:
                raw_content = f.read()
                return raw_content.decode('utf-8', errors='ignore')
        
        return None
        
    except Exception as e:
        print(f"Error loading campaign content from {campaign_path}: {str(e)}")
        return None

def load_json_campaign(campaign_path):
    """Load and process JSON campaign file"""
    try:
        with open(campaign_path, 'r', encoding='utf-8') as f:
            campaign_data = json.load(f)
        
        print(f"Loaded JSON campaign: {campaign_path}")
        
        # JSON campaign can have multiple formats:
        # Format 1: Simple format with subject and content
        if 'subject' in campaign_data and 'content' in campaign_data:
            return {
                'subject': campaign_data['subject'],
                'content': campaign_data['content'],
                'from_name': campaign_data.get('from_name', 'Campaign System'),
                'content_type': campaign_data.get('content_type', 'html'),
                'metadata': campaign_data.get('metadata', {})
            }
        
        # Format 2: Multiple campaign variants
        elif 'campaigns' in campaign_data:
            # For now, use the first campaign
            if campaign_data['campaigns']:
                first_campaign = campaign_data['campaigns'][0]
                return {
                    'subject': first_campaign.get('subject', 'Campaign'),
                    'content': first_campaign.get('content', ''),
                    'from_name': first_campaign.get('from_name', 'Campaign System'),
                    'content_type': first_campaign.get('content_type', 'html'),
                    'metadata': campaign_data.get('metadata', {})
                }
        
        # Format 3: Direct content (backwards compatibility)
        elif isinstance(campaign_data, str):
            return {
                'subject': 'Campaign',
                'content': campaign_data,
                'from_name': 'Campaign System',
                'content_type': 'html',
                'metadata': {}
            }
        
        # Format 4: Template-based (if you use templates)
        elif 'template' in campaign_data:
            template_path = os.path.join('campaign-templates', campaign_data['template'])
            if os.path.exists(template_path):
                template_content = load_campaign_content(template_path)
                if template_content:
                    # Replace template variables
                    for key, value in campaign_data.get('variables', {}).items():
                        template_content = template_content.replace(f'{{{{{key}}}}}', str(value))
                    
                    return {
                        'subject': campaign_data.get('subject', 'Campaign'),
                        'content': template_content,
                        'from_name': campaign_data.get('from_name', 'Campaign System'),
                        'content_type': campaign_data.get('content_type', 'html'),
                        'metadata': campaign_data.get('metadata', {})
                    }
        
        print(f"Warning: Unknown JSON campaign format in {campaign_path}")
        return None
        
    except Exception as e:
        print(f"Error loading JSON campaign {campaign_path}: {str(e)}")
        return None

def extract_subject_from_content(content):
    """Extract subject line from campaign content"""
    try:
        if isinstance(content, dict):
            return content.get('subject', 'Campaign')
            
        lines = str(content).split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.lower().startswith('subject:'):
                return line.split(':', 1)[1].strip()
            elif line.lower().startswith('# '):  # Markdown heading
                return line[2:].strip()
        return None
    except:
        return None

def send_summary_alert(emailer, campaigns_count, sent_count, failed_count, campaign_results):
    """Send summary alert after all campaigns complete"""
    try:
        total_emails = sent_count + failed_count
        success_rate = (sent_count / max(1, total_emails)) * 100
        
        subject = f"Campaign Summary: {campaigns_count} campaigns, {total_emails} emails"
        
        body = f"""
Campaign Execution Summary
=========================

Campaigns Processed: {campaigns_count}
Total Emails: {total_emails}
Successful: {sent_count}
Failed: {failed_count}
Success Rate: {success_rate:.1f}%

Campaign Details:
"""
        
        for result in campaign_results:
            body += f"\n• {result['campaign_name']}: {result['sent']}/{result['total_recipients']} sent"
            if result['failed'] > 0:
                body += f" ({result['failed']} failed)"
        
        body += f"\n\nExecution completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        emailer.send_alert(subject, body)
        print("Summary alert sent")
        
    except Exception as e:
        print(f"Warning: Could not send summary alert: {e}")

def campaign_main(templates_root, contacts_root, scheduled_root, tracking_root, alerts_email, dry_run=False):
    """Main campaign execution function"""
    try:
        print(f"Starting campaign_main with dry_run={dry_run}")
        print(f"Templates: {templates_root}")
        print(f"Contacts: {contacts_root}")
        print(f"Scheduled: {scheduled_root}")
        print(f"Tracking: {tracking_root}")
        print(f"Alerts: {alerts_email}")
        
        os.makedirs(tracking_root, exist_ok=True)
        print("Created tracking directory")
        
        # Initialize contact parser
        contact_parser = ContactParser()
        print("ContactParser initialized")
        
        # Parse all contacts from the contacts directory
        all_contacts = contact_parser.parse_contacts_directory(contacts_root)
        print(f"Total contacts loaded: {len(all_contacts)}")
        
        if not all_contacts:
            print("Warning: No contacts found. Please check the contacts directory.")
            return
        
        # Save contacts to tracking directory for reference
        contacts_file = os.path.join(tracking_root, 'parsed_contacts.json')
        with open(contacts_file, 'w') as f:
            json.dump(all_contacts, f, indent=2, default=str)
        print(f"Contacts saved to: {contacts_file}")
        
        # Initialize enhanced email sender
        emailer = EmailSender(alerts_email=alerts_email, dry_run=dry_run)
        print("Enhanced EmailSender initialized successfully")
        
        # Initialize log file
        log_file = "dryrun.log" if dry_run else "campaign.log"
        with open(log_file, 'w') as f:
            f.write(f"Campaign log started - Dry run: {dry_run}\n")
            f.write(f"Total contacts loaded: {len(all_contacts)}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        # Process campaigns
        campaigns_processed = 0
        total_emails_sent = 0
        total_failures = 0
        campaign_results = []
        
        # Check if scheduled campaigns directory exists
        if not os.path.exists(scheduled_root):
            print(f"Warning: Scheduled campaigns directory does not exist: {scheduled_root}")
            return
        
        # Get list of campaign files
        campaign_files = [f for f in os.listdir(scheduled_root) 
                         if f.endswith(('.docx', '.txt', '.html', '.md', '.json'))]
        
        if not campaign_files:
            print("No campaign files found in scheduled directory")
            return
        
        print(f"Found {len(campaign_files)} campaign files to process")
        
        # Process each campaign
        for campaign_file in campaign_files:
            campaign_name = os.path.splitext(campaign_file)[0]
            campaign_path = os.path.join(scheduled_root, campaign_file)
            
            print(f"\n--- Processing Campaign: {campaign_name} ---")
            
            # Load campaign content
            campaign_content = load_campaign_content(campaign_path)
            
            if not campaign_content:
                print(f"Warning: Could not load content for {campaign_file}")
                continue
            
            # Handle different content types
            if isinstance(campaign_content, dict):
                subject = campaign_content.get('subject', f"Campaign: {campaign_name}")
                content = campaign_content.get('content', '')
                from_name = campaign_content.get('from_name', 'Campaign System')
            else:
                # Extract subject from content (look for Subject: line or use filename)
                subject = extract_subject_from_content(campaign_content) or f"Campaign: {campaign_name}"
                content = str(campaign_content)
                from_name = "Campaign System"
            
            # Add recipient IDs for tracking
            contacts_with_ids = []
            for i, contact in enumerate(all_contacts):
                contact_copy = contact.copy()
                contact_copy['recipient_id'] = f"{campaign_name}_{i+1}"
                contact_copy['campaign_id'] = campaign_name
                contacts_with_ids.append(contact_copy)
            
            # Send campaign using enhanced emailer
            try:
                campaign_result = emailer.send_campaign(
                    campaign_name=campaign_name,
                    subject=subject,
                    content=content,
                    recipients=contacts_with_ids,
                    from_name=from_name
                )
                
                campaigns_processed += 1
                total_emails_sent += campaign_result['sent']
                total_failures += campaign_result['failed']
                campaign_results.append(campaign_result)
                
                # Log campaign details
                with open(log_file, 'a') as f:
                    f.write(f"Campaign: {campaign_name}\n")
                    f.write(f"Recipients: {campaign_result['total_recipients']}\n")
                    f.write(f"Sent: {campaign_result['sent']}\n")
                    f.write(f"Failed: {campaign_result['failed']}\n")
                    f.write(f"Content source: {campaign_file}\n")
                    f.write(f"Subject: {subject}\n")
                    if dry_run:
                        f.write("Status: SIMULATED - no emails sent\n")
                    else:
                        f.write("Status: SENT\n")
                    f.write(f"Duration: {campaign_result.get('duration_seconds', 0):.2f}s\n")
                    f.write("\n")
                
                print(f"Campaign '{campaign_name}' completed:")
                print(f"   Sent: {campaign_result['sent']}")
                print(f"   Failed: {campaign_result['failed']}")
                
            except Exception as e:
                print(f"Error processing campaign '{campaign_name}': {str(e)}")
                with open(log_file, 'a') as f:
                    f.write(f"Campaign: {campaign_name}\n")
                    f.write(f"Status: ERROR - {str(e)}\n\n")
                continue
        
        # Final summary
        with open(log_file, 'a') as f:
            f.write("=== CAMPAIGN SUMMARY ===\n")
            f.write(f"Total campaigns processed: {campaigns_processed}\n")
            f.write(f"Total emails sent: {total_emails_sent}\n")
            f.write(f"Total failures: {total_failures}\n")
            if total_emails_sent + total_failures > 0:
                success_rate = (total_emails_sent / (total_emails_sent + total_failures)) * 100
                f.write(f"Success rate: {success_rate:.1f}%\n")
            f.write(f"Run mode: {'DRY-RUN' if dry_run else 'LIVE'}\n")
            f.write(f"Completed: {datetime.now().isoformat()}\n")
        
        print(f"\n=== FINAL SUMMARY ===")
        print(f"Campaigns processed: {campaigns_processed}")
        print(f"Total emails: {total_emails_sent + total_failures}")
        print(f"Successful: {total_emails_sent}")
        print(f"Failed: {total_failures}")
        if total_emails_sent + total_failures > 0:
            success_rate = (total_emails_sent / (total_emails_sent + total_failures)) * 100
            print(f"Success rate: {success_rate:.1f}%")
        print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
        
        # Send summary alert if not dry run and there are results
        if not dry_run and campaigns_processed > 0 and EMAIL_SENDER_AVAILABLE:
            send_summary_alert(emailer, campaigns_processed, total_emails_sent, total_failures, campaign_results)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()
        
        # Log error
        error_log = "error.log"
        with open(error_log, 'w') as f:
            f.write(f"ERROR: {str(e)}\n")
            f.write(traceback.format_exc())
        
        # Send error alert
        try:
            if not dry_run and EMAIL_SENDER_AVAILABLE:
                emailer = EmailSender(alerts_email=alerts_email, dry_run=False)
                emailer.send_alert(
                    "Campaign System Error",
                    f"Campaign execution failed with error:\n\n{str(e)}\n\nCheck logs for details."
                )
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    print("Script started successfully")
    print(f"Remote environment: {IS_REMOTE}")
    print(f"Available libraries: pandas={PANDAS_AVAILABLE}, docx={DOCX_AVAILABLE}, requests={REQUESTS_AVAILABLE}, email_sender={EMAIL_SENDER_AVAILABLE}")
    
    parser = argparse.ArgumentParser(description='Email Campaign System - Remote Optimized')
    parser.add_argument("--templates", required=True, help="Templates directory path")
    parser.add_argument("--contacts", required=True, help="Contacts directory path")
    parser.add_argument("--scheduled", required=True, help="Scheduled campaigns directory path")
    parser.add_argument("--tracking", required=True, help="Tracking directory path")
    parser.add_argument("--alerts", required=True, help="Alerts email address")
    parser.add_argument("--dry-run", action="store_true", help="Print emails instead of sending")
    parser.add_argument("--remote-only", action="store_true", help="Force remote-only mode")
    
    print("Parsing arguments...")
    args = parser.parse_args()
    
    # Override remote detection if specified
    if args.remote_only:
        globals()['IS_REMOTE'] = True
        print("Forced remote-only mode enabled")
    
    print(f"Arguments parsed successfully:")
    print(f"  --templates: {args.templates}")
    print(f"  --contacts: {args.contacts}")
    print(f"  --scheduled: {args.scheduled}")
    print(f"  --tracking: {args.tracking}")
    print(f"  --alerts: {args.alerts}")
    print(f"  --dry-run: {args.dry_run}")
    print(f"  --remote-only: {args.remote_only}")
    
    print("Calling campaign_main...")
    campaign_main(
        args.templates, 
        args.contacts, 
        args.scheduled, 
        args.tracking, 
        args.alerts,
        dry_run=args.dry_run
    )
    print("Script completed successfully")
