#!/usr/bin/env python3
"""
Advanced reply analysis system for email campaign tracking.
Analyzes email replies, categorizes responses, and extracts insights.
"""

import imaplib
import email
import json
import re
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from email.header import decode_header
import time


class ReplyAnalyzer:
    """Advanced email reply analysis and categorization system."""
    
    def __init__(self, imap_host=None, imap_user=None, imap_pass=None, 
                 tracking_dir='tracking', enhanced_mode=True):
        self.imap_host = imap_host
        self.imap_user = imap_user
        self.imap_pass = imap_pass
        self.tracking_dir = Path(tracking_dir)
        self.enhanced_mode = enhanced_mode
        
        self.analysis_stats = {
            'total_replies': 0,
            'bounce_emails': 0,
            'auto_replies': 0,
            'genuine_feedback': 0,
            'unsubscribe_requests': 0,
            'positive_responses': 0,
            'negative_responses': 0,
            'neutral_responses': 0,
            'processing_errors': 0
        }
        
        # Pattern matching for different reply types
        self.bounce_patterns = [
            r'delivery.*failed',
            r'undelivered.*mail',
            r'mail.*delivery.*failure',
            r'delivery.*status.*notification',
            r'message.*could.*not.*be.*delivered',
            r'permanent.*failure',
            r'mailbox.*unavailable',
            r'user.*unknown',
            r'address.*not.*found'
        ]
        
        self.auto_reply_patterns = [
            r'out.*of.*office',
            r'automatic.*reply',
            r'away.*message',
            r'vacation.*response',
            r'i.*am.*currently.*away',
            r'thank.*you.*for.*your.*email',
            r'delivery.*receipt',
            r'read.*receipt',
            r'auto.*generated',
            r'do.*not.*reply'
        ]
        
        self.unsubscribe_patterns = [
            r'unsubscribe',
            r'remove.*from.*list',
            r'opt.*out',
            r'stop.*sending',
            r'no.*longer.*interested',
            r'please.*remove',
            r'take.*me.*off'
        ]
        
        self.positive_patterns = [
            r'thank.*you',
            r'interested',
            r'great.*opportunity',
            r'sounds.*good',
            r'would.*like.*more',
            r'please.*send.*more',
            r'tell.*me.*more',
            r'looks.*interesting'
        ]
        
        self.negative_patterns = [
            r'not.*interested',
            r'spam',
            r'annoying',
            r'inappropriate',
            r'waste.*of.*time',
            r'already.*have',
            r'don.*t.*need'
        ]
    
    def connect_imap(self):
        """Connect to IMAP server."""
        if not all([self.imap_host, self.imap_user, self.imap_pass]):
            raise ValueError("IMAP credentials not provided")
        
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host)
            mail.login(self.imap_user, self.imap_pass)
            return mail
        except Exception as e:
            raise Exception(f"IMAP connection failed: {e}")
    
    def decode_mime_header(self, header_value):
        """Decode MIME encoded email headers."""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_string += part.decode(encoding)
                else:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += part
        
        return decoded_string.strip()
    
    def extract_tracking_id(self, email_content):
        """Extract tracking ID from email content."""
        # Look for tracking IDs in various formats
        tracking_patterns = [
            r'tracking[-_]?id[:\s]*([a-zA-Z0-9\-_]+)',
            r'tid[:\s]*([a-zA-Z0-9\-_]+)',
            r'campaign[-_]?id[:\s]*([a-zA-Z0-9\-_]+)',
            r'ref[:\s]*([a-zA-Z0-9\-_]+)'
        ]
        
        for pattern in tracking_patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def categorize_reply_content(self, content):
        """Categorize reply based on content analysis."""
        content_lower = content.lower()
        
        # Check for bounce indicators
        is_bounce = any(re.search(pattern, content_lower) for pattern in self.bounce_patterns)
        
        # Check for auto-reply indicators
        is_auto_reply = any(re.search(pattern, content_lower) for pattern in self.auto_reply_patterns)
        
        # Check for unsubscribe requests
        is_unsubscribe = any(re.search(pattern, content_lower) for pattern in self.unsubscribe_patterns)
        
        # Sentiment analysis
        is_positive = any(re.search(pattern, content_lower) for pattern in self.positive_patterns)
        is_negative = any(re.search(pattern, content_lower) for pattern in self.negative_patterns)
        
        # Determine primary category
        if is_bounce:
            return 'bounce'
        elif is_auto_reply:
            return 'auto_reply'
        elif is_unsubscribe:
            return 'unsubscribe'
        elif is_positive:
            return 'positive'
        elif is_negative:
            return 'negative'
        else:
            return 'neutral'
    
    def extract_reply_insights(self, content, subject):
        """Extract insights and key information from reply."""
        insights = {
            'word_count': len(content.split()),
            'has_questions': '?' in content,
            'has_phone_number': bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content)),
            'has_email': bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)),
            'has_url': bool(re.search(r'https?://[^\s]+', content)),
            'urgency_indicators': [],
            'key_phrases': []
        }
        
        # Check for urgency indicators
        urgency_patterns = [
            r'urgent', r'asap', r'immediately', r'right away',
            r'time sensitive', r'deadline', r'expires'
        ]
        
        for pattern in urgency_patterns:
            if re.search(pattern, content.lower()):
                insights['urgency_indicators'].append(pattern)
        
        # Extract key phrases (simple approach)
        sentences = content.split('.')
        short_sentences = [s.strip() for s in sentences if 5 <= len(s.split()) <= 15]
        insights['key_phrases'] = short_sentences[:3]  # Top 3 key phrases
        
        return insights
    
    def analyze_single_email(self, raw_email):
        """Analyze a single email message."""
        try:
            msg = email.message_from_bytes(raw_email)
            
            # Extract basic information
            from_header = self.decode_mime_header(msg.get('From', ''))
            subject = self.decode_mime_header(msg.get('Subject', ''))
            date_str = msg.get('Date', '')
            message_id = msg.get('Message-ID', '')
            
            # Extract email content
            content = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            content += payload.decode('utf-8', errors='ignore')
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    content = payload.decode('utf-8', errors='ignore')
            
            # Parse date
            try:
                email_date = email.utils.parsedate_to_datetime(date_str)
            except:
                email_date = datetime.now()
            
            # Extract tracking information
            tracking_id = self.extract_tracking_id(content)
            
            # Categorize reply
            category = self.categorize_reply_content(content)
            
            # Extract insights
            insights = self.extract_reply_insights(content, subject) if self.enhanced_mode else {}
            
            # Create analysis result
            analysis_result = {
                'message_id': message_id,
                'from_email': from_header,
                'subject': subject,
                'date': email_date.isoformat() if email_date else None,
                'category': category,
                'tracking_id': tracking_id,
                'content_preview': content[:200] + "..." if len(content) > 200 else content,
                'full_content': content if self.enhanced_mode else None,
                'insights': insights,
                'analysis_timestamp': datetime.now().isoformat(),
                'bounce': category == 'bounce',
                'auto_reply': category == 'auto_reply',
                'unsubscribe': category == 'unsubscribe'
            }
            
            # Update statistics
            self.analysis_stats['total_replies'] += 1
            if category == 'bounce':
                self.analysis_stats['bounce_emails'] += 1
            elif category == 'auto_reply':
                self.analysis_stats['auto_replies'] += 1
            elif category == 'unsubscribe':
                self.analysis_stats['unsubscribe_requests'] += 1
            elif category == 'positive':
                self.analysis_stats['positive_responses'] += 1
                self.analysis_stats['genuine_feedback'] += 1
            elif category == 'negative':
                self.analysis_stats['negative_responses'] += 1
                self.analysis_stats['genuine_feedback'] += 1
            else:
                self.analysis_stats['neutral_responses'] += 1
                self.analysis_stats['genuine_feedback'] += 1
            
            return analysis_result
            
        except Exception as e:
            self.analysis_stats['processing_errors'] += 1
            return {
                'error': f"Failed to analyze email: {e}",
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def fetch_and_analyze_replies(self, days_back=7, mark_seen=False):
        """Fetch and analyze email replies from the specified time period."""
        if not all([self.imap_host, self.imap_user, self.imap_pass]):
            print("IMAP credentials not available. Creating placeholder analysis.")
            return self.create_placeholder_analysis()
        
        try:
            mail = self.connect_imap()
            mail.select('INBOX')
            
            # Calculate date range
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')
            
            # Search for emails
            search_criteria = f'(SINCE {since_date})'
            result, message_numbers = mail.search(None, search_criteria)
            
            if result != 'OK':
                raise Exception(f"Email search failed: {result}")
            
            message_numbers = message_numbers[0].split()
            analyzed_replies = []
            
            print(f"Found {len(message_numbers)} emails to analyze")
            
            for i, num in enumerate(message_numbers):
                try:
                    # Fetch email
                    result, msg_data = mail.fetch(num, '(RFC822)')
                    if result != 'OK':
                        continue
                    
                    raw_email = msg_data[0][1]
                    analysis = self.analyze_single_email(raw_email)
                    analyzed_replies.append(analysis)
                    
                    # Mark as seen if requested
                    if mark_seen:
                        mail.store(num, '+FLAGS', '\\Seen')
                    
                    # Progress indication
                    if (i + 1) % 10 == 0:
                        print(f"Analyzed {i + 1}/{len(message_numbers)} emails")
                
                except Exception as e:
                    print(f"Error analyzing email {num}: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
            return analyzed_replies
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return self.create_placeholder_analysis()
    
    def create_placeholder_analysis(self):
        """Create placeholder analysis when IMAP is not available."""
        return [{
            'message_id': 'placeholder',
            'from_email': 'placeholder@example.com',
            'subject': 'Placeholder analysis',
            'date': datetime.now().isoformat(),
            'category': 'neutral',
            'tracking_id': None,
            'content_preview': 'IMAP credentials not available for real analysis',
            'analysis_timestamp': datetime.now().isoformat(),
            'bounce': False,
            'auto_reply': False,
            'unsubscribe': False,
            'placeholder': True
        }]
    
    def generate_analysis_report(self, analyzed_replies):
        """Generate comprehensive analysis report."""
        # Calculate metrics
        total_replies = len(analyzed_replies)
        
        if total_replies == 0:
            bounce_rate = 0
            auto_reply_rate = 0
            unsubscribe_rate = 0
            positive_rate = 0
            negative_rate = 0
        else:
            bounce_rate = (self.analysis_stats['bounce_emails'] / total_replies) * 100
            auto_reply_rate = (self.analysis_stats['auto_replies'] / total_replies) * 100
            unsubscribe_rate = (self.analysis_stats['unsubscribe_requests'] / total_replies) * 100
            positive_rate = (self.analysis_stats['positive_responses'] / total_replies) * 100
            negative_rate = (self.analysis_stats['negative_responses'] / total_replies) * 100
        
        # Categorize replies by type
        reply_categories = {}
        tracking_ids = {}
        domain_analysis = {}
        
        for reply in analyzed_replies:
            if reply.get('placeholder'):
                continue
                
            # Category analysis
            category = reply.get('category', 'unknown')
            reply_categories[category] = reply_categories.get(category, 0) + 1
            
            # Tracking ID analysis
            tid = reply.get('tracking_id')
            if tid:
                tracking_ids[tid] = tracking_ids.get(tid, 0) + 1
            
            # Domain analysis
            from_email = reply.get('from_email', '')
            if '@' in from_email:
                domain = from_email.split('@')[-1].lower()
                domain_analysis[domain] = domain_analysis.get(domain, 0) + 1
        
        # Generate insights
        insights = []
        
        if bounce_rate > 10:
            insights.append(f"High bounce rate ({bounce_rate:.1f}%) indicates potential email delivery issues")
        
        if unsubscribe_rate > 5:
            insights.append(f"Unsubscribe rate ({unsubscribe_rate:.1f}%) may indicate targeting or content issues")
        
        if positive_rate > negative_rate and positive_rate > 10:
            insights.append(f"Positive response rate ({positive_rate:.1f}%) suggests good campaign reception")
        
        if len(tracking_ids) > 0:
            insights.append(f"Tracking IDs found in {len(tracking_ids)} replies, enabling campaign attribution")
        
        # Create comprehensive report
        report = {
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_replies_analyzed': total_replies,
                'analysis_mode': 'enhanced' if self.enhanced_mode else 'basic',
                'processing_errors': self.analysis_stats['processing_errors']
            },
            'summary_statistics': {
                'total_replies': total_replies,
                'bounce_emails': self.analysis_stats['bounce_emails'],
                'auto_replies': self.analysis_stats['auto_replies'],
                'genuine_feedback': self.analysis_stats['genuine_feedback'],
                'unsubscribe_requests': self.analysis_stats['unsubscribe_requests'],
                'positive_responses': self.analysis_stats['positive_responses'],
                'negative_responses': self.analysis_stats['negative_responses'],
                'neutral_responses': self.analysis_stats['neutral_responses']
            },
            'performance_metrics': {
                'bounce_rate': round(bounce_rate, 2),
                'auto_reply_rate': round(auto_reply_rate, 2),
                'unsubscribe_rate': round(unsubscribe_rate, 2),
                'positive_response_rate': round(positive_rate, 2),
                'negative_response_rate': round(negative_rate, 2),
                'engagement_rate': round((self.analysis_stats['genuine_feedback'] / total_replies * 100) if total_replies > 0 else 0, 2)
            },
            'categorization_breakdown': reply_categories,
            'tracking_analysis': {
                'tracked_replies': len(tracking_ids),
                'tracking_ids_found': list(tracking_ids.keys())[:10],  # Top 10
                'tracking_coverage': round((len(tracking_ids) / total_replies * 100) if total_replies > 0 else 0, 2)
            },
            'domain_analysis': dict(sorted(domain_analysis.items(), key=lambda x: x[1], reverse=True)[:10]),
            'insights_and_recommendations': insights,
            'detailed_replies': analyzed_replies if self.enhanced_mode else []
        }
        
        return report
    
    def save_analysis_results(self, analyzed_replies, report):
        """Save analysis results to tracking directory."""
        # Create tracking directories
        reply_tracking_dir = self.tracking_dir / 'reply_tracking'
        reply_tracking_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save detailed analysis
        detailed_file = reply_tracking_dir / f'detailed_reply_analysis_{timestamp}.json'
        try:
            with open(detailed_file, 'w') as f:
                json.dump(analyzed_replies, f, indent=2, default=str)
            print(f"Detailed analysis saved: {detailed_file}")
        except Exception as e:
            print(f"Error saving detailed analysis: {e}")
        
        # Save summary report
        report_file = reply_tracking_dir / f'reply_analysis_report_{timestamp}.json'
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Analysis report saved: {report_file}")
        except Exception as e:
            print(f"Error saving analysis report: {e}")
        
        # Save current analysis (for workflow integration)
        current_file = reply_tracking_dir / 'enhanced_reply_analysis.json'
        try:
            with open(current_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Current analysis saved: {current_file}")
        except Exception as e:
            print(f"Error saving current analysis: {e}")
    
    def print_analysis_summary(self, report):
        """Print analysis summary to console."""
        print("\n" + "="*60)
        print("EMAIL REPLY ANALYSIS SUMMARY")
        print("="*60)
        
        metrics = report['performance_metrics']
        stats = report['summary_statistics']
        
        print(f"Total Replies Analyzed: {stats['total_replies']}")
        print(f"Bounce Rate: {metrics['bounce_rate']}%")
        print(f"Auto-Reply Rate: {metrics['auto_reply_rate']}%")
        print(f"Unsubscribe Rate: {metrics['unsubscribe_rate']}%")
        print(f"Positive Response Rate: {metrics['positive_response_rate']}%")
        print(f"Negative Response Rate: {metrics['negative_response_rate']}%")
        print(f"Overall Engagement Rate: {metrics['engagement_rate']}%")
        
        if report['insights_and_recommendations']:
            print("\nKey Insights:")
            for insight in report['insights_and_recommendations']:
                print(f"• {insight}")
        
        print("\nReply Categories:")
        for category, count in report['categorization_breakdown'].items():
            percentage = (count / stats['total_replies'] * 100) if stats['total_replies'] > 0 else 0
            print(f"• {category.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
        
        print("="*60)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Email Reply Analysis System')
    parser.add_argument('--tracking-dir', default='tracking', help='Tracking directory path')
    parser.add_argument('--days-back', type=int, default=7, help='Days to look back for emails')
    parser.add_argument('--mark-seen', action='store_true', help='Mark analyzed emails as seen')
    parser.add_argument('--enhanced-mode', action='store_true', default=True, help='Enable enhanced analysis')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Get IMAP credentials from environment
    imap_host = os.getenv('IMAP_HOST')
    imap_user = os.getenv('IMAP_USER')
    imap_pass = os.getenv('IMAP_PASS')
    
    print("Email Reply Analysis System")
    print("="*40)
    
    # Initialize analyzer
    analyzer = ReplyAnalyzer(
        imap_host=imap_host,
        imap_user=imap_user,
        imap_pass=imap_pass,
        tracking_dir=args.tracking_dir,
        enhanced_mode=args.enhanced_mode
    )
    
    # Fetch and analyze replies
    print(f"Analyzing replies from last {args.days_back} days...")
    analyzed_replies = analyzer.fetch_and_analyze_replies(
        days_back=args.days_back,
        mark_seen=args.mark_seen
    )
    
    # Generate report
    report = analyzer.generate_analysis_report(analyzed_replies)
    
    # Save results
    analyzer.save_analysis_results(analyzed_replies, report)
    
    # Print summary
    analyzer.print_analysis_summary(report)
    
    if args.verbose:
        print(f"\nDetailed analysis saved to: {args.tracking_dir}/reply_tracking/")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
