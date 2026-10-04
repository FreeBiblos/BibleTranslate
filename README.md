# Bible Translate

A tool for translating the Bible into languages that don't have one yet. Speakers of the language teach the AI with a word list and a few verses they translate themselves; the AI drafts more verses from those examples, each with an English back-translation; and speakers review every draft before it is approved. Approved chapters export in the format the free [Bible app](https://github.com/Bluesboy13/BibleApp) reads, so a language joins the app only after it has been tested and confirmed.

Nothing here is published as Scripture. Every AI verse is marked as a draft until a reviewer approves it.

## How it works

0. **Languages in need** (in the app): every living language with no Bible translation started yet, with its country, language family, links to recordings of speakers, and the closest related languages that already have a Bible. **Start** opens a project for it.
1. **Language** (in the app): name, code, writing system, and grammar and spelling notes for the AI.
2. **Word list**: key words in the language, such as God, Lord, Jesus, spirit, sin, forgive and kingdom. The AI uses them exactly.
3. **Sample verses**: a speaker translates verses, shown one at a time beside the KJV. Mark is a good place to start; 50 to 100 verses make a useful first set.
4. **Test**: `tools/draft.py --test` holds back some of the speaker's verses, drafts them from the rest, and scores each draft against the speaker's own translation. Low scores mean the AI needs more examples before its drafts are worth reviewing.
5. **Draft**: `tools/draft.py` drafts a passage from the Greek or Hebrew, with the KJV as an English anchor and the speaker's examples as its guide.
6. **Review** (in the app): open the draft, compare each back-translation with the KJV, correct the wording, then approve it or mark it for more work. Approved verses become examples for the next drafts.
7. **Export**: download the approved chapters for the Bible app.

The app keeps its work in the browser. **Export → Download project file** saves everything to one file, which is both the backup and the input to the drafting tool.

## Practise and check the method
A language with no Bible can't be checked against anything, so we practise on a related language that has one. We pretend a speaker has given only the first verses of Mark, draft the rest, and score the drafts against the real translation:
```
python3 tools/practice.py ong-ong                 # Olo, a relative of Agi (Papua New Guinea)
python3 tools/draft.py practice/ong-ong-project.json --test 10
python3 tools/draft.py practice/ong-ong-project.json "Mark 4:1-20" --answers practice/ong-ong-answers.json
```
Scores are chrF (0 to 100, character overlap with the real translation). Use them to compare methods and prompts, and to decide how many sample verses a speaker needs to give before drafts are worth reviewing. The score never replaces speakers' review.

## Working together
Many people, each with their own AI agent, can work on different languages and chapters at once, Wikipedia-style. See [CONTRIBUTING.md](CONTRIBUTING.md) for roles, claiming work, and the rule that two speakers confirm every verse.

## Volunteer your Claude
Anyone with Claude Code can donate their own Claude usage to this project. No API key is needed: the work runs on your Claude plan. In Claude Code, run:
```
/plugin marketplace add FreeBiblos/BibleTranslate
/plugin install bible-translate@freebiblos
/bible-translate:volunteer 3
```
The number is how many tasks to do (default 1, at most 10). Each task picks a language that has a Bible and is closely related to one that doesn't, drafts about eight verses of Mark from its first 60 verses, and scores the drafts against the published text. One task in five is a control run with no examples, which shows how much of the language Claude already knew. Each draft is written by a fresh subagent that reads only the prompt file. A second fresh subagent back-translates it without seeing the English or Greek, and then the automatic checks run. Results come back as a pull request adding files to `results/practice/`. They hold the drafts, the checks and the scores, but not the published verses, which keep their own licences. Without the GitHub CLI, the command gives web upload steps instead.

Working inside a copy of this repository, `/volunteer` does the same. To see the scores so far, run `python3 tools/volunteer.py report`.

The command uses `tools/volunteer.py`, which writes the prompts and checks the answers but never calls an API. For a real language project, `tools/volunteer.py start --project projects/<code>.json --passage "Mark 2:1-12"` drafts a passage the same way.

## Run the app
```
python3 -m http.server 8000
```
Then open http://localhost:8000. It is plain HTML, CSS and JavaScript, so it can also be hosted on GitHub Pages.

## Draft with Claude
```
pip install anthropic          # and set ANTHROPIC_API_KEY (in Claude Code cloud sessions, BIBLETRANSLATE_API_KEY)
python3 tools/draft.py my-language-project.json --test 10
python3 tools/draft.py my-language-project.json "Mark 1:16-20"
```
Drafts are saved to `drafts/<language>/`. Open them in the app under **Review drafts**. Add `--dry-run` to see the prompt without calling the API. The tool uses Claude Opus 5.5; if a safety check declines a request, the API retries on Anthropic's recommended fallback model.

### How a draft is checked before speakers see it
1. **Examples chosen for coverage.** Up to 40 speaker verses are picked so that together they cover the passage's key words (English, Greek and Hebrew), plus the verses just before the passage so names and pronouns stay consistent. Confirmed verses are trusted most.
2. **Blind back-translation.** A second, separate request translates the draft back into English without seeing the KJV. The app shows what share of the verse's key words came back. A low score means the meaning may have drifted.
3. **Automatic checks** (`tools/checks.py`): repeated words, mixed writing systems, punctuation and quote problems, agreed key terms missing from the draft, and words no speaker has used yet (with likely misspellings).
4. **Every draft records** the model, the prompt version and the date, so results can be compared when the method changes.

None of these replace speakers. They point reviewers at the verses that need the closest look.

## Adding a confirmed language to the Bible app
**Export → Download approved chapters** writes `<code>-draft.json` with books keyed by KJV book index, in the Bible app's `data/texts` format. Only chapters with every verse approved are included, and each book stops at its first chapter that is not fully approved, because the app lines verses up by position.

## Refreshing the language list
```
python3 tools/languages/build_needs.py
```
It downloads the sources below and rewrites `data/languages-needing.json`.

## Sources
Every source this project uses. Add new ones here in the same pull request that starts using them.

| What | Source | License / terms | Used for |
| --- | --- | --- | --- |
| Languages still needing a Bible, Bible status, recording links | [Joshua Project](https://joshuaproject.net) language data, via the [joshua-project-data](https://github.com/lukeslp/joshua-project-data) mirror (fetched Dec 2025). BibleStatus codes from the [Joshua Project API docs](https://api.joshuaproject.net/v1/docs/column_descriptions/people_groups) | Free for non-commercial use with the credit "Data provided by Joshua Project" ([terms](https://joshuaproject.net/help/terms)); mirror code MIT | `data/languages-needing.json` |
| Language families and relatives | [Glottolog](https://glottolog.org) via [glottolog-cldf](https://github.com/glottolog/glottolog-cldf) | CC BY 4.0 | Family, subgroup, closest related languages |
| Which languages have a Bible, and their texts | [eBible.org](https://ebible.org) via the [eBible corpus](https://github.com/BibleNLP/ebible) (metadata/translations.csv, corpus/) | Only texts eBible marks as redistributable; each text keeps its own license | Related languages, practice projects |
| Recordings of speakers | [Global Recordings Network](https://globalrecordings.net) (links per language) | Linked, not copied | Hearing the language, finding speakers |
| Global figures (544 languages waiting, 36.8M people) | [Wycliffe Global Alliance, 2025 statistics](https://www.wycliffe.net/2025-global-scripture-access-statistics/) | Cited | Context |
| KJV, Greek TR, Hebrew WLC | BibleApp's `data/` (see Texts and credits) | Public domain; verse map CC BY 4.0 | Source texts for drafting |
| Background survey | [AI Bible Translation Tools: Landscape Survey](https://claude.ai/code/artifact/a7c98145-d23d-4657-a360-787a9021dc97) | Project document | Choosing approach and partners |

Joshua Project counts 487 living languages with a translation need and nothing started (Wycliffe counts 544 using ProgressBible data). The two lists differ a little; when a language's status is in doubt, check with the partners below.

## Partners and related tools
Groups and tools we plan to build on or work with. Add any new contact or tool here.

| Who | What they offer | How it fits |
| --- | --- | --- |
| [SIL](https://www.sil.org) / [Scripture Forge](https://scriptureforge.org) / [Serval](https://github.com/sillsdev/serval) | Open-source MT drafting used in about 500 translation projects | Fine-tuned drafting once a language has thousands of verses |
| [Paratext](https://paratext.org) | The standard translation editor; registry of vetted translation organizations | Exporting confirmed text (USFM) to professional teams |
| [ETEN Innovation Lab](https://www.etenlab.org) | Funds and pilots AI translation tools (Fluent, Aquilla) | Possible funding and partnership |
| [Global Recordings Network](https://globalrecordings.net) | Recordings in thousands of languages, made with native speakers | Finding speakers; audio of the language |
| [unfoldingWord](https://unfoldingword.org) | Translation notes, key terms and Open Bible Stories (CC BY-SA) | Word-list and key-term guidance for speakers |
| [Clear.Bible MACULA](https://github.com/Clear-Bible) | Greek and Hebrew syntax and glosses (CC BY 4.0) | Richer source context for drafting |
| [Joshua Project](https://joshuaproject.net) | People group and language data | Keeping the language list current |
| [Wycliffe Global Alliance](https://www.wycliffe.net) / [ProgressBible](https://progress.bible) | Authoritative translation status | Confirming which languages truly need a start |

### Open-source projects to build on
Checked 2026-10-03 (license from each repo; "last active" is its latest commit).

| Project | What it does | License | Last active | How it fits |
| --- | --- | --- | --- | --- |
| [Codex Translation Editor](https://github.com/genesis-ai-dev/codex-editor) (Frontier R&D) | VS Code extension for scripture translation with LLM drafting and checks | MIT | Sep 2026 | Closest match to this project; reuse ideas from its project format and review UI |
| [LangQuest](https://github.com/genesis-ai-dev/langquest) (Frontier R&D) | Offline mobile app where native speakers record or type translations and the community validates them | No license file; ask before reusing | Sep 2026 | Collecting speaker data on phones |
| [Fluent](https://github.com/eten-tech-foundation/fluent-web) ([API](https://github.com/eten-tech-foundation/fluent-api)) (ETEN) | AI-assisted suite for drafting, checking and publishing | MIT | Oct 2026 | Partner; a model for a later web backend |
| [BT Servant](https://github.com/unfoldingWord/bt-servant-worker) (unfoldingWord) | Claude-based helper for translators over WhatsApp, Telegram and Signal, with speech-to-text | MIT | Sep 2026 | Already uses Claude; a model for reviewing by chat |
| [Serval](https://github.com/sillsdev/serval), [SILNLP](https://github.com/sillsdev/silnlp), [SIL Machine](https://github.com/sillsdev/machine) (SIL) | Translation and word-alignment engines; USFM tools | MIT | Oct 2026 | Second drafting engine, alignment checks, USFM export |
| [Scripture Forge](https://github.com/sillsdev/web-xforge) (SIL) | Web translation and community checking linked to Paratext | MIT | Oct 2026 | Model for community checking; route into Paratext |
| [Greek Room](https://github.com/BibleNLP/greek-room) (USC ISI) | Automatic checks: script, punctuation, spelling consistency | BSD-3 | Sep 2026 | Run before speakers review |
| [uroman](https://github.com/isi-nlp/uroman) | Converts any writing system to Latin letters | MIT-style | Jul 2024 | Languages written in non-Latin scripts |
| [MACULA Greek](https://github.com/Clear-Bible/macula-greek) (Clear.Bible) | Greek NT with word-by-word analysis and glosses | CC BY 4.0 | Jul 2026 | Richer source context for drafting |
| [Bible Aquifer](https://github.com/BibleAquifer) | Openly licensed study resources and key terms | CC BY / CC BY-SA | Jul 2026 | Key terms and notes for speakers |
| [Omnilingual ASR](https://github.com/facebookresearch/omnilingual-asr) (Meta) | Speech recognition for 1,600+ languages, extendable from a few examples | Apache-2.0 | Dec 2025 | Speakers could dictate verses instead of typing |
| [Render](https://github.com/faithcomesbyhearing/render) (Faith Comes By Hearing) | Oral Bible translation workflow | MIT | Nov 2024 | Oral review ideas; development has gone quiet |
| [awesome-bible-nlp](https://github.com/BibleNLP/awesome-bible-nlp) | Curated list of Bible NLP resources | MIT | Sep 2025 | Finding more |

GPL tools such as [translationCore](https://github.com/unfoldingWord) and [BTT Writer](https://github.com/Bible-Translation-Tools/BTT-Writer-Desktop) are useful references, but their code can't be copied into this MIT-style project without relicensing.

Most of these tools read and write **USFM**, so exporting confirmed text as USFM is the planned next step for sharing with Paratext and other teams.

### Ideas we took from other projects
Our own code, written after reading theirs; no code was copied.

| Idea | From |
| --- | --- |
| Pick examples that cover the passage's words; include the verses just before it | [Codex](https://github.com/genesis-ai-dev/codex-editor) (MIT) |
| Blind back-translation as a separate step | [Codex](https://github.com/genesis-ai-dev/codex-editor), [Fluent](https://github.com/eten-tech-foundation/fluent-web) |
| Mechanical checks and a sound-aware spelling distance | [Greek Room](https://github.com/BibleNLP/greek-room) (BSD-3) |
| The person who edits a verse can't also count as one of its two approvers; reasons required for "needs work"; full history per verse | [LangQuest](https://github.com/genesis-ai-dev/langquest), [Fluent](https://github.com/eten-tech-foundation/fluent-web) |
| Log the model and prompt version with every draft | [Fluent](https://github.com/eten-tech-foundation/fluent-web), [LangQuest](https://github.com/genesis-ai-dev/langquest) |
| Planned: per-verse Translation Notes, key words and a simplified text from unfoldingWord in the prompt (CC BY-SA) | [BT Servant](https://github.com/unfoldingWord/bt-servant-worker) |

Research worth following: retrieval with more context helps most in extremely low-resource translation ([arXiv 2601.09982](https://arxiv.org/abs/2601.09982)), and closely related languages can guide translation ([arXiv 2603.16660](https://arxiv.org/abs/2603.16660)).

## Texts and credits
- **KJV**: 1769 text, public domain (`data/kjv.json`, from BibleApp).
- **Greek New Testament**: Scrivener's 1894 Textus Receptus, public domain (`data/tr.json`, from BibleApp).
- **Hebrew Old Testament**: Westminster Leningrad Codex, public domain (`data/wlc.json`, from BibleApp). Hebrew ↔ KJV verse numbering from STEPBible's TVTMS table ([STEPBible.org](https://www.stepbible.org), CC BY 4.0).
