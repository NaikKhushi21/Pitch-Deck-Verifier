"""
Sago Pitch Verifier Agent - Main orchestrator
100% Real - No mock data!
"""
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

from .config import config
from .models import PitchDeckAnalysis, InvestorProfile
from .pdf_parser import PitchDeckParser
from .claim_extractor import ClaimExtractor
from .verification_engine import VerificationEngine
from .question_generator import QuestionGenerator
from .llm_client import LLMClient
from .web_search import WebSearchClient


class SagoPitchVerifier:
    """
    Main agent that orchestrates the pitch deck verification workflow.
    
    Workflow:
    1. Parse PDF pitch deck
    2. Extract verifiable claims (using Gemini)
    3. Verify claims via real web search (DuckDuckGo)
    4. Generate personalized investor questions
    5. Deliver results via Gmail
    """
    
    def __init__(self, investor_profile: Optional[InvestorProfile] = None):
        """
        Initialize the agent with real services.
        
        Args:
            investor_profile: Optional investor profile for personalization
        """
        print("\n🚀 Initializing Sago Pitch Verifier...")
        
        # Initialize real LLM client (Gemini by default)
        self.llm = LLMClient()
        
        # Initialize real web search (DuckDuckGo - free!)
        self.search = WebSearchClient()
        
        # Initialize components
        self.parser = PitchDeckParser(llm_client=self.llm)  # Pass LLM for company name extraction
        self.extractor = ClaimExtractor(self.llm)
        self.verifier = VerificationEngine(self.llm, self.search)
        self.question_gen = QuestionGenerator(self.llm)
        
        # Integrations (lazy loaded)
        self._gmail = None
        
        # Default investor profile from config
        self.investor_profile = investor_profile or InvestorProfile(
            name=config.investor_name,
            focus_areas=config.investor_focus_areas.split(', '),
            investment_stage=config.investment_stage
        )
        
        print(f"✓ Investor profile: {self.investor_profile.name}")
        print(f"✓ Focus areas: {', '.join(self.investor_profile.focus_areas)}")
        print("✓ Ready!\n")
    
    @property
    def gmail(self):
        """Lazy load Gmail integration"""
        if self._gmail is None:
            from .integrations.gmail_integration import GmailIntegration
            self._gmail = GmailIntegration()
        return self._gmail
    
    def analyze(
        self,
        pdf_path: str,
        max_claims: int = 25,
        max_questions: int = 10
    ) -> PitchDeckAnalysis:
        """
        Perform complete pitch deck analysis.
        
        Args:
            pdf_path: Path to the pitch deck PDF
            max_claims: Maximum claims to verify
            max_questions: Maximum questions to generate
            
        Returns:
            Complete PitchDeckAnalysis with all results
        """
        print(f"{'='*60}")
        print(f"🔍 ANALYZING: {pdf_path}")
        print(f"{'='*60}\n")
        
        # Step 1: Parse the PDF
        print("📄 Step 1: Parsing PDF...")
        parsed_deck = self.parser.parse(pdf_path)
        company_name = self.parser.extract_company_name(parsed_deck)
        print(f"   ✓ Company: {company_name}")
        print(f"   ✓ Pages: {parsed_deck.total_pages}")
        print(f"   ✓ Text extracted: {len(parsed_deck.full_text)} characters\n")
        
        # Step 2: Extract claims using LLM
        print("🔎 Step 2: Extracting claims (using Gemini)...")
        all_claims = self.extractor.extract_claims(parsed_deck)
        prioritized_claims = self.extractor.prioritize_claims(all_claims)[:max_claims]
        print(f"   ✓ Found {len(all_claims)} total claims")
        print(f"   ✓ Analyzing top {len(prioritized_claims)} claims\n")
        
        # Step 3: Verify claims via web search
        print("🌐 Step 3: Verifying claims (searching the web)...")
        verified_claims = self.verifier.verify_claims(prioritized_claims, company_name)
        overall_score = self.verifier.calculate_overall_score(verified_claims)
        
        # Count verification results
        verified_count = sum(1 for v in verified_claims if v.status.value == 'verified')
        contradicted_count = sum(1 for v in verified_claims if v.status.value == 'contradicted')
        partial_count = sum(1 for v in verified_claims if v.status.value == 'partially_verified')
        
        print(f"   ✓ Verified: {verified_count}")
        print(f"   ✓ Partially verified: {partial_count}")
        print(f"   ✓ Contradicted: {contradicted_count}")
        print(f"   ✓ Overall score: {overall_score:.0%}\n")
        
        # Step 4: Generate personalized questions
        print("❓ Step 4: Generating personalized questions...")
        questions = self.question_gen.generate_questions(
            verified_claims,
            self.investor_profile,
            company_name,
            max_questions
        )
        print(f"   ✓ Generated {len(questions)} questions\n")
        
        # Step 5: Generate summaries
        print("📝 Step 5: Creating executive summary...")
        executive_summary = self._generate_executive_summary(
            company_name, 
            verified_claims, 
            overall_score
        )
        risk_assessment = self._generate_risk_assessment(verified_claims)
        print("   ✓ Summary complete\n")
        
        # Compile final analysis
        analysis = PitchDeckAnalysis(
            deck_filename=parsed_deck.filename,
            company_name=company_name,
            analysis_timestamp=datetime.now(),
            extracted_claims=all_claims,
            verified_claims=verified_claims,
            generated_questions=questions,
            executive_summary=executive_summary,
            risk_assessment=risk_assessment,
            overall_verification_score=overall_score
        )
        
        print(f"{'='*60}")
        print("✨ ANALYSIS COMPLETE!")
        print(f"{'='*60}\n")
        
        return analysis
    
    def _generate_executive_summary(
        self,
        company_name: str,
        verified_claims: list,
        score: float
    ) -> str:
        """Generate an executive summary of the analysis"""
        
        verified_count = sum(1 for v in verified_claims if v.status.value == 'verified')
        contradicted_count = sum(1 for v in verified_claims if v.status.value == 'contradicted')
        
        prompt = f"""Write a brief executive summary (3-4 sentences) for an investor about {company_name}'s pitch deck analysis.

Verification Score: {score:.0%}
Total claims analyzed: {len(verified_claims)}
Claims verified: {verified_count}
Claims contradicted: {contradicted_count}

Key findings from verification:
{json.dumps([{'claim': v.claim.text[:100], 'status': v.status.value, 'summary': v.verification_summary[:100]} for v in verified_claims[:5]], indent=2)}

Write a professional, balanced summary highlighting the key verification findings. Be specific about what was verified and what needs attention."""
        
        try:
            return self.llm.complete(prompt, temperature=0.3, max_tokens=300)
        except Exception as e:
            return f"Analysis of {company_name}'s pitch deck completed with a {score:.0%} verification score. {verified_count} claims verified, {contradicted_count} contradicted."
    
    def _generate_risk_assessment(self, verified_claims: list) -> str:
        """Generate risk assessment based on verification results"""
        red_flags = []
        for vc in verified_claims:
            red_flags.extend(vc.red_flags)
        
        if not red_flags:
            return "No significant red flags identified during automated verification. Standard due diligence still recommended."
        
        return "Potential concerns identified:\n" + "\n".join([f"• {flag}" for flag in red_flags[:7]])
    
    def send_via_email(
        self,
        analysis: PitchDeckAnalysis,
        to_email: str,
        attach_pdf: bool = True
    ) -> dict:
        """
        Send analysis results via Gmail with PDF report attached.
        """
        print(f"📧 Sending analysis to {to_email}...")
        
        pdf_path = None
        
        if attach_pdf:
            # Generate PDF report
            print("   📄 Generating PDF report...")
            pdf_path = self._generate_pdf_report(analysis)
        
        # Send with PDF attachment
        result = self.gmail.send_report_with_pdf(
            to_email=to_email,
            company_name=analysis.company_name,
            pdf_path=pdf_path or "",
            num_claims=len(analysis.extracted_claims),
            num_questions=len(analysis.generated_questions)
        )
        
        print(f"   ✅ Email sent successfully to {to_email}!")
        return result
    
    def _generate_pdf_report(self, analysis: PitchDeckAnalysis) -> str:
        """Generate a PDF report from the analysis"""
        from datetime import datetime
        
        # First save as HTML
        html_path = "Pitch_Deck_Analysis_Report.html"
        self._save_full_html_report(analysis, html_path)
        
        # Convert HTML to PDF
        pdf_path = "Pitch_Deck_Analysis_Report.pdf"
        try:
            from weasyprint import HTML
            HTML(html_path).write_pdf(pdf_path)
            print(f"   ✓ PDF generated: {pdf_path}")
        except ImportError:
            print("   ⚠ WeasyPrint not installed - sending HTML only")
            return html_path
        except Exception as e:
            print(f"   ⚠ PDF generation failed: {e}")
            return html_path
        
        return pdf_path
    
    def _save_full_html_report(self, analysis: PitchDeckAnalysis, output_path: str):
        """Generate a beautiful, professional HTML report for PDF conversion"""
        
        # Calculate score color
        score = analysis.overall_verification_score
        if score >= 0.7:
            score_color = "#22c55e"
            score_label = "Strong"
        elif score >= 0.4:
            score_color = "#eab308"
            score_label = "Moderate"
        else:
            score_color = "#ef4444"
            score_label = "Needs Review"
        
        # Build claims HTML - grouped by category
        claims_by_category = {}
        for claim in analysis.extracted_claims:
            cat = claim.category.value.replace('_', ' ').title()
            if cat not in claims_by_category:
                claims_by_category[cat] = []
            claims_by_category[cat].append(claim.text)
        
        claims_html = ""
        for category, claims in claims_by_category.items():
            claims_html += f'<div class="category-group"><h4>{category}</h4><ul>'
            for claim in claims:
                claims_html += f'<li>{claim}</li>'
            claims_html += '</ul></div>'
        
        # Build questions HTML
        high_priority = [q for q in analysis.generated_questions if q.priority == "high"]
        medium_priority = [q for q in analysis.generated_questions if q.priority == "medium"]
        low_priority = [q for q in analysis.generated_questions if q.priority not in ["high", "medium"]]
        
        questions_html = ""
        
        if high_priority:
            questions_html += '<div class="priority-section"><h4 class="priority-label high">High Priority</h4>'
            for i, q in enumerate(high_priority, 1):
                questions_html += f'''
                <div class="question-card high">
                    <div class="question-num">{i}</div>
                    <div class="question-content">
                        <p class="question-text">{q.question}</p>
                        <p class="question-rationale">{q.rationale}</p>
                    </div>
                </div>'''
            questions_html += '</div>'
        
        if medium_priority:
            questions_html += '<div class="priority-section"><h4 class="priority-label medium">Medium Priority</h4>'
            for i, q in enumerate(medium_priority, len(high_priority) + 1):
                questions_html += f'''
                <div class="question-card medium">
                    <div class="question-num">{i}</div>
                    <div class="question-content">
                        <p class="question-text">{q.question}</p>
                        <p class="question-rationale">{q.rationale}</p>
                    </div>
                </div>'''
            questions_html += '</div>'
        
        # Full HTML template - Clean, professional design
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Investment Analysis: {analysis.company_name}</title>
    <style>
        @page {{ size: A4; margin: 0; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
            line-height: 1.6; 
            color: #1e293b; 
            background: #ffffff;
        }}
        
        .page {{ 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 60px 50px;
        }}
        
        /* Header */
        .header {{ 
            border-bottom: 3px solid #1e293b;
            padding-bottom: 30px;
            margin-bottom: 40px;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }}
        .logo {{
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        .date {{
            font-size: 13px;
            color: #64748b;
        }}
        .company-name {{
            font-size: 42px;
            font-weight: 700;
            color: #0f172a;
            margin: 10px 0;
            letter-spacing: -1px;
        }}
        .report-type {{
            font-size: 16px;
            color: #64748b;
            font-weight: 400;
        }}
        
        /* Score Section */
        .score-section {{
            display: flex;
            align-items: center;
            gap: 30px;
            background: #f8fafc;
            border-radius: 12px;
            padding: 25px 30px;
            margin-bottom: 40px;
        }}
        .score-circle {{
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: {score_color};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            flex-shrink: 0;
        }}
        .score-value {{
            font-size: 28px;
            font-weight: 700;
            line-height: 1;
        }}
        .score-label-small {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 4px;
        }}
        .score-details h3 {{
            font-size: 18px;
            color: #0f172a;
            margin-bottom: 8px;
        }}
        .score-details p {{
            font-size: 14px;
            color: #64748b;
            line-height: 1.5;
        }}
        
        /* Sections */
        .section {{
            margin-bottom: 45px;
        }}
        .section-title {{
            font-size: 13px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        /* Executive Summary */
        .summary-text {{
            font-size: 16px;
            line-height: 1.8;
            color: #334155;
        }}
        
        /* Claims */
        .category-group {{
            margin-bottom: 25px;
        }}
        .category-group h4 {{
            font-size: 14px;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 12px;
        }}
        .category-group ul {{
            list-style: none;
            padding: 0;
        }}
        .category-group li {{
            font-size: 14px;
            color: #475569;
            padding: 10px 0 10px 20px;
            border-left: 2px solid #e2e8f0;
            margin-bottom: 8px;
        }}
        .category-group li:hover {{
            border-left-color: #3b82f6;
        }}
        
        /* Questions */
        .priority-section {{
            margin-bottom: 30px;
        }}
        .priority-label {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 6px 14px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 15px;
        }}
        .priority-label.high {{
            background: #fef2f2;
            color: #dc2626;
        }}
        .priority-label.medium {{
            background: #fffbeb;
            color: #d97706;
        }}
        .question-card {{
            display: flex;
            gap: 15px;
            padding: 20px 0;
            border-bottom: 1px solid #f1f5f9;
        }}
        .question-card:last-child {{
            border-bottom: none;
        }}
        .question-num {{
            width: 28px;
            height: 28px;
            background: #1e293b;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            flex-shrink: 0;
        }}
        .question-card.high .question-num {{
            background: #dc2626;
        }}
        .question-card.medium .question-num {{
            background: #d97706;
        }}
        .question-content {{
            flex: 1;
        }}
        .question-text {{
            font-size: 15px;
            font-weight: 500;
            color: #0f172a;
            margin-bottom: 8px;
            line-height: 1.5;
        }}
        .question-rationale {{
            font-size: 13px;
            color: #64748b;
            font-style: italic;
            line-height: 1.5;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 60px;
            padding-top: 30px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
        }}
        .footer-logo {{
            font-size: 11px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }}
        .footer-tagline {{
            font-size: 12px;
            color: #cbd5e1;
        }}
        
        /* Print styles */
        @media print {{
            body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .page {{ padding: 40px; }}
            .question-card {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="page">
        <!-- Header -->
        <div class="header">
            <div class="header-top">
                <div class="logo">Sago Investment Analysis</div>
                <div class="date">{analysis.analysis_timestamp.strftime('%B %d, %Y')}</div>
            </div>
            <h1 class="company-name">{analysis.company_name}</h1>
            <p class="report-type">Pitch Deck Verification Report</p>
        </div>
        
        <!-- Score Section -->
        <div class="score-section">
            <div class="score-circle">
                <span class="score-value">{int(score * 100)}%</span>
                <span class="score-label-small">Score</span>
            </div>
            <div class="score-details">
                <h3>Verification Status: {score_label}</h3>
                <p>{len(analysis.extracted_claims)} claims analyzed • {len(analysis.generated_questions)} due diligence questions prepared</p>
            </div>
        </div>
        
        <!-- Executive Summary -->
        <div class="section">
            <h2 class="section-title">Executive Summary</h2>
            <p class="summary-text">{analysis.executive_summary}</p>
        </div>
        
        <!-- Key Claims -->
        <div class="section">
            <h2 class="section-title">Key Claims Identified</h2>
            {claims_html}
        </div>
        
        <!-- Questions -->
        <div class="section">
            <h2 class="section-title">Due Diligence Questions</h2>
            <p style="font-size: 14px; color: #64748b; margin-bottom: 25px;">
                The following questions are tailored to your investment focus and designed to probe the key claims made in the pitch deck.
            </p>
            {questions_html}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="footer-logo">Sago Pitch Deck Verifier</div>
            <div class="footer-tagline">AI-Powered Investment Due Diligence</div>
        </div>
    </div>
</body>
</html>'''
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        return output_path
    
    def _format_plain_text(self, analysis: PitchDeckAnalysis) -> str:
        """Format analysis as plain text"""
        lines = [
            f"PITCH DECK ANALYSIS: {analysis.company_name}",
            f"Generated: {analysis.analysis_timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"Verification Score: {analysis.overall_verification_score:.0%}",
            "",
            "="*50,
            "EXECUTIVE SUMMARY",
            "="*50,
            analysis.executive_summary,
            "",
            "="*50,
            "RISK ASSESSMENT",
            "="*50,
            analysis.risk_assessment,
            "",
            "="*50,
            "RECOMMENDED QUESTIONS",
            "="*50,
        ]
        
        for i, q in enumerate(analysis.generated_questions, 1):
            priority_label = f"[{q.priority.upper()}]"
            lines.append(f"\n{i}. {priority_label} {q.question}")
            lines.append(f"   Why: {q.rationale}")
        
        return "\n".join(lines)
    
    def save_results(
        self,
        analysis: PitchDeckAnalysis,
        output_path: str
    ):
        """Save analysis results to JSON file"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(analysis.to_dict(), f, indent=2, default=str)
        
        print(f"📁 Results saved to {output_path}")
    
    def save_as_html(
        self,
        analysis: PitchDeckAnalysis,
        output_path: str = "analysis_report.html"
    ):
        """Save analysis as HTML file (can open in browser or email)"""
        html = self.gmail.format_analysis_html(
            analysis.company_name,
            analysis.overall_verification_score,
            analysis.verified_claims,
            analysis.generated_questions
        )
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        print(f"📄 HTML report saved to {output_path}")
        return output_path
