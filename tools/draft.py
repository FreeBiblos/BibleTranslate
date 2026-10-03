"""Draft Bible verses in a language that has no Bible yet, learning from a speaker's examples.

The speaker's word list, grammar notes and sample verses come from the project file the
Bible Translate app exports (Export -> Download project file). Every result is an AI DRAFT:
speakers of the language review it in the app (Review drafts) before anything is approved.

Usage:
  pip install anthropic          # and set ANTHROPIC_API_KEY
  python tools/draft.py PROJECT.json "Mark 1:16-20"
      draft a passage (one chapter at a time) -> drafts/<language>/mark-1-16-20.json
  python tools/draft.py PROJECT.json --test 10
      hold back 10 of the speaker's sample verses, draft them from the rest, and score each
      draft against the speaker's own translation (chrF, 0-100). Shows how well the AI has
      learned the language before you rely on its drafts.
  Add --dry-run to print the prompt without calling the API.
"""
import argparse
import datetime
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data")

MODEL = "claude-opus-5-5"
MAX_EXAMPLES = 60   # sample verses put in each prompt, most relevant first
NOTICE = ("AI DRAFT - NOT REVIEWED. Machine-generated translation for speakers of the language "
          "to check, correct and approve. Do not publish or quote as Scripture.")

SYSTEM = """You are helping a community translate the Bible into their own language, which has no Bible yet and may have very little written material. You probably know little or nothing of this language, so learn it from what the speakers have given you: their word list, their grammar and spelling notes, and verses they translated themselves.

How to translate:
- Translate the meaning of the original-language text (Greek or Hebrew). The KJV is an English anchor for verse boundaries and meaning, not the source to copy.
- Imitate the speakers' examples closely: their vocabulary, spelling, word order, particles and sentence patterns. Use word-list terms exactly as given, every time.
- When a word you need is not in the examples or the word list, use the closest form the examples support, or a loanword from the related language if one is named, and say so in the notes. Never invent words silently.
- Use natural, everyday language. Do not add explanation or commentary inside the verse.

For each verse return:
- translation: the draft in the language, in its usual writing system.
- back_translation: a literal English rendering of your draft, word for word where you can, so a reviewer can check what it actually says.
- confidence: "high", "medium" or "low". Use "low" whenever you had to guess a word or a grammatical form.
- notes: short notes for the reviewers: words you guessed or borrowed, key terms, places the source is ambiguous. Use an empty list only when there is nothing worth checking."""

SCHEMA = {
    "type": "object",
    "properties": {
        "verses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "verse": {"type": "integer"},
                    "translation": {"type": "string"},
                    "back_translation": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "notes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["verse", "translation", "back_translation", "confidence", "notes"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verses"],
    "additionalProperties": False,
}

_cache = {}


def load(name):
    if name not in _cache:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def clean(text):
    return text.replace("¶", "").strip()   # drop the KJV's paragraph marks


def kjv_verse(b, c, v):
    return clean(load("kjv.json")[b][1][c - 1][v - 1])


def ref_name(b, c, v):
    return f"{load('kjv.json')[b][0]} {c}:{v}"


def parse_passage(ref):
    """'Mark 1:16-20' -> (book index, chapter, [verses]) in KJV numbering."""
    kjv = load("kjv.json")
    m = re.match(r"^\s*(.+?)\s+(\d+):(\d+)(?:-(\d+))?\s*$", ref)
    if not m:
        sys.exit(f"Can't read {ref!r}; use the form 'Mark 1:16' or 'Mark 1:16-20' (one chapter at a time).")
    name, ch, v1, v2 = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4) or m.group(3))
    names = [b[0].lower() for b in kjv]
    key = name.lower()
    hits = [i for i, n in enumerate(names) if n == key] or [i for i, n in enumerate(names) if n.startswith(key)]
    if len(hits) != 1:
        sys.exit(f"Unknown or ambiguous book {name!r}.")
    b = hits[0]
    chapters = kjv[b][1]
    if not 1 <= ch <= len(chapters):
        sys.exit(f"{kjv[b][0]} has {len(chapters)} chapters.")
    last = len(chapters[ch - 1])
    if not 1 <= v1 <= v2 <= last:
        sys.exit(f"{kjv[b][0]} {ch} has verses 1-{last}.")
    return b, ch, list(range(v1, v2 + 1))


def original(b, c, v):
    """(label, Greek or Hebrew text) for a KJV verse, or (label, None) if it can't be lined up."""
    if b >= 39:
        chap = load("tr.json")["books"].get(str(b), [])
        text = chap[c - 1][v - 1] if c <= len(chap) and v <= len(chap[c - 1]) else None
        return "Greek (Scrivener 1894 Textus Receptus)", text
    wlc = load("wlc.json")
    chaps, vmap = wlc["books"].get(str(b), []), wlc.get("map", {}).get(str(b))
    label = "Hebrew (Westminster Leningrad Codex)"
    if not vmap:
        return label, chaps[c - 1][v - 1] if c <= len(chaps) and v <= len(chaps[c - 1]) else None
    # map[chapter][verse] lists the KJV (chapter, verse) pairs each Hebrew verse covers
    parts = [chaps[hc][hv] for hc, hverses in enumerate(vmap) for hv, refs in enumerate(hverses)
             if [c, v] in refs and hc < len(chaps) and hv < len(chaps[hc])]
    return label, " ".join(parts) or None


# ---------- Examples ----------

def examples_from(project):
    """Speaker samples plus reviewer-approved draft verses, keyed (b, c, v). The speaker's own text wins."""
    out = {}
    for item in project.get("approved", []):
        out[(item["b"], item["c"], item["v"])] = (item["text"], "approved draft")
    for s in project.get("samples", []):
        out[(s["b"], s["c"], s["v"])] = (s["text"], "speaker")
    return out


def words(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}


def pick_examples(examples, targets, limit=MAX_EXAMPLES):
    """The examples most useful for these target verses: same chapter first, then shared English words."""
    want = set().union(*(words(kjv_verse(*t)) for t in targets))
    tb, tc = targets[0][0], targets[0][1]

    def score(key):
        b, c, v = key
        near = 3 if (b, c) == (tb, tc) else 1 if b == tb else 0
        return (near, len(want & words(kjv_verse(b, c, v))))

    keys = sorted((k for k in examples if k not in targets), key=score, reverse=True)[:limit]
    return sorted(keys)


def build_prompt(project, examples, targets):
    lang = project["language"]
    name = lang.get("name") or "the target language"
    lines = [f"Target language: {name}"]
    for label, key in (("Language code", "code"), ("Writing system", "script"), ("Spoken in", "region"),
                       ("Related or trade language", "related")):
        if lang.get(key):
            lines.append(f"{label}: {lang[key]}")
    if lang.get("notes"):
        lines += ["", "Grammar and spelling notes from the speakers:", lang["notes"]]

    if project.get("wordlist"):
        lines += ["", "Word list (English = word in the language):"]
        for w in sorted(project["wordlist"], key=lambda w: w["en"].lower()):
            lines.append(f"- {w['en']} = {w['word']}" + (f"  ({w['notes']})" if w.get("notes") else ""))

    keys = pick_examples(examples, targets)
    if keys:
        lines += ["", f"Verses already translated into {name} (study these):"]
        for b, c, v in keys:
            text, source = examples[(b, c, v)]
            lines += [f"{ref_name(b, c, v)}", f"  KJV: {kjv_verse(b, c, v)}", f"  {name} ({source}): {text}"]
    else:
        lines += ["", f"No verses have been translated into {name} yet, so mark every draft low confidence."]

    lines += ["", "Verses to draft:"]
    for b, c, v in targets:
        label, orig = original(b, c, v)
        lines.append(f"Verse {v} ({ref_name(b, c, v)})")
        if orig:
            lines.append(f"  {label}: {orig}")
        lines.append(f"  KJV: {kjv_verse(b, c, v)}")
    lines += ["", f"Draft each verse above in {name}."]
    return "\n".join(lines)


# ---------- Claude ----------

def call_claude(prompt):
    import anthropic   # imported here so --dry-run works without the SDK installed

    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "adaptive"},
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",   # if a safety classifier declines, retry on Anthropic's recommended model
        )
    except anthropic.AuthenticationError:
        sys.exit("The API key was rejected. Set ANTHROPIC_API_KEY to a valid key.")
    except anthropic.RateLimitError:
        sys.exit("Rate limited by the API. Wait a minute and try again.")
    except anthropic.APIStatusError as e:
        sys.exit(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        sys.exit("Couldn't reach the API. Check the network connection.")
    if response.stop_reason == "refusal":
        sys.exit("The model declined this request.")
    if response.stop_reason == "max_tokens":
        sys.exit("The draft was cut off; try fewer verses at a time.")
    text = next(b.text for b in response.content if b.type == "text")
    return {d["verse"]: d for d in json.loads(text)["verses"]}, response.model


# ---------- Scoring ----------

def chrf(hyp, ref, n=6, beta=2.0):
    """Character n-gram F-score (chrF), 0-100: how closely a draft matches the speaker's translation."""
    hyp, ref = re.sub(r"\s+", " ", hyp.strip()), re.sub(r"\s+", " ", ref.strip())
    precs, recs = [], []
    for k in range(1, n + 1):
        h = Counter(hyp[i:i + k] for i in range(len(hyp) - k + 1))
        r = Counter(ref[i:i + k] for i in range(len(ref) - k + 1))
        if not h or not r:
            continue
        match = sum((h & r).values())
        precs.append(match / sum(h.values()))
        recs.append(match / sum(r.values()))
    if not precs:
        return 0.0
    p, r = sum(precs) / len(precs), sum(recs) / len(recs)
    return 0.0 if p + r == 0 else 100 * (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


# ---------- Main ----------

def slug(s):
    return re.sub(r"\W+", "-", str(s).lower()).strip("-") or "language"


def draft_record(project, title, targets, drafted, served_by, examples_used):
    return {
        "status": "ai-draft",
        "needs_human_review": True,
        "notice": NOTICE,
        "passage": title,
        "target_language": project["language"].get("name", ""),
        "language_code": project["language"].get("code", ""),
        "model": served_by,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "examples_used": examples_used,
        "verses": [{
            "book": b, "chapter": c, "verse": v, "ref": ref_name(b, c, v),
            "kjv": kjv_verse(b, c, v),
            **{k: drafted[v][k] for k in ("translation", "back_translation", "confidence", "notes")},
            "review": {"status": "pending", "reviewer": None, "approved_text": None, "comments": None},
        } for b, c, v in targets if v in drafted],
    }


def run_passage(project, examples, passage, dry_run):
    b, c, verses = parse_passage(passage)
    targets = [(b, c, v) for v in verses]
    prompt = build_prompt(project, examples, targets)
    if dry_run:
        print("SYSTEM:\n" + SYSTEM + "\n\nUSER:\n" + prompt)
        return None
    drafted, served_by = call_claude(prompt)
    missing = [v for v in verses if v not in drafted]
    if missing:
        print(f"Warning: no draft returned for verse(s) {missing}.", file=sys.stderr)
    title = f"{load('kjv.json')[b][0]} {c}:{verses[0]}" + (f"-{verses[-1]}" if len(verses) > 1 else "")
    return draft_record(project, title, targets, drafted, served_by, len(pick_examples(examples, targets)))


def run_test(project, examples, count, dry_run):
    """Draft held-back speaker verses from the rest; compare with the speaker's own translation."""
    speaker = sorted(k for k, (_, src) in examples.items() if src == "speaker")
    if len(speaker) < 2:
        sys.exit("A test needs at least two speaker sample verses.")
    count = min(count, len(speaker) - 1)
    step = len(speaker) / count
    held = [speaker[int(i * step)] for i in range(count)]   # spread through the samples
    rest = {k: val for k, val in examples.items() if k not in held}

    records, scores = [], []
    for (b, c) in sorted({(b, c) for b, c, _ in held}):   # one request per chapter
        targets = [k for k in held if k[:2] == (b, c)]
        prompt = build_prompt(project, rest, targets)
        if dry_run:
            print("SYSTEM:\n" + SYSTEM + "\n\nUSER:\n" + prompt + "\n")
            continue
        drafted, served_by = call_claude(prompt)
        rec = draft_record(project, "", targets, drafted, served_by, len(pick_examples(rest, targets)))
        for item in rec["verses"]:
            expected = examples[(item["book"], item["chapter"], item["verse"])][0]
            item["expected"] = expected
            item["score"] = round(chrf(item["translation"], expected), 1)
            scores.append(item["score"])
        records.append(rec)
    if dry_run:
        return None
    verses = [v for r in records for v in r["verses"]]
    out = records[0] if records else draft_record(project, "", [], {}, MODEL, 0)
    out["verses"] = verses
    out["passage"] = f"Test: {len(verses)} sample verses"
    out["test"] = {"held_back": len(held), "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
                   "metric": "chrF (0-100) against the speaker's own translation"}
    return out


def main():
    ap = argparse.ArgumentParser(description="Draft Bible verses in a new language from a speaker's examples.")
    ap.add_argument("project", help="project file exported from the Bible Translate app")
    ap.add_argument("passage", nargs="?", help="passage in KJV numbering, one chapter at a time, e.g. 'Mark 1:16-20'")
    ap.add_argument("--test", type=int, metavar="N", help="hold back N speaker verses and score the drafts")
    ap.add_argument("--out", help="output JSON path (default: drafts/<language>/...)")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt and exit without calling the API")
    args = ap.parse_args()
    if bool(args.passage) == bool(args.test):
        ap.error("give either a passage or --test N")

    with open(args.project, encoding="utf-8") as f:
        project = json.load(f)
    if project.get("format") != "bibletranslate-project":
        sys.exit("That is not a project file from the Bible Translate app.")
    examples = examples_from(project)

    result = (run_test(project, examples, args.test, args.dry_run) if args.test
              else run_passage(project, examples, args.passage, args.dry_run))
    if result is None:
        return

    name = slug(project["language"].get("name"))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    default = f"test-{stamp}.json" if args.test else f"{slug(result['passage'])}.json"
    out = args.out or os.path.join(ROOT, "drafts", name, default)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"*** {NOTICE} ***\n\n{result['passage']} - {result['target_language']}\n")
    for d in result["verses"]:
        print(f"{d['ref']}  {d['translation']}")
        print(f"    back-translation: {d['back_translation']}")
        print(f"    confidence: {d['confidence']}" + (f"   match: {d['score']}" if "score" in d else ""))
        if "expected" in d:
            print(f"    speaker's version: {d['expected']}")
        for n in d["notes"]:
            print(f"    - {n}")
        print()
    if "test" in result:
        print(f"Average match with the speakers' own translations: {result['test']['average_score']} / 100 (chrF)")
    print(f"Saved to {os.path.relpath(out)}. Open it in the app under Review drafts.")


if __name__ == "__main__":
    main()
