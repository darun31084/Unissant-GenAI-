# Charge Narrative Gap Review

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python -m streamlit run app.py`.
5. Open the local address Streamlit prints (normally `http://localhost:8501`). Keep the terminal running while you use the site.

## Main workflow

- **Home:** start a single review or batch review; open the short How It Works tour.
- **Review a Case:** choose a synthetic example or paste a synthetic narrative, add optional case facts, and run the checks. Review each flag and record the officer's disposition.
- **Batch Review:** run the built-in synthetic set (42 cases) or upload JSON, CSV, or TXT files. Then choose **what to review**: everything, only certain categories (Clean, Missing facts, Conflicting facts, Citation problem, Needs human review; each shows how many cases it holds), or individual cases. Export reports as a zip or a summary CSV.
- **Scorecard:** run the built-in benchmark (the 20 practice cases, or all 42 including the held-out set) against its expected answer key, rules-only by default so the result is fast and repeatable. The four measures correspond to the ChallengeX goals: at least 90% planted issues caught, no more than 10% incorrect extra flags, 100% of ambiguous/hard cases routed to a human, and each review under 60 seconds. Detailed rows and CSV export are tucked away until requested.
- **Impact:** explore hypothetical time-savings assumptions. These are not measured outcomes.
- **Settings:** choose optional AI and animation preferences; expand Advanced for backend AI configuration and the safeguards/deployment notes.
- **Recent reports:** the sidebar lists reports created in the current Streamlit session. Select one to reopen its findings. This prototype history is session-only; it is not a permanent records system.

## Optional AI

The required-element, contradiction, and citation checks run without AI. AI is an optional second check. If the AI endpoint is unavailable, times out, returns malformed output, or is disabled, the app keeps the rule-based result and labels the review as rules-only. AI failure does not stop the review.

For AI-enabled use, set `CHALLENGEX_API_KEY` as a server environment variable or in a local `.env` file. Keep the key out of source code and Git. For a shared deployment, use the hosting provider's secret manager; do not expose the key in browser-side code.

## Data and deployment boundary

This prototype is for **synthetic or public test data only**. Do not enter PII, CUI, live government data, production case records, or production credentials. Before any real operational deployment, the team would need approved authentication, role-based access, encrypted storage and transport, audit logging, retention/deletion rules, security review, and approval from the relevant organization.

For a team showcase, host it on an approved platform with authentication and server-side secrets rather than asking every officer to run a local copy. Local hosting is suitable for development and a controlled single-machine demo. A public unauthenticated deployment is not appropriate.

## Checks

Run `python samples.py` to score the built-in synthetic test set and `python test_guardrails.py` to run the AI-output guardrail tests.

## Speed: what is slow and what is not

The rule checks take about a millisecond per case (all 42 built-in cases in well under a second). The only slow part is the optional AI call, which takes seconds per case. So: Batch Review and the Scorecard run **rules only by default**; tick "Also run the AI double-check" to include it. With the AI on, cases are sent in parallel (8 at a time), identical cases are answered from a cache, each call times out after 20 s, and after two failures in a row the AI is skipped for 90 s so an unreachable server cannot hold up a whole batch. `python test_speed.py` demonstrates this with a fake slow AI.

## Accuracy checks

`python samples.py` scores the checker on the 20 practice cases and on 22 held-out cases written with different wording. `python test_speed.py` and `python test_guardrails.py` need no network or key.
