import os
import json
import argparse
from pathlib import Path
from datetime import datetime

def load_tracking(tracking_dir, campaign_name):
    """Load tracking JSON for a specific campaign."""
    tracking_file = Path(tracking_dir) / f"{campaign_name}_tracking.json"
    if not tracking_file.exists():
        return []
    with open(tracking_file, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_summary(campaign_json_path, tracking_dir="tracking", dry_run=True, sample_count=5):
    """Generate markdown summary for a campaign."""
    campaign_path = Path(campaign_json_path)
    if not campaign_path.exists():
        raise FileNotFoundError(f"Campaign file not found: {campaign_json_path}")

    with open(campaign_path, "r", encoding="utf-8") as f:
        campaign = json.load(f)

    campaign_name = campaign.get("name", "Unknown Campaign")
    contacts_count = 0
    summary_lines = []

    # Load tracking data
    tracking_data = load_tracking(tracking_dir, campaign_name)
    contacts_count = len(tracking_data)

    successful = sum(1 for c in tracking_data if c.get("status") == "Sent")
    failed = sum(1 for c in tracking_data if c.get("status") == "Failed")
    pending = sum(1 for c in tracking_data if c.get("status") not in ["Sent", "Failed"])

    summary_lines.append(f"## 📋 Campaign Summary: {campaign_name}")
    summary_lines.append(f"- **Sector:** {campaign.get('sector','N/A')}")
    summary_lines.append(f"- **Mode:** {'DRY-RUN' if dry_run else 'LIVE'}")
    summary_lines.append(f"- **Total Contacts:** {contacts_count}")
    summary_lines.append(f"- **Successful:** {successful}")
    summary_lines.append(f"- **Failed:** {failed}")
    summary_lines.append(f"- **Pending / Follow-up:** {pending}")
    summary_lines.append(f"- **Timestamp:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    summary_lines.append("")

    # Sample recipients
    if tracking_data and sample_count > 0:
        sample = tracking_data[:sample_count]
        summary_lines.append(f"### 👥 Sample Recipients (First {len(sample)})")
        summary_lines.append("```json")
        summary_lines.append(json.dumps(sample, indent=2))
        summary_lines.append("```")
        summary_lines.append("")

    # Default table for full contacts
    if tracking_data:
        summary_lines.append("### 📊 Tracking Table")
        summary_lines.append("| Email | Status | Follow-up | Notes |")
        summary_lines.append("|-------|--------|-----------|-------|")
        for entry in tracking_data:
            summary_lines.append(
                f"| {entry.get('email','N/A')} | {entry.get('status','N/A')} | "
                f"{entry.get('follow_up','')} | {entry.get('notes','')} |"
            )

    return "\n".join(summary_lines)

def main():
    parser = argparse.ArgumentParser(description="Generate campaign summary (dry-run / live)")
    parser.add_argument("--campaign", required=True, help="Path to scheduled campaign JSON")
    parser.add_argument("--tracking-dir", default="tracking", help="Directory storing tracking JSON")
    parser.add_argument("--dry-run", action="store_true", help="Set if dry-run mode")
    parser.add_argument("--sample-count", type=int, default=5, help="Number of sample recipients to display")
    parser.add_argument("--output", help="File to save the summary (optional)")

    args = parser.parse_args()
    summary_md = generate_summary(
        campaign_json_path=args.campaign,
        tracking_dir=args.tracking_dir,
        dry_run=args.dry_run,
        sample_count=args.sample_count,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary_md)
        print(f"Summary saved to {args.output}")
    else:
        print(summary_md)

if __name__ == "__main__":
    main()
