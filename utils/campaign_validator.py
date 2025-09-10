#!/usr/bin/env python3
"""
Campaign Validator - Handles domain-specific templates and unique tracking IDs
"""
import os
import sys
import json
import glob
import hashlib
import uuid
from pathlib import Path
from datetime import datetime

class DomainCampaignValidator:
    def __init__(self, templates_dir="campaign-templates", contacts_dir="contacts", tracking_dir="tracking"):
        self.templates_dir = Path(templates_dir)
        self.contacts_dir = Path(contacts_dir)
        self.tracking_dir = Path(tracking_dir)
        self.errors = []
        self.warnings = []
        self.valid_domains = ["education", "finance", "healthcare", "industry", "technology", "government"]
    
    def validate_directories(self):
        """Check if required directories exist"""
        if not self.templates_dir.exists():
            self.errors.append(f"Templates directory not found: {self.templates_dir}")
        if not self.contacts_dir.exists():
            self.errors.append(f"Contacts directory not found: {self.contacts_dir}")
        if not self.tracking_dir.exists():
            self.tracking_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created tracking directory: {self.tracking_dir}")
    
    def scan_domain_templates(self):
        """Scan for domain-specific templates"""
        domain_templates = {}
        
        if not self.templates_dir.exists():
            return domain_templates
        
        # Scan each domain subdirectory
        for domain_dir in self.templates_dir.iterdir():
            if domain_dir.is_dir():
                domain_name = domain_dir.name
                templates = list(domain_dir.glob("*.docx"))
                if templates:
                    domain_templates[domain_name] = templates
                    print(f"✓ Found {len(templates)} template(s) in {domain_name}/")
                    for template in templates:
                        print(f"  - {template.name}")
        
        return domain_templates
    
    def scan_contacts(self):
        """Scan for contact files"""
        contacts = []
        if self.contacts_dir.exists():
            for ext in ["*.csv", "*.xlsx", "*.url"]:
                contacts.extend(list(self.contacts_dir.glob(ext)))
        return contacts
    
    def validate_domain_structure(self):
        """Validate the domain-based template structure"""
        domain_templates = self.scan_domain_templates()
        
        if not domain_templates:
            self.errors.append("No domain directories found in campaign-templates/")
            self.warnings.append(f"Expected domains: {', '.join(self.valid_domains)}")
            return False
        
        # Check for common template files across domains
        template_files = {}
        for domain, templates in domain_templates.items():
            for template in templates:
                filename = template.name
                if filename not in template_files:
                    template_files[filename] = []
                template_files[filename].append(domain)
        
        # Report template distribution
        print(f"\nTemplate distribution across domains:")
        for filename, domains in template_files.items():
            print(f"  {filename}: {', '.join(domains)}")
        
        return True
    
    def generate_unique_tracking_id(self, domain, campaign_name, template_name):
        """Generate unique tracking ID for domain/campaign combination"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a unique seed from domain, campaign, template, and timestamp
        seed_string = f"{domain}_{campaign_name}_{template_name}_{timestamp}"
        hash_object = hashlib.md5(seed_string.encode())
        short_hash = hash_object.hexdigest()[:8]
        
        # Format: DOMAIN_HASH_TIMESTAMP
        tracking_id = f"{domain.upper()}_{short_hash}_{timestamp}"
        
        return tracking_id
    
    def ensure_tracking_structure(self):
        """Create domain-specific tracking directories"""
        domain_templates = self.scan_domain_templates()
        
        for domain in domain_templates.keys():
            domain_tracking = self.tracking_dir / domain
            domain_tracking.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for different tracking types
            (domain_tracking / "campaigns").mkdir(exist_ok=True)
            (domain_tracking / "responses").mkdir(exist_ok=True)
            (domain_tracking / "analytics").mkdir(exist_ok=True)
            
            print(f"✓ Tracking structure ready for {domain}/")
    
    def validate_campaign_config(self, config_path):
        """Validate campaign configuration with domain support"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load config {config_path}: {e}")
            return False
        
        # Validate required fields
        required_fields = ["name", "sector", "templates", "contacts"]
        for field in required_fields:
            if field not in config:
                self.errors.append(f"Missing required field '{field}' in {config_path}")
        
        # Validate sector/domain
        sector = config.get("sector")
        if sector not in self.valid_domains:
            self.warnings.append(f"Sector '{sector}' not in recommended domains: {self.valid_domains}")
        
        # Validate domain-specific templates
        domain_templates = self.scan_domain_templates()
        
        if sector in domain_templates:
            available_templates = [t.name for t in domain_templates[sector]]
            
            for template in config.get("templates", []):
                if template not in available_templates:
                    self.errors.append(f"Template '{template}' not found in {sector}/ domain")
                    self.warnings.append(f"Available in {sector}/: {available_templates}")
        else:
            self.errors.append(f"No templates found for sector '{sector}'")
        
        # Validate contacts
        contacts = self.scan_contacts()
        contact_names = [c.name for c in contacts]
        contacts_file = Path(config.get("contacts", "")).name
        
        if contacts_file not in contact_names:
            self.errors.append(f"Contacts file '{contacts_file}' not found")
            self.warnings.append(f"Available contacts: {contact_names}")
        
        # Generate and store tracking ID for this config
        if sector and config.get("name") and config.get("templates"):
            tracking_id = self.generate_unique_tracking_id(
                sector, 
                config["name"], 
                config["templates"][0]  # Use first template for ID generation
            )
            config["tracking_id"] = tracking_id
            
            # Save updated config with tracking ID
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✓ Generated tracking ID: {tracking_id}")
        
        return len(self.errors) == 0
    
    def create_tracking_manifest(self):
        """Create a tracking manifest to prevent ID collisions"""
        manifest_file = self.tracking_dir / "tracking_manifest.json"
        
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
        else:
            manifest = {"created": datetime.now().isoformat(), "campaigns": {}}
        
        # Scan for existing tracking IDs
        existing_ids = set()
        for domain_dir in self.tracking_dir.iterdir():
            if domain_dir.is_dir() and domain_dir.name != "__pycache__":
                campaign_dir = domain_dir / "campaigns"
                if campaign_dir.exists():
                    for tracking_file in campaign_dir.glob("*.json"):
                        try:
                            with open(tracking_file, 'r') as f:
                                data = json.load(f)
                                if "tracking_id" in data:
                                    existing_ids.add(data["tracking_id"])
                        except:
                            continue
        
        manifest["existing_ids"] = list(existing_ids)
        manifest["last_updated"] = datetime.now().isoformat()
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ Tracking manifest updated with {len(existing_ids)} existing IDs")
        return existing_ids
    
    def generate_report(self):
        """Generate comprehensive validation report"""
        domain_templates = self.scan_domain_templates()
        contacts = self.scan_contacts()
        existing_ids = self.create_tracking_manifest()
        
        report = {
            "validation_status": "PASS" if len(self.errors) == 0 else "FAIL",
            "domains": {
                domain: [t.name for t in templates] 
                for domain, templates in domain_templates.items()
            },
            "available_contacts": [c.name for c in contacts],
            "tracking_structure": {
                "total_existing_ids": len(existing_ids),
                "tracking_dir_exists": self.tracking_dir.exists()
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "domain_count": len(domain_templates),
            "template_count": sum(len(templates) for templates in domain_templates.values()),
            "contact_count": len(contacts)
        }
        
        return report
    
    def print_report(self):
        """Print human-readable validation report"""
        report = self.generate_report()
        
        print("=" * 70)
        print("DOMAIN-BASED CAMPAIGN VALIDATION REPORT")
        print("=" * 70)
        print(f"Status: {report['validation_status']}")
        print(f"Domains found: {report['domain_count']}")
        print(f"Total templates: {report['template_count']}")
        print(f"Contact files: {report['contact_count']}")
        print(f"Existing tracking IDs: {report['tracking_structure']['total_existing_ids']}")
        print()
        
        # Domain breakdown
        if report['domains']:
            print("📁 DOMAIN STRUCTURE:")
            for domain, templates in report['domains'].items():
                print(f"  {domain}/")
                for template in templates:
                    print(f"    ├── {template}")
            print()
        
        # Contacts
        if report['available_contacts']:
            print("📋 AVAILABLE CONTACTS:")
            for contact in report['available_contacts']:
                print(f"  ├── {contact}")
            print()
        
        # Errors and warnings
        if report['errors']:
            print("❌ ERRORS:")
            for error in report['errors']:
                print(f"  • {error}")
            print()
        
        if report['warnings']:
            print("⚠️  WARNINGS:")
            for warning in report['warnings']:
                print(f"  • {warning}")
            print()
        
        return report['validation_status'] == "PASS"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate domain-based campaign resources")
    parser.add_argument("--templates", default="campaign-templates", help="Templates directory")
    parser.add_argument("--contacts", default="contacts", help="Contacts directory")
    parser.add_argument("--tracking", default="tracking", help="Tracking directory")
    parser.add_argument("--config", help="Campaign config file to validate")
    parser.add_argument("--json-output", action="store_true", help="Output JSON report")
    parser.add_argument("--setup-tracking", action="store_true", help="Setup tracking structure")
    
    args = parser.parse_args()
    
    validator = DomainCampaignValidator(args.templates, args.contacts, args.tracking)
    validator.validate_directories()
    validator.validate_domain_structure()
    
    if args.setup_tracking:
        validator.ensure_tracking_structure()
    
    if args.config:
        validator.validate_campaign_config(args.config)
    
    if args.json_output:
        report = validator.generate_report()
        print(json.dumps(report, indent=2))
    else:
        success = validator.print_report()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
