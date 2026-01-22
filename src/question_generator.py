"""
Question Generator - Generates personalized investor questions based on verification results
"""
import json
from typing import List, Optional, Dict, Any
from .models import (
    VerifiedClaim, 
    InvestorQuestion, 
    InvestorProfile,
    VerificationStatus
)
from .llm_client import LLMClient


class QuestionGenerator:
    """
    Generates intelligent, personalized questions for investors based on:
    1. Verification results (especially unverified/contradicted claims)
    2. Investor profile and focus areas
    3. Best practices for investor due diligence
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def generate_questions(
        self,
        verified_claims: List[VerifiedClaim],
        investor_profile: InvestorProfile,
        company_name: str,
        max_questions: int = 10,
    ) -> List[InvestorQuestion]:
        """
        Generate personalized questions for the investor.
        
        Args:
            verified_claims: Claims with their verification status
            investor_profile: Profile of the investor for personalization
            company_name: Name of the company being evaluated
            max_questions: Maximum number of questions to generate
            
        Returns:
            List of InvestorQuestion objects, prioritized by importance
        """
        all_questions = []
        
        # Generate questions based on verification gaps
        verification_questions = self._generate_verification_questions(
            verified_claims, 
            investor_profile,
            company_name
        )
        all_questions.extend(verification_questions)
        
        # Generate general due diligence questions
        due_diligence_questions = self._generate_due_diligence_questions(
            verified_claims,
            investor_profile,
            company_name
        )
        all_questions.extend(due_diligence_questions)
        
        # Prioritize and deduplicate
        prioritized = self._prioritize_questions(all_questions, investor_profile)
        
        return prioritized[:max_questions]
    
    def _generate_verification_questions(
        self,
        verified_claims: List[VerifiedClaim],
        investor_profile: InvestorProfile,
        company_name: str
    ) -> List[InvestorQuestion]:
        """Generate questions about unverified or problematic claims"""
        
        # Focus on claims that need more scrutiny
        problematic_claims = [
            vc for vc in verified_claims
            if vc.status in [
                VerificationStatus.UNVERIFIED,
                VerificationStatus.CONTRADICTED,
                VerificationStatus.PARTIALLY_VERIFIED,
                VerificationStatus.UNABLE_TO_VERIFY
            ]
        ]
        
        if not problematic_claims:
            return []
        
        # Prepare claims summary for LLM
        claims_summary = []
        for vc in problematic_claims[:10]:
            claims_summary.append({
                'claim_id': vc.claim.claim_id,
                'claim': vc.claim.text,
                'category': vc.claim.category.value,
                'status': vc.status.value,
                'verification_summary': vc.verification_summary,
                'red_flags': vc.red_flags
            })
        
        prompt = f"""You are helping an investor prepare questions for a meeting with {company_name}.

INVESTOR PROFILE:
- Name: {investor_profile.name}
- Focus Areas: {', '.join(investor_profile.focus_areas)}
- Investment Stage: {investor_profile.investment_stage}

CLAIMS THAT NEED CLARIFICATION:
{json.dumps(claims_summary, indent=2)}

Generate specific, incisive questions that:
1. Probe the unverified or contradicted claims
2. Are tailored to this investor's focus areas
3. Would reveal important information for investment decisions
4. Are professional but direct

Return a JSON array of questions:
[
  {{
    "question": "The exact question to ask",
    "category": "market_size|revenue|team|product|competition|other",
    "priority": "high|medium|low",
    "rationale": "Why this question is important",
    "related_claim_ids": ["claim_0001"],
    "personalization": "How this relates to the investor's interests"
  }}
]

Generate 3-5 high-impact questions. Return ONLY valid JSON.
"""
        
        try:
            response = self.llm.complete(prompt)
            questions_data = self._parse_json_response(response)
            
            questions = []
            for q in questions_data:
                questions.append(InvestorQuestion(
                    question=q.get('question', ''),
                    category=q.get('category', 'other'),
                    priority=q.get('priority', 'medium'),
                    rationale=q.get('rationale', ''),
                    related_claim_ids=q.get('related_claim_ids', []),
                    personalization_context=q.get('personalization', '')
                ))
            
            return questions
            
        except Exception as e:
            print(f"Error generating verification questions: {e}")
            return []
    
    def _generate_due_diligence_questions(
        self,
        verified_claims: List[VerifiedClaim],
        investor_profile: InvestorProfile,
        company_name: str
    ) -> List[InvestorQuestion]:
        """Generate standard due diligence questions tailored to investor"""
        
        prompt = f"""You are helping an investor with due diligence for {company_name}.

INVESTOR PROFILE:
- Name: {investor_profile.name}
- Focus Areas: {', '.join(investor_profile.focus_areas)}
- Investment Stage: {investor_profile.investment_stage}

Generate strategic due diligence questions that a {investor_profile.investment_stage} investor 
should ask, specifically tailored to someone focused on {', '.join(investor_profile.focus_areas)}.

Categories to cover:
1. Business model and unit economics
2. Go-to-market strategy
3. Team and execution capability
4. Technology and product differentiation
5. Competition and market dynamics

Return a JSON array of questions:
[
  {{
    "question": "The exact question to ask",
    "category": "business_model|gtm|team|technology|competition",
    "priority": "high|medium|low",
    "rationale": "Why this question matters for this investor",
    "related_claim_ids": [],
    "personalization": "How this connects to investor's specific interests"
  }}
]

Generate 4-5 strategic questions. Return ONLY valid JSON.
"""
        
        try:
            response = self.llm.complete(prompt)
            questions_data = self._parse_json_response(response)
            
            questions = []
            for q in questions_data:
                questions.append(InvestorQuestion(
                    question=q.get('question', ''),
                    category=q.get('category', 'other'),
                    priority=q.get('priority', 'medium'),
                    rationale=q.get('rationale', ''),
                    related_claim_ids=q.get('related_claim_ids', []),
                    personalization_context=q.get('personalization', '')
                ))
            
            return questions
            
        except Exception as e:
            print(f"Error generating due diligence questions: {e}")
            return []
    
    def _parse_json_response(self, response: str) -> List[dict]:
        """Parse JSON from LLM response"""
        response = response.strip()
        
        if response.startswith('```'):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1] if lines[-1].startswith('```') else lines[1:])
        
        start = response.find('[')
        end = response.rfind(']') + 1
        
        if start != -1 and end > start:
            return json.loads(response[start:end])
        
        return []
    
    def _prioritize_questions(
        self,
        questions: List[InvestorQuestion],
        investor_profile: InvestorProfile
    ) -> List[InvestorQuestion]:
        """Prioritize questions based on importance and investor profile"""
        
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        
        # Boost priority for questions related to investor's focus areas
        def sort_key(q: InvestorQuestion):
            base_priority = priority_order.get(q.priority, 1)
            
            # Check if question relates to focus areas
            focus_boost = 0
            q_lower = q.question.lower()
            for area in investor_profile.focus_areas:
                if area.lower() in q_lower:
                    focus_boost = -0.5
                    break
            
            # Boost questions about red flags
            if q.related_claim_ids:
                focus_boost -= 0.3
            
            return base_priority + focus_boost
        
        return sorted(questions, key=sort_key)
    
    def format_questions_for_email(
        self,
        questions: List[InvestorQuestion],
        company_name: str
    ) -> str:
        """Format questions into a readable email/document format"""
        
        lines = [
            f"# Due Diligence Questions for {company_name}",
            "",
            "## High Priority Questions",
            ""
        ]
        
        high_priority = [q for q in questions if q.priority == 'high']
        for i, q in enumerate(high_priority, 1):
            lines.append(f"{i}. **{q.question}**")
            lines.append(f"   - *Rationale:* {q.rationale}")
            lines.append("")
        
        lines.extend(["## Additional Questions", ""])
        
        other = [q for q in questions if q.priority != 'high']
        for i, q in enumerate(other, 1):
            lines.append(f"{i}. {q.question}")
            lines.append(f"   - *Category:* {q.category}")
            lines.append("")
        
        return "\n".join(lines)

