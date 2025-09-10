#!/usr/bin/env python3
"""
Campaign Configuration Checker
Validates JSON campaign configs against available resources
"""

import json
import sys
from pathlib import Path

def validate_test_campaign_config():
    """Validate the specific test campaign configuration"""
    
    # Your test configuration
    config = {
        "name": "Test Campaign",
        "sector": "education", 
        "templates": ["outreach.docx"],
        "contacts": "contacts/client_test.url",
        "mode": "schedule_now",
        "date": "2025-09-09",
        "from_email": "campaigns@yourdomain.com",
        "from_name": "Outreach Team", 
        "subject": "Collaboration Opportunity Test",
        "defaults": {
            "Status": "Pending",
            "Follow-up": "TBD", 
            "Region": "Global",
            "Notes": ""
        }
    }
    
    print("🔍 VALIDATING TEST CAMPAIGN CONFIG")
    print("=" * 50)
    
    errors = []
    warnings = []
    
    # Check templates directory and files
    templates_dir = Path("campaign-templates")
    if not templates_dir.exists():
        errors.append("❌ campaign-templates/ directory not found")
    else:
        print(f"✅ Templates directory exists: {templates_dir}")
        
        # Check each template file
        for template in config["templates"]:
            template_path = templates_dir / template
            if template_path.exists():
                print(f"✅ Template found: {template}")
            else:
                errors.append(f"❌ Template missing: {template}")
                
                # Show available templates
                available = list(templates_dir.glob("*.docx"))
                if available:
                    print(f"   Available templates: {[t.name for t in available]}")
    
    # Check contacts directory and files  
    contacts_dir = Path("contacts")
    if not contacts_dir.exists():
        errors.append("❌ contacts/ directory not found")
    else:
        print(f"✅ Contacts directory exists: {contacts_dir}")
        
        # Extract filename from path
        contacts_file = Path(config["contacts"]).name
        contacts_path = contacts_dir / contacts_file
        
        if contacts_path.exists():
            print(f"✅ Contacts file found: {contacts_file}")
        else:
            errors.append(f"❌ Contacts file missing: {contacts_file}")
            
            # Show available contact files
            available = []
            for ext in ["*.csv", "*.xlsx", "*.url"]:
                available.extend(list(contacts_dir.glob(ext)))
            if available:
                print(f"   Available contacts: {[c.name for c in available]}")
    
    # Validate configuration structure
    required_fields = ["name", "templates", "contacts", "mode"]
    for field in required_fields:
        if field not in config:
            errors.append(f"❌ Missing required field: {field}")
        else:
            print(f"✅ Required field present: {field}")
    
    # Check email configuration
    if "from_email" in config and "@" not in config["from_email"]:
        warnings.append("⚠️  Invalid email format in from_email")
    
    # Check date format (basic)
    if "date" in config:
        try:
            from datetime import datetime
            datetime.strptime(config["date"], "%Y-%m-%d")
            print(f"✅ Date format valid: {config['date']}")
        except ValueError:
            warnings.append("⚠️  Date format should be YYYY-MM-DD")
    
    # Print results
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS")
    print("=" * 50)
    
    if not errors:
        print("🎉 CONFIGURATION VALID!")
        print("All templates and contacts are available.")
    else:
        print("❌ CONFIGURATION INVALID!")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
    
    print(f"\nSummary:")
    print(f"- Templates to use: {len(config['templates'])}")
    print(f"- Contact files: 1")
    print(f"- Campaign mode: {config['mode']}")
    print(f"- Target date: {config.get('date', 'Not specified')}")
    
    return len(errors) == 0

def scan_and_suggest():
    """Scan directories and suggest valid configurations"""
    print("\n🔍 SCANNING FOR AVAILABLE RESOURCES")
    print("=" * 50)
    
    templates_dir = Path("campaign-templates")
    contacts_dir = Path("contacts")
    
    # Find templates
    templates = []
    if templates_dir.exists():
        templates = list(templates_dir.glob("*.docx"))
        print(f"Found {len(templates)} template(s):")
        for t in templates:
            print(f"  📄 {t.name}")
    else:
        print("❌ No campaign-templates directory found")
    
    # Find contacts  
    contacts = []
    if contacts_dir.exists():
        for ext in ["*.csv", "*.xlsx", "*.url"]:
            contacts.extend(list(contacts_dir.glob(ext)))
        print(f"\nFound {len(contacts)} contact file(s):")
        for c in contacts:
            print(f"  📋 {c.name}")
    else:
        print("❌ No contacts directory found")
    
    # Generate suggested config
    if templates and contacts:
        print(f"\n💡 SUGGESTED CONFIGURATION:")
        print("-" * 30)
        suggested = {
            "name": "Auto-Generated Campaign",
            "sector": "general",
            "templates": [templates[0].name],  # First available template
            "contacts": f"contacts/{contacts[0].name}",  # First available contact file
            "mode": "schedule_now",
            "from_email": "campaigns@yourdomain.com",
            "from_name": "Campaign Team",
            "subject": "Automated Campaign"
        }
        print(json.dumps(suggested, indent=2))

def main():
    print("CAMPAIGN CONFIGURATION VALIDATOR")
    print("=" * 60)
    
    # First, validate the test config
    is_valid = validate_test_campaign_config()
    
    # Then scan and suggest alternatives
    scan_and_suggest()
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
