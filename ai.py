# ai.py  --  the AI part. It sends the narrative to Unissant's model and gets a JSON answer back.
# The AI is only a helper: its answer is CLEANED before we use it (see the checks below).

import os, json, time, copy, threading
from openai import OpenAI            # Unissant's server speaks the same language as OpenAI, so we use this library

URL = "https://challengex-ext2.unissantmissionworks.com/v1"
MODEL = "gpt-oss-20b"                # exactly this name

# ---- SPEED. The AI is the slow part (seconds per case); the rule checks take about a millisecond. ----
TIMEOUT = 20                         # seconds to wait for the model (was 45): a stuck call must not hold up the whole batch
MAX_TOKENS = 1500                    # the answer is a small JSON object, 3000 only made a slow model think longer
PAUSE_AFTER = 2                      # after this many failures IN A ROW ...
PAUSE_SECONDS = 90                   # ... stop calling the AI for this long. Without this, a dead server costs TIMEOUT seconds on EVERY case.
_lock = threading.Lock()
_state = {"fails": 0, "paused_until": 0.0}
_cache = {}                          # same narrative + same facts -> same answer (the model runs at temperature 0), so reuse it instantly

def clear_cache():
    _cache.clear()
    _state["fails"], _state["paused_until"] = 0, 0.0

# The rules we give the AI. "Reasoning: low" makes this model answer faster.
RULES = """Reasoning: low
You review synthetic immigration charge narratives for documentation problems.
Rules: Never write or rewrite the narrative. Never suggest or name any charge or law other than ones the officer already cited.
Only flag problems the text clearly shows. If unsure, do not flag.
Every flag needs a sentence number and a short exact quote from that sentence.
Reply with ONE JSON object and nothing else:
{"flags":[{"type":"missing|inconsistent|unclear","element":"","sentence":0,"quote":"","reason":"one plain sentence"}],
 "present":[{"element":"","quote":""}],
 "ambiguous":""}
"present" = for each element in the 'maybe missing' list that the text actually states, give a quote.
"ambiguous" = a short reason if the facts are too unclear or contradictory for a computer to judge, else an empty string."""

def reason_is_safe(reason, cited_laws, known_laws):
    # Throws away AI text that recommends a charge, or names a law the officer did NOT cite.
    r = reason.lower().replace(" ", "")
    for bad in ["shouldbecharged", "recommendcharging", "appropriatecharge", "correctchargeis"]:
        if bad in r:
            return False
    for law in known_laws:
        if law in r and law not in cited_laws:
            return False
    return True

def _ask_model(sentences, facts, cited_laws, known_laws, missing_names):
    key = os.environ.get("CHALLENGEX_API_KEY")          # the secret key lives in your computer's settings, NOT in the code
    if not key:
        raise Exception("CHALLENGEX_API_KEY is not set")
    client = OpenAI(base_url=URL, api_key=key, timeout=TIMEOUT, max_retries=0)   # give up after TIMEOUT seconds

    numbered = ""
    for i in range(len(sentences)):
        numbered += "[" + str(i + 1) + "] " + sentences[i] + "\n"
    question = ("NARRATIVE:\n" + numbered + "\nFORM FIELDS: " + json.dumps(facts) +
                "\nLAWS THE OFFICER CITED: " + ", ".join(cited_laws) +
                "\nMAYBE MISSING: " + ", ".join(missing_names))

    reply = client.chat.completions.create(
        model=MODEL, temperature=0, max_tokens=MAX_TOKENS,
        messages=[{"role": "system", "content": RULES}, {"role": "user", "content": question}])
    text = reply.choices[0].message.content or ""
    if "{" not in text:
        raise Exception("the AI model returned no JSON answer")
    data = json.loads(text[text.find("{"): text.rfind("}") + 1])   # keep only the part between { and }
    if not isinstance(data, dict):
        raise Exception("the AI model returned an unexpected answer")

    # ---- clean the answer ----
    present = []
    for p in data.get("present", []):
        quote = str(p.get("quote", "")).lower()[:40]
        if quote != "" and quote in " ".join(sentences).lower():   # the quote must really be in the narrative
            present.append(p.get("element"))

    good_flags = []
    blocked = 0                                                     # how many AI suggestions we throw away
    for f in data.get("flags", []):
        num = f.get("sentence")
        reason = str(f.get("reason", ""))
        if f.get("type") not in ["missing", "inconsistent", "unclear"] or reason == "":
            blocked += 1
            continue
        if not reason_is_safe(reason, cited_laws, known_laws):
            blocked += 1
            continue
        if not isinstance(num, int) or num < 1 or num > len(sentences):
            blocked += 1
            continue                                                # must point to a REAL sentence
        quote = str(f.get("quote", "")).lower()[:40]
        if quote not in sentences[num - 1].lower():
            blocked += 1
            continue                                                # quote must really be in that sentence
        good_flags.append({"type": f["type"], "element": f.get("element", "other"), "reason": reason, "severity": "medium", "ask": "",
                           "sentence": num, "field": None, "quote": sentences[num - 1], "source": "ai"})

    ambiguous = str(data.get("ambiguous", ""))
    if ambiguous != "" and not reason_is_safe(ambiguous, cited_laws, known_laws):
        ambiguous = "The AI judged the facts unclear."
    return {"flags": good_flags, "present": present, "ambiguous": ambiguous, "blocked": blocked}


def ask_ai(sentences, facts, cited_laws, known_laws, missing_names):
    # The safe front door: cache first, then a circuit breaker, then the real call.
    cache_key = json.dumps([sentences, facts, cited_laws, missing_names], sort_keys=True, default=str)
    with _lock:
        if cache_key in _cache:
            return copy.deepcopy(_cache[cache_key])
        if time.time() < _state["paused_until"]:
            raise Exception("the AI was paused for a minute after repeated failures (the rule checks still ran)")
    try:
        answer = _ask_model(sentences, facts, cited_laws, known_laws, missing_names)
    except Exception as e:
        if "key is not set" not in str(e) and "CHALLENGEX_API_KEY" not in str(e):      # a missing key is not an outage
            with _lock:
                _state["fails"] += 1
                if _state["fails"] >= PAUSE_AFTER:
                    _state["paused_until"] = time.time() + PAUSE_SECONDS
        raise
    with _lock:
        _state["fails"] = 0
        _cache[cache_key] = copy.deepcopy(answer)
    return answer


def ping():
    # Quick connection test used by the "Test AI connection" button. Returns (ok, message).
    key = os.environ.get("CHALLENGEX_API_KEY")
    if not key:
        return False, "No key set."
    try:
        client = OpenAI(base_url=URL, api_key=key, timeout=TIMEOUT, max_retries=0)
        r = client.chat.completions.create(model=MODEL, max_tokens=200, messages=[{"role": "user", "content": "Reply with the single word: ok"}])
        return True, "Connected. The model answered."
    except Exception as e:
        return False, str(e)[:200]
