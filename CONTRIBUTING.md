# Contributing: a network of people and AI

Bible Translate works like Wikipedia: anyone can help, every change is signed and can be undone, and discussion happens in the open. Translation adds one stricter rule. **No verse is confirmed until two different speakers of the language approve the same wording.**

## Roles

| Role | Who | What they do |
| --- | --- | --- |
| **Speaker** | Someone who grew up speaking the language | Translates sample verses, builds the word list, and reviews AI drafts in the app |
| **Drafter** | Anyone with Claude Code or a Claude API key | Runs `/bible-translate:volunteer` (see README → Volunteer your Claude) or `tools/draft.py` for a claimed passage and submits the result |
| **Checker** | Anyone, no need to know the language | Compares each back-translation with the KJV and flags meaning errors in the verse comments |
| **Language steward** | A trusted speaker or partner organization | Watches over one language, settles disagreements over key terms, and decides when chapters go to the Bible app |

## How work flows

1. **Pick a language.** The **Languages in need** tab lists every living language with no Bible translation started (from Joshua Project data). Search it, then open a GitHub issue titled `Language: <name> (<code>)`. That issue is the language's talk page.
2. **Find speakers.** Check the language's recordings link and partner organizations (see README → Partners). The issue records who the speakers are and how to reach them.
3. **Collect examples.** Speakers enter a word list and 50 to 100 sample verses in the app, then commit the project file to `projects/<code>.json` through a pull request.
4. **Test first.** A drafter runs `python3 tools/draft.py projects/<code>.json --test 10` and posts the average score in the issue. If it is low, gather more examples before drafting.
5. **Claim and draft.** Comment on the issue to claim a passage (one chapter at a time). Run `tools/draft.py`, then open a pull request adding the file to `drafts/<code>/`.
6. **Review.** Speakers open the draft in the app, correct it, and approve verses. Each approval carries the reviewer's name. When two different speakers have approved the same wording, the verse shows **confirmed**. They commit the reviewed file through a pull request.
7. **Send to the Bible app.** The language steward exports the confirmed chapters (**Export → Download approved chapters**) and opens a pull request on [BibleApp](https://github.com/Bluesboy13/BibleApp) adding the text.

## Ground rules

- **AI drafts are drafts.** Never publish or quote one as Scripture before it is confirmed.
- **Speakers decide.** When a speaker and the AI disagree, the speaker wins. When two speakers disagree, the steward decides, in the open on the issue.
- **Changing the wording clears approvals**, so both speakers always approved the same text.
- **Two independent speakers.** The speaker who last changed a verse's wording can approve it, but that approval doesn't count toward the two.
- **Say why.** Marking a verse "needs work" requires a comment, and every edit, approval and objection is kept in the verse's history.
- **Look hardest where the checks point.** A low back-translation match, a low meaning grade or an automatic check finding means a verse needs extra care, not that it is wrong. A high meaning grade doesn't make a verse right either: only speakers can say it reads naturally and means what it should.
- **Keep everything traceable.** Drafts record the model and date, approvals record who approved and when, and git history keeps every earlier version.
- **Respect sources.** Use only texts and recordings whose licenses allow it, and add each new source to the README's Sources section in the same pull request.
- **Practise before you trust.** For a new method or prompt change, run `tools/practice.py` on related languages that already have a Bible and compare scores before using it on a real language.
