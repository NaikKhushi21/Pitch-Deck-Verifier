"""
Gmail Integration - Send analysis results via email
Supports two methods:
1. SMTP with App Password (Simple - Recommended!)
2. OAuth2 (Complex - for advanced users)
"""
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
import os
from pathlib import Path
import logging
from ..config import config

logger = logging.getLogger(__name__)


class GmailIntegration:
    """
    Gmail integration for sending pitch deck analysis results.
    
    Two modes:
    1. SMTP Mode (Simple): Uses Gmail App Password - NO OAuth needed!
    2. OAuth Mode (Complex): Full Gmail API access
    
    Seamless Integration Design:
    - Works with existing Gmail
    - Can send directly or save as draft
    - Beautiful HTML formatting
    """
    
    def __init__(
        self, 
        use_oauth: bool = False,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None
    ):
        self.use_oauth = use_oauth
        self.credentials_path = credentials_path or "credentials/gmail_credentials.json"
        self.token_path = token_path or "credentials/gmail_token.json"
        self._service = None
        
        # SMTP settings
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.gmail_address = config.gmail_address
        self.gmail_app_password = config.gmail_app_password
    
    def send_analysis(
        self,
        to_email: str,
        subject: str,
        analysis_html: str,
        analysis_text: str,
        cc: Optional[List[str]] = None
    ) -> dict:
        """
        Send analysis results via email.
        Uses SMTP by default (simple), falls back to OAuth if configured.
        """
        if self.use_oauth:
            return self._send_via_oauth(to_email, subject, analysis_html, analysis_text, cc)
        else:
            return self._send_via_smtp(to_email, subject, analysis_html, analysis_text, cc)
    
    def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        analysis_html: str,
        analysis_text: str,
        cc: Optional[List[str]] = None
    ) -> dict:
        """
        Send email using Gmail SMTP with App Password.
        This is the SIMPLE method - no OAuth needed!
        """
        if not self.gmail_address or not self.gmail_app_password:
            raise ValueError(
                "Gmail SMTP not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env\n"
                "To get an App Password:\n"
                "1. Go to https://myaccount.google.com/security\n"
                "2. Enable 2-Step Verification\n"
                "3. Go to App passwords (search for it)\n"
                "4. Generate a new app password for 'Mail'\n"
                "5. Copy the 16-character password to your .env file"
            )
        
        # Create message
        message = MIMEMultipart('alternative')
        message['From'] = self.gmail_address
        message['To'] = to_email
        message['Subject'] = subject
        
        if cc:
            message['Cc'] = ', '.join(cc)
        
        # Attach both plain text and HTML
        message.attach(MIMEText(analysis_text, 'plain'))
        message.attach(MIMEText(analysis_html, 'html'))
        
        # Send via SMTP
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable security
                server.login(self.gmail_address, self.gmail_app_password)
                
                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                
                server.sendmail(self.gmail_address, recipients, message.as_string())
            
            return {
                'status': 'sent',
                'to': to_email,
                'subject': subject,
                'method': 'smtp'
            }
            
        except smtplib.SMTPAuthenticationError:
            raise ValueError(
                "Gmail authentication failed. Make sure you're using an App Password, not your regular password.\n"
                "Get an App Password at: https://myaccount.google.com/apppasswords"
            )
    
    def send_report_with_pdf(
        self,
        to_email: str,
        company_name: str,
        pdf_path: str,
        num_claims: int = 0,
        num_questions: int = 0
    ) -> dict:
        """
        Send email with PDF report attached.
        This is the main method for sending analysis reports.
        """
        if not self.gmail_address or not self.gmail_app_password:
            raise ValueError(
                "Gmail not configured. Add to .env:\n"
                "  GMAIL_ADDRESS=your.email@gmail.com\n"
                "  GMAIL_APP_PASSWORD=your-16-char-app-password\n\n"
                "Get App Password: https://myaccount.google.com/apppasswords"
            )
        
        # Create message
        message = MIMEMultipart()
        message['From'] = self.gmail_address
        message['To'] = to_email
        message['Subject'] = f"📊 Pitch Deck Analysis Report: {company_name}"
        
        # Email body HTML - Professional format
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f4f4f7;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f7; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 40px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">Your Analysis Report is Ready</h1>
                            <p style="color: #a0aec0; margin: 12px 0 0 0; font-size: 16px;">{company_name} • Pitch Deck Review</p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px;">
                            <p style="color: #2d3748; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Dear Investor,
                            </p>
                            
                            <p style="color: #4a5568; font-size: 15px; line-height: 1.7; margin: 0 0 25px 0;">
                                Your comprehensive pitch deck analysis for <strong style="color: #1a1a2e;">{company_name}</strong> has been completed. Please find the detailed report attached to this email.
                            </p>
                            
                            <!-- Stats Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background: #f8fafc; border-radius: 8px; margin: 25px 0;">
                                <tr>
                                    <td style="padding: 25px;">
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td width="50%" style="text-align: center; padding: 10px;">
                                                    <div style="font-size: 32px; font-weight: 700; color: #1a1a2e;">{num_claims}</div>
                                                    <div style="font-size: 13px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px;">Claims Analyzed</div>
                                                </td>
                                                <td width="50%" style="text-align: center; padding: 10px; border-left: 1px solid #e2e8f0;">
                                                    <div style="font-size: 32px; font-weight: 700; color: #1a1a2e;">{num_questions}</div>
                                                    <div style="font-size: 13px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px;">Questions Generated</div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="color: #4a5568; font-size: 15px; line-height: 1.7; margin: 25px 0;">
                                <strong style="color: #2d3748;">The attached report includes:</strong>
                            </p>
                            
                            <ul style="color: #4a5568; font-size: 15px; line-height: 2; margin: 0 0 25px 0; padding-left: 20px;">
                                <li>Executive summary with key findings</li>
                                <li>Verified claims from the pitch deck</li>
                                <li>Personalized due diligence questions</li>
                                <li>Risk assessment and red flags</li>
                            </ul>
                            
                            <p style="color: #4a5568; font-size: 15px; line-height: 1.7; margin: 25px 0 0 0;">
                                We recommend reviewing this report before your meeting with the founders.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background: #f8fafc; padding: 25px 40px; border-top: 1px solid #e2e8f0;">
                            <p style="color: #718096; font-size: 13px; margin: 0; text-align: center;">
                                Generated by <strong style="color: #4a5568;">Sago Pitch Deck Verifier</strong><br>
                                <span style="font-size: 12px;">AI-Powered Investment Due Diligence</span>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        # Plain text version - Professional format
        text_body = f"""
YOUR ANALYSIS REPORT IS READY
{company_name} • Pitch Deck Review
{'='*50}

Dear Investor,

Your comprehensive pitch deck analysis for {company_name} has been completed. Please find the detailed report attached to this email.

ANALYSIS SUMMARY
────────────────
• Claims Analyzed: {num_claims}
• Questions Generated: {num_questions}

THE ATTACHED REPORT INCLUDES:
• Executive summary with key findings
• Verified claims from the pitch deck
• Personalized due diligence questions
• Risk assessment and red flags

We recommend reviewing this report before your meeting with the founders.

────────────────────────────────────────
Sago Pitch Deck Verifier
AI-Powered Investment Due Diligence
        """
        
        # Attach text and HTML
        message.attach(MIMEText(text_body, 'plain'))
        message.attach(MIMEText(html_body, 'html'))
        
        # Attach PDF
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                pdf_attachment = MIMEBase('application', 'pdf')
                pdf_attachment.set_payload(f.read())
                encoders.encode_base64(pdf_attachment)
                pdf_attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{company_name}_Analysis_Report.pdf"'
                )
                message.attach(pdf_attachment)
            logger.info(f"Attached PDF: {pdf_path}")
        else:
            logger.warning(f"PDF not found: {pdf_path}")
        
        # Send via SMTP
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.gmail_address, self.gmail_app_password)
                server.sendmail(self.gmail_address, to_email, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return {
                'status': 'sent',
                'to': to_email,
                'company': company_name,
                'pdf_attached': os.path.exists(pdf_path)
            }
            
        except smtplib.SMTPAuthenticationError:
            raise ValueError(
                "Gmail authentication failed!\n"
                "Make sure you're using an App Password, not your regular password.\n"
                "Get one at: https://myaccount.google.com/apppasswords"
            )
        except Exception as e:
            logger.error(f"Email failed: {e}")
            raise
    
    def save_as_html_file(
        self,
        analysis_html: str,
        output_path: str = "analysis_email.html"
    ) -> str:
        """
        Save the analysis as an HTML file that can be opened in browser
        or copy-pasted into an email.
        """
        with open(output_path, 'w') as f:
            f.write(analysis_html)
        
        return output_path
    
    # =========================================================================
    # OAuth Methods (Complex - Only if you really need them)
    # =========================================================================
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.readonly'
    ]
    
    def _get_oauth_service(self):
        """Get or create Gmail API service (OAuth method)"""
        if self._service:
            return self._service
        
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "Gmail OAuth dependencies not installed. Run: "
                "pip install google-api-python-client google-auth-oauthlib"
            )
        
        creds = None
        
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {self.credentials_path}. "
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self._service = build('gmail', 'v1', credentials=creds)
        return self._service
    
    def _send_via_oauth(
        self,
        to_email: str,
        subject: str,
        analysis_html: str,
        analysis_text: str,
        cc: Optional[List[str]] = None
    ) -> dict:
        """Send via Gmail API (OAuth method)"""
        service = self._get_oauth_service()
        
        message = MIMEMultipart('alternative')
        message['To'] = to_email
        message['Subject'] = subject
        
        if cc:
            message['Cc'] = ', '.join(cc)
        
        message.attach(MIMEText(analysis_text, 'plain'))
        message.attach(MIMEText(analysis_html, 'html'))
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return result
    
    def create_draft(
        self,
        to_email: str,
        subject: str,
        analysis_html: str,
        analysis_text: str,
        thread_id: Optional[str] = None
    ) -> dict:
        """Create a draft email (requires OAuth)"""
        service = self._get_oauth_service()
        
        message = MIMEMultipart('alternative')
        message['To'] = to_email
        message['Subject'] = subject
        
        message.attach(MIMEText(analysis_text, 'plain'))
        message.attach(MIMEText(analysis_html, 'html'))
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        draft_body = {'message': {'raw': raw}}
        
        if thread_id:
            draft_body['message']['threadId'] = thread_id
        
        result = service.users().drafts().create(
            userId='me',
            body=draft_body
        ).execute()
        
        return result
    
    def format_analysis_html(
        self,
        company_name: str,
        verification_score: float,
        verified_claims: list,
        questions: list
    ) -> str:
        """Format analysis as beautiful HTML email"""
        
        score_color = (
            '#22c55e' if verification_score > 0.7 
            else '#eab308' if verification_score > 0.4 
            else '#ef4444'
        )
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 30px; background: #f9fafb; border-radius: 0 0 10px 10px; }}
        .score-badge {{ display: inline-block; background: {score_color}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 18px; }}
        .claim-card {{ background: white; border-radius: 8px; padding: 15px; margin: 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .question-item {{ background: white; border-left: 4px solid #667eea; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
        .high-priority {{ border-left-color: #ef4444; }}
        .verified {{ color: #22c55e; font-weight: bold; }}
        .unverified {{ color: #ef4444; font-weight: bold; }}
        .partial {{ color: #eab308; font-weight: bold; }}
        h2 {{ color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin:0;">📊 Pitch Deck Analysis</h1>
        <h2 style="margin:10px 0 0 0; opacity: 0.9;">{company_name}</h2>
    </div>
    <div class="content">
        <h2>Verification Score</h2>
        <p><span class="score-badge">{verification_score:.0%}</span></p>
        
        <h2>🔍 Key Findings</h2>
"""
        
        for vc in verified_claims[:5]:
            status_class = (
                'verified' if vc.status.value == 'verified'
                else 'unverified' if vc.status.value in ['unverified', 'contradicted']
                else 'partial'
            )
            status_emoji = (
                '✅' if vc.status.value == 'verified'
                else '❌' if vc.status.value == 'contradicted'
                else '⚠️'
            )
            html += f"""
        <div class="claim-card">
            <span class="{status_class}">{status_emoji} {vc.status.value.upper()}</span>
            <p style="margin: 10px 0;"><strong>"{vc.claim.text}"</strong></p>
            <p style="color: #666; margin: 0;">{vc.verification_summary}</p>
        </div>
"""
        
        html += """
        <h2>❓ Recommended Questions</h2>
"""
        
        for i, q in enumerate(questions[:7], 1):
            priority_class = 'high-priority' if q.priority == 'high' else ''
            priority_emoji = '🔴' if q.priority == 'high' else '🟡' if q.priority == 'medium' else '⚪'
            html += f"""
        <div class="question-item {priority_class}">
            <strong>{priority_emoji} {i}. {q.question}</strong>
            <p style="color: #666; margin: 5px 0 0 0;"><em>{q.rationale}</em></p>
        </div>
"""
        
        html += """
    </div>
    <div style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
        Generated by Sago Pitch Verifier • Your AI-powered investment assistant
    </div>
</body>
</html>
"""
        
        return html
