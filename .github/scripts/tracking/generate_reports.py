#!/usr/bin/env python3
"""
Comprehensive report generation system for email campaign analytics.
Generates detailed reports, visualizations, and insights from campaign data.
"""

import json
import os
import sys
import glob
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import pandas as pd
from collections import defaultdict
import re


class CampaignReportGenerator:
    """Comprehensive campaign analytics and report generation system."""
    
    def __init__(self, tracking_dir='tracking', reports_dir='reports'):
        self.tracking_dir = Path(tracking_dir)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.campaign_data = {}
        self.contact_data = {}
        self.reply_data = {}
        self.execution_data = {}
        
    def load_tracking_data(self):
        """Load all available tracking data from various sources."""
        print("Loading tracking data from multiple sources...")
        
        # Load execution data
        self.load_execution_data()
        
        # Load reply analysis data
        self.load_reply_data()
        
        # Load contact analysis data
        self.load_contact_data()
        
        # Load any additional tracking files
        self.load_additional_tracking()
        
        print(f"Data loaded: {len(self.execution_data)} execution records, "
              f"{len(self.reply_data)} reply records, {len(self.contact_data)} contact records")
    
    def load_execution_data(self):
        """Load campaign execution data."""
        execution_files = []
        
        # Look for execution logs and reports
        for pattern in ['execution_logs/*.json', 'enhanced_execution_report_*.json', 
                       'execution_summary_*.json', '*.log']:
            files = list(self.tracking_dir.glob(pattern))
            execution_files.extend(files)
        
        for file_path in execution_files:
            try:
                if file_path.suffix == '.json':
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        self.execution_data[file_path.name] = data
                elif file_path.suffix == '.log':
                    with open(file_path, 'r') as f:
                        content = f.read()
                        self.execution_data[file_path.name] = {
                            'type': 'log_file',
                            'content': content,
                            'parsed_metrics': self.parse_log_metrics(content)
                        }
            except Exception as e:
                print(f"Error loading execution data from {file_path}: {e}")
    
    def load_reply_data(self):
        """Load reply analysis data."""
        reply_files = list(self.tracking_dir.glob('reply_tracking/*.json'))
        
        for file_path in reply_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.reply_data[file_path.name] = data
            except Exception as e:
                print(f"Error loading reply data from {file_path}: {e}")
    
    def load_contact_data(self):
        """Load contact analysis and campaign data."""
        # Look for contact analysis files in root and tracking directory
        for search_dir in [Path('.'), self.tracking_dir]:
            for pattern in ['contact_analysis.json', 'domain_analysis.json', 
                           'enhanced_reply_analysis.json']:
                files = list(search_dir.glob(pattern))
                for file_path in files:
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            self.contact_data[file_path.name] = data
                    except Exception as e:
                        print(f"Error loading contact data from {file_path}: {e}")
    
    def load_additional_tracking(self):
        """Load additional tracking files."""
        additional_patterns = [
            'feedback_responses/*.json',
            'domain_stats/*.json',
            'batch_reports/*.json',
            'execution_start.json',
            'execution_complete.json'
        ]
        
        for pattern in additional_patterns:
            files = list(self.tracking_dir.glob(pattern))
            for file_path in files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        # Categorize data by type
                        if 'feedback' in file_path.name:
                            key = f"feedback_{file_path.name}"
                        elif 'domain' in file_path.name:
                            key = f"domain_{file_path.name}"
                        elif 'batch' in file_path.name:
                            key = f"batch_{file_path.name}"
                        else:
                            key = file_path.name
                        
                        self.campaign_data[key] = data
                        
                except Exception as e:
                    print(f"Error loading additional data from {file_path}: {e}")
    
    def parse_log_metrics(self, log_content):
        """Parse metrics from log file content."""
        metrics = {
            'total_lines': len(log_content.split('\n')),
            'errors': log_content.count('ERROR'),
            'warnings': log_content.count('WARNING'),
            'success_indicators': log_content.count('SUCCESS'),
            'contacts_processed': 0,
            'emails_sent': 0,
            'personalizations': 0
        }
        
        # Extract numeric metrics using regex
        patterns = {
            'contacts_processed': r'(?:contacts?.*?processed|processed.*?contacts?)[:\s]*(\d+)',
            'emails_sent': r'(?:emails?.*?sent|sent.*?emails?)[:\s]*(\d+)',
            'personalizations': r'(?:personalizations?|substitutions?)[:\s]*(\d+)'
        }
        
        for metric, pattern in patterns.items():
            matches = re.findall(pattern, log_content, re.IGNORECASE)
            if matches:
                try:
                    metrics[metric] = max([int(m) for m in matches])
                except ValueError:
                    pass
        
        return metrics
    
    def calculate_campaign_metrics(self):
        """Calculate comprehensive campaign performance metrics."""
        metrics = {
            'execution_metrics': {},
            'reply_metrics': {},
            'contact_metrics': {},
            'overall_performance': {}
        }
        
        # Calculate execution metrics
        total_contacts = 0
        total_emails_sent = 0
        total_errors = 0
        execution_count = 0
        
        for filename, data in self.execution_data.items():
            if isinstance(data, dict):
                if 'parsed_metrics' in data:
                    parsed = data['parsed_metrics']
                    total_contacts += parsed.get('contacts_processed', 0)
                    total_emails_sent += parsed.get('emails_sent', 0)
                    total_errors += parsed.get('errors', 0)
                    execution_count += 1
                elif 'execution_statistics' in data:
                    stats = data['execution_statistics']
                    total_contacts += stats.get('contacts_processed', 0)
                    total_emails_sent += stats.get('emails_sent', 0)
                    total_errors += stats.get('errors', 0)
                    execution_count += 1
        
        metrics['execution_metrics'] = {
            'total_contacts_processed': total_contacts,
            'total_emails_sent': total_emails_sent,
            'total_execution_errors': total_errors,
            'execution_runs': execution_count,
            'average_contacts_per_run': total_contacts / execution_count if execution_count > 0 else 0,
            'success_rate': ((execution_count - total_errors) / execution_count * 100) if execution_count > 0 else 0
        }
        
        # Calculate reply metrics
        total_replies = 0
        total_bounces = 0
        total_positive = 0
        total_negative = 0
        total_unsubscribes = 0
        
        for filename, data in self.reply_data.items():
            if isinstance(data, dict) and 'summary_statistics' in data:
                stats = data['summary_statistics']
                total_replies += stats.get('total_replies', 0)
                total_bounces += stats.get('bounce_emails', 0)
                total_positive += stats.get('positive_responses', 0)
                total_negative += stats.get('negative_responses', 0)
                total_unsubscribes += stats.get('unsubscribe_requests', 0)
        
        metrics['reply_metrics'] = {
            'total_replies': total_replies,
            'bounce_count': total_bounces,
            'positive_responses': total_positive,
            'negative_responses': total_negative,
            'unsubscribe_requests': total_unsubscribes,
            'bounce_rate': (total_bounces / total_replies * 100) if total_replies > 0 else 0,
            'response_rate': (total_replies / total_emails_sent * 100) if total_emails_sent > 0 else 0,
            'positive_rate': (total_positive / total_replies * 100) if total_replies > 0 else 0,
             'negative_rate': (total_negative / total_replies * 100) if total_replies > 0 else 0,  # ADD THIS LINE
            'unsubscribe_rate': (total_unsubscribes / total_replies * 100) if total_replies > 0 else 0
        }
        
        # Calculate contact metrics
        unique_contacts = 0
        contact_sources = 0
        domains_reached = 0
        
        for filename, data in self.contact_data.items():
            if 'contact_analysis.json' in filename and isinstance(data, dict):
                unique_contacts = data.get('total_contacts', 0)
                contact_sources = len(data.get('sources_breakdown', {}))
                domains_reached = len(data.get('domain_breakdown', {}))
        
        metrics['contact_metrics'] = {
            'unique_contacts': unique_contacts,
            'contact_sources': contact_sources,
            'domains_reached': domains_reached,
            'contacts_per_source': unique_contacts / contact_sources if contact_sources > 0 else 0
        }
        
        # Calculate overall performance
        delivery_rate = ((total_emails_sent - total_bounces) / total_emails_sent * 100) if total_emails_sent > 0 else 0
        engagement_quality = (total_positive - total_negative) / total_replies if total_replies > 0 else 0
        
        metrics['overall_performance'] = {
            'delivery_rate': delivery_rate,
            'engagement_quality_score': engagement_quality,
            'campaign_reach': unique_contacts,
            'campaign_effectiveness': delivery_rate * (total_positive / total_emails_sent) if total_emails_sent > 0 else 0
        }
        
        return metrics
    
    def generate_executive_summary(self, metrics):
        """Generate executive summary of campaign performance."""
        exec_metrics = metrics['execution_metrics']
        reply_metrics = metrics['reply_metrics']
        contact_metrics = metrics['contact_metrics']
        overall_metrics = metrics['overall_performance']
        
        # Determine overall campaign status
        if overall_metrics['delivery_rate'] > 90 and reply_metrics['bounce_rate'] < 5:
            campaign_status = "EXCELLENT"
        elif overall_metrics['delivery_rate'] > 80 and reply_metrics['bounce_rate'] < 10:
            campaign_status = "GOOD"
        elif overall_metrics['delivery_rate'] > 70:
            campaign_status = "SATISFACTORY"
        else:
            campaign_status = "NEEDS_IMPROVEMENT"
        
        summary = {
            'campaign_status': campaign_status,
            'key_achievements': [],
            'areas_for_improvement': [],
            'recommendations': [],
            'next_steps': []
        }
        
        # Key achievements
        if exec_metrics['total_contacts_processed'] > 100:
            summary['key_achievements'].append(f"Successfully processed {exec_metrics['total_contacts_processed']} contacts")
        
        if reply_metrics['positive_rate'] > 10:
            summary['key_achievements'].append(f"Achieved {reply_metrics['positive_rate']:.1f}% positive response rate")
        
        if overall_metrics['delivery_rate'] > 85:
            summary['key_achievements'].append(f"High delivery rate of {overall_metrics['delivery_rate']:.1f}%")
        
        # Areas for improvement
        if reply_metrics['bounce_rate'] > 10:
            summary['areas_for_improvement'].append(f"High bounce rate ({reply_metrics['bounce_rate']:.1f}%) indicates email quality issues")
        
        if reply_metrics['unsubscribe_rate'] > 5:
            summary['areas_for_improvement'].append(f"Elevated unsubscribe rate ({reply_metrics['unsubscribe_rate']:.1f}%) suggests content or targeting concerns")
        
        if reply_metrics['response_rate'] < 2:
            summary['areas_for_improvement'].append(f"Low response rate ({reply_metrics['response_rate']:.1f}%) may indicate engagement issues")
        
        # Recommendations
        if reply_metrics['bounce_rate'] > 5:
            summary['recommendations'].append("Implement email validation to reduce bounce rates")
        
        if reply_metrics['positive_rate'] < reply_metrics['negative_rate']:
            summary['recommendations'].append("Review and improve email content to increase positive responses")
        
        if contact_metrics['contact_sources'] < 3:
            summary['recommendations'].append("Diversify contact data sources to improve campaign reach")
        
        # Next steps
        summary['next_steps'].append("Monitor reply trends and adjust campaign strategy accordingly")
        summary['next_steps'].append("Analyze high-performing segments for future targeting")
        if reply_metrics['total_replies'] > 0:
            summary['next_steps'].append("Follow up on positive responses for lead nurturing")
        
        return summary
    
    def generate_detailed_analysis(self, metrics):
        """Generate detailed campaign analysis with insights."""
        analysis = {
            'performance_analysis': {},
            'trend_analysis': {},
            'segmentation_insights': {},
            'technical_analysis': {}
        }
        
        # Performance analysis
        exec_metrics = metrics['execution_metrics']
        reply_metrics = metrics['reply_metrics']
        
        analysis['performance_analysis'] = {
            'execution_efficiency': {
                'contacts_processed': exec_metrics['total_contacts_processed'],
                'average_per_run': exec_metrics['average_contacts_per_run'],
                'success_rate': exec_metrics['success_rate'],
                'error_rate': (exec_metrics['total_execution_errors'] / exec_metrics['execution_runs']) if exec_metrics['execution_runs'] > 0 else 0
            },
            'email_delivery': {
                'total_sent': exec_metrics['total_emails_sent'],
                'delivery_rate': metrics['overall_performance']['delivery_rate'],
                'bounce_analysis': {
                    'bounce_count': reply_metrics['bounce_count'],
                    'bounce_rate': reply_metrics['bounce_rate'],
                    'impact_on_delivery': reply_metrics['bounce_count'] / exec_metrics['total_emails_sent'] * 100 if exec_metrics['total_emails_sent'] > 0 else 0
                }
            },
            'engagement_metrics': {
                'response_rate': reply_metrics['response_rate'],
                'positive_engagement': reply_metrics['positive_rate'],
                'negative_feedback': reply_metrics['negative_responses'],
                'engagement_quality': metrics['overall_performance']['engagement_quality_score']
            }
        }
        
        # Technical analysis
        analysis['technical_analysis'] = {
            'system_performance': {
                'execution_runs': exec_metrics['execution_runs'],
                'average_contacts_per_execution': exec_metrics['average_contacts_per_run'],
                'error_frequency': exec_metrics['total_execution_errors'] / exec_metrics['execution_runs'] if exec_metrics['execution_runs'] > 0 else 0
            },
            'data_quality': {
                'contact_sources_utilized': metrics['contact_metrics']['contact_sources'],
                'domain_diversity': metrics['contact_metrics']['domains_reached'],
                'data_distribution': metrics['contact_metrics']['contacts_per_source']
            }
        }
        
        return analysis
    
    def create_campaign_timeline(self):
        """Create timeline of campaign activities."""
        timeline = []
        
        # Collect timestamps from various data sources
        for filename, data in {**self.execution_data, **self.reply_data, **self.campaign_data}.items():
            if isinstance(data, dict):
                timestamp = None
                event_type = "unknown"
                description = filename
                
                # Extract timestamp and event type
                if 'execution_timestamp' in data:
                    timestamp = data['execution_timestamp']
                    event_type = "execution"
                elif 'analysis_timestamp' in data:
                    timestamp = data['analysis_timestamp']
                    event_type = "analysis"
                elif 'timestamp' in data:
                    timestamp = data['timestamp']
                elif 'execution_start' in data:
                    timestamp = data['execution_start']
                    event_type = "execution_start"
                elif 'execution_end' in data:
                    timestamp = data['execution_end']
                    event_type = "execution_end"
                
                if timestamp:
                    timeline.append({
                        'timestamp': timestamp,
                        'event_type': event_type,
                        'description': description,
                        'source_file': filename
                    })
        
        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        return timeline
    
    def generate_comprehensive_report(self):
        """Generate comprehensive campaign report."""
        print("Generating comprehensive campaign report...")
        
        # Load all data
        self.load_tracking_data()
        
        # Calculate metrics
        metrics = self.calculate_campaign_metrics()
        
        # Generate analysis components
        executive_summary = self.generate_executive_summary(metrics)
        detailed_analysis = self.generate_detailed_analysis(metrics)
        timeline = self.create_campaign_timeline()
        
        # Create comprehensive report structure
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_version': '1.0',
                'data_sources': {
                    'execution_files': len(self.execution_data),
                    'reply_files': len(self.reply_data),
                    'contact_files': len(self.contact_data),
                    'additional_files': len(self.campaign_data)
                }
            },
            'executive_summary': executive_summary,
            'campaign_metrics': metrics,
            'detailed_analysis': detailed_analysis,
            'campaign_timeline': timeline,
            'raw_data_summary': {
                'execution_data_available': bool(self.execution_data),
                'reply_data_available': bool(self.reply_data),
                'contact_data_available': bool(self.contact_data),
                'additional_tracking_available': bool(self.campaign_data)
            }
        }
        
        return report
    
    def save_report_files(self, report):
        """Save report in multiple formats."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save comprehensive JSON report
        json_report_file = self.reports_dir / f'comprehensive_campaign_report_{timestamp}.json'
        try:
            with open(json_report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Comprehensive report saved: {json_report_file}")
        except Exception as e:
            print(f"Error saving JSON report: {e}")
        
        # Save executive summary as markdown
        self.save_executive_summary_markdown(report, timestamp)
        
        # Save metrics summary as CSV
        self.save_metrics_csv(report, timestamp)
        
        return json_report_file
    
    def save_executive_summary_markdown(self, report, timestamp):
        """Save executive summary as markdown file."""
        summary = report['executive_summary']
        metrics = report['campaign_metrics']
        
        markdown_content = f"""# Email Campaign Executive Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Campaign Status: {summary['campaign_status']}

### Key Performance Metrics

**Execution Performance:**
- Contacts Processed: {metrics['execution_metrics']['total_contacts_processed']:,}
- Emails Sent: {metrics['execution_metrics']['total_emails_sent']:,}
- Success Rate: {metrics['execution_metrics']['success_rate']:.1f}%

**Delivery & Engagement:**
- Delivery Rate: {metrics['overall_performance']['delivery_rate']:.1f}%
- Response Rate: {metrics['reply_metrics']['response_rate']:.1f}%
- Bounce Rate: {metrics['reply_metrics']['bounce_rate']:.1f}%

**Response Analysis:**
- Total Replies: {metrics['reply_metrics']['total_replies']:,}
- Positive Responses: {metrics['reply_metrics']['positive_responses']:,} ({metrics['reply_metrics']['positive_rate']:.1f}%)
- Unsubscribe Rate: {metrics['reply_metrics']['unsubscribe_rate']:.1f}%

### Key Achievements
"""
        
        for achievement in summary['key_achievements']:
            markdown_content += f"- {achievement}\n"
        
        if summary['areas_for_improvement']:
            markdown_content += "\n### Areas for Improvement\n"
            for area in summary['areas_for_improvement']:
                markdown_content += f"- {area}\n"
        
        if summary['recommendations']:
            markdown_content += "\n### Recommendations\n"
            for rec in summary['recommendations']:
                markdown_content += f"- {rec}\n"
        
        if summary['next_steps']:
            markdown_content += "\n### Next Steps\n"
            for step in summary['next_steps']:
                markdown_content += f"- {step}\n"
        
        # Save markdown file
        md_file = self.reports_dir / f'executive_summary_{timestamp}.md'
        try:
            with open(md_file, 'w') as f:
                f.write(markdown_content)
            print(f"Executive summary saved: {md_file}")
        except Exception as e:
            print(f"Error saving markdown summary: {e}")
    
    def save_metrics_csv(self, report, timestamp):
        """Save key metrics as CSV file."""
        metrics = report['campaign_metrics']
        
        # Flatten metrics for CSV
        csv_data = []
        
        for category, category_metrics in metrics.items():
            for metric_name, value in category_metrics.items():
                csv_data.append({
                    'category': category,
                    'metric': metric_name,
                    'value': value,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Save CSV file
        csv_file = self.reports_dir / f'campaign_metrics_{timestamp}.csv'
        try:
            df = pd.DataFrame(csv_data)
            df.to_csv(csv_file, index=False)
            print(f"Metrics CSV saved: {csv_file}")
        except Exception as e:
            print(f"Error saving CSV metrics: {e}")
    
    def print_report_summary(self, report):
        """Print report summary to console."""
        print("\n" + "="*70)
        print("COMPREHENSIVE CAMPAIGN REPORT SUMMARY")
        print("="*70)
        
        summary = report['executive_summary']
        metrics = report['campaign_metrics']
        
        print(f"Campaign Status: {summary['campaign_status']}")
        print(f"Report Generated: {report['report_metadata']['generated_at']}")
        print()
        
        print("KEY METRICS:")
        print(f"  Contacts Processed: {metrics['execution_metrics']['total_contacts_processed']:,}")
        print(f"  Emails Sent: {metrics['execution_metrics']['total_emails_sent']:,}")
        print(f"  Delivery Rate: {metrics['overall_performance']['delivery_rate']:.1f}%")
        print(f"  Response Rate: {metrics['reply_metrics']['response_rate']:.1f}%")
        print(f"  Bounce Rate: {metrics['reply_metrics']['bounce_rate']:.1f}%")
        print()
        
        if summary['key_achievements']:
            print("KEY ACHIEVEMENTS:")
            for achievement in summary['key_achievements']:
                print(f"  ✓ {achievement}")
            print()
        
        if summary['recommendations']:
            print("RECOMMENDATIONS:")
            for rec in summary['recommendations']:
                print(f"  → {rec}")
            print()
        
        print(f"Data Sources: {report['report_metadata']['data_sources']['execution_files']} execution, "
              f"{report['report_metadata']['data_sources']['reply_files']} reply, "
              f"{report['report_metadata']['data_sources']['contact_files']} contact files")
        print("="*70)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Campaign Report Generator')
    parser.add_argument('--tracking-dir', default='tracking', help='Tracking directory path')
    parser.add_argument('--reports-dir', default='reports', help='Reports output directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--format', choices=['json', 'markdown', 'csv', 'all'], default='all',
                       help='Output format')
    
    args = parser.parse_args()
    
    print("Campaign Report Generator")
    print("=" * 40)
    
    # Initialize report generator
    generator = CampaignReportGenerator(
        tracking_dir=args.tracking_dir,
        reports_dir=args.reports_dir
    )
    
    # Generate comprehensive report
    report = generator.generate_comprehensive_report()
    
    # Save report files
    report_file = generator.save_report_files(report)
    
    # Print summary
    generator.print_report_summary(report)
    
    if args.verbose:
        print(f"\nDetailed reports saved to: {args.reports_dir}/")
        print(f"Main report file: {report_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
