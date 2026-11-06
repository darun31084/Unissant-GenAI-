# test_speed.py -- shows WHERE the time goes, using a fake slow AI (no network or key needed). Run: python test_speed.py
import sys, types, json, os, time
os.environ["CHALLENGEX_API_KEY"] = "fake"
MODE = {"delay": 2.0, "fail": False}
class _Msg:
    def __init__(s, t): s.message = types.SimpleNamespace(content=t)
def _create(**kw):
    time.sleep(MODE["delay"])
    if MODE["fail"]:
        raise Exception("connection timed out")
    return types.SimpleNamespace(choices=[_Msg(json.dumps({"flags": [], "present": [], "ambiguous": ""}))])
class _Client:
    def __init__(s, **k): s.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=_create))
sys.modules["openai"] = types.SimpleNamespace(OpenAI=_Client)
import ai, checker
from samples import SAMPLES
cases = [{"id": s["id"], "narrative": s["narrative"], "facts": s["facts"]} for s in SAMPLES]

t = time.time(); checker.review_many(cases, False); rules = time.time() - t
print("Rules only, 20 cases:                      %.3f s" % rules)

ai.clear_cache(); t = time.time()
for c in cases[:6]:
    checker.review(c["narrative"], c["facts"], True)
seq = time.time() - t
print("AI one-by-one (old way), 6 cases:          %.1f s  (so 20 cases would take about %.0f s)" % (seq, seq / 6 * 20))

ai.clear_cache(); t = time.time(); checker.review_many(cases, True); par = time.time() - t
print("AI in parallel (new way), all 20 cases:    %.1f s" % par)

t = time.time(); checker.review_many(cases, True); again = time.time() - t
print("Same 20 cases again (cached):              %.3f s" % again)

ai.clear_cache(); MODE["fail"], MODE["delay"] = True, 1.0; t = time.time()
res = checker.review_many(cases, True); down = time.time() - t
skipped = len([r for r in res.values() if "paused" in r["ai_error"]])
print("AI DOWN, 20 cases (1 s to fail each):      %.1f s, %d cases skipped the AI after it failed repeatedly" % (down, skipped))
assert par < seq / 6 * 20 / 2, "parallel run should be much faster"
assert again < 1, "cached run should be instant"
assert skipped > 0, "circuit breaker should have skipped the AI"
assert all(r["flags"] is not None for r in res.values()), "rule results must still come back when the AI is down"

# AI flags are tidied: duplicates dropped, off-checklist remarks become quiet advisory notes, at most 3 kept
existing = [{"type": "missing", "element": "documents"}]
mine = [{"type": "missing", "element": "Documents"}, {"type": "unclear", "element": "weather"}, {"type": "unclear", "element": "manner_of_entry"},
        {"type": "unclear", "element": "subject_name"}, {"type": "unclear", "element": "documents"}]
out = checker.tidy_ai_flags(mine, existing)
assert len(out) == 3 and out[0]["advisory"] is True and out[0]["severity"] == "low", out
print("All speed and tidy-up tests passed.")
