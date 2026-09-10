# Roadmap — Warqana

Source of truth for what phase this project is on. Durable rules and
architecture live in `CLAUDE.md`, not here.

## Status: Phase 1, 2 & 3 complete, Phase 4 (motion/DepthFlow) in progress

**Architecture change mid-Phase-4**: Google Cloud Platform billing does not
support Iraq (confirmed directly, not a UI bug) — blocks Cloud Run
entirely. Switched the worker's GPU compute to **Replicate** instead (same
provider as the image generation), deployed via Cog + a GitHub Actions
remote build (no local Docker/GPU available on this machine). Full detail
in `CLAUDE.md`'s Backend shape section. Firestore itself is still usable
(free tier doesn't need billing), so only the compute piece moved.

**Phase 4 progress so far** (if resuming after a context loss, start here):
- GitHub repo created and pushed: https://github.com/forwork255-cmyk/warqana
  (public). All Phase 1-3 code is there.
- Replicate model page created: r8.im/forwork255-cmyk/warqana-depthflow
  (private, Nvidia T4 GPU selected).
- `REPLICATE_API_TOKEN` GitHub secret added (a dedicated token, separate
  from the local dev one, named `github-actions-warqana` on Replicate).
- `cog/cog.yaml` + `cog/predict.py` written: wraps DepthFlow's real
  confirmed API (`DepthScene(backend="headless")` →
  `scene.input(image=...)` → `scene.main(output=..., time=...)`, sourced
  directly from BrokenSource/DepthFlow's own `examples/presets.py`, not
  guessed) with a `HorizontalPan` motion preset matching the brief's
  "simulated camera pan" requirement.
- `.github/workflows/push-depthflow.yml` written: builds and pushes the
  Cog model to Replicate on every push to `cog/`.
- Pushed to `main` — this triggered the first build
  (run: github.com/forwork255-cmyk/warqana/actions/runs/34428920114).
  **As of this note, build result (success/failure) had not yet been
  confirmed** — check that Actions page for current status before assuming
  it worked. If it failed, the job logs there will show why; the DepthFlow
  Docker/EGL setup in `cog.yaml` was assembled from moderngl's own headless
  rendering docs (DepthFlow's own docs site returned 403 and couldn't be
  fetched directly), so it may need iteration.
- **First build succeeded**, but the actual test render **crashed**:
  `cog.server.exceptions.FatalWorkerException: ... exitcode -11`. The real
  clue in the log: `OpenGL Renderer: llvmpipe` — DepthFlow was using Mesa's
  *software* renderer, never touching the GPU at all, and almost certainly
  crashed from memory pressure as a result.
- **Two fix attempts failed, same error both times**:
  1. Tried `environment: [NVIDIA_DRIVER_CAPABILITIES=all]` in `cog.yaml` —
     **build itself failed validation**: `"Additional property environment
     is not allowed"`. Cog has no top-level `environment` key (confirmed
     via cog.run/yaml/ docs) — reverted.
  2. Tried setting `os.environ["NVIDIA_DRIVER_CAPABILITIES"]` etc. at the
     top of `predict.py` instead (process-level, before any GL import) —
     build succeeded, but the render **still showed `llvmpipe`, still
     crashed**. This suggests GPU capability mounting happens at container-
     creation time, before Python runs — too late to fix from inside the
     predictor.
- **Third attempt, just pushed, not yet confirmed**: found DepthFlow's own
  author's real working deployment
  (huggingface.co/spaces/BrokenSource/DepthFlow, files: `packages.txt` +
  `README.md`) and copied their actual system packages exactly —
  critically, **Vulkan libraries** (`libvulkan1`, `libvulkan-dev`), which
  our config never had at all. Also `libglvnd-dev` and `libegl1-mesa-dev`
  (dev/headers variants, not just the runtime libs we had). If this also
  fails with the same `llvmpipe` symptom, the next thing to check is
  whether Replicate's container runtime supports GPU *graphics* capability
  at all (as opposed to just CUDA/compute) — that would mean this approach
  needs to change more fundamentally (e.g. a custom base image, or asking
  Replicate support directly), not just another package/env tweak.
- **Not yet done**: confirming this build succeeded AND the render actually
  works (not just builds), then wiring `drawing_pass.py`-equivalent code
  to call the deployed model for real, from a real chapter's scenes.

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
      stays the reader-facing app; a separate worker handles the
      understanding pass, image generation, and DepthFlow rendering,
      coordinated via a Firestore job queue. **Originally planned as a
      Google Cloud Run Job — changed to Replicate (Cog-based custom
      model) after discovering Google Cloud billing doesn't support Iraq.**
      Full rationale and current state in `CLAUDE.md`.
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

- [~] Integrate DepthFlow (depth map → parallax video) as a rendering job
      run by the Phase 1 worker service. In progress — see the detailed
      progress note under Status above before resuming this.
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
