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
        
        # Initialize log file for GitHub Actions summary
        log_file = "dryrun.log" if dry_run else "campaign.log"
        with open(log_file, 'w') as f:
            f.write(f"Campaign log started - Dry run: {dry_run}\n")
        
        emailer = EmailSender(alerts_email=alerts_email, dry_run=dry_run)
        print("EmailSender initialized successfully")
        
        # Example campaign processing (replace with your actual logic)
        campaigns_processed = 0
        total_recipients = 0
        
        # Simulate finding and processing campaigns
        if os.path.exists(scheduled_root):
            for campaign_file in os.listdir(scheduled_root):
                if campaign_file.endswith('.docx') or campaign_file.endswith('.txt'):
                    campaign_name = os.path.splitext(campaign_file)[0]
                    recipients_count = 125  # This should come from your actual contact counting logic
                    
                    campaigns_processed += 1
                    total_recipients += recipients_count
                    
                    # Log campaign details for GitHub Actions summary
                    with open(log_file, 'a') as f:
                        f.write(f"Campaign: {campaign_name}\n")
                        f.write(f"Recipients: {recipients_count}\n")
                        if dry_run:
                            f.write("Status: SIMULATED - no emails sent\n")
                        else:
                            f.write("Status: SENT\n")
                        f.write("\n")
                    
                    print(f"Processed campaign: {campaign_name} ({recipients_count} recipients)")
        
        # Summary logging
        with open(log_file, 'a') as f:
            f.write(f"Total campaigns processed: {campaigns_processed}\n")
            f.write(f"Total recipients: {total_recipients}\n")
            f.write(f"Run mode: {'DRY-RUN' if dry_run else 'LIVE'}\n")
        
        print(f"Campaign completed successfully - {campaigns_processed} campaigns, {total_recipients} recipients")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()
        
        # Log error for GitHub Actions summary
        error_log = "error.log"
        with open(error_log, 'w') as f:
            f.write(f"ERROR: {str(e)}\n")
            f.write(traceback.format_exc())
        
        sys.exit(1)

if __name__ == "__main__":
    print("Script started successfully")
    
    parser = argparse.ArgumentParser(description='Email Campaign System')
    parser.add_argument("--templates", required=True, help="Templates directory path")
    parser.add_argument("--contacts", required=True, help="Contacts directory path")
    parser.add_argument("--scheduled", required=True, help="Scheduled campaigns directory path")
    parser.add_argument("--tracking", required=True, help="Tracking directory path")
    parser.add_argument("--alerts", required=True, help="Alerts email address")
    parser.add_argument("--dry-run", action="store_true", help="Print emails instead of sending")
    
    print("Parsing arguments...")
    args = parser.parse_args()
    
    print(f"Arguments parsed successfully:")
    print(f"  --templates: {args.templates}")
    print(f"  --contacts: {args.contacts}")
    print(f"  --scheduled: {args.scheduled}")
    print(f"  --tracking: {args.tracking}")
    print(f"  --alerts: {args.alerts}")
    print(f"  --dry-run: {args.dry_run}")
    
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
