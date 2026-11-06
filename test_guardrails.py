# test_guardrails.py -- proves the AI guardrails work WITHOUT a network or key (the model is faked).
# Run:  python test_guardrails.py
import sys, types, json, os
os.environ["CHALLENGEX_API_KEY"] = "fake"

FAKE = {}
class _Msg:  # mimics the OpenAI reply object
    def __init__(s, t): s.message = types.SimpleNamespace(content=t)
class _Client:
    def __init__(s, **k): s.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kw: types.SimpleNamespace(choices=[_Msg(FAKE["text"])])))
sys.modules["openai"] = types.SimpleNamespace(OpenAI=_Client)
import ai, checker

S = ["On March 14, 2025, agents apprehended 'Ana Ruiz' near the Yuma station", "Subject is a citizen of Mexico", "Subject is inadmissible under section 212(a)(6)(A)(i) of the INA"]
laws = ["212(a)(6)(a)(i)"]; known = list(checker.CHARGES.keys())
def run(obj): ai.clear_cache(); FAKE["text"] = "Here you go:\n```json\n" + json.dumps(obj) + "\n```"; return ai.ask_ai(S, {}, laws, known, ["documents"])

good = {"type": "unclear", "element": "manner_of_entry", "sentence": 3, "quote": "Subject is inadmissible", "reason": "The manner of entry is not described."}
bad_charge = dict(good, reason="She should be charged under 212(a)(7)(A)(i)(I).")
bad_law = dict(good, reason="This fits 212(a)(2)(A)(i)(I) better.")
bad_sentence = dict(good, sentence=99)
bad_quote = dict(good, quote="invented words that are not there")
bad_type = dict(good, type="rewrite")
r = run({"flags": [good, bad_charge, bad_law, bad_sentence, bad_quote, bad_type], "present": [{"element": "documents", "quote": "citizen of Mexico"}, {"element": "documents", "quote": "made up quote"}], "ambiguous": ""})
assert len(r["flags"]) == 1 and r["blocked"] == 5, r
assert r["flags"][0]["sentence"] == 3 and r["flags"][0]["source"] == "ai"
assert r["present"] == ["documents"], r          # only the real quote counts
r = run({"flags": [], "present": [], "ambiguous": "You should be charged with fraud instead"})
assert r["ambiguous"] == "The AI judged the facts unclear.", r
FAKE["text"] = "no json here at all"; ai.clear_cache()
try: ai.ask_ai(S, {}, laws, known, []); raise SystemExit("should have failed")
except Exception as e: assert "no JSON" in str(e)
res = checker.review("On March 14, 2025 agents apprehended 'A B' near the Yuma station.", {}, use_ai=False)
assert res["ai_used"] is False
print("All guardrail tests passed: unsafe / invented AI output is blocked, real output is kept.")
