#!/usr/bin/env python3
"""
Enhanced directory setup script for email campaign system.
Creates comprehensive directory structure with validation.
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime


def create_directory_structure():
    """Create enhanced directory structure with absolute paths."""
    work_dir = Path.cwd()
    
    # Define directory structure
    directories = {
        'templates': 'campaign-templates',
        'contacts': 'contacts',
        'scheduled': 'scheduled-campaigns', 
        'tracking': 'tracking',
        'utils': 'utils',
        'reports': 'reports',
        'scripts': 'scripts'
    }
    
    # Define subdirectories
    subdirectories = {
        'tracking': [
            'feedback_responses',
            'domain_stats', 
            'execution_logs',
            'batch_reports',
            'reply_tracking'
        ],
        'templates': [
            'education',
            'finance',
            'healthcare',
            'industry',
            'technology',
            'government'
        ],
        'contacts': [
            'csv',
            'excel', 
            'docx',
            'urls'
        ],
        'scripts': [
            'validation',
            'execution',
            'tracking',
            'utils'
        ]
    }
    
    print("Creating enhanced directory structure...")
    print(f"Working directory: {work_dir}")
    
    created_dirs = []
    failed_dirs = []
    
    # Create main directories
    for dir_name, dir_path in directories.items():
        full_path = work_dir / dir_path
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(full_path))
            print(f"✓ Created: {dir_path}")
        except Exception as e:
            failed_dirs.append((dir_path, str(e)))
            print(f"✗ Failed to create {dir_path}: {e}")
    
    # Create subdirectories
    for parent_key, subdirs in subdirectories.items():
        if parent_key in directories:
            parent_path = work_dir / directories[parent_key]
            for subdir in subdirs:
                subdir_path = parent_path / subdir
                try:
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(subdir_path))
                    print(f"  ✓ Created: {directories[parent_key]}/{subdir}")
                except Exception as e:
                    failed_dirs.append((f"{directories[parent_key]}/{subdir}", str(e)))
                    print(f"  ✗ Failed to create {directories[parent_key]}/{subdir}: {e}")
    
    # Verify directory structure
    print("\nVerifying directory structure...")
    verification_results = verify_directories(work_dir, directories, subdirectories)
    
    # Create setup report
    setup_report = {
        'setup_timestamp': datetime.now().isoformat(),
        'working_directory': str(work_dir),
        'directories_created': created_dirs,
        'directories_failed': failed_dirs,
        'verification_results': verification_results,
        'setup_status': 'success' if not failed_dirs else 'partial_success'
    }
    
    # Save setup report
    try:
        reports_dir = work_dir / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f'directory_setup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(setup_report, f, indent=2)
        print(f"Setup report saved: {report_file}")
    except Exception as e:
        print(f"Warning: Could not save setup report: {e}")
    
    return len(failed_dirs) == 0


def verify_directories(work_dir, directories, subdirectories):
    """Verify that all directories were created successfully."""
    verification_results = {}
    
    for dir_name, dir_path in directories.items():
        full_path = work_dir / dir_path
        verification_results[dir_path] = {
            'exists': full_path.exists(),
            'is_directory': full_path.is_dir() if full_path.exists() else False,
            'subdirectories': {}
        }
        
        if dir_name in subdirectories:
            for subdir in subdirectories[dir_name]:
                subdir_path = full_path / subdir
                verification_results[dir_path]['subdirectories'][subdir] = {
                    'exists': subdir_path.exists(),
                    'is_directory': subdir_path.is_dir() if subdir_path.exists() else False
                }
    
    # Print verification summary
    all_verified = True
    for dir_path, results in verification_results.items():
        status = "✓" if results['exists'] and results['is_directory'] else "✗"
        print(f"{status} {dir_path}")
        
        if not (results['exists'] and results['is_directory']):
            all_verified = False
        
        for subdir, sub_results in results['subdirectories'].items():
            sub_status = "✓" if sub_results['exists'] and sub_results['is_directory'] else "✗"
            print(f"  {sub_status} {dir_path}/{subdir}")
            
            if not (sub_results['exists'] and sub_results['is_directory']):
                all_verified = False
    
    print(f"\nDirectory structure verification: {'PASSED' if all_verified else 'FAILED'}")
    return verification_results


def create_sample_files():
    """Create sample configuration and template files."""
    work_dir = Path.cwd()
    
    # Create sample contact file
    contacts_dir = work_dir / 'contacts'
    if contacts_dir.exists():
        sample_csv = contacts_dir / 'sample_contacts.csv'
        if not sample_csv.exists():
            csv_content = """name,email,organization,role,domain,country
John Doe,john.doe@example.com,Example Corp,Manager,education,US
Jane Smith,jane.smith@test.org,Test Organization,Director,healthcare,UK
Bob Johnson,bob.johnson@sample.net,Sample Company,Analyst,finance,CA"""
            
            try:
                with open(sample_csv, 'w') as f:
                    f.write(csv_content)
                print(f"✓ Created sample contact file: {sample_csv}")
            except Exception as e:
                print(f"✗ Failed to create sample contact file: {e}")
    
    # Create sample campaign template
    scheduled_dir = work_dir / 'scheduled-campaigns'
    if scheduled_dir.exists():
        sample_template = scheduled_dir / 'welcome_campaign.txt'
        if not sample_template.exists():
            template_content = """Subject: Welcome {{name}} to Our Platform!

Dear {{name}},

We're excited to welcome you to our platform! This personalized message is being sent to {{email}} to confirm your registration.

Your organization, {{organization}}, has been successfully added to our records in the {{domain}} sector.

Best regards,
The Platform Team

---
This email was personalized for {{name}} at {{organization}}.
"""
            
            try:
                with open(sample_template, 'w') as f:
                    f.write(template_content)
                print(f"✓ Created sample campaign template: {sample_template}")
            except Exception as e:
                print(f"✗ Failed to create sample campaign template: {e}")


def main():
    """Main function to set up directory structure."""
    print("Enhanced Email Campaign System - Directory Setup")
    print("=" * 50)
    
    try:
        # Create directory structure
        success = create_directory_structure()
        
        # Create sample files
        print("\nCreating sample files...")
        create_sample_files()
        
        print("\n" + "=" * 50)
        if success:
            print("✓ Directory setup completed successfully!")
            print("\nNext steps:")
            print("1. Add your contact data files to the 'contacts/' directory")
            print("2. Add your campaign templates to the 'scheduled-campaigns/' directory")
            print("3. Configure your email settings in the main campaign script")
            return 0
        else:
            print("⚠ Directory setup completed with some errors.")
            print("Check the output above for failed directories.")
            return 1
            
    except Exception as e:
        print(f"✗ Directory setup failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
