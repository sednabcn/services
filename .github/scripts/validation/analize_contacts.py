#!/usr/bin/env python3
"""
Enhanced contact source analysis script.
Analyzes contact data from multiple sources and generates comprehensive reports.
"""

import sys
import os
import json
import glob
from datetime import datetime
from pathlib import Path
import pandas as pd


def load_csv_contacts(contacts_dir):
    """Load contacts from CSV files."""
    contacts = []
    csv_files = glob.glob(os.path.join(contacts_dir, '*.csv'))
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            # Clean column names (strip whitespace)
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                contact = row.to_dict()
                contact['source'] = os.path.basename(csv_file)
                contact['source_type'] = 'csv'
                contacts.append(contact)
                
            print(f"✓ Loaded {len(df)} contacts from {csv_file}")
            
        except Exception as e:
            print(f"✗ Error loading CSV {csv_file}: {e}")
            
    return contacts


def load_excel_contacts(contacts_dir):
    """Load contacts from Excel files."""
    contacts = []
    excel_files = glob.glob(os.path.join(contacts_dir, '*.xlsx')) + \
                  glob.glob(os.path.join(contacts_dir, '*.xls'))
    
    for excel_file in excel_files:
        try:
            df = pd.read_excel(excel_file)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                contact = row.to_dict()
                contact['source'] = os.path.basename(excel_file)
                contact['source_type'] = 'excel'
                contacts.append(contact)
                
            print(f"✓ Loaded {len(df)} contacts from {excel_file}")
            
        except Exception as e:
            print(f"✗ Error loading Excel {excel_file}: {e}")
            
    return contacts


def load_json_contacts(contacts_dir):
    """Load contacts from JSON files."""
    contacts = []
    json_files = glob.glob(os.path.join(contacts_dir, '*.json'))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            if isinstance(data, list):
                contact_list = data
            elif isinstance(data, dict) and 'contacts' in data:
                contact_list = data['contacts']
            else:
                contact_list = [data]
                
            for contact in contact_list:
                if isinstance(contact, dict):
                    contact['source'] = os.path.basename(json_file)
                    contact['source_type'] = 'json'
                    contacts.append(contact)
                    
            print(f"✓ Loaded {len(contact_list)} contacts from {json_file}")
            
        except Exception as e:
            print(f"✗ Error loading JSON {json_file}: {e}")
            
    return contacts


def load_google_sheets_urls(contacts_dir):
    """Load Google Sheets URLs from .url files."""
    url_files = []
    url_file_paths = glob.glob(os.path.join(contacts_dir, '*.url'))
    
    for url_file in url_file_paths:
        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            url_files.append({
                'file': os.path.basename(url_file),
                'url': content,
                'source_type': 'google_sheets'
            })
            
            print(f"✓ Found Google Sheets URL in {url_file}")
            
        except Exception as e:
            print(f"✗ Error reading URL file {url_file}: {e}")
            
    return url_files


def analyze_domains(contacts):
    """Analyze email domains in contact list."""
    domains = {}
    invalid_emails = 0
    
    for contact in contacts:
        email = str(contact.get('email', '')).lower().strip()
        if '@' in email and '.' in email:
            try:
                domain = email.split('@')[-1]
                domains[domain] = domains.get(domain, 0) + 1
            except:
                invalid_emails += 1
        else:
            invalid_emails += 1
            
    return domains, invalid_emails


def analyze_contact_fields(contacts):
    """Analyze available fields in contact data."""
    all_fields = set()
    field_coverage = {}
    
    for contact in contacts:
        for field in contact.keys():
            all_fields.add(field)
            if field not in field_coverage:
                field_coverage[field] = 0
            if contact.get(field) is not None and str(contact.get(field)).strip():
                field_coverage[field] += 1
                
    # Calculate coverage percentages
    total_contacts = len(contacts)
    field_stats = {}
    
    for field in all_fields:
        coverage_count = field_coverage.get(field, 0)
        coverage_percentage = (coverage_count / total_contacts * 100) if total_contacts > 0 else 0
        field_stats[field] = {
            'count': coverage_count,
            'percentage': round(coverage_percentage, 2)
        }
        
    return field_stats


def generate_contact_samples(contacts, count=5):
    """Generate sample contacts for preview."""
    samples = []
    
    for i, contact in enumerate(contacts[:count]):
        sample = {}
        # Only include non-empty fields for sample
        for key, value in contact.items():
            if value is not None and str(value).strip():
                sample[key] = str(value)[:50]  # Truncate long values
        samples.append(sample)
        
    return samples


def load_contacts_with_professional_loader(contacts_dir):
    """Try to use professional data_loader if available."""
    try:
        sys.path.insert(0, 'utils')
        from data_loader import load_contacts
        
        print("Using professional data_loader.py")
        contacts = load_contacts(contacts_dir)
        return contacts, 'professional_data_loader.py'
        
    except ImportError:
        print("Professional data_loader not available, using enhanced fallback")
        return None, 'enhanced_fallback_loader'


def main():
    """Main contact analysis function."""
    contacts_dir = os.environ.get('CONTACTS_DIR', 'contacts')
    contact_source_filter = os.environ.get('CONTACT_SOURCE', '')
    
    print(f"Enhanced contact source analysis for: {contacts_dir}")
    print(f"Contact source filter: {contact_source_filter or 'all_sources'}")
    
    # Initialize analysis structure
    analysis = {
        'total_contacts': 0,
        'sources_breakdown': {},
        'domain_breakdown': {},
        'field_analysis': {},
        'top_domains': [],
        'sample_contacts': [],
        'google_sheets_urls': [],
        'loaded_with': 'enhanced_system',
        'analysis_timestamp': datetime.now().isoformat(),
        'contact_source_filter': contact_source_filter or 'all_sources',
        'data_quality': {},
        'recommendations': []
    }
    
    contacts = []
    
    # Try professional data loader first
    professional_contacts, loader_type = load_contacts_with_professional_loader(contacts_dir)
    analysis['loaded_with'] = loader_type
    
    if professional_contacts:
        contacts = professional_contacts
    else:
        # Use enhanced fallback loading
        print("Using enhanced multi-source fallback loader...")
        
        if os.path.exists(contacts_dir):
            # Load from different sources
            csv_contacts = load_csv_contacts(contacts_dir)
            excel_contacts = load_excel_contacts(contacts_dir)
            json_contacts = load_json_contacts(contacts_dir)
            
            contacts = csv_contacts + excel_contacts + json_contacts
            
            # Also detect Google Sheets URLs
            analysis['google_sheets_urls'] = load_google_sheets_urls(contacts_dir)
            
        else:
            print(f"Contacts directory not found: {contacts_dir}")
            analysis['error'] = f"Contacts directory not found: {contacts_dir}"
    
    # Apply contact source filter if specified
    if contact_source_filter and contacts:
        filtered_contacts = []
        for contact in contacts:
            if contact.get('source', '').startswith(contact_source_filter):
                filtered_contacts.append(contact)
        
        if len(filtered_contacts) != len(contacts):
            print(f"Applied source filter '{contact_source_filter}': {len(filtered_contacts)}/{len(contacts)} contacts")
            contacts = filtered_contacts
    
    # Perform analysis
    contact_count = len(contacts)
    analysis['total_contacts'] = contact_count
    
    print(f"Total contacts loaded: {contact_count}")
    
    if contacts:
        # Source breakdown
        sources = {}
        for contact in contacts:
            source = contact.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        analysis['sources_breakdown'] = sources
        
        # Domain analysis
        domains, invalid_emails = analyze_domains(contacts)
        analysis['domain_breakdown'] = domains
        analysis['data_quality']['invalid_emails'] = invalid_emails
        analysis['top_domains'] = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Field analysis
        analysis['field_analysis'] = analyze_contact_fields(contacts)
        
        # Generate samples
        analysis['sample_contacts'] = generate_contact_samples(contacts)
        
        # Data quality assessment
        total_emails = len([c for c in contacts if c.get('email')])
        analysis['data_quality'].update({
            'total_records': contact_count,
            'records_with_email': total_emails,
            'email_coverage_percentage': round((total_emails / contact_count * 100) if contact_count > 0 else 0, 2),
            'invalid_email_percentage': round((invalid_emails / contact_count * 100) if contact_count > 0 else 0, 2),
            'unique_domains': len(domains),
            'unique_sources': len(sources)
        })
        
        # Generate recommendations
        recommendations = []
        if invalid_emails > (contact_count * 0.1):  # More than 10% invalid emails
            recommendations.append("High invalid email rate detected - consider email validation")
        
        if len(analysis['field_analysis']) < 3:
            recommendations.append("Limited contact fields available - consider enriching contact data")
            
        if len(sources) == 1:
            recommendations.append("Single data source detected - consider diversifying contact sources")
            
        analysis['recommendations'] = recommendations
        
        print(f"Analysis completed:")
        print(f"  - Sources: {len(sources)}")
        print(f"  - Domains: {len(domains)}")
        print(f"  - Email coverage: {analysis['data_quality']['email_coverage_percentage']}%")
        print(f"  - Data quality issues: {len(recommendations)}")
        
    else:
        print("No contacts loaded")
        analysis['error'] = 'No contacts could be loaded'
    
    # Save analysis to file
    with open('contact_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, default=str, ensure_ascii=False)
    
    # Output for GitHub Actions
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/stdout'), 'a') as f:
        f.write(f'count={contact_count}\n')
    
    print(f"Contact analysis saved to contact_analysis.json")
    
    if contact_count == 0:
        print("::warning::No contacts loaded - check contact directory and files")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
