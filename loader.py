# loader.py  --  BACKEND helper: turns uploaded files into a clean list of cases (and tells people what is wrong, kindly).
# No website code in here, so it can be tested on its own.

import csv, io, json
import checker

FACT_COLUMNS = list(checker.REQUIRED.keys()) + list(getattr(checker, "ADVISORY", {}).keys()) + ["selected_charge"]


def _unique(case_id, used):
    # Two cases with the same id would overwrite each other, so we number the repeats.
    base, n = case_id, 2
    while case_id in used:
        case_id = base + "_" + str(n)
        n += 1
    used.add(case_id)
    return case_id


def parse_uploads(files):
    """files = list of (file_name, bytes).  Returns (cases, problems).
    cases = [{"id", "narrative", "facts"}]   problems = [plain-English message, ...]"""
    cases, problems, used = [], [], set()
    for name, raw_bytes in files:
        raw = raw_bytes.decode("utf-8-sig", errors="ignore")
        lower = name.lower()
        if lower.endswith(".json"):
            try:
                data = json.loads(raw)
            except Exception as e:
                problems.append(name + ": this is not a valid JSON file (" + str(e)[:80] + ").")
                continue
            if isinstance(data, dict) and isinstance(data.get("cases"), list):
                data = data["cases"]
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                problems.append(name + ": expected a list of cases like [{\"id\": \"C1\", \"narrative\": \"...\"}].")
                continue
            for i, d in enumerate(data):
                if not isinstance(d, dict) or not str(d.get("narrative", "")).strip():
                    problems.append(name + ": item " + str(i + 1) + " has no \"narrative\" text, so it was skipped.")
                    continue
                facts = d.get("facts") or d.get("case_facts") or {}
                if not isinstance(facts, dict):
                    facts = {}
                cid = _unique(str(d.get("id") or (name.rsplit(".", 1)[0] + "_" + str(i + 1))), used)
                cases.append({"id": cid, "narrative": str(d["narrative"]), "facts": {k: str(v) for k, v in facts.items()}})
        elif lower.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(raw))
            headers = {(h or "").strip().lower(): h for h in (reader.fieldnames or [])}
            if "narrative" not in headers:
                problems.append(name + ": the first row must have a column called \"narrative\" (and optionally \"id\").")
                continue
            for i, row in enumerate(reader):
                text = (row.get(headers["narrative"]) or "").strip()
                if text == "":
                    problems.append(name + ": row " + str(i + 2) + " has an empty narrative, so it was skipped.")
                    continue
                facts = {}
                for col in FACT_COLUMNS:                      # optional extra columns named like the case facts
                    if col in headers and (row.get(headers[col]) or "").strip():
                        facts[col] = row[headers[col]].strip()
                given = (row.get(headers["id"]) or "").strip() if "id" in headers else ""
                cid = _unique(given or ("row" + str(i + 1)), used)
                cases.append({"id": cid, "narrative": text, "facts": facts})
        elif lower.endswith(".txt"):
            if raw.strip() == "":
                problems.append(name + ": the file is empty, so it was skipped.")
                continue
            cases.append({"id": _unique(name.rsplit(".", 1)[0], used), "narrative": raw, "facts": {}})
        else:
            problems.append(name + ": unsupported file type (use .json, .csv or .txt).")
    return cases, problems


def template_csv():
    # A tiny file people can fill in.
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "narrative"])
    w.writerow(["CASE-001", "On March 14, 2025, Border Patrol agents encountered 'John Doe' near the Yuma Station area. Subject is a citizen of Mexico. ..."])
    return buf.getvalue()
