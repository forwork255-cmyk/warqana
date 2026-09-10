# Roadmap — Warqana

Source of truth for what phase this project is on. Durable rules and
architecture live in `CLAUDE.md`, not here.

## Status: Phase 1, 2 & 3 complete, Phase 4 (motion/DepthFlow) not started

**Pre-Phase-3 review fixes** (`claude_client.py`): every Claude call
(chapter_detection, understanding_pass, name_resolution) was calling the
SDK directly with no error handling and no cost visibility. Centralized
into one helper: explicit retries + a clear error instead of a crash or
opaque StopIteration on failure, and per-call token usage logging. Verified
working after the refactor. Deferred, not fixed: the Firestore concurrency
lock isn't wired into `catchup.py` yet (fine for solo local testing, needed
before multi-user deployment); locations don't get identity-resolution the
way characters do.

Phase 0 (a hand-made sample — one short public-domain story, a handful of
manually generated scenes in the manuscript style — shown to real Arabic
readers) happens outside this codebase, before Phase 1 coding starts, to
confirm the concept lands before investing real development time.

## Phase 1 — Foundations & the two decisions everything else depends on

- [x] Image-generation API selection: **Flux (via Replicate)** chosen after
      test generations — handled both the Baghdad-school manuscript style
      and a modern/contemporary style cleanly from prompt changes alone.
      Google Imagen was not tested (its free tier turned out to require
      billing enabled, same cost as Replicate, so no reason to add a second
      setup step for comparison).
- [ ] Explicit style guide: turn the manuscript-style description into a
      concrete, reusable prompt spec, not left to per-scene improvisation.
- [x] Backend shape: Streamlit UI (matching the Arabic Research Assistant)
      stays the reader-facing app; a separate worker (Google Cloud Run Job,
      L4 GPU, scale-to-zero) handles the understanding pass, image
      generation, and DepthFlow rendering, coordinated via a Firestore job
      queue. Full rationale in `CLAUDE.md`.
- [x] Data model: Firestore schema for books, chapters, story bible
      (characters/locations), and per-book/chapter/style processing state.
      Ownership-based privacy design — full schema in `CLAUDE.md`.
- [x] Book ingestion: PDF/EPUB text extraction (`book_ingestion.py`, via
      pypdf/ebooklib). Scanned PDFs are detected and flagged `needs_ocr`
      rather than processed — real OCR trust-testing stays Phase 9.

## Phase 2 — Understanding pass (cheap, text-only)

- [x] Chapter/section boundary detection by structural signal
      (`chapter_detection.py`). First attempt used regex and failed on real
      Arabic word-based ordinal headings (no digits) — rebuilt as a single
      Claude call per book instead, since "any structural word" can't be
      enumerated by pattern matching. Verified on synthetic English/Arabic
      cases and a real public-domain excerpt (Sindbad the Sailor, Arabic
      Wikisource) — correctly detected two different heading styles ("night"
      markers and a distinct story-title heading) in the same passage.
- [x] Claude-based extraction (`understanding_pass.py`): characters (with
      descriptions), locations, and 3–10 visually-weighted moments per
      chapter. Verified on the real Sindbad section — names preserved
      exactly, missing-description fallback produced a plausible
      non-stereotyped description, and a key narrative detail (the
      "island" is actually a giant fish) was correctly captured in the
      location description, not lost.
- [x] Story bible (`story_bible.py`): persistent per-book record reused
      across chapters. Verified across all 6 real Sindbad sections —
      recurring characters kept their exact original description every
      time, never overwritten. Also surfaced a real case of the name-variant
      problem below: "السندباد" was added as a separate character from the
      already-established "السندباد البحري" (same person) — confirms the
      next item is a real, necessary fix, not hypothetical.
- [x] Name/identity resolution (`name_resolution.py`): semantic matching,
      not string matching, so the same character isn't recorded twice
      under a different name or title. Verified on real text — correctly
      identified that "الرجل العظيم المحترم" (a title used at first
      introduction) and "السندباد البحري" (the name revealed later) are
      the same person, purely from context, not spelling similarity.
- [x] Catch-up mechanism (`catchup.py`): jumping to a later chapter triggers
      the understanding pass over all earlier unprocessed chapters first.
      Verified end-to-end: a simulated reader jumping straight to section 5
      correctly triggered processing of sections 0-5 in order (~111s, real
      API calls); a second reader then requesting an already-covered
      section returned instantly (0.0s, no reprocessing) — the caching
      genuinely works, not just in theory.

## Phase 3 — Drawing pass (expensive, per-chapter)

- [x] Generate one image per identified scene (`drawing_pass.py`), using
      the Flux/Replicate API + style guide, conditioned on the story bible
      for character consistency. Fixed a real gap along the way: scenes
      weren't being persisted anywhere (only characters/locations were),
      which would have forced a duplicate paid understanding-pass call
      just to redraw a chapter -- added `chapter_scenes` caching to the
      story bible. Also added retry/backoff for Replicate rate limits
      (hit real 429s during testing -- recovered automatically every time).
      Verified end-to-end on a real chapter: 7 scenes, all generated
      correctly, with caching confirmed (already-processed chapters and
      already-generated images were correctly skipped on rerun).
- [x] Missing-description fallback: already built and verified as part of
      the understanding pass (Phase 2) -- character extraction generates a
      plausible non-stereotyped appearance when the text doesn't describe
      one, and the story bible saves it as canonical from then on.

## Phase 4 — Motion pipeline (the differentiator)

- [ ] Integrate DepthFlow (depth map → parallax video) as a rendering job
      run by the Phase 1 worker service.
- [ ] Video storage: private per user for non-public-domain books;
      shared/cached for the public-domain tier.
- [ ] Processing lock keyed on (book, chapter, style) so concurrent
      requests for an uncached combination queue behind one paid
      generation; waiting readers get notified.

## Phase 5 — Reader experience & sync

- [ ] Reading view in the existing Streamlit shell: pick book → chapter,
      read, see generated scenes appear in sync with reading position.
- [ ] Style switching mid-book reuses the same cache/catch-up mechanism,
      keyed additionally on style.

## Phase 6 — Accounts, privacy tiers, retention

- [ ] Reuse the Arabic Research Assistant's auth pattern (bcrypt accounts,
      sessions, password reset).
- [ ] Enforce private-by-default generated content for non-public-domain
      books (no cross-account sharing regardless of who uploaded it).
- [ ] Public-domain tier: fully shareable/cacheable (also the free
      showcase content).
- [ ] Understanding-layer (text-only) caching across users — flagged as
      needing real legal review before scaling.
- [ ] 30-day auto-delete of generated content after cancellation.

## Phase 7 — Usage & cost controls

- [ ] Three-layer cap mirroring the Arabic Research Assistant: small daily
      free tier, higher paid-tier cap, global emergency ceiling.
- [ ] Per-generation cost logging (image + DepthFlow render).

## Phase 8 — Payments

- [ ] Contact FastPay, ZainCash, and FIB in parallel.
- [ ] Manual/pay-the-owner fallback as a bridge until a gateway is live.

## Phase 9 — Real-world validation before scaling trust

- [ ] Test Arabic OCR accuracy against an actual scanned book.
- [ ] Sanity-check generic-character-fallback prompts against real output
      for stereotype leakage.
- [ ] Confirm content policy stance in practice (no extra moderation layer
      beyond the image API's own rules, except the absolute minors
      exception).

## Phase 10 — Launch prep

- [ ] Seed the public-domain showcase tier (e.g. *Alf Layla wa Layla* via
      Wikisource/Hindawi).
- [ ] Refund policy and ToS text (no refunds, stated plainly).
- [ ] Revisit legal review on understanding-layer caching before any
      paid-scale claims are made about it.

---

Each phase gets its own separate go-ahead before coding starts — this is
the map, not a green light to build all ten phases in one pass.
