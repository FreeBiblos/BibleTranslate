# Bible Translate

A tool for translating the Bible into languages that don't have one yet. Speakers of the language teach the AI with a word list and a few verses they translate themselves; the AI drafts more verses from those examples, each with an English back-translation; and speakers review every draft before it is approved. Approved chapters export in the format the free [Bible app](https://github.com/Bluesboy13/BibleApp) reads, so a language joins the app only after it has been tested and confirmed.

Nothing here is published as Scripture. Every AI verse is marked as a draft until a reviewer approves it.

## How it works

1. **Language** (in the app): name, code, writing system, and grammar and spelling notes for the AI.
2. **Word list**: key words in the language, such as God, Lord, Jesus, spirit, sin, forgive and kingdom. The AI uses them exactly.
3. **Sample verses**: a speaker translates verses, shown one at a time beside the KJV. Mark is a good place to start; 50 to 100 verses make a useful first set.
4. **Test**: `tools/draft.py --test` holds back some of the speaker's verses, drafts them from the rest, and scores each draft against the speaker's own translation. Low scores mean the AI needs more examples before its drafts are worth reviewing.
5. **Draft**: `tools/draft.py` drafts a passage from the Greek or Hebrew, with the KJV as an English anchor and the speaker's examples as its guide.
6. **Review** (in the app): open the draft, compare each back-translation with the KJV, correct the wording, then approve it or mark it for more work. Approved verses become examples for the next drafts.
7. **Export**: download the approved chapters for the Bible app.

The app keeps its work in the browser. **Export → Download project file** saves everything to one file, which is both the backup and the input to the drafting tool.

## Run the app
```
python3 -m http.server 8000
```
Then open http://localhost:8000. It is plain HTML, CSS and JavaScript, so it can also be hosted on GitHub Pages.

## Draft with Claude
```
pip install anthropic          # and set ANTHROPIC_API_KEY
python3 tools/draft.py my-language-project.json --test 10
python3 tools/draft.py my-language-project.json "Mark 1:16-20"
```
Drafts are saved to `drafts/<language>/`. Open them in the app under **Review drafts**. Add `--dry-run` to see the prompt without calling the API. The tool uses Claude Opus 5.5; if a safety check declines a request, the API retries on Anthropic's recommended fallback model.

## Adding a confirmed language to the Bible app
**Export → Download approved chapters** writes `<code>-draft.json` with books keyed by KJV book index, in the Bible app's `data/texts` format. Only chapters with every verse approved are included, and each book stops at its first chapter that is not fully approved, because the app lines verses up by position.

## Texts and credits
- **KJV**: 1769 text, public domain (`data/kjv.json`, from BibleApp).
- **Greek New Testament**: Scrivener's 1894 Textus Receptus, public domain (`data/tr.json`, from BibleApp).
- **Hebrew Old Testament**: Westminster Leningrad Codex, public domain (`data/wlc.json`, from BibleApp). Hebrew ↔ KJV verse numbering from STEPBible's TVTMS table ([STEPBible.org](https://www.stepbible.org), CC BY 4.0).
