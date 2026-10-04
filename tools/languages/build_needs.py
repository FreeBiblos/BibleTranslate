"""Build data/languages-needing.json: living languages that still need a Bible translation,
with what we know about each (country, language family, recordings, nearest relatives that
already have a Bible on eBible.org).

Sources (see README "Sources"):
  - Joshua Project language data (Bible status, Global Recordings Network links), via the
    MIT-licensed mirror github.com/lukeslp/joshua-project-data. Data provided by Joshua Project
    (https://joshuaproject.net); non-commercial use with attribution.
  - Glottolog (CC BY 4.0) for language families and classification, github.com/glottolog/glottolog-cldf.
  - eBible.org's list of translations, via github.com/BibleNLP/ebible (metadata/translations.csv).

Usage:
  python tools/languages/build_needs.py [CACHE_DIR]
Downloads the three sources into CACHE_DIR (default: a temporary folder) unless already there.
"""
import csv
import datetime
import json
import os
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "data", "languages-needing.json")

SOURCES = {
    "joshua_project_languages.json":
        "https://raw.githubusercontent.com/lukeslp/joshua-project-data/main/joshua_project_languages.json",
    "glottolog_languages.csv":
        "https://raw.githubusercontent.com/glottolog/glottolog-cldf/master/cldf/languages.csv",
    "glottolog_values.csv":
        "https://raw.githubusercontent.com/glottolog/glottolog-cldf/master/cldf/values.csv",
    "ebible_translations.csv":
        "https://raw.githubusercontent.com/BibleNLP/ebible/main/metadata/translations.csv",
}
# Joshua Project BibleStatus codes (api.joshuaproject.net column descriptions).
STATUS = {0: "unspecified", 1: "translation needed", 2: "translation started", 3: "portions",
          4: "New Testament", 5: "complete Bible"}
KEEP = (1, 2)   # 1 = nothing started yet (the main list); 2 = started, nothing published


def fetch(cache):
    os.makedirs(cache, exist_ok=True)
    for name, url in SOURCES.items():
        path = os.path.join(cache, name)
        if not os.path.exists(path):
            print(f"Downloading {url}", file=sys.stderr)
            urllib.request.urlretrieve(url, path)
    return {name: os.path.join(cache, name) for name in SOURCES}


def main():
    cache = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "bibletranslate-sources")
    paths = fetch(cache)

    jp = json.load(open(paths["joshua_project_languages.json"], encoding="utf-8"))

    # Glottolog: ISO code -> language row, glottocode -> name, glottocode -> ancestor chain (top first).
    glotto, names, by_iso = {}, {}, {}
    for r in csv.DictReader(open(paths["glottolog_languages.csv"], encoding="utf-8")):
        names[r["ID"]] = r["Name"]
        glotto[r["ID"]] = r
        if r["ISO639P3code"] and r["Level"] == "language":
            by_iso[r["ISO639P3code"]] = r
    chain = {}
    for r in csv.DictReader(open(paths["glottolog_values.csv"], encoding="utf-8")):
        if r["Parameter_ID"] == "classification" and r["Value"]:
            chain[r["Language_ID"]] = r["Value"].split("/")

    # eBible: languages with a freely shareable text, and how much of the Bible each has.
    ebible = {}
    for r in csv.DictReader(open(paths["ebible_translations.csv"], encoding="utf-8-sig")):
        if r["Redistributable"] != "True" or r["downloadable"] != "True":
            continue
        verses = int(r["OTverses"] or 0) + int(r["NTverses"] or 0)
        best = ebible.get(r["languageCode"])
        if not best or verses > best["verses"]:
            ebible[r["languageCode"]] = {"id": r["translationId"], "name": r["languageNameInEnglish"],
                                         "verses": verses, "nt": int(r["NTbooks"] or 0) >= 27,
                                         "ot": int(r["OTbooks"] or 0) >= 39}

    # For relatives: each eBible language's Glottolog ancestors.
    ebible_chains = {iso: chain.get(by_iso[iso]["ID"], []) for iso in ebible if iso in by_iso}

    def relatives(iso, limit=3):
        """eBible languages sharing the deepest Glottolog subgroup with this language."""
        g = by_iso.get(iso)
        mine = chain.get(g["ID"], []) if g else []
        if not mine:
            return []
        scored = []
        for other, theirs in ebible_chains.items():
            depth = 0
            for a, b in zip(mine, theirs):
                if a != b:
                    break
                depth += 1
            if depth:
                scored.append((depth, ebible[other]["verses"], other, mine[depth - 1]))
        scored.sort(reverse=True)
        return [{"code": o, "name": ebible[o]["name"], "ebible": ebible[o]["id"],
                 "bible": "complete" if ebible[o]["ot"] and ebible[o]["nt"] else "NT" if ebible[o]["nt"] else "portions",
                 "shared_group": names.get(grp, grp), "depth": d} for d, _, o, grp in scored[:limit]]

    out = []
    for r in jp:
        if r.get("BibleStatus") not in KEEP or r.get("Status") != "L":   # L = living language
            continue
        iso = r["ROL3"]
        g = by_iso.get(iso)
        anc = chain.get(g["ID"], []) if g else []
        out.append({
            "code": iso,
            "name": r["Language"],
            "country": r["HubCountry"],
            "status": STATUS[r["BibleStatus"]],
            "family": names.get(anc[0]) if anc else ("isolate" if g and g["Is_Isolate"] == "true" else None),
            "group": names.get(anc[-1]) if anc else None,
            "macroarea": g["Macroarea"] if g else None,
            "lat": float(g["Latitude"]) if g and g["Latitude"] else None,
            "lon": float(g["Longitude"]) if g and g["Longitude"] else None,
            "recordings": r.get("GRN_URL"),
            "jesus_film": r.get("JF_URL"),
            "faith_comes_by_hearing": r.get("FCBH_URL"),
            "ebible_text": ebible.get(iso, {}).get("id"),
            "relatives_with_bible": relatives(iso),
        })
    out.sort(key=lambda x: (x["status"] != "translation needed", x["name"]))

    data = {
        "built": datetime.date.today().isoformat(),
        "attribution": "Language and Bible status data provided by Joshua Project (https://joshuaproject.net). "
                       "Classification from Glottolog (CC BY 4.0). Bible texts listed from eBible.org.",
        "counts": {s: sum(1 for x in out if x["status"] == s) for s in (STATUS[k] for k in KEEP)},
        "languages": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {len(out)} languages to {os.path.relpath(OUT)}: {data['counts']}")


if __name__ == "__main__":
    main()
