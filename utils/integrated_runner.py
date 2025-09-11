#!/usr/bin/env python3
"""
utils/integrated_runner.py - Complete integration orchestrator for email campaign system
This script coordinates data_loader.py, docx_parser.py, and generate_summary.py
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd, description="", timeout=300):
    """Run a command and capture output with proper error handling"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        print(f"Exit code: {result.returncode}")
        
        # Always show stdout if there is any
        if result.stdout:
            print(f"\nSTDOUT:")
            print(result.stdout)
        
        # Show stderr if there is any
        if result.stderr:
            print(f"\nSTDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        if success:
            print(f"✅ {description} completed successfully")
        else:
            print(f"❌ {description} failed with exit code {result.returncode}")
        
        return success, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        print(f"⏰ ERROR: {description} timed out after {timeout} seconds")
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        print(f"💥 ERROR: {description} failed with exception: {str(e)}")
        return False, "", str(e)


def load_contacts_unified(contacts_dir):
    """Load contacts using data_loader.py with comprehensive error handling"""
    contacts = []
    
    if not os.path.exists(contacts_dir):
        print(f"❌ Contacts directory not found: {contacts_dir}")
        return contacts
    
    # Check if data_loader.py exists
    if not os.path.exists('data_loader.py'):
        print("❌ data_loader.py not found - cannot load contacts")
        return contacts
    
    print(f"🔍 Loading contacts from directory: {contacts_dir}")
    
    # Import data_loader dynamically to handle import errors
    sys.path.insert(0, '.')
    try:
        from data_loader import load_contacts
        print("✅ Successfully imported data_loader")
    except ImportError as e:
        print(f"❌ Failed to import data_loader: {e}")
        return contacts
    except Exception as e:
        print(f"❌ Unexpected error importing data_loader: {e}")
        return contacts
    
    # Process each file in contacts directory
    supported_extensions = ['.csv', '.xlsx', '.url', '.json', '.docx', '.txt']
    processed_files = 0
    
    for filename in sorted(os.listdir(contacts_dir)):
        if filename.startswith('.'):
            continue
            
        file_path = os.path.join(contacts_dir, filename)
        if not os.path.isfile(file_path):
            continue
        
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in supported_extensions:
            print(f"⏭️  Skipping unsupported file: {filename}")
            continue
        
        try:
            print(f"📄 Processing: {filename}")
            file_contacts = load_contacts(file_path)
            
            if file_contacts:
                print(f"✅ Loaded {len(file_contacts)} contacts from {filename}")
                contacts.extend(file_contacts)
                processed_files += 1
            else:
                print(f"⚠️  No contacts found in {filename}")
                
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            continue
    
    # Remove duplicates by email
    print(f"\n📊 Processing results:")
    print(f"   Files processed: {processed_files}")
    print(f"   Raw contacts loaded: {len(contacts)}")
    
    unique_contacts = {}
    for contact in contacts:
        email = contact.get('email', '').lower().strip()
        if email and email not in unique_contacts:
            unique_contacts[email] = contact
        elif email:
            # Merge additional info from duplicate
            existing = unique_contacts[email]
            for key, value in contact.items():
                if key not in existing and value:
                    existing[key] = value
    
    final_contacts = list(unique_contacts.values())
    print(f"   Unique contacts: {len(final_contacts)}")
    
    # Show sample contacts
    if final_contacts:
        print(f"\n📋 Sample contacts:")
        for i, contact in enumerate(final_contacts[:5]):
            name = contact.get('name', 'N/A')
            email = contact.get('email', 'N/A')
            source = contact.get('source', 'Unknown')
            source_file = os.path.basename(source) if source != 'Unknown' else 'Unknown'
            print(f"   {i+1}. {name} <{email}> (from {source_file})")
        
        if len(final_contacts) > 5:
            print(f"   ... and {len(final_contacts) - 5} more contacts")
    
    return final_contacts


def validate_setup(args):
    """Validate that all required directories and files exist"""
    issues = []
    warnings = []
    
    print(f"\n🔍 Validating system setup...")
    
    # Check directories
    for dir_name, dir_path in [
        ("contacts", args.contacts),
        ("scheduled", args.scheduled),
        ("tracking", args.tracking)
    ]:
        if not os.path.exists(dir_path):
            issues.append(f"Missing {dir_name} directory: {dir_path}")
        else:
            print(f"✅ Found {dir_name} directory: {dir_path}")
    
    # Check templates directory (optional)
    if args.templates and not os.path.exists(args.templates):
        warnings.append(f"Templates directory not found: {args.templates}")
    elif args.templates:
        print(f"✅ Found templates directory: {args.templates}")
    
    # Check required Python files
    required_files = ['data_loader.py', 'docx_parser.py', 'generate_summary.py']
    for file_name in required_files:
        if not os.path.exists(file_name):
            issues.append(f"Missing required file: {file_name}")
        else:
            print(f"✅ Found required file: {file_name}")
    
    # Check contacts directory has files
    if os.path.exists(args.contacts):
        contact_files = [f for f in os.listdir(args.contacts) 
                        if f.endswith(('.csv', '.xlsx', '.url', '.docx', '.txt', '.json'))]
        if not contact_files:
            warnings.append(f"No contact files found in {args.contacts}")
        else:
            print(f"✅ Found {len(contact_files)} contact files in {args.contacts}")
    
    # Check scheduled campaigns
    if os.path.exists(args.scheduled):
        campaign_files = [f for f in os.listdir(args.scheduled)
                         if f.endswith(('.txt', '.html', '.md', '.json', '.docx'))]
        if not campaign_files:
            warnings.append(f"No campaign files found in {args.scheduled}")
        else:
            print(f"✅ Found {len(campaign_files)} campaign files in {args.scheduled}")
    
    # Check Python dependencies
    try:
        import requests
        print("✅ requests library available")
    except ImportError:
        warnings.append("requests library not available - Google Sheets URLs may not work")
    
    try:
        import pandas
        print("✅ pandas library available")
    except ImportError:
        warnings.append("pandas library not available - Excel files may not work optimally")
    
    if warnings:
        print(f"\n⚠️  Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
    
    return issues, warnings


def save_execution_metadata(args, contacts_count, tracking_dir):
    """Save execution metadata for debugging and reporting"""
    metadata = {
        'execution_time': datetime.now().isoformat(),
        'mode': 'dry-run' if args.dry_run else 'live',
        'contacts_loaded': contacts_count,
        'directories': {
            'contacts': args.contacts,
            'scheduled': args.scheduled,
            'tracking': args.tracking,
            'templates': args.templates
        },
        'alerts_email': args.alerts,
        'system_info': {
            'python_version': sys.version,
            'working_directory': os.getcwd(),
            'environment': 'github-actions' if os.getenv('GITHUB_ACTIONS') else 'local'
        }
    }
    
    metadata_file = os.path.join(tracking_dir, 'execution_metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"📝 Execution metadata saved to: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(description='Integrated Email Campaign System Orchestrator')
    parser.add_argument("--contacts", default="contacts", help="Contacts directory")
    parser.add_argument("--scheduled", default="scheduled-campaigns", help="Scheduled campaigns directory") 
    parser.add_argument("--tracking", default="tracking", help="Tracking directory")
    parser.add_argument("--templates", default="campaign-templates", help="Templates directory")
    parser.add_argument("--alerts", required=True, help="Alerts email address")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--skip-validation", action="store_true", help="Skip initial validation")
    parser.add_argument("--contacts-only", action="store_true", help="Only load and validate contacts")
    parser.add_argument("--summary-only", action="store_true", help="Only generate summary from existing logs")
    parser.add_argument("--force-continue", action="store_true", help="Continue even if validation fails")
    
    args = parser.parse_args()
    
    print("="*80)
    print("INTEGRATED EMAIL CAMPAIGN SYSTEM")
    print("="*80)
    print(f"Start time: {datetime.now()}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"Contacts dir: {args.contacts}")
    print(f"Scheduled dir: {args.scheduled}")
    print(f"Tracking dir: {args.tracking}")
    print(f"Templates dir: {args.templates}")
    print(f"Alerts email: {args.alerts}")
    
    # Create required directories
    os.makedirs(args.tracking, exist_ok=True)
    print(f"Tracking directory ready: {args.tracking}")
    
    # Step 1: System Validation
    if not args.skip_validation:
        issues, warnings = validate_setup(args)
        
        if issues:
            print(f"\nCRITICAL VALIDATION ISSUES:")
            for issue in issues:
                print(f"  - {issue}")
            
            if not args.force_continue:
                print(f"\nAborting due to validation issues.")
                print("Use --force-continue to proceed anyway, or --skip-validation to skip checks.")
                return 1
            else:
                print(f"\nForcing continuation despite validation issues...")
    
    # Step 2: Contact Loading
    print(f"\n" + "="*80)
    print("STEP 1: CONTACT LOADING")
    print("="*80)
    
    contacts = load_contacts_unified(args.contacts)
    
    if contacts:
        print(f"Successfully loaded {len(contacts)} unique contacts")
        
        # Save contacts for campaign processor
        contacts_file = os.path.join(args.tracking, 'loaded_contacts.json')
        with open(contacts_file, 'w') as f:
            json.dump(contacts, f, indent=2, default=str)
        print(f"Contacts saved to: {contacts_file}")
        
        # Save execution metadata
        save_execution_metadata(args, len(contacts), args.tracking)
        
        if args.contacts_only:
            print(f"\nCONTACTS-ONLY MODE COMPLETE")
            print(f"Result: {len(contacts)} contacts loaded and saved")
            return 0
            
    else:
        print("WARNING: No contacts could be loaded")
        if args.contacts_only:
            print("CONTACTS-ONLY MODE FAILED: No contacts found")
            return 1
        print("Continuing with campaign processing (may fail without contacts)")
    
    # Step 3: Campaign Processing
    if not args.summary_only:
        print(f"\n" + "="*80)
        print("STEP 2: CAMPAIGN PROCESSING")
        print("="*80)
        
        # Build docx_parser command
        cmd = [
            'python', 'docx_parser.py',
            '--contacts', args.contacts,
            '--scheduled', args.scheduled, 
            '--tracking', args.tracking,
            '--templates', args.templates,
            '--alerts', args.alerts
        ]
        
        if args.dry_run:
            cmd.append('--dry-run')
        
        success, stdout, stderr = run_command(cmd, "Campaign Processing", timeout=600)
        
        if not success:
            print("Campaign processing encountered issues, but continuing to summary generation")
    
    # Step 4: Summary Generation
    print(f"\n" + "="*80)
    print("STEP 3: SUMMARY GENERATION")
    print("="*80)
    
    # Determine log file
    log_files = []
    if args.dry_run:
        log_files = ["dryrun.log", "campaign_execution.log", "campaign.log"]
    else:
        log_files = ["campaign_execution.log", "campaign.log", "dryrun.log"]
    
    log_file = None
    for lf in log_files:
        if os.path.exists(lf):
            log_file = lf
            break
    
    if log_file:
        print(f"Using log file: {log_file}")
        
        summary_cmd = [
            'python', 'generate_summary.py',
            '--log-file', log_file,
            '--mode', 'dry-run' if args.dry_run else 'live',
            '--contacts-dir', args.contacts,
            '--show-contacts',
            '--max-contacts-display', '10'
        ]
        
        # Set output file for summary
        summary_output = os.path.join(args.tracking, 'campaign_summary.md')
        summary_cmd.extend(['--output-summary', summary_output])
        
        success, stdout, stderr = run_command(summary_cmd, "Summary Generation", timeout=300)
        
        if success and os.path.exists(summary_output):
            print(f"Summary generated successfully: {summary_output}")
            
            # Also output summary to console
            if stdout:
                print(f"\nSUMMARY PREVIEW:")
                print("-" * 60)
                print(stdout[:1000] + "..." if len(stdout) > 1000 else stdout)
                print("-" * 60)
        else:
            print("Summary generation encountered issues")
    else:
        print(f"No log file found for summary generation")
        print(f"Checked for: {', '.join(log_files)}")
    
    # Step 5: Final Status Report
    print(f"\n" + "="*80)
    print("EXECUTION COMPLETE")
    print("="*80)
    
    final_status = "SUCCESS"
    
    # Check results
    if contacts:
        print(f"Contacts loaded: {len(contacts)}")
    else:
        print(f"Contacts loaded: 0 (WARNING)")
        final_status = "PARTIAL"
    
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    
    # List generated files
    if os.path.exists(args.tracking):
        tracking_files = [f for f in os.listdir(args.tracking) if os.path.isfile(os.path.join(args.tracking, f))]
        if tracking_files:
            print(f"\nGenerated files in {args.tracking}:")
            for file in tracking_files:
                file_path = os.path.join(args.tracking, file)
                size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                print(f"  - {file} ({size:,} bytes)")
        else:
            print(f"No files generated in {args.tracking}")
            final_status = "ISSUES"
    
    # Check for log files in current directory
    log_files_found = []
    for lf in ["campaign_execution.log", "dryrun.log", "campaign.log", "error.log"]:
        if os.path.exists(lf):
            size = os.path.getsize(lf)
            log_files_found.append(f"  - {lf} ({size:,} bytes)")
    
    if log_files_found:
        print(f"\nLog files generated:")
        for lf in log_files_found:
            print(lf)
    
    print(f"\nFinal Status: {final_status}")
    print(f"Completed: {datetime.now()}")
    
    return 0 if final_status in ["SUCCESS", "PARTIAL"] else 1


if __name__ == "__main__":
    sys.exit(main())
