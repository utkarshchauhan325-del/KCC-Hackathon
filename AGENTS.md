# AGENTS.md
- Language: Python 3.9+, type hints everywhere, Pydantic v2.
- Never hard-code API keys. Read from environment via app/config.py.
- All prompts live in app/core/prompts.py. All Gemini response schemas live in app/core/schemas.py.
- Every Gemini call goes through app/core/gemini_client.py (retries, timeouts, JSON validation).
- Scoring is deterministic Python in app/core/scoring.py. The VLM must not output the score.
- Violator events must default to review_status = pending_review. Never auto-send them.
- Write or update tests for every new module. Run pytest before finishing a phase.
- Work one phase at a time from CIVICEYE_ARCHITECTURE_AND_PLAN.md; produce a plan artifact first,
  and a walkthrough with screenshots or sample output when done.
- Use the browser agent to verify the Streamlit dashboard actually loads and the upload flow works.
