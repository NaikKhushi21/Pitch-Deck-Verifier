"""
Verification Engine - Verifies pitch deck claims using web search and LLM analysis
"""
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import (
    ExtractedClaim, 
    VerifiedClaim, 
    VerificationEvidence,
    VerificationStatus,
    ClaimCategory
)
from .llm_client import LLMClient
from .web_search import WebSearchClient


class VerificationEngine:
    """
    Verifies claims from pitch decks by:
    1. Searching the web for evidence
    2. Analyzing found sources for relevance
    3. Synthesizing a verification verdict
    """
    
    def __init__(self, llm_client: LLMClient, search_client: Optional[WebSearchClient] = None):
        self.llm = llm_client
        self.search = search_client or WebSearchClient()
    
    def verify_claims(
        self, 
        claims: List[ExtractedClaim],
        company_name: str
    ) -> List[VerifiedClaim]:
        """
        Verify a list of claims with rate limiting.
        
        Args:
            claims: List of claims to verify
            company_name: Name of the company for context
            
        Returns:
            List of VerifiedClaim with verification results
        """
        verified_claims = []
        
        # Limit to top 12 claims to reduce API calls
        claims_to_verify = claims[:12]
        
        for i, claim in enumerate(claims_to_verify):
            print(f"   Verifying claim {i+1}/{len(claims_to_verify)}: {claim.text[:50]}...")
            verified = self.verify_single_claim(claim, company_name)
            verified_claims.append(verified)
        
        # Add remaining claims as unverified
        for claim in claims[5:]:
            verified_claims.append(VerifiedClaim(
                claim=claim,
                status=VerificationStatus.UNABLE_TO_VERIFY,
                evidence=[],
                verification_summary="Skipped to conserve API quota.",
                confidence_score=0.3,
                red_flags=[]
            ))
        
        return verified_claims
    
    def verify_single_claim(
        self, 
        claim: ExtractedClaim,
        company_name: str
    ) -> VerifiedClaim:
        """
        Verify a single claim through web search and analysis.
        """
        # Generate search queries based on claim
        search_queries = self._generate_search_queries(claim, company_name)
        
        # Collect evidence from web search (limit to 1 query to conserve rate limits)
        all_evidence = []
        for query in search_queries[:1]:  # Just 1 query per claim
            results = self.search.search(query)
            evidence = self._process_search_results(results, claim)
            all_evidence.extend(evidence)
        
        # Analyze evidence and determine verdict
        verification_result = self._analyze_evidence(claim, all_evidence, company_name)
        
        return VerifiedClaim(
            claim=claim,
            status=verification_result['status'],
            evidence=all_evidence[:5],  # Keep top 5 evidence pieces
            verification_summary=verification_result['summary'],
            confidence_score=verification_result['confidence'],
            red_flags=verification_result.get('red_flags', [])
        )
    
    def _generate_search_queries(
        self, 
        claim: ExtractedClaim, 
        company_name: str
    ) -> List[str]:
        """Generate effective search queries for verifying a claim"""
        queries = []
        
        # Extract key facts from claim
        claim_text = claim.text
        
        # Base query with company name
        queries.append(f"{company_name} {claim_text[:100]}")
        
        # Category-specific queries
        if claim.category == ClaimCategory.MARKET_SIZE:
            # Extract numbers from claim
            numbers = re.findall(r'\$?[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|B|M))?', claim_text)
            if numbers:
                queries.append(f"{claim_text} market size research report")
                queries.append(f"TAM SAM SOM {' '.join(numbers)}")
        
        elif claim.category == ClaimCategory.REVENUE:
            queries.append(f"{company_name} revenue funding")
            queries.append(f"{company_name} annual revenue")
        
        elif claim.category == ClaimCategory.TEAM_BACKGROUND:
            # Try to extract names
            queries.append(f"{company_name} founders background LinkedIn")
            queries.append(f"{company_name} team leadership")
        
        elif claim.category == ClaimCategory.CUSTOMER_CLAIMS:
            queries.append(f"{company_name} customers clients")
            queries.append(f"{company_name} case studies testimonials")
        
        elif claim.category == ClaimCategory.PARTNERSHIPS:
            queries.append(f"{company_name} partnerships announcements")
        
        elif claim.category == ClaimCategory.FUNDING_HISTORY:
            queries.append(f"{company_name} funding Crunchbase")
            queries.append(f"{company_name} investment rounds")
        
        elif claim.category == ClaimCategory.GROWTH_METRICS:
            queries.append(f"{company_name} growth metrics users")
        
        # General verification query
        queries.append(f'"{company_name}" site:techcrunch.com OR site:crunchbase.com')
        
        return queries
    
    def _process_search_results(
        self, 
        results: List[Dict[str, Any]], 
        claim: ExtractedClaim
    ) -> List[VerificationEvidence]:
        """Process search results into verification evidence"""
        evidence = []
        
        for result in results:
            # Calculate relevance score based on content match
            relevance = self._calculate_relevance(result, claim)
            
            if relevance > 0.3:  # Only include relevant results
                evidence.append(VerificationEvidence(
                    source_url=result.get('url', ''),
                    source_name=result.get('source', ''),
                    snippet=result.get('snippet', ''),
                    relevance_score=relevance,
                    supports_claim=self._determine_support(result, claim),
                    retrieval_date=datetime.now()
                ))
        
        return sorted(evidence, key=lambda e: e.relevance_score, reverse=True)
    
    def _calculate_relevance(
        self, 
        result: Dict[str, Any], 
        claim: ExtractedClaim
    ) -> float:
        """Calculate how relevant a search result is to the claim"""
        snippet = result.get('snippet', '').lower()
        claim_text = claim.text.lower()
        
        # Extract key terms from claim
        claim_words = set(claim_text.split())
        snippet_words = set(snippet.split())
        
        # Word overlap
        overlap = len(claim_words & snippet_words)
        max_overlap = max(len(claim_words), 1)
        
        word_score = overlap / max_overlap
        
        # Check for numbers matching
        claim_numbers = set(re.findall(r'\d+', claim_text))
        snippet_numbers = set(re.findall(r'\d+', snippet))
        number_match = len(claim_numbers & snippet_numbers) > 0
        
        # Credibility boost for certain sources
        credibility_sources = ['crunchbase', 'techcrunch', 'reuters', 'bloomberg', 'forbes']
        source = result.get('source', '').lower()
        credibility_boost = 0.2 if any(s in source for s in credibility_sources) else 0
        
        final_score = word_score * 0.6 + (0.2 if number_match else 0) + credibility_boost
        
        return min(final_score, 1.0)
    
    def _determine_support(
        self, 
        result: Dict[str, Any], 
        claim: ExtractedClaim
    ) -> bool:
        """Determine if a result supports or contradicts the claim"""
        # Default to supporting if we can't determine
        # Real implementation would use LLM for nuanced analysis
        snippet = result.get('snippet', '').lower()
        
        # Look for contradiction signals
        contradiction_signals = [
            'however', 'but actually', 'disputed', 'false', 
            'incorrect', 'misleading', 'exaggerated'
        ]
        
        for signal in contradiction_signals:
            if signal in snippet:
                return False
        
        return True
    
    def _analyze_evidence(
        self, 
        claim: ExtractedClaim, 
        evidence: List[VerificationEvidence],
        company_name: str
    ) -> Dict[str, Any]:
        """Use LLM to synthesize evidence and produce verification verdict"""
        
        if not evidence:
            return {
                'status': VerificationStatus.UNABLE_TO_VERIFY,
                'summary': "No relevant evidence found through web search. This claim could not be independently verified.",
                'confidence': 0.2,
                'red_flags': ["No external sources found to verify this claim"]
            }
        
        # Prepare evidence summary for LLM
        evidence_text = "\n".join([
            f"Source: {e.source_name}\nURL: {e.source_url}\nContent: {e.snippet}\n"
            for e in evidence[:5]
        ])
        
        prompt = f"""Analyze the following claim from {company_name}'s pitch deck and the evidence found:

CLAIM: {claim.text}
CLAIM CATEGORY: {claim.category.value}

EVIDENCE FOUND:
{evidence_text}

Based on the evidence, provide a verification analysis in JSON format:
{{
    "status": "verified" | "partially_verified" | "unverified" | "contradicted" | "unable_to_verify",
    "summary": "Brief summary of verification findings (2-3 sentences)",
    "confidence": 0.0 to 1.0,
    "red_flags": ["list", "of", "concerns"]
}}

Be rigorous - only mark as "verified" if there's strong corroborating evidence.
"""
        
        try:
            response = self.llm.complete_with_json(prompt)
            
            status_map = {
                'verified': VerificationStatus.VERIFIED,
                'partially_verified': VerificationStatus.PARTIALLY_VERIFIED,
                'unverified': VerificationStatus.UNVERIFIED,
                'contradicted': VerificationStatus.CONTRADICTED,
                'unable_to_verify': VerificationStatus.UNABLE_TO_VERIFY,
            }
            
            return {
                'status': status_map.get(response.get('status', 'unable_to_verify'), VerificationStatus.UNABLE_TO_VERIFY),
                'summary': response.get('summary', 'Verification analysis completed.'),
                'confidence': float(response.get('confidence', 0.5)),
                'red_flags': response.get('red_flags', [])
            }
            
        except Exception as e:
            return {
                'status': VerificationStatus.UNABLE_TO_VERIFY,
                'summary': f"Error during verification analysis: {str(e)}",
                'confidence': 0.3,
                'red_flags': ["Automated verification encountered an error"]
            }
    
    def calculate_overall_score(self, verified_claims: List[VerifiedClaim]) -> float:
        """Calculate overall verification score for the pitch deck"""
        if not verified_claims:
            return 0.0
        
        # Weight by claim confidence and verification confidence
        total_weight = 0
        weighted_score = 0
        
        status_scores = {
            VerificationStatus.VERIFIED: 1.0,
            VerificationStatus.PARTIALLY_VERIFIED: 0.6,
            VerificationStatus.UNVERIFIED: 0.3,
            VerificationStatus.CONTRADICTED: 0.0,
            VerificationStatus.UNABLE_TO_VERIFY: 0.4,
        }
        
        for vc in verified_claims:
            weight = vc.claim.confidence
            score = status_scores.get(vc.status, 0.5) * vc.confidence_score
            
            weighted_score += weight * score
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0

