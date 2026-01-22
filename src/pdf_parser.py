"""
PDF Parser for extracting content from pitch decks
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

import pdfplumber
from PyPDF2 import PdfReader


@dataclass
class PageContent:
    """Content extracted from a single PDF page"""
    page_number: int
    text: str
    tables: List[List[str]]
    has_images: bool


@dataclass
class ParsedPitchDeck:
    """Complete parsed pitch deck"""
    filename: str
    total_pages: int
    pages: List[PageContent]
    metadata: Dict[str, Any]
    full_text: str

    def get_text_by_page(self, page_num: int) -> str:
        """Get text for a specific page"""
        for page in self.pages:
            if page.page_number == page_num:
                return page.text
        return ""


class PitchDeckParser:
    """
    Parses pitch deck PDFs to extract text, tables, and structure.
    Uses pdfplumber for accurate text extraction and table detection.
    """

    # Phrases that are often prominent on cover slides but are NOT company names
    GENERIC_COVER_PHRASES = {
        "FOR BUSINESS",
        "INVESTOR DECK",
        "PITCH DECK",
        "PRESENTATION",
        "COMPANY OVERVIEW",
        "CONFIDENTIAL",
        "PRIVATE & CONFIDENTIAL",
        "DECK",
    }

    # Lowercase variants / substrings to screen out
    GENERIC_SUBSTRINGS = [
        "for business",
        "investor",
        "pitch deck",
        "presentation",
        "company overview",
        "confidential",
        "private",
        "do not distribute",
        "all rights reserved",
    ]

    def __init__(self, llm_client=None):
        """Initialize parser with optional LLM client for company name extraction"""
        self.llm_client = llm_client
        self.supported_formats = ['.pdf']

    def parse(self, pdf_path: str) -> ParsedPitchDeck:
        """
        Parse a pitch deck PDF and extract all content.
        """
        pages: List[PageContent] = []
        metadata: Dict[str, Any] = {}

        # Extract metadata using PyPDF2
        try:
            reader = PdfReader(pdf_path)
            if reader.metadata:
                metadata = {
                    'title': (reader.metadata.get('/Title', '') or '').strip(),
                    'author': (reader.metadata.get('/Author', '') or '').strip(),
                    'creator': (reader.metadata.get('/Creator', '') or '').strip(),
                    'creation_date': str(reader.metadata.get('/CreationDate', '') or ''),
                }
        except Exception as e:
            metadata = {'error': str(e)}

        # Extract content using pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                raw_text = page.extract_text() or ""
                text = self._clean_text(raw_text)

                # Extract tables
                tables: List[List[List[str]]] = []
                try:
                    raw_tables = page.extract_tables()
                    if raw_tables:
                        for table in raw_tables:
                            cleaned_table = [
                                [str(cell) if cell is not None else "" for cell in row]
                                for row in table if row
                            ]
                            tables.append(cleaned_table)
                except Exception:
                    pass

                has_images = bool(getattr(page, "images", []))

                pages.append(PageContent(
                    page_number=i + 1,
                    text=text,
                    tables=tables,
                    has_images=has_images
                ))

                # Capture cover-page "largest text" guess, but we'll validate later
                if i == 0:
                    guess = self._company_name_from_largest_text(page)
                    if guess:
                        metadata["company_name_guess"] = guess

        full_text = "\n\n".join([p.text for p in pages])

        return ParsedPitchDeck(
            filename=pdf_path.split('/')[-1],
            total_pages=len(pages),
            pages=pages,
            metadata=metadata,
            full_text=full_text
        )

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text while preserving line breaks.
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

        cleaned_lines: List[str] = []
        for line in text.split('\n'):
            line = re.sub(r'[ \t\f\v]+', ' ', line).strip()
            if line:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def extract_company_name(self, parsed_deck: ParsedPitchDeck) -> str:
        """
        Robust company-name extraction:
        1) Validated cover largest-text guess (must NOT be generic and must appear across pages)
        2) Cover text heuristic (line-aware), validated similarly
        3) Proper-noun frequency across first N pages (good for decks like this Snapchat one)
        4) Metadata (weak)
        5) LLM fallback
        """
        # Build a small corpus from early pages (where company name typically repeats)
        early_text = self._get_early_pages_text(parsed_deck, max_pages=5)
        filename_hint = parsed_deck.filename
        title_hint = (parsed_deck.metadata.get("title") or "").strip()

        # 1) Cover largest-text guess (captured during parse)
        guess = (parsed_deck.metadata.get("company_name_guess") or "").strip()
        if self._is_valid_company_candidate(guess, early_text):
            return guess

        # 2) Cover-page line heuristic
        if parsed_deck.pages:
            cover_candidate = self._company_name_from_cover_text(parsed_deck.pages[0].text)
            if self._is_valid_company_candidate(cover_candidate, early_text):
                return cover_candidate

        # 3) Proper-noun frequency heuristic across first pages
        freq_candidate = self._company_name_from_proper_noun_frequency(
            early_text,
            filename_hint=parsed_deck.filename,
            title_hint=(parsed_deck.metadata.get("title") or "")
)
        if self._is_valid_company_candidate(freq_candidate, early_text, require_occurrences=1):
            return freq_candidate

        # 4) Metadata fallback (often noisy)
        title = (parsed_deck.metadata.get('title') or '').strip()
        if self._is_valid_company_candidate(title, early_text, require_occurrences=0):
            return title

        # 5) LLM fallback
        if self.llm_client:
            try:
                company_name = self._extract_company_name_with_llm(parsed_deck)
                if self._is_valid_company_candidate(company_name, early_text, require_occurrences=0):
                    return company_name
            except Exception as e:
                print(f"   ⚠ LLM company name extraction failed: {e}")

        return "Unknown Company"

    def _get_early_pages_text(self, parsed_deck: ParsedPitchDeck, max_pages: int = 5) -> str:
        pages = parsed_deck.pages[:max_pages] if parsed_deck.pages else []
        return "\n".join(p.text for p in pages if p.text)

    def _is_generic_phrase(self, s: str) -> bool:
        if not s:
            return True
        s_clean = re.sub(r"\s+", " ", s).strip()
        if s_clean.upper() in self.GENERIC_COVER_PHRASES:
            return True
        low = s_clean.lower()
        return any(sub in low for sub in self.GENERIC_SUBSTRINGS)

    def _count_occurrences(self, haystack: str, needle: str) -> int:
        if not haystack or not needle:
            return 0
        # Word-boundary-ish match; allows simple brand names to be counted reliably
        pattern = r"\b" + re.escape(needle) + r"\b"
        return len(re.findall(pattern, haystack, flags=re.IGNORECASE))

    def _is_plausible_company_name(self, s: str) -> bool:
        s = (s or "").strip()
        if not s:
            return False
        if len(s) < 2 or len(s) > 60:
            return False
        if len(s.split()) > 6:
            return False
        if re.fullmatch(r"[\W_]+", s):
            return False
        # Avoid things that look like dates or slide numbers
        if re.fullmatch(r"\d{1,4}", s):
            return False
        return True

    def _is_valid_company_candidate(self, candidate: str, early_text: str, require_occurrences: int = 2) -> bool:
        """
        Candidate must be plausible, not generic, and (optionally) show up repeatedly.
        For this Snapchat deck: "FOR BUSINESS" fails generic filter; "Snapchat" passes frequency.
        """
        candidate = (candidate or "").strip()
        if not self._is_plausible_company_name(candidate):
            return False
        if self._is_generic_phrase(candidate):
            return False
        if require_occurrences > 0:
            occ = self._count_occurrences(early_text, candidate)
            return occ >= require_occurrences
        return True

    def _company_name_from_cover_text(self, first_page_text: str) -> str:
        if not first_page_text:
            return ""

        lines = [ln.strip() for ln in first_page_text.split("\n") if ln.strip()]
        if not lines:
            return ""

        candidates: List[str] = []
        for line in lines[:15]:
            if len(line) > 80:
                continue
            if self._is_generic_phrase(line):
                continue
            if re.fullmatch(r"(\d{4}|\w+\s+\d{4}|\w+\s+\d{1,2},\s*\d{4})", line):
                continue
            if len(line.split()) > 8:
                continue
            candidates.append(line)

        if not candidates:
            return ""

        candidates = sorted(candidates, key=lambda s: (len(s.split()), len(s)))
        return candidates[0].strip()

    def _company_name_from_largest_text(self, page) -> Optional[str]:
        """
        Heuristic: company name is usually the largest text on the cover slide.
        We'll validate against generic phrases + frequency later.
        """
        try:
            words = page.extract_words(extra_attrs=["size", "top", "x0"])
        except Exception:
            return None

        if not words:
            return None

        words = [w for w in words if (w.get("text") or "").strip()]
        if not words:
            return None

        max_size = max((w.get("size", 0) or 0) for w in words)
        if max_size <= 0:
            return None

        tol = 0.92
        big_words = [w for w in words if (w.get("size", 0) or 0) >= max_size * tol]
        if not big_words:
            return None

        big_words = sorted(big_words, key=lambda w: (w.get("top", 0) or 0, w.get("x0", 0) or 0))
        candidate = " ".join(w["text"] for w in big_words).strip()
        candidate = re.sub(r"\s+", " ", candidate).strip()

        return candidate or None

    def _company_name_from_proper_noun_frequency(self, early_text: str, filename_hint: str = "", title_hint: str = "") -> str:
        """
        Smarter fallback:
        - Extract TitleCase-ish tokens from early pages
        - Score with frequency + pattern bonuses + filename/title bonuses
        - Penalize generic/plural feature words (e.g., Snaps, Stories)
        """
        if not early_text:
            return ""

        # Tokens like Snapchat, Evan, Spiegel, America, etc.
        tokens = re.findall(r"\b[A-Z][a-zA-Z0-9&.\-]{2,}\b", early_text)
        if not tokens:
            return ""

        counts = Counter(tokens)

        # Common pitch-deck / feature words to avoid as "company"
        blacklist = {
            "Snaps", "Snap", "Stories", "Story",
            "Confidential", "July", "America", "Age", "People", "They", "Our",
            "Business", "Investor", "Deck", "Presentation", "Overview",
            "Snap", "SNAP", "FOR", "BUSINESS", "GET", "KNOW", "HISTORY", "OUR"
        }

        # Normalize hints
        filename_low = (filename_hint or "").lower()
        title_low = (title_hint or "").lower()

        # Pattern bonuses that strongly indicate a company name
        def pattern_bonus(name: str) -> int:
            n = re.escape(name)
            bonus = 0
            # e.g., "Snapchat was created in 2011"
            if re.search(rf"\b{n}\b\s+was\s+created\b", early_text, flags=re.IGNORECASE):
                bonus += 8
            # e.g., "At Snapchat, ..."
            if re.search(rf"\bAt\s+{n}\b", early_text, flags=re.IGNORECASE):
                bonus += 5
            # e.g., "Snapchat is ..."
            if re.search(rf"\b{n}\b\s+is\b", early_text, flags=re.IGNORECASE):
                bonus += 3
            return bonus

        def hint_bonus(name: str) -> int:
            bonus = 0
            low = name.lower()
            # Filename match is very strong (e.g., Snapchat_PitchDeck.pdf)
            if low and low in filename_low:
                bonus += 10
            # Title match is moderate
            if low and low in title_low:
                bonus += 4
            return bonus

        def plural_penalty(name: str) -> int:
            # Penalize simple plural feature words (Snaps/Stories/etc.)
            # Keep penalty small so real brands like "Vans" aren't automatically killed.
            return 2 if name.endswith("s") else 0

        best_name = ""
        best_score = -10**9

        # Consider top candidates by raw frequency
        for name, freq in counts.most_common(30):
            if name in blacklist:
                continue
            if not self._is_plausible_company_name(name):
                continue
            if self._is_generic_phrase(name):
                continue

            score = 0
            score += freq * 2                      # frequency weight
            score += pattern_bonus(name)           # linguistic cues
            score += hint_bonus(name)              # filename/title cues
            score -= plural_penalty(name)          # mild plural penalty

            if score > best_score:
                best_score = score
                best_name = name

        return best_name


    def _extract_company_name_with_llm(self, parsed_deck: ParsedPitchDeck) -> str:
        first_page_text = parsed_deck.pages[0].text[:2000] if parsed_deck.pages else ""

        prompt = f"""Extract the company name from this pitch deck. Return ONLY the company name, nothing else.

PITCH DECK TEXT (first page):
{first_page_text}

What is the name of the company this pitch deck is for? Return only the company name (1-4 words), no explanations."""
        try:
            response = self.llm_client.complete(prompt, max_tokens=50)
            company_name = (response or "").strip()
            company_name = company_name.replace('"', '').replace("'", '').strip()

            prefixes = ['the company name is', 'company:', 'name:', 'the company is']
            low = company_name.lower()
            for prefix in prefixes:
                if low.startswith(prefix):
                    company_name = company_name[len(prefix):].strip()
                    break

            return company_name
        except Exception:
            return "Unknown Company"

    def extract_sections(self, parsed_deck: ParsedPitchDeck) -> Dict[str, bool]:
        """
        Identify common pitch deck sections (presence/absence).
        """
        sections: Dict[str, bool] = {}
        section_keywords = {
            'problem': ['problem', 'challenge', 'pain point'],
            'solution': ['solution', 'our product', 'how we solve'],
            'market': ['market', 'tam', 'sam', 'som', 'market size', 'opportunity'],
            'business_model': ['business model', 'revenue model', 'how we make money', 'monetization'],
            'traction': ['traction', 'metrics', 'growth', 'customers', 'users'],
            'competition': ['competition', 'competitive', 'landscape', 'competitors'],
            'team': ['team', 'founders', 'leadership', 'about us'],
            'financials': ['financials', 'projections', 'revenue', 'forecast'],
            'ask': ['ask', 'funding', 'investment', 'raise', 'use of funds'],
        }

        full_text_lower = (parsed_deck.full_text or "").lower()
        for section_name, keywords in section_keywords.items():
            sections[section_name] = any(keyword in full_text_lower for keyword in keywords)

        return sections
