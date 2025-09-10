#!/usr/bin/env python3
"""
Email Feedback Injector - Automatically adds feedback email to all outgoing campaigns
"""
import re
import json
from pathlib import Path

class EmailFeedbackInjector:
    def __init__(self, feedback_email="feedback@modelphysmat.com"):
        self.feedback_email = feedback_email
        self.feedback_templates = {
            "footer_signature": self._generate_footer_signature(),
            "header_notice": self._generate_header_notice(),
            "inline_callout": self._generate_inline_callout(),
            "reply_to_addition": self._generate_reply_to_addition()
        }
    
    def _generate_footer_signature(self):
        """Generate professional footer with feedback email"""
        return f"""

---
📧 **We value your feedback!** 
Have thoughts on this outreach? Please share them with us at: {self.feedback_email}

🔄 **Help us improve** - Your input helps us create better, more relevant communications.

This email was sent as part of our outreach initiative. If you have any concerns or feedback about our communication, please don't hesitate to reach out to {self.feedback_email}.
"""
    
    def _generate_header_notice(self):
        """Generate subtle header notice"""
        return f"""📝 *Your feedback matters to us - {self.feedback_email}*

"""
    
    def _generate_inline_callout(self):
        """Generate inline feedback callout"""
        return f"""

💬 **Quick feedback?** Drop us a line at {self.feedback_email} - we read every message!

"""
    
    def _generate_reply_to_addition(self):
        """Generate reply-to field addition"""
        return {
            "reply_to": self.feedback_email,
            "cc": [self.feedback_email]  # Optional: CC feedback email
        }
    
    def inject_into_template_content(self, content, injection_type="footer_signature"):
        """Inject feedback email into email content"""
        
        if injection_type not in self.feedback_templates:
            raise ValueError(f"Unknown injection type: {injection_type}")
        
        injection_content = self.feedback_templates[injection_type]
        
        if injection_type == "header_notice":
            # Add at the beginning
            return injection_content + content
        
        elif injection_type == "footer_signature":
            # Add at the end
            return content + injection_content
        
        elif injection_type == "inline_callout":
            # Insert in the middle (after first paragraph)
            paragraphs = content.split('\n\n')
            if len(paragraphs) > 1:
                return paragraphs[0] + injection_content + '\n\n'.join(paragraphs[1:])
            else:
                return content + injection_content
        
        return content
    
    def process_campaign_config(self, config_path, injection_type="footer_signature"):
        """Process campaign config to add feedback email settings"""
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Add feedback email to config
        if 'feedback' not in config:
            config['feedback'] = {}
        
        config['feedback'].update({
            'email': self.feedback_email,
            'injection_type': injection_type,
            'auto_inject': True,
            'reply_to_feedback': True
        })
        
        # Update reply-to if not specified
        if 'reply_to' not in config:
            config['reply_to'] = self.feedback_email
        
        # Add feedback CC if requested
        if injection_type == "reply_to_addition":
            if 'cc' not in config:
                config['cc'] = []
            if self.feedback_email not in config['cc']:
                config['cc'].append(self.feedback_email)
        
        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config
    
    def process_all_campaign_configs(self, scheduled_campaigns_dir="scheduled-campaigns"):
        """Process all campaign configs in directory"""
        campaigns_path = Path(scheduled_campaigns_dir)
        processed_configs = []
        
        if not campaigns_path.exists():
            print(f"⚠️  Directory not found: {scheduled_campaigns_dir}")
            return processed_configs
        
        for config_file in campaigns_path.glob("*.json"):
            try:
                print(f"Processing: {config_file.name}")
                config = self.process_campaign_config(config_file)
                processed_configs.append({
                    'file': str(config_file),
                    'name': config.get('name', 'Unknown'),
                    'feedback_enabled': True
                })
                print(f"✅ Added feedback email to: {config.get('name', config_file.name)}")
            except Exception as e:
                print(f"❌ Failed to process {config_file.name}: {e}")
        
        return processed_configs
    
    def generate_email_templates_with_feedback(self, domain, base_subject="Outreach"):
        """Generate sample email templates with feedback integration"""
        
        templates = {}
        
        # Professional template
        templates['professional'] = {
            'subject': f'{base_subject} - Partnership Opportunity',
            'content': f"""Dear {{{{recipient_name}}}},

I hope this email finds you well. I'm reaching out regarding a potential collaboration opportunity that aligns with your work in {domain}.

{{{{main_content}}}}

We believe this partnership could be mutually beneficial and would love to discuss this further at your convenience.

Best regards,
{{{{sender_name}}}}
{{{{sender_title}}}}
{{{{company_name}}}}

{self.feedback_templates['footer_signature']}""",
            'feedback_type': 'footer_signature'
        }
        
        # Casual template
        templates['casual'] = {
            'subject': f'{base_subject} - Let\'s Connect!',
            'content': f"""{self.feedback_templates['header_notice']}Hi {{{{recipient_name}}}},

Hope you're having a great day! I came across your work in {domain} and was really impressed.

{{{{main_content}}}}

{self.feedback_templates['inline_callout']}

Would love to chat more about this - are you available for a quick call sometime this week?

Cheers,
{{{{sender_name}}}}""",
            'feedback_type': 'header_notice'
        }
        
        return templates
    
    def validate_feedback_injection(self, email_content):
        """Validate that feedback email was properly injected"""
        has_feedback_email = self.feedback_email in email_content
        has_feedback_text = any(phrase in email_content.lower() for phrase in [
            'feedback', 'thoughts', 'input', 'improve', 'concerns'
        ])
        
        return {
            'has_feedback_email': has_feedback_email,
            'has_feedback_text': has_feedback_text,
            'properly_injected': has_feedback_email and has_feedback_text
        }
    
    def create_feedback_tracking_config(self, tracking_dir="tracking"):
        """Create feedback tracking configuration"""
        tracking_path = Path(tracking_dir)
        tracking_path.mkdir(parents=True, exist_ok=True)
        
        feedback_config = {
            'feedback_email': self.feedback_email,
            'auto_forward_to': [
                'campaigns@modelphysmat.com',
                'outreach-team@modelphysmat.com'
            ],
            'tracking_enabled': True,
            'response_analysis': True,
            'sentiment_tracking': True,
            'categories': [
                'positive_feedback',
                'improvement_suggestion',
                'complaint',
                'unsubscribe_request',
                'partnership_interest',
                'general_inquiry'
            ]
        }
        
        feedback_config_path = tracking_path / 'feedback_config.json'
        with open(feedback_config_path, 'w') as f:
            json.dump(feedback_config, f, indent=2)
        
        print(f"✅ Feedback tracking config created: {feedback_config_path}")
        return feedback_config

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Inject feedback email into campaigns")
    parser.add_argument("--feedback-email", default="feedback@modelphysmat.com", 
                       help="Feedback email address")
    parser.add_argument("--campaigns-dir", default="scheduled-campaigns",
                       help="Campaigns directory")
    parser.add_argument("--injection-type", 
                       choices=["footer_signature", "header_notice", "inline_callout", "reply_to_addition"],
                       default="footer_signature",
                       help="Type of feedback injection")
    parser.add_argument("--generate-templates", action="store_true",
                       help="Generate sample email templates")
    parser.add_argument("--domain", default="education",
                       help="Domain for template generation")
    parser.add_argument("--setup-tracking", action="store_true",
                       help="Setup feedback tracking")
    
    args = parser.parse_args()
    
    injector = EmailFeedbackInjector(args.feedback_email)
    
    print(f"🔧 Email Feedback Injector")
    print(f"📧 Feedback Email: {args.feedback_email}")
    print(f"📁 Campaigns Dir: {args.campaigns_dir}")
    print(f"🎯 Injection Type: {args.injection_type}")
    print("=" * 50)
    
    if args.setup_tracking:
        injector.create_feedback_tracking_config()
    
    if args.generate_templates:
        templates = injector.generate_email_templates_with_feedback(args.domain)
        print(f"\n📄 Generated templates for {args.domain}:")
        for name, template in templates.items():
            print(f"\n{name.upper()} TEMPLATE:")
            print("-" * 30)
            print(f"Subject: {template['subject']}")
            print(f"Content:\n{template['content']}")
    
    # Process all campaign configs
    processed = injector.process_all_campaign_configs(args.campaigns_dir)
    
    print(f"\n📊 SUMMARY:")
    print(f"✅ Processed {len(processed)} campaign configs")
    print(f"📧 Feedback email: {args.feedback_email}")
    print(f"🎯 Injection method: {args.injection_type}")
    
    for config in processed:
        print(f"  - {config['name']} ({Path(config['file']).name})")

if __name__ == "__main__":
    main()
