# add to imports
import argparse

# inside campaign_main
def campaign_main(templates_root, contacts_root, scheduled_root, tracking_root, alerts_email, dry_run=False):
    os.makedirs(tracking_root, exist_ok=True)
    emailer = EmailSender(alerts_email=alerts_email, dry_run=dry_run)

    # ... (rest unchanged, just pass dry_run into EmailSender)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", required=True)
    parser.add_argument("--contacts", required=True)
    parser.add_argument("--scheduled", required=True)
    parser.add_argument("--tracking", required=True)
    parser.add_argument("--alerts", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Print emails instead of sending")
    args = parser.parse_args()

    campaign_main(
        args.templates, args.contacts, args.scheduled, args.tracking, args.alerts,
        dry_run=args.dry_run
    )
