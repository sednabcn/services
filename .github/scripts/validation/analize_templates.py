#!/usr/bin/env python3
"""
Enhanced template and domain analysis script.
Analyzes campaign templates and generates domain-based statistics.
"""

import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path


def analyze_template_variables(content):
    """Extract template variables from content."""
    # Find variables in {{variable}} format
    variables = re.findall(r'{{([^}]+)}}', content)
    
    # Clean and deduplicate variables
    clean_variables = []
    for var in variables:
        cleaned = var.strip()
        if cleaned and cleaned not in clean_variables:
            clean_variables.append(cleaned)
            
    return clean_variables


def analyze_template_file(file_path):
    """Analyze a single template file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract basic information
        file_info = {
            'name': file_path.name,
            'path': str(file_path),
            'size': file_path.stat().st_size,
            'extension': file_path.suffix.lower(),
            'variables': analyze_template_variables(content),
            'content_preview': content[:200] + "..." if len(content) > 200 else content,
            'word_count': len(content.split()),
            'line_count': len(content.split('\n'))
        }
        
        # Try to extract subject line
        lines = content.split('\n')
        for line in lines:
            if line.strip().lower().startswith('subject:'):
                file_info['subject'] = line.replace('Subject:', '').replace('subject:', '').strip()
                break
        
        return file_info
        
    except Exception as e:
        return {
            'name': file_path.name,
            'path': str(file_path),
            'error': str(e),
            'variables': [],
            'size': 0
        }


def analyze_domain_templates(templates_dir, domain):
    """Analyze templates for a specific domain."""
    domain_path = Path(templates_dir) / domain
    templates = []
    
    if domain_path.exists():
        # Look for all template file types
        template_extensions = ['*.txt', '*.docx', '*.html', '*.md', '*.json']
        
        for extension in template_extensions:
            for file_path in domain_path.glob(extension):
                template_info = analyze_template_file(file_path)
                template_info['domain'] = domain
                templates.append(template_info)
                
    return templates


def analyze_scheduled_campaigns(scheduled_dir):
    """Analyze scheduled campaign files."""
    scheduled_path = Path(scheduled_dir)
    campaigns = []
    
    if scheduled_path.exists():
        # Look for campaign files
        campaign_extensions = ['*.txt', '*.docx', '*.html', '*.md', '*.json']
        
        for extension in campaign_extensions:
            for file_path in scheduled_path.glob(extension):
                campaign_info = analyze_template_file(file_path)
                campaign_info['type'] = 'scheduled_campaign'
                campaigns.append(campaign_info)
                
    return campaigns


def generate_template_statistics(all_templates):
    """Generate comprehensive template statistics."""
    if not all_templates:
        return {}
        
    # Basic statistics
    total_templates = len(all_templates)
    
    # Variable analysis
    all_variables = []
    for template in all_templates:
        all_variables.extend(template.get('variables', []))
        
    unique_variables = list(set(all_variables))
    variable_frequency = {}
    for var in all_variables:
        variable_frequency[var] = variable_frequency.get(var, 0) + 1
        
    # File type analysis
    file_types = {}
    for template in all_templates:
        ext = template.get('extension', 'unknown')
        file_types[ext] = file_types.get(ext, 0) + 1
        
    # Size analysis
    sizes = [t.get('size', 0) for t in all_templates if t.get('size', 0) > 0]
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    
    return {
        'total_templates': total_templates,
        'unique_variables': len(unique_variables),
        'most_common_variables': sorted(variable_frequency.items(), 
                                       key=lambda x: x[1], reverse=True)[:10],
        'file_types': file_types,
        'average_size_bytes': round(avg_size, 2),
        'templates_with_errors': len([t for t in all_templates if 'error' in t])
    }


def main():
    """Main template analysis function."""
    templates_dir = os.environ.get('TEMPLATES_DIR', 'campaign-templates')
    scheduled_dir = os.environ.get('SCHEDULED_DIR', 'scheduled-campaigns')
    
    print(f"Enhanced template analysis for:")
    print(f"  Templates directory: {templates_dir}")
    print(f"  Scheduled directory: {scheduled_dir}")
    
    # Standard domains to analyze
    domains = ['education', 'finance', 'healthcare', 'industry', 'technology', 'government']
    
    domain_stats = {}
    all_templates = []
    total_templates = 0
    
    print("Analyzing domain-based template structure...")
    
    # Analyze each domain
    for domain in domains:
        domain_templates = analyze_domain_templates(templates_dir, domain)
        
        domain_stats[domain] = {
            'template_count': len(domain_templates),
            'templates': [
                {
                    'name': t['name'],
                    'variables': t['variables'],
                    'size': t['size'],
                    'extension': t.get('extension', ''),
                    'subject': t.get('subject', '')
                } for t in domain_templates
            ]
        }
        
        all_templates.extend(domain_templates)
        total_templates += len(domain_templates)
        
        print(f"  - {domain}: {len(domain_templates)} templates")
    
    # Analyze scheduled campaigns
    scheduled_campaigns = analyze_scheduled_campaigns(scheduled_dir)
    scheduled_count = len(scheduled_campaigns)
    
    print(f"  - Scheduled campaigns: {scheduled_count}")
    
    # Generate comprehensive statistics
    template_stats = generate_template_statistics(all_templates + scheduled_campaigns)
    
    # Create comprehensive analysis
    domain_analysis = {
        'analysis_timestamp': datetime.now().isoformat(),
        'templates_directory': templates_dir,
        'scheduled_directory': scheduled_dir,
        'domain_count': len([d for d in domain_stats.values() if d['template_count'] > 0]),
        'template_count': total_templates,
        'scheduled_campaigns': scheduled_count,
        'domains': domain_stats,
        'scheduled_campaign_details': [
            {
                'name': c['name'],
                'variables': c['variables'],
                'size': c['size'],
                'extension': c.get('extension', ''),
                'subject': c.get('subject', '')
            } for c in scheduled_campaigns
        ],
        'overall_statistics': template_stats,
        'recommendations': []
    }
    
    # Generate recommendations
    recommendations = []
    
    if total_templates == 0:
        recommendations.append("No domain templates found - consider adding templates to domain subdirectories")
    
    if scheduled_count == 0:
        recommendations.append("No scheduled campaigns found - add campaign files to scheduled-campaigns directory")
    
    if template_stats.get('unique_variables', 0) == 0:
        recommendations.append("No template variables found - consider using {{name}}, {{email}} for personalization")
    
    common_vars = template_stats.get('most_common_variables', [])
    if common_vars and common_vars[0][1] < (total_templates * 0.5):
        recommendations.append("Low variable usage across templates - ensure consistent personalization")
    
    if template_stats.get('templates_with_errors', 0) > 0:
        recommendations.append(f"{template_stats['templates_with_errors']} templates have errors - review template files")
    
    domain_analysis['recommendations'] = recommendations
    
    # Save analysis
    with open('domain_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(domain_analysis, f, indent=2, default=str, ensure_ascii=False)
    
    # Output for GitHub Actions
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/stdout'), 'a') as f:
        f.write(f'campaigns={total_templates}\n')
    
    # Print summary
    print(f"\nTemplate analysis completed:")
    print(f"  - Total templates: {total_templates}")
    print(f"  - Scheduled campaigns: {scheduled_count}")
    print(f"  - Active domains: {domain_analysis['domain_count']}")
    print(f"  - Unique variables: {template_stats.get('unique_variables', 0)}")
    print(f"  - Recommendations: {len(recommendations)}")
    
    if template_stats.get('most_common_variables'):
        print(f"  - Most used variables: {[var[0] for var in template_stats['most_common_variables'][:5]]}")
    
    print(f"Analysis saved to domain_analysis.json")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
