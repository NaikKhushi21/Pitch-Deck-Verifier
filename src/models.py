"""
Data models for Sago Pitch Verifier
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ClaimCategory(Enum):
    """Categories of claims that can be extracted from pitch decks"""
    MARKET_SIZE = "market_size"
    REVENUE = "revenue"
    GROWTH_METRICS = "growth_metrics"
    TEAM_BACKGROUND = "team_background"
    COMPETITIVE_LANDSCAPE = "competitive_landscape"
    CUSTOMER_CLAIMS = "customer_claims"
    TECHNOLOGY = "technology"
    PARTNERSHIPS = "partnerships"
    FUNDING_HISTORY = "funding_history"
    OTHER = "other"


class VerificationStatus(Enum):
    """Status of claim verification"""
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    UNABLE_TO_VERIFY = "unable_to_verify"


@dataclass
class ExtractedClaim:
    """A claim extracted from the pitch deck"""
    claim_id: str
    text: str
    category: ClaimCategory
    source_page: int
    context: str  # Surrounding text for context
    confidence: float  # How confident we are this is a verifiable claim (0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "category": self.category.value,
            "source_page": self.source_page,
            "context": self.context,
            "confidence": self.confidence
        }


@dataclass
class VerificationEvidence:
    """Evidence found during verification"""
    source_url: str
    source_name: str
    snippet: str
    relevance_score: float
    supports_claim: bool  # True if supports, False if contradicts
    retrieval_date: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_url": self.source_url,
            "source_name": self.source_name,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score,
            "supports_claim": self.supports_claim,
            "retrieval_date": self.retrieval_date.isoformat()
        }


@dataclass
class VerifiedClaim:
    """A claim after verification"""
    claim: ExtractedClaim
    status: VerificationStatus
    evidence: List[VerificationEvidence]
    verification_summary: str
    confidence_score: float  # Overall confidence in verification (0-1)
    red_flags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "status": self.status.value,
            "evidence": [e.to_dict() for e in self.evidence],
            "verification_summary": self.verification_summary,
            "confidence_score": self.confidence_score,
            "red_flags": self.red_flags
        }


@dataclass
class InvestorQuestion:
    """A generated question for the investor to ask"""
    question: str
    category: str
    priority: str  # "high", "medium", "low"
    rationale: str  # Why this question is important
    related_claim_ids: List[str]
    personalization_context: str  # How this relates to investor's interests
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "category": self.category,
            "priority": self.priority,
            "rationale": self.rationale,
            "related_claim_ids": self.related_claim_ids,
            "personalization_context": self.personalization_context
        }


@dataclass
class PitchDeckAnalysis:
    """Complete analysis of a pitch deck"""
    deck_filename: str
    company_name: str
    analysis_timestamp: datetime
    extracted_claims: List[ExtractedClaim]
    verified_claims: List[VerifiedClaim]
    generated_questions: List[InvestorQuestion]
    executive_summary: str
    risk_assessment: str
    overall_verification_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deck_filename": self.deck_filename,
            "company_name": self.company_name,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "extracted_claims": [c.to_dict() for c in self.extracted_claims],
            "verified_claims": [v.to_dict() for v in self.verified_claims],
            "generated_questions": [q.to_dict() for q in self.generated_questions],
            "executive_summary": self.executive_summary,
            "risk_assessment": self.risk_assessment,
            "overall_verification_score": self.overall_verification_score
        }


@dataclass
class InvestorProfile:
    """Profile of the investor for personalization"""
    name: str
    focus_areas: List[str]
    investment_stage: str
    portfolio_companies: List[str] = field(default_factory=list)
    past_interactions: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "focus_areas": self.focus_areas,
            "investment_stage": self.investment_stage,
            "portfolio_companies": self.portfolio_companies,
            "past_interactions": self.past_interactions,
            "preferences": self.preferences
        }

