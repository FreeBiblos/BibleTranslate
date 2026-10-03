"""Make a practice project from a language that already has a Bible, so the method can be checked.

A language with no Bible can't be checked: nobody's translation exists to compare against. So we
practise on a closely related language that does have one (data/languages-needing.json lists the
closest for each language), pretend only a speaker's first few verses exist, and score the AI's
drafts of the rest against the real translation.

Usage:
  python tools/practice.py ong-ong                  # an eBible corpus file: <language>-<translation id>
  python tools/practice.py ong-ong --samples 80     # how many verses of Mark the "speaker" gives (default 60)
Then:
  python tools/draft.py practice/ong-ong-project.json --test 10
  python tools/draft.py practice/ong-ong-project.json "Mark 4:1-20" --answers practice/ong-ong-answers.json

The project uses only the New Testament, whose verse numbering matches the KJV's.
Texts come from the eBible corpus (github.com/BibleNLP/ebible), which includes only texts that may be shared.
"""
import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CORPUS = "https://raw.githubusercontent.com/BibleNLP/ebible/main/corpus/{}.txt"
VREF = "https://raw.githubusercontent.com/BibleNLP/ebible/main/metadata/vref.txt"
# USFM book codes in KJV order: index = the KJV book index the app uses.
BOOKS = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM "
         "EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP "
         "COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()
MARK = BOOKS.index("MRK")


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8").splitlines()


def load_corpus(corpus):
    """{(book, chapter, verse): text} for the New Testament of an eBible corpus file."""
    lines, vref = get(CORPUS.format(corpus)), get(VREF)
    if len(lines) != len(vref):
        raise ValueError("The corpus file and the verse list don't line up.")
    nt = {}
    for ref, text in zip(vref, lines):
        book, cv = ref.split(" ")
        b = BOOKS.index(book) if book in BOOKS else -1
        text = text.strip()
        if b < 39 or not text or text == "<range>":   # NT only; skip empty and merged-verse markers
            continue
        c, v = map(int, cv.split(":"))
        nt[(b, c, v)] = text
    return nt


def language_name(code):
    try:
        langs = json.load(open(os.path.join(ROOT, "data", "languages-needing.json"), encoding="utf-8"))["languages"]
        return next((r["name"] for l in langs for r in l["relatives_with_bible"] if r["code"] == code), None)
    except OSError:
        return None


def make_project(corpus, nt, samples, name=None):
    """A practice project whose "speaker" gave the first `samples` verses of Mark. Returns (project, sample keys)."""
    code = corpus.split("-")[0]
    name = name or language_name(code) or code
    keys = sorted(k for k in nt if k[0] == MARK)[:samples]
    project = {
        "format": "bibletranslate-project", "version": 1,
        "practice": {"corpus": corpus, "source": "eBible corpus (github.com/BibleNLP/ebible)"},
        "language": {"name": name, "code": code, "script": "", "dir": "ltr", "region": "",
                     "related": "", "notes": ""},   # nothing that hints the text is published
        "wordlist": [],
        "samples": [{"b": b, "c": c, "v": v, "text": nt[(b, c, v)], "by": "published translation"} for b, c, v in keys],
        "drafts": [], "approved": [],
    }
    return project, keys


def main():
    ap = argparse.ArgumentParser(description="Make a practice project from a language that has a Bible.")
    ap.add_argument("corpus", help="eBible corpus file name without .txt, e.g. ong-ong")
    ap.add_argument("--samples", type=int, default=60, help="verses of Mark given as the speaker's examples")
    ap.add_argument("--name", help="language name (default: from data/languages-needing.json or the code)")
    args = ap.parse_args()

    try:
        nt = load_corpus(args.corpus)
    except ValueError as e:
        sys.exit(str(e))
    if not nt:
        sys.exit("No New Testament text in that file.")
    project, samples = make_project(args.corpus, nt, args.samples, args.name)
    name = project["language"]["name"]
    if len(samples) < args.samples:
        print(f"Only {len(samples)} verses of Mark in this text.", file=sys.stderr)
    answers = {f"{b}:{c}:{v}": t for (b, c, v), t in nt.items() if (b, c, v) not in set(samples)}

    out = os.path.join(ROOT, "practice")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"{args.corpus}-project.json"), "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, f"{args.corpus}-answers.json"), "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False)
    print(f"practice/{args.corpus}-project.json: {name}, {len(samples)} sample verses from Mark")
    print(f"practice/{args.corpus}-answers.json: {len(answers)} held-back NT verses to score drafts against")


if __name__ == "__main__":
    main()
