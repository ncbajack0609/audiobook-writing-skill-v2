# Audiobook Writing V2

**Turn ideas and manuscripts into Traditional Chinese scripts designed to be heard.**

[繁體中文](README.zh-TW.md)

An agent skill for audiobook planning, print-to-audio adaptation, single- and dual-voice scripts, and production handoff. It defaults to **Traditional Chinese, Taiwan usage, and general adult listeners**, with writing intended for a Taiwan-accent TTS workflow or a human production team.

**This skill writes text. It does not generate audio.**

## Who it is for

- Writers developing a new audiobook from a topic or outline.
- Editors adapting existing manuscripts without losing their meaning or structure.
- Creators planning episodic books, Podbooks, or two-speaker narration.
- Production teams needing consistent scripts, pronunciation notes, voice specifications, and listening-QA checklists.

The focus is listening-first writing: one main idea per auditory unit, natural spoken language, clear speaker attribution, and sources kept outside the narration.

## What you can make

Task modes can be combined; they are distinct from the checker’s genre options.

| Task mode | Bring | Get |
| --- | --- | --- |
| New-book writing | A topic; audience and length when relevant | A core question, table of contents, and chapter outlines before large-scale drafting |
| Print-book adaptation | A manuscript, audience, and listening context | Full-book versus split-edition advice, source mapping, adaptation risks, and narration scripts |
| Full book / split edition / Podbook | Source structure and episode length or use case | Format rationale, episode questions, source coverage, and essential content to preserve |
| Single- / dual-voice script | Content and role count; role functions or permission to design them | Readable narration, consistent speaker labels, emotion and pause cues, and pronunciation risks |
| Voice-production specifications | A finalized script and voice or role direction | Voice personalities, role sheets, pacing and pause guidance, segmentation, and post-production handoff fields |
| Listening-QA preparation | A script; actual audio requires separate authorization and available tools | Text preflight, a seven-part listening checklist, risk locations, and suggested fixes |
| Audio-IP extensions | Core content, audience, and channels or goals | Content mappings and written plans for audiobooks, audiovisual courses, short-form quote videos, and Podbooks |

A **Podbook** organizes a book into episodes built around one question, theme, or story, with a recurring program rhythm and a self-contained ending. Split editions are organized by meaning and listener needs, not equal page or word counts.

The references also provide six genre templates: quotation/keyword explanations, psychological stories and counseling dialogue, workplace fables, AI/social-issue Q&A, two-speaker dialogue, and modern retellings of classic works.

## Load it in an agent or Codex environment

This repository is a skill bundle, not a standalone audiobook application. Start with [SKILL.md](SKILL.md), the authoritative entry point.

1. Make the **complete directory** available to your agent using that environment’s supported skill-loading mechanism. Preserve the relative layout of `SKILL.md`, `references/`, `scripts/`, and `agents/`.
2. Ask the agent to load `SKILL.md` and the task-relevant references before writing. If your environment does not discover skills automatically, explicitly ask it to read those files from the supplied directory.
3. Provide your topic or source manuscript, intended listeners, desired format, and constraints. For adaptations, confirm that you have the necessary rights.

For Codex environments that support this skill format, [agents/openai.yaml](agents/openai.yaml) supplies display metadata and a default prompt invoking **`$audiobook-writing-v2`**. Once the skill is available to that environment, you can use that identifier in your request. The repository does not include an installer; loading and discovery depend on the host environment.

### Example requests

**Plan a new book**

> Use $audiobook-writing-v2 to plan a Traditional Chinese audiobook about everyday decision-making for adult listeners. Propose a core question, table of contents, and chapter outlines. Wait for my approval before drafting chapters.

**Adapt a manuscript**

> Read SKILL.md and the adaptation references. Compare a full-book edition with a Podbook version of the manuscript I provide. Recommend a format, map episodes to the source, and identify content that must not be lost.

**Prepare a two-speaker handoff**

> Turn the supplied chapter into an A/B script in Traditional Chinese with Taiwan usage. Define each role’s function and voice personality, add pronunciation notes, and provide production specifications and a listening-QA checklist. Do not generate audio.

New-book work normally pauses for outline approval before substantial drafting, unless you explicitly request completion in one pass. Review tasks default to diagnosis and actionable recommendations; request a full rewrite when you want one.

## Run the text preflight

From the skill directory, use Python 3 and replace the manuscript placeholder with your own file:

```sh
python3 scripts/style_check.py path/to/manuscript.md --mode auto
python3 scripts/style_check.py path/to/manuscript.md --mode auto --format json
```

- Inputs: `.txt`, `.md`, `.markdown`, and `.docx`.
- Genre options: `auto`, `aphorism`, `counseling`, `workplace`, `social-ai`, `dialogue`, and `classic`.
- Reports: text or JSON; `--output path/to/report.json` saves the report when combined with `--format json`.
- Checks include long sentences, narration URLs, unfinished markers, source-link risks, role-label consistency, and pronunciation risks. Automatic mode reports a primary genre alongside detected voice-format features.
- Exit codes: `0` for a rule-based pass, `1` for revision needed, and `2` for input/read errors.

The checker uses heuristics, not factual verification or audio analysis. Its automated scoring is separate from the editorial review rubric; a passing score does not certify accuracy, rights clearance, natural delivery, or finished audio quality.

## Where TTS fits

**Planning → narration script → voice specifications → separately authorized TTS or recording → actual listening QA.**

This skill covers the writing, specifications, and text-checking stages. It can describe voice direction, pronunciation, pauses, segmentation, and post-production requirements, but it does not run TTS, generate or edit audio, mix sound, produce video, upload, or publish.

Use a separate tool or production workflow for those steps, with explicit authorization and appropriate content, voice, music, and sound-effect permissions. Unknown engine parameters remain recommendations or items to test—not invented settings. Without actual audio and suitable tools, the deliverable is **pre-listening text review**, never a claim that listening QA has been completed.

## Included materials

| File | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Task routing, workflow, and authorization boundaries |
| [Writing principles](references/author-fingerprint.md) | Generalized narrative voice, spoken rhythm, and Taiwan usage |
| [Genre templates](references/genre-templates.md) | Six writing structures and format selection |
| [Adaptation methodology](references/audiobook-adaptation-methodology.md) | Source mapping, listening-first rewriting, and dual-voice design |
| [Review rubric](references/review-rubric.md) | Editorial priorities and delivery criteria |
| [Production and listening QA](references/production-and-listening-qa.md) | Voice specifications, seven listening standards, and extension planning |
| [Text checker](scripts/style_check.py) | Local rule-based manuscript preflight |
| [Agent metadata](agents/openai.yaml) | Display information and skill invocation prompt |

The public writing references contain generalized methods rather than original source manuscripts. Facts, quotations, attribution, and adaptation rights still need independent verification for each project.

## License

Licensed under the [MIT License](LICENSE).
