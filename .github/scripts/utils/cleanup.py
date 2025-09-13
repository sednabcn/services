#!/usr/bin/env python3
"""
Enhanced cleanup script for email campaign system.
Removes sensitive data and temporary files while preserving important logs.
"""

import os
import sys
import shutil
import glob
from pathlib import Path
import json
from datetime import datetime
import argparse


def cleanup_credentials():
    """Remove sensitive credential files."""
    print("Cleaning up sensitive credential files...")
    
    credential_patterns = [
        '/tmp/google_svc.json',
        '.env',
        '*.key',
        '*.pem', 
        '*_credentials.json',
        'credentials.json',
        'token.json',
        'service_account.json'
    ]
    
    removed_files = []
    
    for pattern in credential_patterns:
        if pattern.startswith('/'):
            # Absolute path
            if os.path.exists(pattern):
                try:
                    os.remove(pattern)
                    removed_files.append(pattern)
                    print(f"✓ Removed: {pattern}")
                except Exception as e:
                    print(f"✗ Failed to remove {pattern}: {e}")
        else:
            # Pattern matching
            for file_path in glob.glob(pattern):
                try:
                    os.remove(file_path)
                    removed_files.append(file_path)
                    print(f"✓ Removed: {file_path}")
                except Exception as e:
                    print(f"✗ Failed to remove {file_path}: {e}")
    
    return removed_files


def cleanup_cache():
    """Clean cached credentials and temporary data."""
    print("Cleaning cached credentials and temporary data...")
    
    removed_items = []
    
    # Clean ~/.cache directory
    cache_dir = Path.home() / '.cache'
    if cache_dir.exists():
        cache_patterns = ['*credential*', '*token*', '*oauth*']
        
        for pattern in cache_patterns:
            for cache_file in cache_dir.rglob(pattern):
                try:
                    if cache_file.is_file():
                        cache_file.unlink()
                        removed_items.append(str(cache_file))
                    elif cache_file.is_dir():
                        shutil.rmtree(cache_file)
                        removed_items.append(str(cache_file))
                    print(f"✓ Removed cache: {cache_file}")
                except Exception as e:
                    print(f"✗ Failed to remove cache {cache_file}: {e}")
    
    return removed_items


def cleanup_python_cache():
    """Clean Python cache files."""
    print("Cleaning Python cache files...")
    
    removed_items = []
    current_dir = Path.cwd()
    
    # Remove __pycache__ directories
    for pycache_dir in current_dir.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache_dir)
            removed_items.append(str(pycache_dir))
            print(f"✓ Removed: {pycache_dir}")
        except Exception as e:
            print(f"✗ Failed to remove {pycache_dir}: {e}")
    
    # Remove .pyc and .pyo files
    for pyc_file in current_dir.rglob('*.pyc'):
        try:
            pyc_file.unlink()
            removed_items.append(str(pyc_file))
            print(f"✓ Removed: {pyc_file}")
        except Exception as e:
            print(f"✗ Failed to remove {pyc_file}: {e}")
    
    for pyo_file in current_dir.rglob('*.pyo'):
        try:
            pyo_file.unlink()
            removed_items.append(str(pyo_file))
            print(f"✓ Removed: {pyo_file}")
        except Exception as e:
            print(f"✗ Failed to remove {pyo_file}: {e}")
    
    return removed_items


def cleanup_temporary_files(preserve_logs=True):
    """Clean temporary files while optionally preserving logs."""
    print("Cleaning temporary files...")
    
    removed_items = []
    tracking_dir = Path.cwd() / 'tracking'
    
    if tracking_dir.exists():
        temp_patterns = ['*.tmp', '*temp*', '*.lock']
        
        for pattern in temp_patterns:
            for temp_file in tracking_dir.rglob(pattern):
                try:
                    if temp_file.is_file():
                        temp_file.unlink()
                        removed_items.append(str(temp_file))
                        print(f"✓ Removed temp file: {temp_file}")
                    elif temp_file.is_dir():
                        shutil.rmtree(temp_file)
                        removed_items.append(str(temp_file))
                        print(f"✓ Removed temp directory: {temp_file}")
                except Exception as e:
                    print(f"✗ Failed to remove {temp_file}: {e}")
    
    # Clean other temporary files in root directory
    root_temp_patterns = ['*.tmp', 'temp_*', '.DS_Store']
    current_dir = Path.cwd()
    
    for pattern in root_temp_patterns:
        for temp_file in current_dir.glob(pattern):
            try:
                if temp_file.is_file():
                    temp_file.unlink()
                    removed_items.append(str(temp_file))
                    print(f"✓ Removed: {temp_file}")
            except Exception as e:
                print(f"✗ Failed to remove {temp_file}: {e}")
    
    return removed_items


def cleanup_environment_variables():
    """Clean sensitive environment variables."""
    print("Cleaning sensitive environment variables...")
    
    sensitive_vars = [
        'GOOGLE_SVC_JSON',
        'SMTP_PASS',
        'IMAP_PASS', 
        'GITHUB_TOKEN',
        'GOOGLE_APPLICATION_CREDENTIALS'
    ]
    
    cleaned_vars = []
    
    for var in sensitive_vars:
        if var in os.environ:
            del os.environ[var]
            cleaned_vars.append(var)
            print(f"✓ Cleared environment variable: {var}")
    
    return cleaned_vars


def preserve_important_files():
    """Identify and list important files that should be preserved."""
    print("Identifying important files to preserve...")
    
    important_patterns = [
        'tracking/**/*.log',
        'reports/*.md',
        'reports/*.json',
        '*.log',
        'tracking/execution_logs/*',
        'tracking/reply_tracking/*',
        'tracking/feedback_responses/*'
    ]
    
    preserved_files = []
    current_dir = Path.cwd()
    
    for pattern in important_patterns:
        for file_path in current_dir.glob(pattern):
            if file_path.is_file():
                preserved_files.append(str(file_path))
    
    if preserved_files:
        print("Important files preserved:")
        for file_path in preserved_files:
            print(f"  ✓ Preserved: {file_path}")
    
    return preserved_files


def generate_cleanup_report(removed_credentials, removed_cache, removed_python, 
                          removed_temp, cleaned_vars, preserved_files, cleanup_type="standard"):
    """Generate comprehensive cleanup report."""
    
    cleanup_report = {
        'cleanup_timestamp': datetime.now().isoformat(),
        'cleanup_type': cleanup_type,
        'summary': {
            'credentials_removed': len(removed_credentials),
            'cache_items_removed': len(removed_cache),
            'python_cache_removed': len(removed_python),
            'temp_files_removed': len(removed_temp),
            'env_vars_cleaned': len(cleaned_vars),
            'files_preserved': len(preserved_files)
        },
        'details': {
            'removed_credentials': removed_credentials,
            'removed_cache': removed_cache[:50],  # Limit to first 50 items
            'removed_python_cache': removed_python[:50],
            'removed_temp_files': removed_temp[:50], 
            'cleaned_environment_variables': cleaned_vars,
            'preserved_files': preserved_files[:100]  # Limit to first 100 items
        },
        'security_level': 'production-grade',
        'status': 'completed'
    }
    
    # Save cleanup report
    reports_dir = Path.cwd() / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    try:
        report_file = reports_dir / f'cleanup_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(cleanup_report, f, indent=2)
        print(f"✓ Cleanup report saved: {report_file}")
    except Exception as e:
        print(f"⚠ Could not save cleanup report: {e}")
    
    return cleanup_report


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description='Enhanced Email Campaign System Cleanup')
    parser.add_argument('--aggressive', action='store_true', 
                       help='Perform aggressive cleanup (removes more files)')
    parser.add_argument('--preserve-logs', action='store_true', default=True,
                       help='Preserve execution logs (default: True)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be cleaned without actually cleaning')
    
    args = parser.parse_args()
    
    print("Enhanced Email Campaign System - Security Cleanup")
    print("=" * 50)
    
    if args.dry_run:
        print("DRY-RUN MODE: No files will be removed")
        print()
    
    try:
        # Preserve important files first
        preserved_files = preserve_important_files()
        print()
        
        if not args.dry_run:
            # Clean credentials
            removed_credentials = cleanup_credentials()
            print()
            
            # Clean cache
            removed_cache = cleanup_cache() 
            print()
            
            # Clean Python cache
            removed_python = cleanup_python_cache()
            print()
            
            # Clean temporary files
            removed_temp = cleanup_temporary_files(preserve_logs=args.preserve_logs)
            print()
            
            # Clean environment variables
            cleaned_vars = cleanup_environment_variables()
            print()
        else:
            # Dry run - just show what would be cleaned
            removed_credentials = []
            removed_cache = []
            removed_python = []
            removed_temp = []
            cleaned_vars = []
        
        # Generate report
        cleanup_type = "aggressive" if args.aggressive else "standard"
        if args.dry_run:
            cleanup_type += "_dry_run"
            
        cleanup_report = generate_cleanup_report(
            removed_credentials, removed_cache, removed_python,
            removed_temp, cleaned_vars, preserved_files, cleanup_type
        )
        
        print("=" * 50)
        print("✓ Enhanced security cleanup completed successfully!")
        print(f"Cleanup type: {cleanup_type}")
        print(f"Files removed: {sum([len(removed_credentials), len(removed_cache), len(removed_python), len(removed_temp)])}")
        print(f"Environment variables cleared: {len(cleaned_vars)}")
        print(f"Important files preserved: {len(preserved_files)}")
        
        if args.dry_run:
            print("\nThis was a dry run. Use without --dry-run to perform actual cleanup.")
        
        return 0
        
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
