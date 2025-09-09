# add to imports
import argparse
import os
import sys
import traceback
from email_sender import EmailSender

# inside campaign_main
def campaign_main(templates_root, contacts_root, scheduled_root, tracking_root, alerts_email, dry_run=False):
    try:
        print(f"Starting campaign_main with dry_run={dry_run}")
        print(f"Templates: {templates_root}")
        print(f"Contacts: {contacts_root}")
        print(f"Scheduled: {scheduled_root}")
        print(f"Tracking: {tracking_root}")
        print(f"Alerts: {alerts_email}")
        
        os.makedirs(tracking_root, exist_ok=True)
        print("Created tracking directory")
        
        emailer = EmailSender(alerts_email=alerts_email, dry_run=dry_run)
        print("EmailSender initialized successfully")
        
        # ... (rest unchanged, just pass dry_run into EmailSender)
        print("Campaign completed successfully")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("Script started successfully")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", required=True)
    parser.add_argument("--contacts", required=True)
    parser.add_argument("--scheduled", required=True)
    parser.add_argument("--tracking", required=True)
    parser.add_argument("--alerts", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Print emails instead of sending")
    
    print("Parsing arguments...")
    args = parser.parse_args()
    
    print("Arguments parsed successfully, calling campaign_main...")
    campaign_main(
        args.templates, args.contacts, args.scheduled, args.tracking, args.alerts,
        dry_run=args.dry_run
    )
    print("Script completed successfully")
