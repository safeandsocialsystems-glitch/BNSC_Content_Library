# Instructions for Codex — BNSC Content Library

## Product objective

Help BNSC members find relevant CAMPFIRE videos and original research-explanation posts with minimal effort. The application is a searchable index, **not** a replacement content hosting platform. Audience: trainers, rehabilitation professionals, developmental-support workers.

## Nonnegotiable requirements

1. Preserve the premium BNSC/Neurofit visual identity: charcoal/black, gold/ivory, restrained red accent. Japanese-first, mobile-friendly UI.
2. **Do not fabricate real BNSC posts or URLs**. Sample data must stay clearly marked as demo until replaced with verified entries.
3. Do not expose video-host direct links or members-only full bodies. Link only to the appropriate CAMPFIRE post, where membership remains enforced.
4. Avoid scraping gated content or inferring that an unauthenticated visitor has access to the 104 activities.
5. The static JSON is publicly downloadable when deployed. Never store secrets, payment data, memberships, personal information, private notes, research full texts, or login credentials.
6. Support CSV -> JSON import with validation and clear errors; keep it usable without paid dependencies.
7. Keep core search client-side and zero third-party analytics. Support no JavaScript errors, keyboard access, mobile layouts, and reduced motion.
8. New data fields must have backward-compatible defaults. No semantic claims about the actual research papers without verifiable source.

## Workflow

Run `python3 -m unittest discover -s tests -v`, import CSV, open via `python3 -m http.server 8000`, test a Japanese search, category filtering, bookmarks and mobile layout before releases.

## Next milestone after real entries supplied

Populate `contents.csv` from the owner's own archive, verify each title and post URL, regenerate JSON, review sensitive metadata, then deploy to a static host. If genuine member-only metadata control is demanded, switch to server-side storage with individual authentication rather than a shared password.

## Vimeo integration (owner-authorized update)

- The owner's exact `BNSC` Vimeo tag authorizes automatic PUBLIC SEARCH METADATA inclusion without per-video review. CSV entries retain their existing published/draft/demo workflow.
- Use the official API for the authenticated owner's account. Never persist playback URLs, privacy hashes or tokens in public files or logs. Vimeo cards must not have playback links until member authentication is approved and implemented.
- Fetch and validate the complete inventory before replacing public data; any failure keeps the last successful site. Valid empty snapshots must deploy so removal of the last BNSC tag works.
- GitHub Actions runs hourly and deploys only `dist/` after successful sync. `VIMEO_ACCESS_TOKEN` is a GitHub Secret. Publishing is opt-in via `BNSC_PUBLISH_ENABLED=true`; do not enable it without the owner's explicit publishing confirmation.
- Do not claim live Vimeo/Actions/Pages verification until credentials and hosting are configured and the real tests have run. See `VIMEO_SETUP.md`.

## Owner-authorized simplification (2026-10-29; supersedes member-only and playback restrictions above)

- Use GitHub Pages without login, passwords, Cloudflare, membership checks or revocation management. Anyone knowing the URL can search and watch.
- Retain hourly exact BNSC tag synchronization, CSV workflow, design, search, categories and bookmarks.
- Explicit `--include-playback` export includes a validated Vimeo player URL and the unlisted h parameter required for playback. These are intentionally visitor-visible under the owner's new policy. Never export API tokens, raw API responses or member data.
- Default metadata-only exports remain free of playback information for compatibility.
- Publish only dist after a fully successful sync. Failed sync preserves the prior deployment; valid empty snapshots remove all tagged videos.
- Do not enable Pages, change BNSC_PUBLISH_ENABLED from false, push or deploy without the owner's further confirmation. See VIMEO_SETUP.md for the current procedure.
