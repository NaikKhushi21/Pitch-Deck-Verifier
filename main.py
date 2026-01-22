#!/usr/bin/env python3
"""
Sago Pitch Deck Verifier - CLI Entry Point

An AI-powered tool that verifies pitch deck claims and generates 
personalized investor questions.

Usage:
    python main.py analyze path/to/pitch_deck.pdf
    python main.py analyze deck.pdf --email investor@example.com
    python main.py analyze deck.pdf --output results.json
"""

import argparse
import sys
from pathlib import Path

from src.agent import SagoPitchVerifier
from src.models import InvestorProfile


def analyze_command(args):
    """Analyze a pitch deck"""
    
    # Check if PDF exists
    if not Path(args.pdf_path).exists():
        print(f"❌ Error: File not found: {args.pdf_path}")
        sys.exit(1)
    
    # Create investor profile if provided
    investor_profile = None
    if args.investor_name or args.focus_areas:
        investor_profile = InvestorProfile(
            name=args.investor_name or "Investor",
            focus_areas=args.focus_areas.split(',') if args.focus_areas else ["B2B SaaS"],
            investment_stage=args.stage or "Series A"
        )
    
    # Initialize agent (connects to Gemini, etc.)
    try:
        agent = SagoPitchVerifier(investor_profile=investor_profile)
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        sys.exit(1)
    
    # Run analysis
    try:
        analysis = agent.analyze(
            pdf_path=args.pdf_path,
            max_claims=args.max_claims,
            max_questions=args.max_questions
        )
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        sys.exit(1)
    
    # Print results to console
    print_analysis(analysis)
    
    # Save to file if requested
    if args.output:
        if args.output.endswith('.html'):
            agent.save_as_html(analysis, args.output)
        else:
            agent.save_results(analysis, args.output)
    
    # Send via email if requested (or use default from .env)
    email_recipient = args.email
    if not email_recipient:
        from src.config import config
        email_recipient = config.report_recipient
    
    if email_recipient:
        try:
            agent.send_via_email(analysis, email_recipient)
        except Exception as e:
            print(f"⚠ Email error: {e}")
    
    return analysis


def print_analysis(analysis):
    """Pretty print analysis results"""
    print("\n" + "="*60)
    print(f"📊 RESULTS: {analysis.company_name}")
    print("="*60)
    
    # Verification score with visual bar
    score = analysis.overall_verification_score
    filled = int(score * 20)
    bar = "█" * filled + "░" * (20 - filled)
    
    if score >= 0.7:
        score_emoji = "🟢"
    elif score >= 0.4:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"
    
    print(f"\n{score_emoji} Verification Score: [{bar}] {score:.0%}")
    
    print(f"\n📝 EXECUTIVE SUMMARY")
    print("-"*40)
    print(f"{analysis.executive_summary}")
    
    print(f"\n⚠️  RISK ASSESSMENT")
    print("-"*40)
    print(f"{analysis.risk_assessment}")
    
    print(f"\n🔍 VERIFIED CLAIMS ({len(analysis.verified_claims)})")
    print("-"*40)
    for vc in analysis.verified_claims[:8]:
        status_emoji = {
            'verified': '✅',
            'partially_verified': '🔶',
            'unverified': '❓',
            'contradicted': '❌',
            'unable_to_verify': '⚪'
        }.get(vc.status.value, '⚪')
        
        claim_text = vc.claim.text[:70] + "..." if len(vc.claim.text) > 70 else vc.claim.text
        print(f"\n{status_emoji} {claim_text}")
        
        summary = vc.verification_summary[:100] + "..." if len(vc.verification_summary) > 100 else vc.verification_summary
        print(f"   └─ {summary}")
    
    print(f"\n❓ RECOMMENDED QUESTIONS ({len(analysis.generated_questions)})")
    print("-"*40)
    for i, q in enumerate(analysis.generated_questions[:8], 1):
        priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '⚪'}.get(q.priority, '⚪')
        print(f"\n{priority_emoji} {i}. {q.question}")
        
        rationale = q.rationale[:80] + "..." if len(q.rationale) > 80 else q.rationale
        print(f"   └─ {rationale}")
    
    print("\n" + "="*60)
    print("✨ Analysis complete! Use --output to save, --email to send.")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Sago Pitch Deck Verifier - AI-powered pitch deck analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py analyze deck.pdf
    python main.py analyze deck.pdf --output results.json
    python main.py analyze deck.pdf --email investor@vc.com
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a pitch deck')
    analyze_parser.add_argument('pdf_path', help='Path to the pitch deck PDF')
    analyze_parser.add_argument('--output', '-o', help='Output file path (.json or .html)')
    analyze_parser.add_argument('--email', '-e', help='Send results to this email address')
    analyze_parser.add_argument('--max-claims', type=int, default=15, help='Max claims to verify (default: 15)')
    analyze_parser.add_argument('--max-questions', type=int, default=10, help='Max questions to generate (default: 10)')
    analyze_parser.add_argument('--investor-name', help='Your name for personalization')
    analyze_parser.add_argument('--focus-areas', help='Comma-separated investment focus areas')
    analyze_parser.add_argument('--stage', help='Investment stage preference (e.g., "Series A")')
    
    args = parser.parse_args()
    
    if args.command == 'analyze':
        analyze_command(args)
    else:
        parser.print_help()
        print("\n💡 Quick start: python main.py analyze your_pitch_deck.pdf")
        sys.exit(1)


if __name__ == "__main__":
    main()
