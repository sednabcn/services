#!/usr/bin/env python3
"""
Enhanced import validation script for email campaign system.
Validates that all required modules and utilities are available.
"""

import sys
import os
import importlib.util
from pathlib import Path


def validate_module_import(module_name, package=None):
    """Validate that a Python module can be imported."""
    try:
        if package:
            __import__(f"{package}.{module_name}")
        else:
            __import__(module_name)
        return True
    except ImportError as e:
        print(f"Import error for {module_name}: {e}")
        return False


def validate_file_import(file_path, module_name=None):
    """Validate that a Python file exists and can be imported."""
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {file_path}")
            return False
            
        # Try to load as module
        spec = importlib.util.spec_from_file_location(
            module_name or path.stem, path
        )
        if spec is None:
            print(f"Could not create module spec for: {file_path}")
            return False
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"Successfully validated: {file_path}")
        return True
        
    except Exception as e:
        print(f"Validation error for {file_path}: {e}")
        return False


def validate_docx_parser():
    """Validate the main docx_parser.py script."""
    docx_parser_path = Path("utils/docx_parser.py")
    
    if not docx_parser_path.exists():
        print("CRITICAL: utils/docx_parser.py not found")
        return False
        
    try:
        # Add utils to path for import
        sys.path.insert(0, str(docx_parser_path.parent))
        
        # Try to import the module
        spec = importlib.util.spec_from_file_location("docx_parser", docx_parser_path)
        if spec is None:
            print("Could not create spec for docx_parser.py")
            return False
            
        docx_parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(docx_parser)
        
        # Check if it has expected functions/classes
        expected_attributes = ['main', '__main__', 'process_campaigns', 'load_contacts']
        found_attributes = []
        
        for attr in expected_attributes:
            if hasattr(docx_parser, attr):
                found_attributes.append(attr)
                
        print(f"docx_parser.py validation: {len(found_attributes)}/{len(expected_attributes)} expected attributes found")
        print(f"Found attributes: {found_attributes}")
        
        return True
        
    except Exception as e:
        print(f"Error validating docx_parser.py: {e}")
        return False


def validate_core_dependencies():
    """Validate core Python dependencies."""
    core_modules = [
        'pandas', 'requests', 'docx', 'openpyxl', 
        'xlrd', 'jinja2', 'gspread', 'oauth2client',
        'google.auth', 'google.api_core', 'beautifulsoup4'
    ]
    
    success_count = 0
    total_count = len(core_modules)
    
    for module in core_modules:
        if validate_module_import(module):
            success_count += 1
            print(f"✓ {module}")
        else:
            print(f"✗ {module}")
            
    print(f"\nCore dependencies: {success_count}/{total_count} available")
    return success_count >= (total_count * 0.8)  # 80% success rate required


def validate_utility_scripts():
    """Validate utility scripts availability."""
    utility_scripts = [
        "utils/data_loader.py",
        "utils/email_feedback_injector.py", 
        "utils/docx_feedback_processor.py",
        "utils/reply_tracker.py"
    ]
    
    available_count = 0
    total_count = len(utility_scripts)
    
    for script in utility_scripts:
        if Path(script).exists():
            available_count += 1
            print(f"✓ Found {script}")
        else:
            print(f"⚠ Missing {script}")
            
    print(f"\nUtility scripts: {available_count}/{total_count} available")
    return available_count, total_count


def main():
    """Run comprehensive validation."""
    print("=== Enhanced Import Validation ===\n")
    
    validation_results = {
        'core_dependencies': validate_core_dependencies(),
        'docx_parser': validate_docx_parser(),
        'utility_scripts': validate_utility_scripts()
    }
    
    print(f"\n=== Validation Summary ===")
    print(f"Core Dependencies: {'PASS' if validation_results['core_dependencies'] else 'FAIL'}")
    print(f"Main Processor: {'PASS' if validation_results['docx_parser'] else 'FAIL'}")
    print(f"Utility Scripts: {validation_results['utility_scripts'][0]}/{validation_results['utility_scripts'][1]} available")
    
    # Determine overall status
    critical_components = [
        validation_results['core_dependencies'],
        validation_results['docx_parser']
    ]
    
    overall_success = all(critical_components)
    print(f"Overall Status: {'SUCCESS' if overall_success else 'ISSUES DETECTED'}")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
