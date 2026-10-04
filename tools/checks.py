"""Automatic checks on a draft, run before speakers review it.

The mechanical checks follow the ideas of Greek Room's checks (github.com/BibleNLP/greek-room, BSD-3);
this is our own small implementation. The key-term and unknown-word checks use the speakers' word list
and sample verses. Every finding is a hint for reviewers, never an automatic correction.

Usage:
  python tools/checks.py PROJECT.json DRAFT.json    # adds "checks" to each verse and prints them
"""
import json
import re
import sys
import unicodedata
from collections import Counter

WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|[̀-ͯ'’-])*", re.UNICODE)
OK_REPEATS = {"truly", "verily", "holy", "amen", "very", "father", "lord", "master", "teacher", "rabbi",
              "jerusalem", "simon", "martha", "saul", "eloi", "crucify", "come"}
PAIRS = {"(": ")", "[": "]", "{": "}", "“": "”", "‘": "’", "«": "»"}


def words(text):
    return WORD.findall(text or "")


def script(ch):
    name = unicodedata.name(ch, "")
    return name.split(" ")[0] if name else ""


def mechanical(text, ok_repeats=frozenset()):
    """Repeated words, mixed writing systems, punctuation and spacing problems, unpaired quotes.
    ok_repeats: words the speakers themselves repeat (many languages double words on purpose)."""
    found = []
    toks = words(text)
    for a, b in zip(toks, toks[1:]):
        if (a.lower() == b.lower() and re.search(re.escape(a) + r"[\s,]+" + re.escape(b), text)
                and a.lower() not in OK_REPEATS and a.lower() not in ok_repeats):
            found.append(f'Repeated word "{a} {b}"')
    scripts = Counter(script(ch) for ch in text if ch.isalpha())
    if len(scripts) > 1:
        main = scripts.most_common(1)[0][0]
        odd = sorted({w for w in toks if any(ch.isalpha() and script(ch) != main for ch in w)})
        if odd:
            found.append(f"Letters from another writing system ({', '.join(s for s in scripts if s != main)}): {', '.join(odd[:5])}")
    if re.search(r"[,;:!?]{2,}|[,;:]\.|\.[,;:]", text.replace("...", "")):
        found.append("Doubled or clashing punctuation")
    if re.search(r"\s[,.;:!?]", text):
        found.append("Space before punctuation")
    if re.search(r"[,;:!?](?=[^\W\d_])", text) or re.search(r"\.(?=[^\W\d_]{2})", text):
        found.append("No space after punctuation")
    if re.search(r"[+*<=>|_`#@]", text):
        found.append("Unexpected symbol")
    if "  " in text or text != text.strip():
        found.append("Extra spaces")
    for o, c in PAIRS.items():
        if text.count(o) != text.count(c) and o != c:
            found.append(f"Unpaired {o}{c} (may continue from or into a neighbouring verse)")
    if text.count('"') % 2:
        found.append('Unpaired " (may continue from or into a neighbouring verse)')
    return found


def stem(w):
    return re.sub(r"(eth|est|ed|es|s)$", "", w.lower()) or w.lower()


def key_terms(kjv, draft, wordlist):
    """Word-list terms whose English word is in the KJV verse but whose agreed word is missing from the draft."""
    found = []
    kjv_stems = {stem(w) for w in re.findall(r"[A-Za-z]+", kjv)}
    have = [w.lower() for w in words(draft)]
    for entry in wordlist:
        en = entry.get("en", "").strip()
        target = entry.get("word", "").strip()
        if not en or not target:
            continue
        if all(stem(p) in kjv_stems for p in re.findall(r"[A-Za-z]+", en)):
            first = words(target)[0].lower() if words(target) else target.lower()
            root = first[:max(3, len(first) - 2)]   # allow endings added to the word
            if not any(w.startswith(root) for w in have):
                found.append(f'Key term "{en}" is usually "{target}" but it is not in this draft')
    return found


def distance(a, b):
    """Edit distance where similar-sounding swaps and vowel changes cost less (after Greek Room's smart edit distance)."""
    cheap = [set("aeiou"), set("bp"), set("dt"), set("gk"), set("fv"), set("sz"), set("lr"), set("mn")]
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            sub = 0 if ca == cb else 0.5 if any(ca in g and cb in g for g in cheap) else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + sub))
        prev = cur
    return prev[-1]


def unknown_words(draft, known):
    """Words the speakers have never used. A near-match to a known word may be a misspelling; the rest may be
    new forms or guesses, so reviewers should look at them closely."""
    found, new = [], []
    for w in dict.fromkeys(x.lower() for x in words(draft)):
        if w in known or len(w) < 3:
            continue
        close = min(known, key=lambda k: distance(w, k), default=None) if known else None
        if close and distance(w, close) <= (1 if len(w) >= 7 else 0.5):
            found.append(f'"{w}" is new; did you mean "{close}"?')
        else:
            new.append(w)
    if new:
        found.append(f"Words no speaker has used yet: {', '.join(new)}")
    return found


def speaker_repeats(project):
    """Words the speakers write twice in a row, so the repeated-word check doesn't flag them."""
    out = set()
    for s in project.get("samples", []) + project.get("approved", []):
        toks = [w.lower() for w in words(s["text"])]
        out |= {a for a, b in zip(toks, toks[1:]) if a == b}
    return out


def known_words(project):
    known = Counter()
    for s in project.get("samples", []):
        known.update(w.lower() for w in words(s["text"]))
    for a in project.get("approved", []):
        known.update(w.lower() for w in words(a["text"]))
    for e in project.get("wordlist", []):
        known.update(w.lower() for w in words(e.get("word", "")))
    return set(known)


def check_draft(project, draft):
    """Add a "checks" list to every verse of a draft record. Returns the number of findings."""
    known = known_words(project)
    repeats = speaker_repeats(project)
    total = 0
    for v in draft["verses"]:
        text = v["translation"]
        found = mechanical(text, repeats) + key_terms(v.get("kjv", ""), text, project.get("wordlist", []))
        if known:
            found += unknown_words(text, known)
        v["checks"] = found
        total += len(found)
    return total


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    project = json.load(open(sys.argv[1], encoding="utf-8"))
    draft = json.load(open(sys.argv[2], encoding="utf-8"))
    n = check_draft(project, draft)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)
    for v in draft["verses"]:
        for c in v["checks"]:
            print(f"{v.get('ref', v['verse'])}: {c}")
    print(f"{n} findings")


if __name__ == "__main__":
    main()
