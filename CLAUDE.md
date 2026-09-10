# Warqana — Arabic Novel Visual Companion

Working project name: **Warqana**. Chosen after "Literate Visualizer"
(placeholder) and four other candidates (Warraq, Rawi, Khayal, Katib) were
checked and found to collide with existing apps/brands. Warqana is an
invented word built on the Arabic root *waraq* (paper/manuscript), and
turned up no app, domain, trademark, or brand collision in web searches —
still pending your own direct registrar/trademark-office confirmation
before relying on it commercially.

## My situation

I'm programming apps, and built and shipped one real product (an
Arabic-first academic research assistant) by directing AI-assisted
development end-to-end, with no prior coding background. I understand the
fundamentals well enough to direct, test, debug, and improve AI-generated
software. This is my second real project, not a demo or a toy — build it to
the standard of something real people would pay for.

## Project goal

Build an Arabic-first visual companion for novels. A reader picks a book and
a chapter; the app quietly reads that chapter, identifies the moments that
actually matter visually, generates an image for each one in a deliberate
Arabic/Islamic manuscript-inspired art style (not generic AI fantasy art),
animates each image with depth-based parallax motion, and shows them to the
reader in sync with where they are in the story.

This is a storytelling companion, not a search tool, and not a video
generator. The reader experience should feel like the book is quietly
illustrating itself as they go.

See `ROADMAP.md` for the phase-by-phase build plan and current progress —
that file is the source of truth for "what phase are we on"; this file only
holds durable project rules/architecture.

## Why this, not the obvious alternative

A very close competitor (Visibl) already does this well for English
audiobooks — free, technically sophisticated, live. That door is closed;
don't rebuild it. Nobody found is doing this for Arabic novels, and a real
existing Arabic reading platform (Abjjad, 1.5M+ users, 200+ publisher deals)
proves a large paying Arabic reading audience already exists — it just has
no visual layer at all. That's the actual gap this project fills.

## Critical rules

- Never fabricate facts about competitors, legal standing, or technical
  capability — verify before asserting, and flag clearly when something is
  an estimate rather than a confirmed fact.
- Keep the system as inexpensive and practical so the customer pays —
  avoid unnecessary complexity.
- Do not build features just because they sound impressive, and if there
  is one, tell me and wait for my permission.
- Assume a limited budget.
- Tell me plainly when I'm overengineering something.

## Development style

- Explain important decisions in beginner-friendly language.
- Before major changes, tell me what you plan to change and why.
- Make one meaningful feature at a time; test before declaring it finished.
- When something fails, find the root cause instead of repeatedly patching
  symptoms.
- Before large implementations, inspect the existing project and explain
  the intended change first.

## Architecture — settled decisions

**Backend shape.** A Streamlit app (reader-facing, deployed the same way as
the Arabic Research Assistant) handles login, book/chapter browsing, and
displaying results — it never runs generation work itself. A separate
worker does the actual understanding pass, image generation, and DepthFlow
rendering, coordinated through a Firestore job queue: Streamlit writes a job
record (book + chapter + style, status: pending), the worker picks it up and
writes results/status back, Streamlit polls for status. The job record
itself doubles as the processing lock from the Concurrency section below.
**Superseded, kept for history**: the worker was originally planned as a
Google Cloud Run Job with an NVIDIA L4 GPU. **Changed because Google Cloud
Platform billing does not currently support Iraq** — confirmed directly
(the country isn't offered when setting up Cloud Billing), not a UI glitch.
This blocks Cloud Run and any Firestore usage beyond its free tier, but NOT
Google AI Studio (a separate signup path) or Firestore's free "Spark" tier
(no billing account needed) — both still usable.

**Current plan: DepthFlow runs as a custom model on Replicate** (the same
provider already used for Flux image generation) instead of Google Cloud
Run. Packaged via Cog (Replicate's model-packaging tool) and deployed
through a GitHub Actions workflow (`replicate/setup-cog`) that builds and
pushes the model remotely — avoids needing local Docker/GPU, which this
dev machine doesn't have. Same scale-to-zero cost behavior as the original
Cloud Run plan: $0 while idle, billed per-second only while actually
rendering (confirmed: Replicate deployments scale to zero by default,
unless `min_instances` is explicitly set above 0, which this project
doesn't do). Cheapest GPU tier (Nvidia T4, ~$0.81/hr, ~$0.000225/sec) was
selected on the model's Replicate page. Rough estimated cost per
newly-generated chapter (image generation + GPU render + text calls,
one-time, then cached): ~$0.25-$0.50 — still an estimate pending a real
timed test, not a confirmed number.

Code lives in `warqana` GitHub repo (public):
https://github.com/forwork255-cmyk/warqana — `cog/cog.yaml` +
`cog/predict.py` define the model; `.github/workflows/push-depthflow.yml`
builds/pushes it on every push to `cog/`. Replicate model page:
r8.im/forwork255-cmyk/warqana-depthflow (private, Nvidia T4).

No VPS, no always-on server, no message broker (Kafka/RabbitMQ) — overkill
for expected traffic and budget at this stage.

**Firestore schema.**
- `users/{user_id}` — auth (bcrypt hash), subscription tier, daily
  free-tier usage counter + reset date, cancellation date (drives the
  30-day auto-delete retention rule).
- `books/{book_id}` — title, full text, source type (PDF/EPUB),
  `is_public_domain` (bool), `owner_id`. Public-domain books use one
  shared `book_id` that every reader points to (this is what makes the
  free/showcase tier's caching work automatically). A reader's own
  uploaded book is always owned by that one user, even if another user
  uploads the same copyrighted title separately — this ownership tagging
  is what keeps generated content private per the Legal/privacy model,
  without needing a separate permissions layer.
- `books/{book_id}/chapters/{n}` — chapter text, detected boundaries.
- `story_bibles/{book_id}` — characters (with descriptions), locations,
  name-normalization map. Scoped per `book_id`, not deduplicated across
  different users' uploads of the same copyrighted text — cross-user
  understanding-layer sharing is a "may, not must" per the Legal/privacy
  model, pending real legal review, so this stays simple for now rather
  than optimizing for it.
- `processing_jobs/{job_id}` — keyed by (book_id, chapter, style), status,
  type (understanding/drawing). This *is* the processing lock from the
  Concurrency/cost controls section — no separate lock mechanism needed.
- `generated_scenes/{book_id}/{chapter}_{style}` — image/video URLs per
  scene.

**Lazy, on-demand processing.** The full book text is stored immediately on
upload, but nothing gets read or processed by AI until a reader actually
requests a specific chapter. Never pre-process a whole book speculatively.

**Two-tier processing per chapter:**
- Cheap "understanding" pass — Claude reads the chapter and extracts
  characters (with descriptions), locations, and the 3-10 moments that
  actually carry real visual weight. Text only, no images. Cheap enough to
  run ahead of the reader when needed.
- Expensive "drawing" pass — only for the exact chapter requested: generate
  an image per identified scene, then animate it (see Motion, below).

**Catch-up mechanism for skipped chapters.** If a reader jumps straight to
chapter 10 without 1-9 ever being processed, the system runs the cheap
understanding pass on 1-9 first (in the background, text only) to build an
accurate running character/location record, before generating chapter 10's
images. This prevents a character being drawn inconsistently just because
earlier chapters were skipped. First reader to reach a given chapter absorbs
a small delay; the result is cached for everyone after.

**Character consistency.** A running "story bible" per book carries forward
between chapters — once a character's appearance is established (either
from the text or generated as a fallback, see below), every later scene
featuring that character reuses the same description.

**Missing character description fallback.** If the text never describes a
character's appearance, generate a plausible one from available context
(setting, era, culture) and save it into the story bible as if it were real,
so the character stays visually consistent afterward. Use deliberate,
careful prompt design here to avoid defaulting into visual stereotypes.

**Foreign/code-switched names.** Keep exactly as written in the text, never
translated or altered. The understanding pass must also normalize
inconsistent Arabic transliterations of the same foreign name (e.g. جون vs
چون for "John") so they resolve to one character, not two.

**Chapter/section detection.** Detect by structural signal (title, number,
formatting break) rather than the literal word "chapter" — this correctly
handles books using a different structural word (e.g. "Seasons"). Scene
count per chapter is not fixed — a short chapter yields fewer visual beats,
a long one yields more. An unusually long chapter may need internal
splitting purely to fit one AI request; this is invisible to the reader.

## Motion — the actual differentiator

Use depth-based parallax animation (near elements move more than far
elements during a simulated camera pan), not flat pan-and-zoom and not
full AI-generated video. Reference implementation: DepthFlow
(github.com/BrokenSource/DepthFlow) — free, open source, self-hosted, no
per-render API cost. Note: DepthFlow renders an actual video file per scene
(real but small storage/bandwidth cost when served) — it does not compute
motion live for free; a custom live-in-browser reimplementation of the same
depth-based technique is a possible future optimization, not assumed by
default.

## Visual identity — the real moat

The motion technique itself is copyable by anyone within weeks. The
defensible edge is a deliberate, consistent Arabic/Islamic visual style,
not generic AI fantasy art. Reference: the Baghdad School of manuscript
painting, specifically the 13th-century illustrated *Maqamat al-Hariri*
manuscripts (Yahya al-Wasiti) — flat, non-perspectival composition,
ornamental borders, gold backgrounds, bold outlines, real historical
Iraqi/Abbasid motifs (geometric star patterns, arabesque scrollwork,
muqarnas, mashrabiya lattice). Aim at authentic manuscript tradition, not
the Westernized "Hollywood genie" aesthetic most people have actually seen.
Define this as an explicit style guide before generating production content,
not left to chance per prompt.

In case a user wants a different style, ask them and generate in the style
they request instead, if that's possible.

## Legal / privacy model

- Generated images and video stay strictly private per user for any
  non-public-domain book — never shared or cached across different users'
  accounts, regardless of how many people uploaded the same title. This is
  the deliberate, conservative choice given unresolved 2026 "AI output
  liability" case law — not a technical limitation.
- The cheap text-only "understanding" layer (character descriptions,
  locations, key beats) MAY be shared/cached across users even for
  copyrighted books — a reasoned position, not a lawyer-confirmed one; get
  real legal review before relying on this at real scale.
- Public-domain texts (e.g. *Alf Layla wa Layla*) are fully shareable and
  cacheable without restriction — this is the natural free/showcase content
  tier.
- Revenue/cost modeling should assume the conservative-to-moderate scenario,
  not the optimistic one — full caching benefits only apply to the
  public-domain tier, not to the majority of realistic content.
- Book source: user uploads their own PDF/EPUB (OCR needed for scanned
  files — Arabic OCR accuracy needs real testing before being trusted, it
  is less mature than English OCR). For public-domain works, point users to
  real legitimate sources (Arabic Wikisource, the Hindawi Foundation's
  Arabic digital library). Never source or locate a "free" copy of a book
  that isn't legitimately free — that's facilitating piracy and is out of
  scope, full stop.
- If a translation is uploaded, disclose to the user that a translation may
  not carry the same effect as the original — this manages expectations,
  it does not by itself resolve the separate legal question of processing
  someone else's copyrighted translation. Covered by the private-only rule
  above regardless.
- Retention: generated content auto-deletes 30 days after a user
  cancels/stops paying.

## Content policy

No restrictions beyond whatever the image-generation API itself already
enforces — do not add an extra layer of moderation on top of the provider's
own rules. Adult themes, violence, moral darkness, adult romantic/sexual
content between clearly adult characters: in scope, age-gated. One absolute
exception, non-negotiable regardless of framing or hosting choice: nothing
sexualizing minors. When the image API refuses a specific generation for its
own reasons, that's final — no attempt to route around a provider's content
rules.

## Concurrency / cost controls

- A processing lock keyed to book + chapter + style: if two readers request
  the same not-yet-cached combination simultaneously, the second request
  waits for the first to finish rather than triggering a duplicate paid
  generation call. Both get notified they're waiting on an in-progress job.
- Three-layer usage caps, mirroring the Arabic Research Assistant's
  approach: a small daily free-tier allowance, a higher cap for paying
  users, and a global emergency ceiling underneath both protecting total
  API spend regardless of per-user caps.

## Style switching mid-book

If a reader switches art style partway through, don't force a full redraw
and don't leave it inconsistent by default — extend the same cache/catch-up
mechanism used for skipped chapters to also key on style. First reader to
request "this book, these earlier chapters, in this style" triggers a
one-time catch-up cost for just the already-read chapters (not the
unprocessed rest of the book); every reader after that gets it instantly
from cache.

## Payment

Do not rely on a single Iraqi payment gateway. Reach out to multiple in
parallel — FastPay, ZainCash, and FIB (First Iraqi Bank, Central
Bank-licensed, supports local and international cards) — matching standard
practice for Iraqi e-commerce launches, which typically ship with 2-3
gateways plus cash-on-delivery rather than betting on one provider
responding.

## Platform

Web app, not native mobile, for now — matches the existing Arabic Research
Assistant, and avoids the heavier mobile-data cost of serving DepthFlow's
rendered video output.

## Language scope

Arabic-first, not Arabic-only. Other languages are fine if a user uploads
them; no artificial restriction, but no special support commitment beyond
Arabic either.

## Refund policy

None, matching standard subscription-industry norms. State this plainly in
terms of service.

## Still open, deliberately not decided yet

- No concrete mitigation designed yet against the generic-character-fallback
  leaning on visual stereotypes — flagged, not solved.
- OCR accuracy for scanned Arabic PDFs needs real testing against an actual
  scanned book before being trusted in production.
