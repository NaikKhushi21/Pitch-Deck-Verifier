# Sago Pitch Deck Verifier 🔍

**An AI-powered agent that verifies pitch deck claims and generates personalized investor questions.**

🎥 Demo

Watch a demo of the application in action:
**[Demo Video](https://drive.google.com/file/d/1C0JB0DFzl6UbirB-f3r19hMm7e32niGv/view?usp=sharing)**

---

## 🎯 Use Case

> *"An investor receives a pitch deck in PDF but is unsure how accurate the information is. They want to verify everything and know what questions to ask the founder."*

This agent solves this by:

1. **Extracting claims** from pitch decks using LLM-powered analysis
2. **Verifying claims** against web sources (news, Crunchbase, LinkedIn, etc.)
3. **Generating personalized questions** based on verification gaps and investor profile
4. **Delivering results** seamlessly via Gmail or Slack

---

## 🌟 Design Principles

### 1. Seamless Integration

- **Gmail**: Creates drafts or sends analysis directly to your inbox
- **Slack**: Posts to investment team channels with interactive buttons
- No new apps to download - works with your existing workflow

### 2. Hyper-Personalization

- Configure your investor profile (focus areas, investment stage, portfolio)
- Questions are tailored to your specific interests and expertise
- Verification priorities align with your investment thesis

### 3. True Agency

- Actively searches the web to verify claims (not just summarizing)
- Generates actionable questions you can use in founder meetings
- Executes delivery through your preferred channels

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/sago-pitch-verifier.git
cd sago-pitch-verifier

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# LLM Configuration - Using Gemini (Free!)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here
LLM_MODEL=gemini-1.5-flash

# Gmail (Simple SMTP - No OAuth needed!)
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # See below for how to get this
REPORT_RECIPIENT=recipient@example.com

# Web Search (Optional - Recommended!)
# Tavily: Free tier with 1,000 searches/month, no rate limits
# Get your FREE key at: https://tavily.com
# If not provided, falls back to DuckDuckGo (free but has rate limits)
TAVILY_API_KEY=your-tavily-api-key-here
SEARCH_PROVIDER=tavily  # Options: tavily or duckduckgo

# Investor Profile (for personalization)
INVESTOR_NAME=Your Name
INVESTOR_FOCUS_AREAS=B2B SaaS, FinTech, AI/ML
INVESTMENT_STAGE=Series A
```

### Usage

```bash
# Analyze a pitch deck
python main.py analyze path/to/pitch_deck.pdf

# Save results to JSON
python main.py analyze deck.pdf --output results.json

# Send to email (creates draft)
python main.py analyze deck.pdf --email investor@vc.com

# Post to Slack
python main.py analyze deck.pdf --slack "#deal-flow"

# Run demo with mock data
python main.py demo
```

---

## 📁 Project Structure

```
sago-pitch-verifier/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── .env                    # Configuration (create this)
├── src/
│   ├── __init__.py
│   ├── agent.py            # Main orchestrator
│   ├── config.py           # Configuration management
│   ├── models.py           # Data models
│   ├── pdf_parser.py       # PDF text extraction
│   ├── claim_extractor.py  # LLM-powered claim extraction
│   ├── verification_engine.py  # Web search & verification
│   ├── question_generator.py   # Personalized question generation
│   ├── llm_client.py       # LLM abstraction (OpenAI/Anthropic)
│   ├── web_search.py       # DuckDuckGo search client
│   └── integrations/
│       ├── gmail_integration.py  # Gmail API integration
│       └── slack_integration.py  # Slack API integration
├── samples/
│   └── sample_output.json  # Example output
└── docs/
    └── system_architecture.md  # Architecture documentation
```

---

## 🔧 How It Works

### Pipeline Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│   Pitch Deck    │────▶│   PDF Parser     │────▶│  Claim Extractor   │
│     (PDF)       │     │  (pdfplumber)    │     │      (LLM)         │
└─────────────────┘     └──────────────────┘     └────────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│    Delivery     │◀────│    Question      │◀────│   Verification     │
│ (Gmail/Slack)   │     │   Generator      │     │     Engine         │
└─────────────────┘     └──────────────────┘     └────────────────────┘
                                                           │
                                                           ▼
                                                  ┌────────────────────┐
                                                  │    Web Search      │
                                                  │ (Tavily/DuckDuckGo)│
                                                  └────────────────────┘
```

### Claim Categories Verified

| Category        | Examples                  | Verification Sources                 |
| --------------- | ------------------------- | ------------------------------------ |
| Market Size     | TAM/SAM/SOM figures       | Industry reports, Statista, McKinsey |
| Revenue         | ARR, MRR, growth rates    | Crunchbase, press releases           |
| Team Background | Past companies, education | LinkedIn, company websites           |
| Customer Claims | Logos, testimonials       | Case studies, press releases         |
| Partnerships    | Strategic partners        | Press announcements, partner sites   |
| Funding History | Previous rounds           | Crunchbase, TechCrunch               |
| Growth Metrics  | User counts, engagement   | Press releases, app stores           |

---

## 📊 Sample Output

See `samples/sample_output.json` for a complete example.

```json
{
  "company_name": "TechStartup Inc.",
  "overall_verification_score": 0.72,
  "executive_summary": "TechStartup's pitch deck shows strong traction claims with partially verified revenue. Market size estimates appear inflated.",
  "verified_claims": [
    {
      "claim": "The global market is worth $50 billion",
      "status": "contradicted",
      "summary": "Industry reports suggest TAM closer to $20B for core market.",
      "red_flags": ["Market size may include adjacent markets"]
    }
  ],
  "generated_questions": [
    {
      "question": "Can you walk me through exactly how you calculated the $50B TAM?",
      "priority": "high",
      "rationale": "Market size appears significantly higher than third-party estimates.",
      "personalization": "Critical for Series A investment decision"
    }
  ]
}
```

---

## 🔌 Integrations Setup

### Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key to your `.env` file as `GEMINI_API_KEY`

### Gmail Setup (Simple - No OAuth!)

We use Gmail's SMTP with an App Password - much simpler than OAuth!

1. **Enable 2-Step Verification** on your Google account:

   - Go to https://myaccount.google.com/security
   - Turn on 2-Step Verification
2. **Create an App Password**:

   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Click "Generate"
   - Copy the 16-character password
3. **Add to .env**:

   ```env
   GMAIL_ADDRESS=your.email@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   ```

That's it! No OAuth, no credentials.json, no token.json needed.

### Tavily Web Search (Recommended - Avoid Rate Limits!)

Tavily offers a **free tier with 1,000 searches/month** and no rate limits, making it much more reliable than DuckDuckGo.

1. **Get your free API key**:

   - Go to https://tavily.com
   - Sign up for a free account
   - Copy your API key
2. **Add to .env**:

   ```env
   TAVILY_API_KEY=your-tavily-api-key-here
   SEARCH_PROVIDER=tavily
   ```
3. **Install the package** (if not already installed):

   ```bash
   pip install tavily-python
   ```

**Note**: If you don't provide a Tavily API key, the system will automatically fall back to DuckDuckGo (which is free but has rate limits).

### Slack Setup (Optional)

1. Create a Slack app at api.slack.com
2. Add `chat:write` and `channels:read` scopes
3. Install to workspace
4. Copy Bot Token to `.env`

---

## 🛠️ Development

```bash
# Run tests
pytest tests/

# Run with mock data (no API calls)
python main.py analyze deck.pdf --mock

# Lint code
flake8 src/
```

---

## ⚠️ Limitations

- Web search may not find information on stealth/early-stage startups
- Verification accuracy depends on available public information
- LLM may occasionally hallucinate or misinterpret claims
- PDF parsing may struggle with heavily image-based decks

---

## 🔮 Future Enhancements

- [ ] Integration with Crunchbase API for funding data
- [ ] LinkedIn API for team verification
- [ ] Google Drive monitoring for automatic processing
- [ ] WhatsApp/Telegram delivery options
- [ ] Comparison with portfolio companies
- [ ] Historical tracking of startup progress

---

## 📄 License

MIT License - see LICENSE file

---

## 👤 Author

Built for Sago Assessment by [Your Name]

*This is a prototype implementation demonstrating the core concepts. Not intended for production use without further development.*
