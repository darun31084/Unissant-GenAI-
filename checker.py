# checker.py  --  the BACKEND. All the checking logic lives in this one file.
# It only uses things you already know: lists, dictionaries, loops, `in`, and functions.

import time, re, threading

#*****************************************************************************************************
#   PART 1: THE CHECKLIST  (a dictionary: fact name -> list of "clue words")
#*****************************************************************************************************
# If NONE of the clue words appear in the narrative (and the form box is empty),
# we say that fact is missing.
months = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

REQUIRED = {
    "subject_name":           ["mr.", "ms.", "mrs."],             # plus a regex (see has_fact)
    "country_of_citizenship": ["citizen of", "national of", "native of", "citizen and national", "citizenship"],   # plus a regex (see has_fact)
    "date_of_encounter":      [],                                  # handled by a regex (see has_fact)
    "place_of_encounter":     ["near", "station", "port of entry", "checkpoint", "airport", "bridge", "sector", "highway",
                               "residence", "field office", "jail", "prison", "facility", "worksite", "workplace", "address", "county",
                               "road", "interstate", "ranch", "mile marker", "intersection", "street", "avenue", "terminal", "courthouse",
                               "detention", "inspection point"],                          # plus a regex for "in/at <Place>" (see has_fact)
    "manner_of_encounter":    ["encounter", "apprehend", "arrest", "observed", "detain", "found", "located", "interdict",
                               "intercept", "stopped", "contacted", "custody", "referred", "identified", "screened", "interviewed"],
    "manner_of_entry":        ["entered", "crossed", "arrived", "presented", "admitted", "without inspection", "not designated",
                               "walked", "waded", "swam", "smuggled", "stowaway", "drove across", "illegally", "surreptitious", "evaded"],
    "subject_statements":     ["stated", "claimed", "said", "advised", "interview", "declined", "told", "admits", "admitted that", "admitted to",
                               "responded", "replied", "acknowledged", "confessed", "denied", "explained", "volunteered", "sworn", "under oath",
                               "miranda", "questioned", "interrogat"],
    "immigration_history":    ["prior", "previous", "never", "removed", "deported", "visa", "history",
                               "records check", "records show", "records indicate", "records confirm", "a-file", "alien file", "system check"],
    "documents":              ["document", "passport", "visa", "card", "permit", "papers", "identification", "i-94", "i-551", "i-766"],
}

# Regexes for facts that plain clue words cannot catch well.
MONTH_RE = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)"
DATE_RES = [
    r"\b" + MONTH_RE + r"\.?\s+\d{1,2}\b",                 # March 14, 2025
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?" + MONTH_RE + r"\b", # 14 March 2025
    r"\b" + MONTH_RE + r"\.?,?\s+(?:19|20)\d\d\b",           # March 2025
    r"\b\d{1,2}[/-]\d{1,2}[/-](?:\d{2}|\d{4})\b",              # 05/02/2025
    r"\b(?:19|20)\d\d-\d{1,2}-\d{1,2}\b",                      # 2025-03-14
]
NAME_RES = [
    r"['‘’\"“”][A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+)*['’\"“”]",   # 'John Doe'
    r"\b(?:[Ss]ubject|[Aa]lien|[Rr]espondent|[Ii]ndividual|[Dd]etainee)\s+(?:named\s+|identified as\s+)?[A-Z][a-z]+(?:[\s\-][A-Z][A-Za-z\-']+)+",   # Subject John Doe
    r"\b(?:named|identified as|known as|a\.k\.a\.?|alias)\s+[A-Z][A-Za-z\-']+",                                                      # named John Doe
    r"\b(?:encountered|apprehended|arrested|located|detained|interviewed|identified|intercepted|stopped|contacted)\s+(?:an?\s+)?[A-Z][a-z]+(?:[\s\-][A-Z][A-Za-z\-']+)+",   # arrested John Doe
    r"\b(?:Mr|Ms|Mrs|Mx)\.?\s+[A-Z][a-z]+",                                                                                           # Mr. Doe
]
ALLCAPS_NAME_RE = r"\b[A-Z]{2,}(?:\s+[A-Z]\.?)?\s+[A-Z]{2,}(?:-[A-Z]{2,})?\b"                    # JOHN DOE (all caps, as in I-213s)
AGENCY_WORDS = {"ICE", "ERO", "CBP", "USBP", "DHS", "HSI", "OFO", "INA", "USCIS", "FBI", "DEA", "ATF", "BP", "EOIR", "NTA", "USA", "US",
                "TX", "AZ", "NM", "CA", "FL", "NY", "WA", "MI", "OH", "IL", "GA", "NV", "LA", "UT", "CO", "NC", "VA", "NJ", "PA", "MA"}
# a place written as "in/at/near <Capitalized Place>" (not a month, not "the United States")
PLACE_RE = (r"(?i:\b(?:in|at|near|outside|inside|within|along|north of|south of|east of|west of))\s+(?:the\s+)?"
            r"(?!(?:" + MONTH_RE + r"|United|U\.S|Attorney|Subject|Immigration|Section|Notice|Form|Act|INA|That|This)\b)[A-Z][A-Za-z.\-']+")
CITIZEN_RE = r"\b(?:citizens?|citizenship|nationals?|nationality)\b(?!\s+(?:park|guard|forest|security|targeting))"
COUNTRY_RE = r"\b(?:citizens?|nationals?)\s+of\s+(?:the\s+)?([A-Z][A-Za-z]+(?:\s+(?:and\s+)?[A-Z][A-Za-z]+)?)"

#*****************************************************************************************************
#   PART 2: THE LAW CHEAT SHEET  (a dictionary: law -> info about it)
#*****************************************************************************************************
# Laws are written in lowercase with no spaces so we can match messy typing like "212(A) (9) (A) (I)".
# "supports"    = words that FIT this law.   "contradicts" = words that go AGAINST this law.
# "needs"       = facts from the checklist that must be present for this law to make sense.
# Unissant will give you the real reference sheet: add/replace entries here.
CHARGES = {
    "212(a)(6)(a)(i)": {
        "meaning": "Entered the U.S. without being admitted or paroled (entry without inspection).",
        "supports": ["without inspection", "not designated", "ewi", "illegally entered", "not then admitted", "without admission", "without being admitted",
                     "not admitted", "outside a port", "between ports", "surreptitious", "evaded inspection", "illegally", "unlawfully", "entered at a place",
                     "walked across", "waded", "swam"],
        "contradicts": ["was admitted", "inspected and admitted", "lawfully admitted", "legally admitted", "overstay"],
        "needs": ["manner_of_entry"]},
    "212(a)(6)(c)(i)": {
        "meaning": "Fraud or willful misrepresentation of a material fact.",
        "supports": ["misrepresent", "fraud", "false", "counterfeit", "altered", "impersonat"],
        "contradicts": [],
        "needs": ["documents"]},
    "212(a)(7)(a)(i)(i)": {
        "meaning": "Immigrant without a valid, unexpired entry document or visa.",
        "supports": ["no passport", "no visa", "no valid", "no document", "never had any documents", "lacked", "not in possession"],
        "contradicts": [],
        "needs": ["documents"]},
    "212(a)(9)(a)": {
        "meaning": "Previously removed or deported, then entered or tried to enter again.",
        "supports": ["ordered removed", "previously removed", "removed from", "deported", "removal order"],
        "contradicts": ["no prior removal", "never been removed", "never removed"],
        "needs": ["immigration_history"]},
    "212(a)(9)(b)(i)": {
        "meaning": "Left the U.S. after a period of unlawful presence (3- or 10-year bar).",
        "supports": ["unlawful presence", "unlawfully present", "overstay", "departed"],
        "contradicts": [],
        "needs": ["manner_of_entry"]},
    "212(a)(2)(a)(i)(i)": {
        "meaning": "Convicted of, or admits, a crime involving moral turpitude.",
        "supports": ["convict", "crime", "offense", "charged with", "sentenced"],
        "contradicts": ["no criminal record", "no criminal history"],
        "needs": []},
    "237(a)(1)(b)": {
        "meaning": "Was admitted to the U.S. but is now here in violation of the law.",
        "supports": ["admitted", "overstay", "visa", "status", "remained", "violation", "expired", "failed to maintain"],
        "contradicts": ["without inspection", "not designated", "ewi"],
        "needs": ["manner_of_entry"]},
    "235(b)(1)": {
        "meaning": "Expedited removal of an arriving alien found inadmissible.",
        "supports": ["arriving", "port of entry", "expedited", "airport", "seeking admission", "sought admission"],
        "contradicts": [],
        "needs": ["place_of_encounter"]},
}

#*****************************************************************************************************
#   PART 3: PAIRS OF CLUES THAT CONTRADICT EACH OTHER
#*****************************************************************************************************
# If one sentence has a clue from list A and a different sentence has a clue from list B, we flag it.
CONFLICTS = [
    {"element": "manner_of_entry",
     "a": ["without inspection", "not designated", "ewi", "illegally", "surreptitious", "evaded inspection", "between ports of entry", "outside a port of entry"],
     "b": ["was admitted", "inspected and admitted", "lawfully admitted", "legally admitted", "re:\\badmitted (?:as|in|on|with|at) ", "was inspected",
           "entered legally", "entered lawfully", "presented herself at", "presented himself at", "presented themselves at"],
     "reason": "One sentence says the subject entered without inspection, but another says the subject was inspected or admitted."},
    {"element": "documents",
     "a": ["never had any documents", "no documents", "no valid documents", "no papers", "had no passport", "without any documents", "no identity documents"],
     "b": ["re:\\bpresented (?:a |an |his |her |their |the )?(?:valid |genuine |current |unexpired |expired )?(?:passport|visa|permit|border crossing card|i-94)",
           "re:\\b(?:produced|provided|displayed) (?:a |an |his |her |their |the )?(?:valid |genuine )?(?:passport|visa|permit)",
           "re:\\b(?:possessed|had|held|carried) (?:a |an |his |her )(?:valid |genuine )?(?:passport|visa)"],
     "reason": "One sentence says the subject had no documents, but another says a document was presented."},
    {"element": "immigration_history",
     "a": ["no prior immigration", "no prior history", "no prior removal", "never been removed", "never been deported", "no previous removal",
           "no previous immigration", "never removed", "re:no (?:prior|previous) (?:removals?|deportations?)"],
     "b": ["previously ordered removed", "previously removed", "was deported", "ordered removed", "was removed", "previously deported", "had been removed"],
     "reason": "One sentence says there is no prior history/removal, but another describes a prior removal."},
]

#*****************************************************************************************************
#   PART 4: SMALL HELPER FUNCTIONS
#*****************************************************************************************************
ABBREVIATIONS = ["U.S.", "Mr.", "Ms.", "Mrs.", "Dr.", "No.", "St.", "Sec.", "Sgt.", "Ofc.", "Lt.", "Jr.", "Sr.", "a.k.a.", "A.K.A.",
                 "approx.", "Approx.", "Ave.", "Mt.", "Ft.", "Hwy.", "Rd.", "Dept.", "vs.", "e.g.", "i.e."]

def split_into_sentences(text):
    # Turn line breaks into ". " then cut at every ". " so we get a list of sentences.
    for ab in ABBREVIATIONS:                          # keep "U.S. Border Patrol" in one piece
        text = text.replace(ab, ab.replace(".", "\x00"))
    text = text.replace("\n", ". ")
    pieces = [p.replace("\x00", ".") for p in text.split(". ")]
    sentences = []
    for p in pieces:
        p = p.strip().rstrip(".")
        if p != "":
            sentences.append(p)
    return sentences

def has_any(text, words):
    # True if ANY word from the list appears in the text. A word that starts with "re:" is a regular expression.
    text = text.lower()
    for w in words:
        if w.startswith("re:"):
            if re.search(w[3:], text):
                return True
        elif w in text:
            return True
    return False

def has_name(text):
    if has_any(text, REQUIRED["subject_name"]) or any(re.search(r, text) for r in NAME_RES):
        return True
    for m in re.finditer(ALLCAPS_NAME_RE, text):                       # ALL-CAPS name, but not "ICE ERO" or "CBP OFO"
        if not any(tok in AGENCY_WORDS for tok in re.split(r"[\s\-.]+", m.group(0))):
            return True
    return False

def has_fact(text, name):
    # Like has_any, but uses regexes for dates and names (so the word "may" or "Subject's" is not mistaken for a fact).
    if name == "date_of_encounter":
        return any(re.search(r, text, re.I) for r in DATE_RES)
    if name == "subject_name":
        return has_name(text)
    if name == "country_of_citizenship":
        return has_any(text, REQUIRED[name]) or bool(re.search(CITIZEN_RE, text, re.I))
    if name == "place_of_encounter":
        return has_any(text, REQUIRED[name]) or bool(re.search(PLACE_RE, text))
    return has_any(text, REQUIRED.get(name, []))

def find_sentence(sentences, words):
    # Returns the number (1, 2, 3...) of the first sentence containing any of the words, or None.
    for i in range(len(sentences)):
        if has_any(sentences[i], words):
            return i + 1
    return None

# How serious is each kind of problem? (shown as a colored badge in the website)
HIGH_FACTS = ["country_of_citizenship", "date_of_encounter", "place_of_encounter",
              "manner_of_encounter", "manner_of_entry"]

# For missing facts we give the officer a QUESTION to answer (we never write the narrative for them).
QUESTIONS = {
    "subject_name": "What is the subject's name?",
    "country_of_citizenship": "What is the subject's country of citizenship?",
    "date_of_encounter": "On what date did the encounter happen?",
    "place_of_encounter": "Where did the encounter happen (station, port of entry, or location)?",
    "manner_of_encounter": "How was the subject encountered (apprehended, arrested, referred...)?",
    "manner_of_entry": "How and where did the subject enter the United States?",
    "subject_statements": "What did the subject say when questioned?",
    "immigration_history": "What is the subject's prior immigration history, if any?",
    "documents": "What documents did the subject have or present?",
}

def make_flag(kind, element, reason, sentences, number=None, field=None, source="rules"):
    # One problem = one dictionary. "number" says which sentence it came from.
    quote = ""
    if number is not None:
        quote = sentences[number - 1]
    # severity: contradictions and citation problems are high; missing facts depend on the fact
    if kind in ["inconsistent", "citation_mismatch"]:
        severity = "high"
    elif kind == "missing" and element in HIGH_FACTS:
        severity = "high"
    else:
        severity = "medium"
    ask = QUESTIONS.get(element, "") if kind == "missing" else ""
    return {"type": kind, "element": element, "reason": reason, "severity": severity, "ask": ask,
            "sentence": number, "field": field, "quote": quote, "source": source, "advisory": False}

CITE_RE = r"(?:212|237|235)(?:\([a-z0-9]{1,4}\))+"

def find_laws(text):
    # Reads every citation like 212(a)(6)(A)(i) as a WHOLE and matches it to the cheat sheet.
    # Returns: laws found (list), incomplete citations such as "Section 212" with nothing after it (list),
    #          and well-formed citations that are NOT on our cheat sheet (list, a human must check those).
    squashed = text.lower().replace(" ", "")          # remove spaces so messy typing still matches
    squashed = squashed.replace("1182(", "212(").replace("1227(", "237(").replace("1225(", "235(")  # 8 U.S.C. numbers -> INA numbers
    laws, unlisted = [], []
    for m in re.finditer(CITE_RE, squashed):
        cited = m.group(0)
        best = ""
        for law in CHARGES:                           # exact match, or a deeper part of a listed law, e.g. 212(a)(9)(a)(i) -> 212(a)(9)(a)
            if (cited == law or cited.startswith(law)) and len(law) > len(best):
                best = law
        if best != "":
            if best not in laws:
                laws.append(best)
        elif cited not in unlisted and len(cited) > 8:      # "235(b)" alone is too short to judge, so it is ignored
            unlisted.append(cited)
    incomplete = []
    for num in ["212", "237", "235"]:
        word = "section" + num
        start = 0
        while True:
            i = squashed.find(word, start)
            if i == -1:
                break
            after = squashed[i + len(word): i + len(word) + 1]   # the character right after "section212"
            if after != "(":
                incomplete.append("Section " + num)
            start = i + 1
    return laws, incomplete, unlisted

#*****************************************************************************************************
#   PART 5: THE THREE CHECKS
#*****************************************************************************************************
def check_missing(narrative, facts, sentences):
    # CHECK 1: is each required fact in the narrative or in the form box?
    flags = []
    for name in REQUIRED:
        filled_in_form = facts.get(name, "").strip() != ""
        found_in_text = has_fact(narrative, name)
        if not filled_in_form and not found_in_text:
            reason = name.replace("_", " ").capitalize() + " is not stated in the narrative."
            flags.append(make_flag("missing", name, reason, sentences))
    return flags

def check_conflicts(sentences):
    # CHECK 2: do two sentences contradict each other?
    flags = []
    for c in CONFLICTS:
        a = find_sentence(sentences, c["a"])
        b = find_sentence(sentences, c["b"])
        if a is not None and b is not None and a != b:
            reason = c["reason"] + " (Compare sentence " + str(a) + " and sentence " + str(b) + ".)"
            flags.append(make_flag("inconsistent", c["element"], reason, sentences, number=b))
    return flags

def check_citizenship(sentences):
    # CHECK 2b: is the subject said to be a citizen of two DIFFERENT countries?
    seen = {}
    for i in range(len(sentences)):
        for m in re.finditer(COUNTRY_RE, sentences[i]):
            seen.setdefault(m.group(1).strip().lower(), i + 1)
    if len(seen) > 1:
        names = list(seen.keys())
        reason = ("Citizenship is stated two different ways ('" + names[0] + "' and '" + names[1] + "'). "
                  "(Compare sentence " + str(seen[names[0]]) + " and sentence " + str(seen[names[1]]) + ".)")
        return [make_flag("inconsistent", "country_of_citizenship", reason, sentences, number=max(seen[names[0]], seen[names[1]]))]
    return []

def check_charges(laws, incomplete, unlisted, sentences, all_text, facts):
    # CHECK 3: does each cited law fit the facts?  (NEVER suggests a different law.)
    flags, citations, reasons = [], [], []

    for sec in incomplete:
        msg = "'" + sec + "' is incomplete. INA charges need the full subsection."
        num = find_sentence(sentences, [sec.lower()])
        flags.append(make_flag("unclear", "charge_citation", msg, sentences, number=num))
        citations.append({"law": sec, "status": "incomplete", "meaning": "Subsection missing."})
        reasons.append("A charge citation is incomplete ('" + sec + "').")

    for cited in unlisted:                              # a real-looking law that our cheat sheet does not cover: we cannot judge it, so a human must
        citations.append({"law": cited, "status": "not on reference sheet", "meaning": "The tool cannot check this law."})
        reasons.append("The cited law (" + cited + ") is not on the reference sheet, so the tool cannot check it.")

    if len(laws) == 0 and len(incomplete) == 0 and len(unlisted) == 0:
        flags.append(make_flag("citation_mismatch", "charge_citation",
                     "No charge citation from the reference sheet was found.", sentences, field="selected_charge"))
        reasons.append("No readable charge citation, so the charge cannot be checked.")

    if len(laws) > 1:
        reasons.append(str(len(laws)) + " different charges are cited (multi-charge case).")

    for law in laws:
        info = CHARGES[law]
        status = "ok"
        # a) any words that go AGAINST this law?
        num = find_sentence(sentences, info["contradicts"])
        if num is not None:
            msg = law + " means: " + info["meaning"] + " Other facts in the record point the other way."
            flags.append(make_flag("citation_mismatch", "charge_citation", msg, sentences, number=num))
            status = "likely mismatch"
        # b) any words that FIT this law?
        if not has_any(all_text, info["supports"]):
            msg = law + " means: " + info["meaning"] + " The narrative does not state facts that match this."
            flags.append(make_flag("citation_mismatch", "charge_citation", msg, sentences))
            status = "likely mismatch"
        # c) is every fact this law needs present?
        for need in info["needs"]:
            if not has_fact(all_text, need) and facts.get(need, "").strip() == "":
                msg = law + " needs '" + need.replace("_", " ") + "' but it is not stated."
                flags.append(make_flag("citation_mismatch", "charge_citation", msg, sentences))
                status = "likely mismatch"
        citations.append({"law": law, "status": status, "meaning": info["meaning"]})
    return flags, citations, reasons

#*****************************************************************************************************
#   PART 6: THE MAIN FUNCTION  (runs everything and returns one result dictionary)
#*****************************************************************************************************
KNOWN_ELEMENTS = list(REQUIRED.keys()) + ["charge_citation"]
MAX_AI_FLAGS = 3

def tidy_ai_flags(ai_flags, existing):
    # The AI may only ADD things that are new. Anything the rules already flagged is dropped (it would be double counting), and an
    # AI remark about something outside our checklist is kept as a quiet "advisory" note that never changes the score or the finish gate.
    have = set((f["type"], f["element"]) for f in existing)
    kept = []
    for f in ai_flags:
        element = str(f.get("element", "")).strip().lower().replace(" ", "_")
        if element in KNOWN_ELEMENTS:
            f["element"] = element
            if (f["type"], element) in have:
                continue
        else:
            f["element"], f["advisory"], f["severity"] = "other", True, "low"
        f.setdefault("advisory", False)
        have.add((f["type"], f["element"]))
        kept.append(f)
        if len(kept) >= MAX_AI_FLAGS:
            break
    return kept

def review(narrative, facts=None, use_ai=False):
    start_time = time.time()
    if facts is None:
        facts = {}
    sentences = split_into_sentences(narrative)

    # the officer's "selected charge" box counts as part of the text we search for laws
    all_text = narrative + " " + " ".join(str(v) for v in facts.values())
    laws, incomplete, unlisted = find_laws(all_text)

    flags = check_missing(narrative, facts, sentences)
    flags += check_conflicts(sentences)
    flags += check_citizenship(sentences)
    charge_flags, citations, reasons = check_charges(laws, incomplete, unlisted, sentences, all_text, facts)
    flags += charge_flags

    # contradicting entry facts mean the case is ambiguous, so a human must look
    for f in flags:
        if f["type"] == "inconsistent" and f["element"] == "manner_of_entry":
            reasons.append("Facts about how the subject entered conflict, so the case is ambiguous.")
        if f["type"] == "inconsistent" and f["element"] == "country_of_citizenship":
            reasons.append("The subject's citizenship is stated two different ways, so the case is ambiguous.")

    # OPTIONAL: ask the AI to double-check (if it fails, we just keep the rules-only result)
    ai_used, ai_error, ai_blocked = False, "", 0
    if use_ai:
        try:
            import ai                                   # our AI file
            missing_names = [f["element"] for f in flags if f["type"] == "missing"]
            answer = ai.ask_ai(sentences, facts, laws, list(CHARGES.keys()), missing_names)
            # the AI found facts we thought were missing -> remove those false alarms
            flags = [f for f in flags if not (f["type"] == "missing" and f["element"] in answer["present"])]
            flags += tidy_ai_flags(answer["flags"], flags)   # extra problems the AI found (already checked, then tidied)
            if answer["ambiguous"] != "":
                reasons.append(answer["ambiguous"])
            ai_blocked = answer["blocked"]              # how many AI suggestions our guardrails threw away
            ai_used = True
        except Exception as e:
            ai_error = str(e)[:200]

    reasons = list(dict.fromkeys(reasons))              # remove duplicate reasons
    # completeness = what % of the required facts are present
    missing_count = len([f for f in flags if f["type"] == "missing" and f["element"] in REQUIRED])
    completeness = round(100 * (len(REQUIRED) - missing_count) / len(REQUIRED))
    # readiness score: starts at 100, each high flag costs 15 points, each other flag costs 6
    high_count = len([f for f in flags if f["severity"] == "high"])
    other_count = len([f for f in flags if f["severity"] != "high" and not f.get("advisory")])
    readiness = max(0, 100 - 15 * high_count - 6 * other_count)
    return {"readiness": readiness, "ai_blocked": ai_blocked, "completeness": completeness, "flags": flags, "citations": citations, "sentences": sentences,
            "human_review": len(reasons) > 0, "reasons": reasons,
            "ai_used": ai_used, "ai_error": ai_error,
            "seconds": round(time.time() - start_time, 2)}

def review_many(cases, use_ai=False, progress=None, workers=8):
    # Reviews a list of cases {"id","narrative","facts"} and returns {id: result}.
    # Rule checks take about a millisecond per case, so they run one after another.
    # The AI call takes seconds, so with the AI on the cases are sent AT THE SAME TIME (workers at once) instead of one by one.
    results, total = {}, len(cases)
    if not use_ai or total == 0:
        for i in range(total):
            c = cases[i]
            results[c["id"]] = review(c["narrative"], c.get("facts") or {}, False)
            if progress:
                progress(i + 1, total, c["id"])
        return results
    from concurrent.futures import ThreadPoolExecutor, as_completed
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, min(workers, total))) as pool:
        futures = {pool.submit(review, c["narrative"], c.get("facts") or {}, True): c["id"] for c in cases}
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
            done += 1
            if progress:
                progress(done, total, futures[fut])
    return {c["id"]: results[c["id"]] for c in cases}                 # keep the original order

#*****************************************************************************************************
#   CATEGORIES: lets the website review "only the cases with conflicts", "only the clean ones", and so on.
#*****************************************************************************************************
CATEGORIES = ["Clean (no gaps)", "Missing facts", "Conflicting facts", "Citation problem", "Needs human review"]

def categories_of(result):
    # Which categories does a (rules-only) result fall into? A case can be in several.
    flags = [f for f in result["flags"] if not f.get("advisory")]
    cats = []
    if len(flags) == 0 and not result["human_review"]:
        cats.append("Clean (no gaps)")
    if any(f["type"] == "missing" for f in flags):
        cats.append("Missing facts")
    if any(f["type"] == "inconsistent" for f in flags):
        cats.append("Conflicting facts")
    if any(f["element"] == "charge_citation" for f in flags):
        cats.append("Citation problem")
    if result["human_review"]:
        cats.append("Needs human review")
    return cats

def make_report(result, case_name="case"):
    # Turns the result dictionary into a readable one-page text report.
    lines = ["GAP REPORT: " + case_name, ""]
    if result["human_review"]:
        lines.append("*** HUMAN REVIEW REQUIRED (this tool never picks or suggests a charge) ***")
        for r in result["reasons"]:
            lines.append("  - " + r)
        lines.append("")
    lines.append("1. GAPS")
    gaps = [f for f in result["flags"] if f["element"] != "charge_citation"]
    if len(gaps) == 0:
        lines.append("  None found.")
    for f in gaps:
        where = "Sentence " + str(f["sentence"]) if f["sentence"] else (f["field"] or "whole narrative")
        lines.append("  - [" + f["type"] + "] " + f["element"] + " (" + where + "): " + f["reason"])
    lines.append("")
    lines.append("2. CITATION CHECK")
    for c in result["citations"]:
        lines.append("  - " + c["law"] + ": " + c["status"] + ". " + c["meaning"])
    for f in result["flags"]:
        if f["element"] == "charge_citation":
            where = "Sentence " + str(f["sentence"]) if f["sentence"] else (f["field"] or "whole narrative")
            lines.append("  - FLAG (" + where + "): " + f["reason"])
    lines.append("")
    lines.append("Review time: " + str(result["seconds"]) + "s. AI check used: " + str(result["ai_used"]))
    return "\n".join(lines)


#*****************************************************************************************************
#   PART 7: SCORING  (compares our flags to an answer key; used by the Scorecard tab)
#*****************************************************************************************************
def _nice(pair):
    return pair[0].replace("_", " ") + ": " + pair[1].replace("_", " ")

def score(results, key):
    # results = {case_id: result dictionary}   key = {case_id: {"planted": [[type, element], ...], "human": True/False}}
    # A flag is compared by (type, element). The same flag repeated in one case counts once, because the key lists it once.
    # Advisory notes (extra AI remarks outside the checklist) are not graded either way.
    caught, missed, total_flags, extra = 0, 0, 0, 0
    human_ok, human_total = 0, 0
    rows = []
    for case_id in key:
        if case_id not in results:
            continue
        result = results[case_id]
        found = []
        for f in result["flags"]:
            if f.get("advisory"):
                continue
            pair = (f["type"], f["element"])
            if pair not in found:
                found.append(pair)
        planted = []
        for p in key[case_id]["planted"]:
            pair = (p[0], p[1])
            if pair not in planted:
                planted.append(pair)
        not_caught = [p for p in planted if p not in found]
        extras = [f for f in found if f not in planted]
        caught += len(planted) - len(not_caught)
        missed += len(not_caught)
        extra += len(extras)
        total_flags += len(found)
        human_flag = ""
        if key[case_id].get("human"):
            human_total += 1
            if result["human_review"]:
                human_ok += 1
                human_flag = "sent to human"
            else:
                human_flag = "MISSED human review"
        perfect = len(not_caught) == 0 and len(extras) == 0 and human_flag != "MISSED human review"
        rows.append({"case": case_id, "result": "OK" if perfect else "CHECK", "planted": len(planted), "caught": len(planted) - len(not_caught),
                     "missed": len(not_caught), "extra flags": len(extras), "human review": human_flag,
                     "what was missed": "; ".join(_nice(p) for p in not_caught),
                     "what was extra": "; ".join(_nice(p) for p in extras)})
    recall = caught / (caught + missed) if (caught + missed) > 0 else 1.0
    false_rate = extra / total_flags if total_flags > 0 else 0.0
    human_recall = human_ok / human_total if human_total > 0 else 1.0
    return {"recall": recall, "false_rate": false_rate, "human_recall": human_recall,
            "caught": caught, "missed": missed, "extra": extra, "rows": rows, "cases_scored": len(rows),
            "not_run": [c for c in key if c not in results], "not_in_key": [c for c in results if c not in key]}


#*****************************************************************************************************
#   PART 8: A GOOD-LOOKING ONE-PAGE REPORT (HTML). Open it in a browser and press Ctrl+P to save as PDF.
#*****************************************************************************************************
def make_html_report(result, case_name="case"):
    import html as h
    score = result["readiness"]
    color = "#16a34a" if score >= 80 else ("#e0a100" if score >= 50 else "#d64545")
    out = "<html><head><meta charset='utf-8'><title>Gap report</title><style>"
    out += "body{font-family:Arial,sans-serif;max-width:850px;margin:30px auto;color:#111}"
    out += ".top{background:#0b2a5b;color:white;padding:18px 22px;border-radius:10px}"
    out += ".score{float:right;font-size:34px;font-weight:bold;color:" + color + ";background:white;padding:4px 14px;border-radius:10px}"
    out += ".hr{background:#ffe3e3;border:2px solid #d64545;padding:10px;border-radius:8px;margin:14px 0}"
    out += "table{border-collapse:collapse;width:100%;margin:8px 0}td,th{border:1px solid #ccc;padding:6px;text-align:left;font-size:14px}"
    out += "th{background:#eef2ff}.high{color:#d64545;font-weight:bold}.medium{color:#b07f00;font-weight:bold}"
    out += "</style></head><body>"
    out += "<div class='top'><span class='score'>" + str(score) + "</span><h2 style='margin:0'>Gap report: " + h.escape(case_name) + "</h2>"
    out += "<div>Record readiness score (100 = no gaps found)</div></div>"
    if result["human_review"]:
        out += "<div class='hr'><b>HUMAN REVIEW REQUIRED.</b> This tool never selects or suggests a charge.<ul>"
        for r in result["reasons"]:
            out += "<li>" + h.escape(r) + "</li>"
        out += "</ul></div>"
    out += "<h3>1. Gaps and flags</h3><table><tr><th>Severity</th><th>Type</th><th>Fact</th><th>Where</th><th>Why</th></tr>"
    for f in result["flags"]:
        where = "Sentence " + str(f["sentence"]) if f["sentence"] else (f["field"] or "whole narrative")
        why = h.escape(f["reason"])
        if f.get("ask"):
            why += "<br><i>Ask the officer: " + h.escape(f["ask"]) + "</i>"
        out += "<tr><td class='" + f["severity"] + "'>" + f["severity"].upper() + "</td><td>" + f["type"] + "</td><td>" + f["element"].replace("_", " ") + "</td><td>" + where + "</td><td>" + why + "</td></tr>"
    if len(result["flags"]) == 0:
        out += "<tr><td colspan='5'>No gaps found.</td></tr>"
    out += "</table><h3>2. Citation check</h3><table><tr><th>Law cited</th><th>Status</th><th>Plain meaning</th></tr>"
    for c in result["citations"]:
        out += "<tr><td>" + h.escape(c["law"]) + "</td><td>" + c["status"] + "</td><td>" + h.escape(c["meaning"]) + "</td></tr>"
    out += "</table><p style='color:#555;font-size:12px'>Reviewed in " + str(result["seconds"]) + " s. AI check used: " + str(result["ai_used"])
    out += ". This tool suggests and flags only. The officer decides. All test data is synthetic.</p></body></html>"
    return out
