# Charge Narrative Gap Review (Challenge+X, Unissant)

GenAI-assisted gap analysis for investigative charge documentation. It flags missing facts, contradictions and
citation mismatches in officer-written charge narratives, ties every flag to a sentence, and sends unclear or
multi-charge cases to a human. It never writes the narrative and never picks or suggests a charge.
All test data is synthetic.

## Run
    pip install -r requirements.txt
    streamlit run app.py          (Windows: double-click run_windows.bat)
Open http://localhost:8501

## AI key (never commit it)
Easiest: paste it in the sidebar box "AI key" (kept in memory only), then click "Test AI connection".
Or copy `.env.example` to `.env` and put the key in it (`.env` is git-ignored).
Or set it in the shell:
    Windows PowerShell:  $env:CHALLENGEX_API_KEY="your_key"
    Mac/Linux:           export CHALLENGEX_API_KEY=your_key
Without a key the rule checks still run.

## Files
- checker.py          the backend: checks, scoring, reports
- ai.py               the AI call and the guardrails on its answer
- app.py              the website (4 tabs)
- samples.py          20 synthetic test cases with an answer key (python samples.py)
- test_guardrails.py  offline test that the AI guardrails block unsafe output (python test_guardrails.py)
- RUN_GUIDE.md        step-by-step operating guide and demo script

## What it checks (aligned to Unissant's core elements)
Identity/citizenship, encounter (date, place, manner), manner of entry, subject statements, immigration history,
documents, the cited INA ground vs. the facts, contradictions between sentences, and (advisory only) the
disposition / procedural record. "Near Brownsville, TX" counts as a place.
