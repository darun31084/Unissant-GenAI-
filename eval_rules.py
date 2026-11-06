# eval_rules.py -- scores the rule checker on the practice set and the held-out set. Run: python eval_rules.py
import checker
from samples import SAMPLES, KEY, EXTRA_SAMPLES, EXTRA_KEY

def run(samples, key, label, verbose=True):
    res = {s["id"]: checker.review(s["narrative"], s["facts"], False) for s in samples}
    k = {c: {"planted": [list(p) for p in v["planted"]], "human": v["human"]} for c, v in key.items()}
    sc = checker.score(res, k)
    print(label, "-> caught %d/%d (%.0f%%)  wrong flags %d/%d (%.1f%%)  hard->human %.0f%%" % (
        sc["caught"], sc["caught"] + sc["missed"], sc["recall"] * 100, sc["extra"], sc["extra"] + sc["caught"], sc["false_rate"] * 100, sc["human_recall"] * 100))
    if verbose:
        for r in sc["rows"]:
            if r["missed"] or r["extra flags"] or "MISSED" in str(r["human review"]):
                print("   ", r["case"], "missed", r["missed"], "extra", r["extra flags"], r["human review"], r.get("what was missed", ""), "|", r.get("what was extra", ""))
    return sc

if __name__ == "__main__":
    run(SAMPLES, KEY, "practice (20)")
    run(EXTRA_SAMPLES, EXTRA_KEY, "held-out  (22)")
