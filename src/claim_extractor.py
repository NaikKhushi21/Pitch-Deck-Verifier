"""
Claim Extractor - Uses LLM to identify verifiable claims from pitch decks
"""
import re
import json
import time
from typing import List, Optional
from .models import ExtractedClaim, ClaimCategory
from .pdf_parser import ParsedPitchDeck
from .llm_client import LLMClient


class ClaimExtractor:
    """
    Extracts verifiable claims from parsed pitch decks using LLM.
    Focuses on factual claims that can be independently verified.
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.claim_counter = 0
    
    def extract_claims(self, parsed_deck: ParsedPitchDeck) -> List[ExtractedClaim]:
        """
        Extract all verifiable claims from a pitch deck.
        
        Args:
            parsed_deck: The parsed pitch deck content
            
        Returns:
            List of ExtractedClaim objects
        """
        all_claims = []
        
        # Combine all pages into one request to minimize API calls
        full_text = "\n\n".join([
            f"=== PAGE {page.page_number} ===\n{page.text}" 
            for page in parsed_deck.pages if page.text.strip()
        ])
        
        # Single API call for all pages
        page_claims = self._extract_claims_from_text(full_text, parsed_deck.filename)
        all_claims.extend(page_claims)
        
        # Deduplicate similar claims
        unique_claims = self._deduplicate_claims(all_claims)
        
        return unique_claims
    
    def _extract_claims_from_text(
        self, 
        text: str,
        filename: str
    ) -> List[ExtractedClaim]:
        """Extract claims from full pitch deck text using LLM"""
        
        if not text.strip():
            return []
        
        prompt = f"""Extract verifiable claims from this pitch deck. Focus on numbers, stats, team backgrounds, customers, and funding.

PITCH DECK:
{text[:10000]}

Return JSON array with claims. Keep text SHORT (under 100 chars). Example:
[{{"text":"700M snaps viewed daily","category":"growth_metrics","confidence":0.9}}]

Categories: market_size, revenue, growth_metrics, team_background, customer_claims, partnerships, funding_history, other

Return ONLY the JSON array, no other text. Max 12 claims.
"""
        
        try:
            response = self.llm.complete(prompt, max_tokens=3000)
            claims_data = self._parse_json_response(response)
            
            claims = []
            for claim_data in claims_data:
                self.claim_counter += 1
                claim = ExtractedClaim(
                    claim_id=f"claim_{self.claim_counter:04d}",
                    text=claim_data.get('text', ''),
                    category=self._parse_category(claim_data.get('category', 'other')),
                    source_page=claim_data.get('page', 1),
                    context=claim_data.get('context', ''),
                    confidence=float(claim_data.get('confidence', 0.5))
                )
                claims.append(claim)
            
            return claims
            
        except Exception as e:
            print(f"Error extracting claims: {e}")
            return []
    
    def _extract_claims_from_page(
        self, 
        text: str, 
        page_number: int,
        filename: str
    ) -> List[ExtractedClaim]:
        """Legacy: Extract claims from a single page"""
        return self._extract_claims_from_text(f"PAGE {page_number}:\n{text}", filename)
    
    def _parse_json_response(self, response: str) -> List[dict]:
        """Parse JSON from LLM response, handling common issues"""
        response = response.strip()
        
        # Remove markdown code blocks if present
        if '```json' in response:
            response = response.split('```json')[1]
            if '```' in response:
                response = response.split('```')[0]
        elif '```' in response:
            parts = response.split('```')
            if len(parts) >= 2:
                response = parts[1]
        
        response = response.strip()
        
        # Find JSON array
        start = response.find('[')
        end = response.rfind(']') + 1
        
        if start != -1 and end > start:
            json_str = response[start:end]
            
            # Clean up common JSON issues
            # Replace problematic characters
            json_str = json_str.replace('\n', ' ').replace('\r', ' ')
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # Remove control chars
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                # Try to fix common issues
                try:
                    # Sometimes quotes are not escaped properly
                    json_str = re.sub(r'(?<!\\)"(?=[^"]*"[^"]*:)', '\\"', json_str)
                    return json.loads(json_str)
                except:
                    print(f"JSON parse error: {e}")
                    # Return empty if we can't parse
                    return []
        
        return []
    
    def _parse_category(self, category_str: str) -> ClaimCategory:
        """Parse category string to enum"""
        category_map = {
            'market_size': ClaimCategory.MARKET_SIZE,
            'revenue': ClaimCategory.REVENUE,
            'growth_metrics': ClaimCategory.GROWTH_METRICS,
            'team_background': ClaimCategory.TEAM_BACKGROUND,
            'competitive_landscape': ClaimCategory.COMPETITIVE_LANDSCAPE,
            'customer_claims': ClaimCategory.CUSTOMER_CLAIMS,
            'technology': ClaimCategory.TECHNOLOGY,
            'partnerships': ClaimCategory.PARTNERSHIPS,
            'funding_history': ClaimCategory.FUNDING_HISTORY,
        }
        return category_map.get(category_str.lower(), ClaimCategory.OTHER)
    
    def _deduplicate_claims(self, claims: List[ExtractedClaim]) -> List[ExtractedClaim]:
        """Remove duplicate or very similar claims"""
        unique = []
        seen_texts = set()
        
        for claim in claims:
            # Normalize text for comparison
            normalized = claim.text.lower().strip()
            
            # Check if we've seen something very similar
            is_duplicate = False
            for seen in seen_texts:
                if self._similarity(normalized, seen) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(claim)
                seen_texts.add(normalized)
        
        return unique
    
    def _similarity(self, text1: str, text2: str) -> float:
        """Simple word-based similarity measure"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def prioritize_claims(self, claims: List[ExtractedClaim]) -> List[ExtractedClaim]:
        """
        Prioritize claims for verification based on importance and verifiability.
        """
        # Priority order for categories
        category_priority = {
            ClaimCategory.REVENUE: 1,
            ClaimCategory.GROWTH_METRICS: 2,
            ClaimCategory.MARKET_SIZE: 3,
            ClaimCategory.CUSTOMER_CLAIMS: 4,
            ClaimCategory.TEAM_BACKGROUND: 5,
            ClaimCategory.PARTNERSHIPS: 6,
            ClaimCategory.FUNDING_HISTORY: 7,
            ClaimCategory.COMPETITIVE_LANDSCAPE: 8,
            ClaimCategory.TECHNOLOGY: 9,
            ClaimCategory.OTHER: 10,
        }
        
        def sort_key(claim: ExtractedClaim):
            return (
                category_priority.get(claim.category, 10),
                -claim.confidence  # Higher confidence first within category
            )
        
        return sorted(claims, key=sort_key)


