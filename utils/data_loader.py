import pandas as pd
import requests
from io import StringIO
import os

# Optional Google Sheets API support
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("Warning: gspread not available, using fallback CSV export method for Google Sheets")


def load_contacts(source, svc_account_json=None):
    """
    Load contacts from CSV, JSON, or Google Sheets URL (.url file).

    Args:
        source (str): Path to file (.csv, .json, .url)
        svc_account_json (dict, optional): Google service account JSON dict.
                                           If not provided, falls back to public CSV export.

    Returns:
        list of dicts: contacts
    """
    # ----------------- CSV -----------------
    if source.endswith(".csv"):
        return pd.read_csv(source).to_dict(orient="records")

    # ----------------- JSON -----------------
    elif source.endswith(".json"):
        return pd.read_json(source).to_dict(orient="records")

    # ----------------- Excel -----------------
    elif source.endswith((".xlsx", ".xls")):
        return pd.read_excel(source).to_dict(orient="records")

    # ----------------- Google Sheets via .url -----------------
    elif source.endswith(".url"):
        # Read the .url file
        with open(source, "r", encoding='utf-8') as f:
            content = f.read().strip()

        # Case 1: Plain URL
        if content.startswith("http"):
            sheet_url = content

        # Case 2: [InternetShortcut] style
        elif "URL=" in content:
            sheet_url = None
            for line in content.splitlines():
                if line.startswith("URL="):
                    sheet_url = line.split("=", 1)[1].strip()
                    break
            if not sheet_url:
                raise ValueError(f"No valid URL found in {source}")
        else:
            raise ValueError(f"Unsupported .url file format in {source}")

        # Extract Sheet ID
        try:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        except IndexError:
            raise ValueError(f"Invalid Google Sheets URL: {sheet_url}")

        # Extract gid if present
        gid = None
        if "gid=" in sheet_url:
            gid = sheet_url.split("gid=")[1].split("&")[0].split("#")[0]

        # ----------------- Use Google API if credentials provided -----------------
        if svc_account_json and GSPREAD_AVAILABLE:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(svc_account_json, scope)
            client = gspread.authorize(creds)

            # Pick correct worksheet
            if gid:
                worksheet = None
                for ws in client.open_by_key(sheet_id).worksheets():
                    if str(ws.id) == str(gid):
                        worksheet = ws
                        break
                if worksheet is None:
                    worksheet = client.open_by_key(sheet_id).sheet1
            else:
                worksheet = client.open_by_key(sheet_id).sheet1

            data = worksheet.get_all_records()

        # ----------------- Fallback: public CSV export -----------------
        else:
            export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            if gid:
                export_url += f"&gid={gid}"
            
            print(f"Fetching Google Sheets data from: {export_url}")
            resp = requests.get(export_url, timeout=30)
            resp.raise_for_status()
            
            if resp.status_code == 200:
                data = pd.read_csv(StringIO(resp.text)).to_dict(orient="records")
                print(f"Successfully loaded {len(data)} records from Google Sheets")
            else:
                raise ValueError(f"Failed to fetch Google Sheets data: HTTP {resp.status_code}")

        return data

    else:
        raise ValueError(f"Unsupported source: {source}")


def load_contacts_directory(directory_path, svc_account_json=None):
    """
    Load contacts from all supported files in a directory.
    This is the missing function that docx_parser.py was trying to import.

    Args:
        directory_path (str): Path to directory containing contact files
        svc_account_json (dict, optional): Google service account JSON dict

    Returns:
        list of dicts: all contacts from all files, with duplicates removed
    """
    all_contacts = []
    
    if not os.path.exists(directory_path):
        print(f"Warning: Directory does not exist: {directory_path}")
        return all_contacts
    
    print(f"Loading contacts from directory: {directory_path}")
    
    # Supported file extensions
    supported_extensions = ['.csv', '.xlsx', '.xls', '.json', '.url']
    
    # Process each file in the directory
    for filename in sorted(os.listdir(directory_path)):
        if filename.startswith('.'):
            continue
            
        file_path = os.path.join(directory_path, filename)
        if not os.path.isfile(file_path):
            continue
        
        # Check if file has supported extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in supported_extensions:
            print(f"Skipping unsupported file: {filename}")
            continue
        
        try:
            print(f"Processing: {filename}")
            file_contacts = load_contacts(file_path, svc_account_json)
            
            if file_contacts:
                # Add source information to each contact
                for contact in file_contacts:
                    if isinstance(contact, dict):
                        contact['source'] = file_path
                        contact['source_file'] = filename
                
                all_contacts.extend(file_contacts)
                print(f"Loaded {len(file_contacts)} contacts from {filename}")
            else:
                print(f"No contacts found in {filename}")
                
        except Exception as e:
            print(f"Error loading {filename}: {str(e)}")
            continue
    
    # Remove duplicates based on email address
    print(f"Removing duplicates from {len(all_contacts)} total contacts...")
    
    unique_contacts = {}
    for contact in all_contacts:
        if not isinstance(contact, dict):
            continue
            
        email = contact.get('email', '').strip().lower()
        if not email:
            continue
            
        if email not in unique_contacts:
            unique_contacts[email] = contact
        else:
            # Merge additional information from duplicate contact
            existing = unique_contacts[email]
            for key, value in contact.items():
                if key not in existing and value:
                    existing[key] = value
    
    final_contacts = list(unique_contacts.values())
    
    print(f"Final result: {len(final_contacts)} unique contacts loaded from {directory_path}")
    
    return final_contacts


def validate_contact_data(contacts):
    """
    Validate contact data and return statistics
    
    Args:
        contacts (list): List of contact dictionaries
        
    Returns:
        dict: Validation statistics
    """
    stats = {
        'total_contacts': len(contacts),
        'valid_emails': 0,
        'missing_emails': 0,
        'missing_names': 0,
        'unique_domains': set(),
        'invalid_emails': []
    }
    
    import re
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    
    for contact in contacts:
        if not isinstance(contact, dict):
            continue
            
        email = contact.get('email', '').strip()
        name = contact.get('name', '').strip()
        
        # Validate email
        if email:
            if re.match(email_pattern, email):
                stats['valid_emails'] += 1
                domain = email.split('@')[1].lower()
                stats['unique_domains'].add(domain)
            else:
                stats['invalid_emails'].append(email)
        else:
            stats['missing_emails'] += 1
        
        # Check for name
        if not name:
            stats['missing_names'] += 1
    
    stats['unique_domains'] = len(stats['unique_domains'])
    
    return stats


# Backward compatibility function
def load_contacts_from_url(url, svc_account_json=None):
    """
    Load contacts directly from a Google Sheets URL (backward compatibility)
    """
    import tempfile
    
    # Create a temporary .url file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.url', delete=False) as temp_file:
        temp_file.write(url)
        temp_path = temp_file.name
    
    try:
        contacts = load_contacts(temp_path, svc_account_json)
        return contacts
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    # Test the functions if run directly
    import sys
    
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
        
        if os.path.isdir(source_path):
            print(f"Testing directory loading: {source_path}")
            contacts = load_contacts_directory(source_path)
        else:
            print(f"Testing file loading: {source_path}")
            contacts = load_contacts(source_path)
        
        print(f"\nLoaded {len(contacts)} contacts")
        
        # Show validation stats
        stats = validate_contact_data(contacts)
        print(f"\nValidation Results:")
        print(f"  Valid emails: {stats['valid_emails']}")
        print(f"  Missing emails: {stats['missing_emails']}")
        print(f"  Missing names: {stats['missing_names']}")
        print(f"  Unique domains: {stats['unique_domains']}")
        print(f"  Invalid emails: {len(stats['invalid_emails'])}")
        
        # Show sample contacts
        if contacts:
            print(f"\nSample contacts:")
            for i, contact in enumerate(contacts[:5]):
                name = contact.get('name', 'N/A')
                email = contact.get('email', 'N/A')
                source = contact.get('source_file', 'Unknown')
                print(f"  {i+1}. {name} <{email}> (from {source})")
    else:
        print("Usage: python data_loader.py <file_or_directory_path>")
