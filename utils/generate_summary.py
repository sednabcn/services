#!/usr/bin/env python3
"""
generate_summary.py

Generates a markdown summary for email campaigns (DRY-RUN or LIVE)
Compatible with GitHub Actions $GITHUB_STEP_SUMMARY
"""

import argparse
import os
import sys
import re
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="Generate campaign summary from log files")
    parser.add_argument("--log-file", type=str, required=True,
                        help="Path to campaign log file (dryrun.log or campaign_execution.log)")
    parser.add_argument("--mode", type=str, default="dry-run", choices=["dry-run", "live"],
                        help="Execution mode")
    parser.add_argument("--output-summary", type=str, default=os.getenv("GITHUB_STEP_SUMMARY", None),
                        help="Optional: file to write GitHub Actions step summary")
    return parser.parse_args()

def extract_metrics(log_file):
    metrics = {
        "total_contacts": 0,
        "unique_contacts": 0,
        "campaigns_processed": 0,
        "total_emails": 0,
        "successful": 0,
        "failed": 0,
        "campaigns": [],
        "sample_recipients": [],
        "errors": []
    }

    if not os.path.isfile(log_file):
        return metrics

    with open(log_file, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if "Total contacts loaded:" in line:
            metrics["total_contacts"] = int(re.search(r"(\d+)", line).group(1))
        elif "Unique contacts:" in line:
            metrics["unique_contacts"] = int(re.search(r"(\d+)", line).group(1))
        elif "Campaigns processed:" in line:
            metrics["campaigns_processed"] = int(re.search(r"(\d+)", line).group(1))
        elif "Total emails:" in line:
            metrics["total_emails"] = int(re.search(r"(\d+)", line).group(1))
        elif "Successful:" in line:
            metrics["successful"] = int(re.search(r"(\d+)", line).group(1))
        elif "Failed:" in line:
            metrics["failed"] = int(re.search(r"(\d+)", line).group(1))
        elif "Campaign '" in line and "completed:" in line:
            campaign_name = re.search(r"Campaign '([^']*)'", line)
            if campaign_name:
                metrics["campaigns"].append(campaign_name.group(1))
        elif "Sample recipients:" in line:
            sample = line.split(":", 1)[-1].strip()
            if sample:
                metrics["sample_recipients"].append(sample)
        elif re.search(r"ERROR|Error|Failed|Warning", line, re.I):
            metrics["errors"].append(line)

    return metrics

def build_summary(metrics, mode):
    md = []
    md.append(f"## Email Campaign Execution Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    md.append(f"**Mode**: {'🔍 DRY-RUN - No emails sent' if mode == 'dry-run' else '📧 LIVE - Emails sent'}\n")

    # Execution statistics
    md.append("### 📊 Execution Statistics\n")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Total Contacts Loaded | {metrics['total_contacts']} |")
    md.append(f"| Unique Contacts | {metrics['unique_contacts']} |")
    md.append(f"| Campaigns Processed | {metrics['campaigns_processed']} |")
    md.append(f"| Total Emails | {metrics['total_emails']} |")
    md.append(f"| Successful | {metrics['successful']} |")
    md.append(f"| Failed | {metrics['failed']} |")
    success_rate = f"{(metrics['successful']/metrics['total_emails']*100):.1f}%" if metrics['total_emails'] else "N/A"
    md.append(f"| Success Rate | {success_rate} |")
    md.append("")

    # Individual campaigns
    if metrics["campaigns"]:
        md.append("### 📋 Campaign Details\n")
        md.append("| Campaign | Status | Details |")
        md.append("|----------|--------|---------|")
        for c in metrics["campaigns"]:
            md.append(f"| {c} | Completed | See logs |")
        md.append("")

    # Sample recipients
    if metrics["sample_recipients"]:
        md.append("### 👥 Sample Recipients (First 5)\n")
        md.append("```")
        for r in metrics["sample_recipients"][:5]:
            md.append(r)
        md.append("```")
        md.append("")

    # Errors
    if metrics["errors"]:
        md.append("### ⚠️ Issues Detected\n")
        md.append("```")
        for e in metrics["errors"][:10]:
            md.append(e)
        md.append("```")
        md.append("")

    # Metadata
    md.append("### 🔧 Execution Metadata\n")
    md.append("| Field | Value |")
    md.append("|-------|-------|")
    md.append(f"| Timestamp | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} |")
    md.append(f"| Mode | {mode} |")
    return "\n".join(md)

def main():
    args = parse_args()
    metrics = extract_metrics(args.log_file)
    summary = build_summary(metrics, args.mode)

    if args.output_summary:
        with open(args.output_summary, "a") as f:
            f.write(summary + "\n")
        print(f"Summary written to {args.output_summary}")
    else:
        print(summary)

if __name__ == "__main__":
    main()
