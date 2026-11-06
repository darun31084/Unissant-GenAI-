# app.py  --  the FRONT END (the website). Streamlit turns each st.something line into something on the page.
# Run it with:  py -m streamlit run app.py     (or double-click run_windows.bat)
# 4 tabs:  1) Review a case   2) Batch test bed   3) Scorecard   4) Impact & trust

import os, io, csv, json, zipfile, html, time
import streamlit as st
import pandas as pd
import checker, loader
from samples import SAMPLES, KEY, ALL_SAMPLES, ALL_KEY

st.set_page_config(page_title="Charge Narrative Gap Review", page_icon="🛡️", layout="wide")

# Optional: read CHALLENGEX_API_KEY from a local .env file (it is git-ignored, so it never reaches GitHub).
if os.path.exists(".env") and not os.environ.get("CHALLENGEX_API_KEY"):
    for line in open(".env", encoding="utf-8", errors="ignore"):
        if line.strip().startswith("CHALLENGEX_API_KEY") and "=" in line:
            os.environ["CHALLENGEX_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")

#*****************************************************************************************************
#   THEME + LOOK AND FEEL
#*****************************************************************************************************
THEMES = {
    "Ocean": {"accent": "#2563eb", "accent2": "#0f4c81", "soft": "#eaf2ff"},
    "Lavender": {"accent": "#7c3aed", "accent2": "#5b21b6", "soft": "#f2eaff"},
    "Forest": {"accent": "#16845b", "accent2": "#075e43", "soft": "#e7f6ef"},
    "Sunset": {"accent": "#d65a31", "accent2": "#9f351d", "soft": "#fff0e9"},
    "Slate": {"accent": "#475569", "accent2": "#263445", "soft": "#edf1f5"},
}
if "theme_name" not in st.session_state:
    st.session_state["theme_name"] = "Ocean"
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

_theme = THEMES.get(st.session_state["theme_name"], THEMES["Ocean"])
_dark = st.session_state["dark_mode"]
_bg = "#111827" if _dark else "#f6f8fc"
_surface = "#1f2937" if _dark else "#ffffff"
_ink = "#f3f4f6" if _dark else "#17243b"
_muted = "#cbd5e1" if _dark else "#64748b"
_line = "#374151" if _dark else "#e5eaf2"
_sidebar = "#172033" if _dark else _theme["soft"]

st.markdown(f"""
<style>
:root {{ --accent:{_theme['accent']}; --accent-dark:{_theme['accent2']}; --soft:{_theme['soft']};
         --bg:{_bg}; --surface:{_surface}; --ink:{_ink}; --muted:{_muted}; --line:{_line}; }}
/* Remove Streamlit's top chrome so the app feels like one workspace. */
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{ visibility:hidden; height:0; }}
.stApp {{ background:var(--bg); color:var(--ink); }}
.block-container {{ max-width:1280px; padding-top:1.25rem; padding-bottom:3rem; }}
h1,h2,h3,h4,p,label,li {{ color:var(--ink); }}
[data-testid="stSidebar"] {{ background:{_sidebar}; border-right:1px solid var(--line); }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color:var(--ink); }}
[data-testid="stSidebar"] button {{ width:100%; border:1px solid var(--line) !important;
  background:var(--surface) !important; color:var(--ink) !important; border-radius:11px !important;
  text-align:left; font-weight:700 !important; min-height:2.55rem; }}
[data-testid="stSidebar"] button * {{ color:var(--ink) !important; }}
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {{
  background:linear-gradient(100deg,var(--accent-dark),var(--accent)) !important; border:0 !important; }}
[data-testid="stSidebar"] button[kind="primary"] *,
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] * {{ color:#fff !important; }}
.stButton>button, .stDownloadButton>button {{ border-radius:11px; min-height:2.6rem; font-weight:650;
  border:1px solid var(--line); }}
.stButton>button[kind="primary"] {{ background:var(--accent); color:#fff; border:0; }}
[data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"] {{ background:var(--surface); border:1px solid var(--line);
  border-radius:14px; color:var(--ink); }}
[data-testid="stMetric"] {{ padding:14px 16px; box-shadow:0 3px 12px rgba(0,0,0,.04); }}
[data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] {{ color:var(--muted); }}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] div[data-baseweb="select"] {{ background:var(--surface); color:var(--ink); }}
.banner {{ background:linear-gradient(105deg,var(--accent-dark),var(--accent) 65%,#8b5cf6);
  padding:26px 30px; border-radius:18px; color:#fff; margin:0 0 20px 0;
  box-shadow:0 12px 28px rgba(0,0,0,.12); }}
.banner h1 {{ color:#fff; margin:0; font-size:clamp(1.7rem,3vw,2.2rem); }}
.banner p {{ color:#f1f5ff; margin:7px 0 0; font-size:1rem; }}
.pill {{ display:inline-block; background:rgba(255,255,255,.18); color:#fff;
  padding:4px 11px; border-radius:14px; margin:10px 6px 0 0; font-size:12px; }}
.badge {{ padding:2px 9px; border-radius:10px; font-size:12px; font-weight:700; color:white; margin-right:6px; }}
.high {{background:#d64545;}} .medium {{background:#b7791f;}} .low {{background:#2563eb;}} .aib {{background:#7c3aed;}}
.chip {{ display:inline-block; padding:3px 10px; margin:2px 4px; border-radius:12px;
  background:#fff0f0; color:#8a1f1f; border:1px solid #f0b4b4; font-size:13px; }}
.sent {{ padding:2px 4px; border-radius:4px; line-height:2.1; color:#111; }}
.gauge {{ width:124px; height:124px; border-radius:50%; display:flex; align-items:center; justify-content:center; }}
.gauge-in {{ width:92px; height:92px; border-radius:50%; background:#fff; color:#111;
  display:flex; flex-direction:column; align-items:center; justify-content:center; }}
.gauge-in b {{font-size:30px; line-height:1;}} .gauge-in span {{font-size:11px; color:#555;}}
</style>
""", unsafe_allow_html=True)

#*****************************************************************************************************
#   HELPER FUNCTIONS FOR THE PAGE
#*****************************************************************************************************
def badge(text, css):
    return '<span class="badge ' + css + '">' + html.escape(text) + '</span>'

def where_text(f):
    if f["sentence"]:
        return "Sentence " + str(f["sentence"])
    if f["field"]:
        return "Field: " + f["field"]
    return "Whole narrative"

def narrative_html(result, upto=None):
    # Builds the narrative with each flagged sentence colored. "upto" lets the animation reveal it sentence by sentence.
    n = len(result["sentences"]) if upto is None else upto
    out = ""
    for i in range(n):
        number = i + 1
        reasons, color = [], ""
        for f in result["flags"]:
            if f["sentence"] == number:
                reasons.append(f["reason"])
                if f["type"] in ["inconsistent", "citation_mismatch"]:
                    color = "#ffc9c9"                      # red = contradiction or citation problem
                elif color == "":
                    color = "#fff3bf"                      # yellow = unclear
        text = html.escape(result["sentences"][i])
        tip = html.escape(" | ".join(reasons), quote=True)
        label = "<sup>[" + str(number) + "]</sup> "
        if color != "":
            out += '<span class="sent" style="background:' + color + ';" title="' + tip + '">' + label + text + '.</span> '
        else:
            out += '<span class="sent">' + label + text + '.</span> '
    return out

def gauge_html(score):
    color = "#16a34a" if score >= 80 else ("#e0a100" if score >= 50 else "#d64545")
    return ('<div class="gauge" style="background: conic-gradient(' + color + ' 0 ' + str(score) + '%, #e5e7eb ' + str(score) + '% 100%);">'
            '<div class="gauge-in"><b>' + str(score) + '</b><span>READINESS</span></div></div>')

def flags_to_csv(flags):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["severity", "type", "element", "where", "reason", "question for officer", "source"])
    for f in flags:
        w.writerow([f["severity"], f["type"], f["element"], where_text(f), f["reason"], f["ask"], f["source"]])
    return buf.getvalue()

def show_result(result, case_name, key_prefix, do_animation=False):
    flags = result["flags"]
    run_id = str(st.session_state.get("run_id", 0))

    # ---- top row: gauge + numbers ----
    g, c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1, 1])
    g.markdown(gauge_html(result["readiness"]), unsafe_allow_html=True)
    c1.metric("Completeness", str(result["completeness"]) + "%")
    prev_key = "prev_" + key_prefix
    delta = None
    if prev_key in st.session_state:
        delta = len(flags) - st.session_state[prev_key]
    c2.metric("Flags found", len(flags), delta=delta, delta_color="inverse")
    c3.metric("Human review", "YES" if result["human_review"] else "No")
    c4.metric("Review time", str(result["seconds"]) + " s", "AI used" if result["ai_used"] else "rules only", delta_color="off")
    st.session_state[prev_key] = len(flags)

    if result["human_review"]:
        st.error("HUMAN REVIEW REQUIRED. " + " | ".join(result["reasons"]) + "  (The tool does not pick or suggest a charge.)")
    if result["ai_error"] != "":
        st.warning("AI was unavailable, so only the rule checks ran: " + result["ai_error"])

    # ---- narrative on the left, flags on the right ----
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Narrative with flags")
        box = st.empty()
        if do_animation:
            total = len(result["sentences"])
            for i in range(1, total + 1):
                box.markdown(narrative_html(result, i) + "<p>🔍 Scanning sentence " + str(i) + " of " + str(total) + "...</p>", unsafe_allow_html=True)
                time.sleep(min(0.6, 3.0 / total))
        box.markdown(narrative_html(result), unsafe_allow_html=True)
        st.caption("Red = contradiction or citation problem. Yellow = unclear. Hover a colored sentence to see why.")
        missing = [f for f in flags if f["type"] == "missing" and f["element"] in checker.REQUIRED]
        if len(missing) > 0:
            st.markdown("**Missing facts:** " + "".join('<span class="chip">' + html.escape(f["element"].replace("_", " ")) + '</span>' for f in missing),
                        unsafe_allow_html=True)
        st.subheader("Citation check")
        if len(result["citations"]) == 0:
            st.write("No citation found.")
        else:
            st.table(result["citations"])

    states = []                                            # (flag, status) so we can build the finalize gate below
    with right:
        st.subheader("Flags (" + str(len(flags)) + ")")
        if len(flags) == 0:
            st.success("No gaps found.")
        order = {"high": 0, "medium": 1, "low": 2}
        sorted_flags = sorted(flags, key=lambda x: order.get(x.get("severity", "medium"), 1))
        for i in range(len(sorted_flags)):
            f = sorted_flags[i]
            with st.container(border=True):
                sev = f.get("severity", "medium")
                line = badge(sev.upper(), sev) + badge(f["type"], "low")
                if f["source"] == "ai":
                    line += badge("AI", "aib")
                st.markdown(line + " **" + f["element"].replace("_", " ") + "** (" + where_text(f) + ")", unsafe_allow_html=True)
                st.write(f["reason"])
                if f.get("advisory"):
                    st.caption("Advisory note from the AI. It does not change the readiness score or the finish gate.")
                if f.get("ask"):
                    st.info("Ask the officer: " + f["ask"])
                status = st.radio("Officer decision", ["Open", "Fixed", "Dismissed"], horizontal=True,
                                  key="st_" + run_id + "_" + key_prefix + "_" + str(i))
                states.append((f, status))

    # ---- the FINALIZE GATE: shows the officer stays in control ----
    st.divider()
    st.subheader("Finalize gate")
    open_high = len([1 for f, s in states if s == "Open" and f["severity"] == "high"])
    open_other = len([1 for f, s in states if s == "Open" and f["severity"] != "high"])
    resolved = len([1 for f, s in states if s != "Open"])
    if len(states) > 0:
        st.progress(resolved / len(states))
        st.caption(str(resolved) + " of " + str(len(states)) + " flags resolved by the officer")
    signed = True
    if result["human_review"]:
        signed = st.checkbox("A human reviewer has looked at this case and signs off", key="sign_" + run_id + "_" + key_prefix)
    if open_high == 0 and signed:
        st.success("✅ READY TO FINALIZE. All high-priority flags are resolved" + (" and a human signed off." if result["human_review"] else "."))
        if open_other > 0:
            st.caption(str(open_other) + " lower-priority flag(s) still open.")
    else:
        why = []
        if open_high > 0:
            why.append(str(open_high) + " high-priority flag(s) still open")
        if not signed:
            why.append("human sign-off needed")
        st.error("⛔ NOT READY: " + ", ".join(why) + ". The tool only flags; the officer decides.")

    # ---- trust panel ----
    t1, t2, t3 = st.columns(3)
    t1.metric("Charges suggested by the tool", 0)
    t2.metric("AI suggestions blocked by guardrails", result["ai_blocked"])
    t3.metric("Flags tied to a sentence or field", str(len([f for f in flags if f["sentence"] or f["field"] or f["type"] == "missing"])) + " of " + str(len(flags)))

    d1, d2, d3 = st.columns(3)
    d1.download_button("Report (.html, print to PDF)", checker.make_html_report(result, case_name), case_name + "_report.html", key="html_" + key_prefix)
    d2.download_button("Report (.txt)", checker.make_report(result, case_name), case_name + "_report.txt", key="rep_" + key_prefix)
    d3.download_button("Flags (.csv)", flags_to_csv(flags), case_name + "_flags.csv", key="csv_" + key_prefix)

def pass_fail(ok):
    return "✅ meets target" if ok else "❌ below target"

#*****************************************************************************************************
#   NAVIGATION + SESSION HISTORY
#*****************************************************************************************************
PAGES = ["Home", "Review a Case", "Batch Review", "Scorecard", "Impact", "How It Works", "Settings"]
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "review_history" not in st.session_state:
    st.session_state.review_history = []
if "history_counter" not in st.session_state:
    st.session_state.history_counter = 0

def go_to(target):
    st.session_state.page = target
    st.rerun()

def save_history(case_name, result, narrative, source="Single review"):
    st.session_state.history_counter += 1
    st.session_state.review_history.insert(0, {
        "id": st.session_state.history_counter,
        "name": str(case_name), "result": result, "narrative": narrative,
        "source": source, "time": time.strftime("%b %d, %Y · %I:%M %p")
    })
    st.session_state.review_history = st.session_state.review_history[:30]

with st.sidebar:
    st.markdown("## 🛡️ Gap Review")
    st.caption("Investigative narrative workspace")
    st.divider()
    for item, glyph in [("Home","⌂"),("Review a Case","✎"),("Batch Review","▤"),("Scorecard","◫"),("Impact","↗"),("How It Works","ⓘ"),("Settings","⚙")]:
        if st.button(f"{glyph}  {item}", key="nav_"+item, width="stretch",
                     type="primary" if st.session_state.page == item else "secondary"):
            go_to(item)
    st.divider()
    st.markdown("**Recent reports**")
    if not st.session_state.review_history:
        st.caption("Completed reviews will appear here during this session.")
    else:
        for entry in st.session_state.review_history[:8]:
            label = f"{entry['name']} · {entry['time'].split('·')[-1].strip()}"
            if st.button(label, key=f"history_{entry['id']}", width="stretch"):
                st.session_state["history_selected"] = entry["id"]
                st.session_state.page = "Review a Case"
                st.rerun()
        if st.button("Clear recent history", key="clear_history", width="stretch"):
            st.session_state.review_history = []
            st.session_state.pop("history_selected", None)
            st.rerun()
    st.divider()
    if os.environ.get("CHALLENGEX_API_KEY"):
        st.caption("● Optional AI configured")
    else:
        st.caption("● Rules-only mode available")

use_ai = st.session_state.get("use_ai", True) and bool(os.environ.get("CHALLENGEX_API_KEY"))   # AI only when switched on AND a key exists
animate = st.session_state.get("animate", False)

if st.session_state.page == "Home":
    st.markdown("<div class='banner'><h1>Investigative Charge Documentation Review</h1><p>Find documentation gaps before a record is finalized. Clear flags, traceable evidence, and human judgment stay at the center.</p><span class='pill'>Sentence-linked findings</span><span class='pill'>Officer-selected charges only</span><span class='pill'>Human review for ambiguity</span><span class='pill'>Works without AI</span></div>", unsafe_allow_html=True)
    st.write("A focused review workspace for synthetic investigative narratives.")
    st.info("The assistant flags possible gaps and citation concerns. It never writes the narrative, chooses a charge, or replaces an officer or human reviewer.")
    c1,c2,c3=st.columns(3, gap="large")
    c1.metric("Review options", "Single or batch")
    c2.metric("Synthetic examples", len(ALL_SAMPLES))
    c3.metric("AI required", "No")
    st.subheader("Start here")
    a,b=st.columns(2)
    with a:
        with st.container(border=True):
            st.markdown("### ✍️ Review one case")
            st.write("Check a narrative, inspect evidence-linked flags, and record officer decisions.")
            if st.button("Open case review →", key="home_review", type="primary", width="stretch"): go_to("Review a Case")
        with st.container(border=True):
            st.markdown("### 📚 Review a batch")
            st.write("Run multiple synthetic narratives together and compare the results.")
            if st.button("Open batch review →", key="home_batch", width="stretch"): go_to("Batch Review")
    with b:
        with st.container(border=True):
            st.markdown("### 📈 Check performance")
            st.write("See how the built-in test set performs against the challenge targets.")
            if st.button("Open scorecard →", key="home_score", width="stretch"): go_to("Scorecard")
        with st.container(border=True):
            st.markdown("### 🧭 Quick tour")
            st.write("A short guide to the review steps and the limits of the assistant.")
            st.write("Explore the complete guided tour, including batch review, the scorecard, impact estimates, and safeguards.")
            if st.button("Explore how it works →", key="home_tour", width="stretch"):
                go_to("How It Works")
    st.caption("Tip: Try a built-in synthetic example first. No AI setup is needed to run the core checks.")

elif st.session_state.page == "Review a Case":
    st.title("Review a Case")
    st.caption("One narrative · required facts · contradictions · officer-selected citation")
    history_item = next((h for h in st.session_state.review_history if h["id"] == st.session_state.get("history_selected")), None)
    names = ["(blank narrative)"] + [s["id"] for s in ALL_SAMPLES]
    if history_item:
        st.info(f"Viewing saved report: **{history_item['name']}** · {history_item['time']}")
        if st.button("Return to a new review", key="new_review"):
            st.session_state.pop("history_selected", None); st.rerun()
        choice = "(saved report)"
        narrative = history_item["narrative"]
    else:
        choice = st.selectbox("Start with a synthetic example (optional)", names, key="review_sample_choice")
        start_text = next((s["narrative"] for s in ALL_SAMPLES if s["id"] == choice), "")
        narrative = st.text_area("Officer-written narrative", value=start_text, height=210,
                                 key="review_narrative_" + choice, placeholder="Paste a synthetic narrative here...")
    facts = {}
    if not history_item:
        with st.expander("Case facts and selected charge (optional)"):
            st.caption("Enter only synthetic/public test information. A populated fact field is considered during the review.")
            for name in checker.REQUIRED:
                facts[name] = st.text_input(name.replace("_", " ").capitalize(), key="review_fact_"+name)
            facts["selected_charge"] = st.text_input("Officer-selected charge", key="review_selected_charge")
    if history_item:
        show_result(history_item["result"], history_item["name"], "history_"+str(history_item["id"]))
    elif st.button("Review narrative", type="primary", disabled=not narrative.strip(), width="stretch"):
        with st.spinner("Checking required facts, consistency, and the selected citation..."):
            result = checker.review(narrative, facts, use_ai)
        st.session_state["one_result"] = result
        st.session_state["one_name"] = choice if choice != "(blank narrative)" else "case"
        save_history(st.session_state["one_name"], result, narrative)
        st.rerun()
    elif "one_result" in st.session_state and not history_item:
        show_result(st.session_state["one_result"], st.session_state.get("one_name", "case"), "one")

elif st.session_state.page == "Batch Review":
    st.title("Batch Review")
    st.write("Run many narratives at once, like the Unissant test bed of 25 to 50 cases. Review everything, or only the kinds of cases you care about.")

    # ---- 1. where are the narratives? ----
    source = st.radio("Where are the narratives?", ["Built-in sample cases", "Upload files (.json, .csv, or .txt)"], horizontal=True)
    cases = []
    if source == "Built-in sample cases":
        cases = [{"id": s["id"], "narrative": s["narrative"], "facts": s["facts"]} for s in ALL_SAMPLES]
        st.caption(str(len(cases)) + " synthetic cases: the 20 practice cases plus 22 held-out cases written with different wording.")
    else:
        uploads = st.file_uploader("Upload one JSON/CSV file, or several .txt files", accept_multiple_files=True, type=["json", "csv", "txt"])
        if uploads:
            cases, problems = loader.parse_uploads([(u.name, u.read()) for u in uploads])
            if cases:
                st.success(str(len(cases)) + " cases loaded.")
            for p in problems:
                st.warning(p)
    with st.expander("Upload format example / sample files"):
        st.code('[{"id":"sample_1","narrative":"Synthetic narrative text","facts":{}}]', language="json")
        d1, d2 = st.columns(2)
        d1.download_button("Download the sample cases (.json)", json.dumps([{"id": s["id"], "narrative": s["narrative"]} for s in ALL_SAMPLES], indent=1),
                           "sample_cases.json", key="dl_samples")
        d2.download_button("Download a CSV template", loader.template_csv(), "cases_template.csv", key="dl_template")

    # ---- 2. what should be reviewed?  (the quick rule screen sorts the cases into categories in about a millisecond each) ----
    selected = cases
    if cases:
        screen = {c["id"]: checker.categories_of(checker.review(c["narrative"], c.get("facts") or {}, False)) for c in cases}
        counts = {cat: len([1 for v in screen.values() if cat in v]) for cat in checker.CATEGORIES}
        scope = st.radio("What should be reviewed?", ["Review everything", "Choose categories", "Pick individual cases"], horizontal=True, key="batch_scope")
        if scope == "Choose categories":
            chosen = st.multiselect("Categories (a case can be in more than one)", checker.CATEGORIES, key="batch_cats",
                                    format_func=lambda c: c + " (" + str(counts[c]) + ")")
            selected = [c for c in cases if any(cat in chosen for cat in screen[c["id"]])]
        elif scope == "Pick individual cases":
            ids = st.multiselect("Cases", [c["id"] for c in cases], key="batch_ids")
            selected = [c for c in cases if c["id"] in ids]
        st.caption(str(len(selected)) + " of " + str(len(cases)) + " cases will be reviewed.")

    # ---- 3. run ----
    ai_ready = bool(os.environ.get("CHALLENGEX_API_KEY")) and st.session_state.get("use_ai", True)
    batch_ai = st.checkbox("Also run the AI double-check (slower: several seconds per case, run in parallel)", value=False, disabled=not ai_ready, key="batch_ai")
    if not ai_ready:
        st.caption("The AI is off or not set up, so the fast rule checks will run. Results are still valid.")
    if st.button("Run batch review", type="primary", disabled=len(selected) == 0) and len(selected) > 0:
        bar = st.progress(0.0, text="Starting reviews...")
        started = time.time()
        results = checker.review_many(selected, batch_ai and ai_ready,
                                      progress=lambda done, total, cid: bar.progress(done / total, text="Reviewed " + str(done) + " of " + str(total)))
        st.session_state["batch_results"] = results
        st.session_state["batch_meta"] = {"seconds": round(time.time() - started, 2), "ai": batch_ai and ai_ready}
        st.session_state["run_id"] = st.session_state.get("run_id", 0) + 1

    if st.session_state.get("batch_results"):
        results = st.session_state["batch_results"]
        meta = st.session_state.get("batch_meta", {})
        st.divider()
        st.subheader("Results")
        st.caption("Reviewed " + str(len(results)) + " cases in " + str(meta.get("seconds", "?")) + " s (" + ("rules + AI" if meta.get("ai") else "rules only") + ").")
        total_flags = sum(len(r["flags"]) for r in results.values())
        human = [cid for cid in results if results[cid]["human_review"]]
        avg_time = sum(r["seconds"] for r in results.values()) / len(results)
        avg_ready = round(sum(r["readiness"] for r in results.values()) / len(results))
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Cases reviewed", len(results))
        m2.metric("Total flags", total_flags)
        m3.metric("Sent to human review", len(human))
        m4.metric("Average time", str(round(avg_time, 2)) + " s")
        m5.metric("Average readiness", avg_ready)

        counts_el = {}
        for r in results.values():
            for f in r["flags"]:
                counts_el[f["element"]] = counts_el.get(f["element"], 0) + 1
        if len(counts_el) > 0:
            st.subheader("Where do narratives fail most?")
            st.bar_chart(pd.DataFrame({"flags": list(counts_el.values())}, index=list(counts_el.keys())))

        rows = []
        for cid in results:
            r = results[cid]
            rows.append({"case": cid, "readiness": r["readiness"], "flags": len(r["flags"]),
                         "human review": "YES" if r["human_review"] else "", "seconds": r["seconds"],
                         "categories": ", ".join(checker.categories_of(r)),
                         "top issues": ", ".join(sorted(set(f["element"] for f in r["flags"])))})
        st.dataframe(rows, width="stretch")

        st.subheader("Human review queue")
        if len(human) == 0:
            st.write("Nothing needs human review.")
        for cid in human:
            st.warning(cid + ": " + " | ".join(results[cid]["reasons"]))

        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as z:
            for cid in results:
                z.writestr(cid + "_report.html", checker.make_html_report(results[cid], cid))
        st.download_button("Download all reports (.zip of HTML pages)", zbuf.getvalue(), "gap_reports.zip", key="zip_all")
        sbuf = io.StringIO()
        w = csv.DictWriter(sbuf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
        st.download_button("Download summary (.csv)", sbuf.getvalue(), "batch_summary.csv", key="sum_all")

        st.subheader("Look at one case")
        pick = st.selectbox("Case", list(results.keys()), key="batch_pick")
        show_result(results[pick], pick, "batch")

elif st.session_state.page == "Scorecard":
    st.title("Scorecard")
    st.caption("A quick test of whether the checker meets the ChallengeX goals. This is a benchmark, not an officer case review.")
    st.markdown("It runs built-in synthetic examples and compares the checker's findings with the expected answer key. It measures **how many planted issues were caught**, **how many extra flags were incorrect**, **whether every hard case reached a human**, and **whether reviews stayed under 60 seconds**. It does not score an officer's individual case.")
    set_choice = st.radio("Which test set?", ["Practice set (20 cases)", "Practice + held-out set (42 cases)"], horizontal=True, key="score_set",
                          help="The held-out cases were written after the rules, with different wording, so they show whether the checker really generalizes.")
    ai_ready = bool(os.environ.get("CHALLENGEX_API_KEY")) and st.session_state.get("use_ai", True)
    score_ai = st.checkbox("Also include the AI double-check (slower)", value=False, disabled=not ai_ready, key="score_ai",
                           help="The answer key only knows the rule checks. Rules-only is the fair, repeatable test. AI remarks outside the checklist are shown as advisory notes and are not graded.")
    if st.button("Run performance check", type="primary"):
        chosen_set = SAMPLES if set_choice.startswith("Practice set") else ALL_SAMPLES
        bar = st.progress(0.0, text="Testing the sample set...")
        started = time.time()
        cases = [{"id": s["id"], "narrative": s["narrative"], "facts": s.get("facts") or {}} for s in chosen_set]
        st.session_state["scorecard_results"] = checker.review_many(cases, score_ai and ai_ready,
            progress=lambda done, total, cid: bar.progress(done / total, text="Tested " + str(done) + " of " + str(total)))
        st.session_state["scorecard_meta"] = {"seconds": round(time.time() - started, 2), "ai": score_ai and ai_ready}
    if st.session_state.get("scorecard_results"):
        results = st.session_state["scorecard_results"]
        meta = st.session_state.get("scorecard_meta", {})
        answer_key = {k: {"planted": [list(p) for p in v["planted"]], "human": v["human"]} for k, v in ALL_KEY.items() if k in results}
        sc = checker.score(results, answer_key)
        slowest = max((r["seconds"] for r in results.values()), default=0)
        measures = [("Issues caught", sc["recall"] * 100, "Goal: at least 90%", sc["recall"] >= .90),
                    ("Incorrect extra flags", sc["false_rate"] * 100, "Goal: no more than 10%", sc["false_rate"] <= .10),
                    ("Ambiguous cases escalated", sc["human_recall"] * 100, "Goal: 100%", sc["human_recall"] >= 1.0),
                    ("Slowest review", slowest, "Goal: under 60 sec", slowest < 60)]
        st.caption("Graded " + str(sc["cases_scored"]) + " cases in " + str(meta.get("seconds", "?")) + " s (" + ("rules + AI" if meta.get("ai") else "rules only") + ").")
        cols = st.columns(4)
        for col, (label, value, target, passed) in zip(cols, measures):
            col.metric(label, "%.1f s" % value if label == "Slowest review" else "%.1f%%" % value)
            col.caption(target)
            if passed:
                col.success("On target")
            else:
                col.warning("Needs improvement")
        if all(m[3] for m in measures):
            st.success("All challenge targets met on this sample set.")
        else:
            st.warning("One or more challenge targets need improvement. The table below says exactly which cases and which flags.")
        with st.expander("See case-by-case benchmark details"):
            st.dataframe(sc["rows"], width="stretch", hide_index=True)
            st.caption("Detected " + str(sc["caught"]) + " planted issues. Missed " + str(sc["missed"]) + ". Extra flags " + str(sc["extra"]) + ". A flag repeated in one case counts once.")
        with st.expander("Download benchmark data"):
            st.download_button("Download scorecard (.csv)", pd.DataFrame(sc["rows"]).to_csv(index=False), "scorecard.csv")
    else:
        st.info("Run the performance check to see how the prototype performs against the challenge goals.")

elif st.session_state.page == "Impact":
    st.title("Impact Estimator")
    st.caption("An illustrative planning tool — not measured operational savings.")
    a,b=st.columns(2)
    per_day=a.number_input("Narratives per day",1,10000,200,10); pct_bad=a.slider("Share later needing rework (%)",1,50,15)
    late=b.slider("Minutes to fix after finalization",5,120,20); early=b.slider("Minutes to fix before finalization",1,60,5); caught=b.slider("Estimated share caught early (%)",0,100,90)
    saved=(per_day*pct_bad/100*caught/100)*max(0,late-early)
    x,y,z=st.columns(3); x.metric("Potential gaps caught / day",f"{per_day*pct_bad/100*caught/100:.1f}"); y.metric("Potential time saved / day",f"{saved/60:.1f} hrs"); z.metric("Potential time saved / month",f"{saved*22/60:.1f} hrs")
    st.caption("Change the assumptions to explore scenarios. Validate with measured pilot data before making operational claims.")

elif st.session_state.page == "How It Works":
    st.title("How It Works")
    st.caption("A friendly tour of the workspace, from the first narrative to the final human decision.")
    steps = [
        ("1. Start with a case", "Open Review a Case and choose a synthetic example, or enter a test narrative and optional case facts. The officer-written narrative remains the source text."),
        ("2. Run the checks", "The rule-based checker looks for missing required facts, contradictions, and possible citation mismatches. Optional AI can provide a second look when it is configured."),
        ("3. Understand the flags", "Each finding includes a plain-language reason and, when possible, points to the sentence or field that needs attention."),
        ("4. Review a batch", "Use Batch Review to test several synthetic cases together. Filter by issue category or select individual cases, then compare results."),
        ("5. Check performance", "Scorecard runs the built-in examples against their answer key. It is a repeatable prototype benchmark, not a score for an individual officer."),
        ("6. Estimate potential impact", "Impact lets you adjust assumptions to explore possible time savings. Treat the output as illustrative until validated with measured pilot data."),
        ("7. Keep the decision with a person", "The tool does not write or rewrite narratives, select or recommend charges, or replace a qualified human reviewer. Ambiguous cases should be escalated."),
    ]
    for heading, explanation in steps:
        with st.container(border=True):
            st.markdown("### " + heading)
            st.write(explanation)
    st.warning("Use synthetic or public test data only. Do not enter PII, CUI, live government records, or production credentials.")
    if st.button("Start with a case review", type="primary"):
        go_to("Review a Case")

elif st.session_state.page == "Settings":
    st.title("Settings")
    st.caption("Personalize the workspace. Technical configuration stays tucked away in Advanced.")
    st.subheader("Appearance")
    theme_col, mode_col = st.columns([2, 1], gap="large")
    with theme_col:
        selected_theme = st.selectbox("Color theme", list(THEMES.keys()), key="theme_name",
                                      help="Changes the accent colors across the workspace.")
    with mode_col:
        st.toggle("Dark mode", key="dark_mode", help="Switches the page, sidebar, cards, and inputs to a dark palette.")
    st.caption("Theme changes apply automatically when Streamlit reruns the page.")
    st.divider()
    st.session_state["use_ai"]=st.toggle("Use optional AI second check",value=st.session_state.get("use_ai",True),help="The rule-based checker always runs. Turn this off to use rules only.")
    st.session_state["animate"]=st.toggle("Show scan animation",value=st.session_state.get("animate",False))
    with st.expander("How this tool works and its safeguards"):
        st.markdown("**Inputs → Checks → Flags → Human decision**")
        st.write("The system checks the officer-written narrative and optional case facts for required elements, internal inconsistencies, and possible mismatches involving the charge already selected by the officer.")
        st.write("It never writes or rewrites a narrative and never selects or recommends a charge. Ambiguous or multi-charge situations are routed for human review. Every finding should be tied to a sentence or field where possible.")
        st.warning("Use synthetic or public data only. Do not enter CUI, PII, live government records, or production credentials. This prototype is not legal advice or an authoritative determination.")
    with st.expander("Advanced · Backend AI configuration"):
        st.write("For a deployed version, set **CHALLENGEX_API_KEY** as a server-side environment variable or secret. Do not commit credentials to source control. A key entered here is held only by this running app process.")
        backend=st.text_input("Backend API key",type="password",key="advanced_backend_key",placeholder="Optional")
        if backend.strip(): os.environ["CHALLENGEX_API_KEY"]=backend.strip(); st.success("Key loaded for this session; its value is hidden.")
        if os.environ.get("CHALLENGEX_API_KEY"):
            st.caption("Backend AI is configured.")
            if st.button("Test AI connection"):
                import ai
                with st.spinner("Testing connection..."):
                    ok,msg=ai.ping()
                if ok:
                    st.success(msg)
                else:
                    st.warning("AI unavailable. Rules-only reviews remain available. " + msg)
        else: st.info("No backend key configured. The application will use rule-based checks only.")
    with st.expander("About deployment"):
        st.write("For a demo, run locally on a trusted machine. For a shared team demo, host behind authentication with server-side secrets and approved storage. This prototype is designed for synthetic data only; do not deploy it for real case records without a security, privacy, retention, and access-control review.")
