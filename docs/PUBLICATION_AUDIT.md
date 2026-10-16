# Publication security and privacy review

## Scope and result

The initial audit inspected all 11 commits reachable from local refs and 131 distinct historical file blobs, plus current source and the original portable archive. No Git remote or preexisting release tag was configured. History was preserved; no reset, filter or force operation was needed.

Checks covered known GitHub/OpenAI/AWS credential signatures, private-key headers, user-directory paths, email addresses, tracked file types and commit identities. Credential-related code uses runtime-generated tokens; test tokens and example domains are not live credentials. All historical commit identities use the neutral `FontFinderLocal Checkpoints <checkpoint@localhost>` identity. No developer-specific path or personal email was found in tracked history. Automated pattern inspection cannot prove the absence of every possible secret; only the reviewed branch and release assets should be published.

## Distribution inspection

The original ZIP passed integrity checking and contains no runtime database, saved preferences, uploaded reference images, font binaries, source checkout, virtual environment or Git metadata. Its complete frontend and embedded native matching runtime were validated outside the development directory during Step 4.

An embedded Python archive review inspected 1,414 code filenames, including the EXE/PYZ and standard library archive. No user-directory code filenames or development-user string constants were found. Native dependency DLLs and wheel metadata contain upstream build/debug paths using generic Administrator or runneradmin accounts. These are vendor build artifacts, not this development machine's private paths; binaries were not patched. Third-party copyright/email notices are retained as required.

Local audit JSON and build logs remain ignored under `test-results/`; they are not publication assets. `releases/build-summary.json` contains local absolute output paths and must not be uploaded. Upload only the named versioned ZIP and its checksum sidecar.

## Files excluded from publication

- `.venv/`, `.python/`, Python bytecode and development caches.
- `data/`, SQLite/database files, logs and temporary files.
- `build/`, `dist/`, `releases/` (ZIP is attached separately to a Release).
- `test-results/`, generated benchmark images, `reference-images/` and `local-fonts/`.
- Font binaries (`ttf`, `otf`, `ttc`, `otc`, `woff`, `woff2`).
- `.env` and `.env.*`, editor-local settings and OS metadata.

Curated documentation screenshots are intentional exceptions to excluding development images. They were captured from a separate test data directory with neutral sample text and a synthetic PINBALL image. They contain no paths, account names, personal preferences, private reference artwork or embedded font binaries. Their visible font names and aggregate library counts are non-sensitive demonstration information.

## Runtime and publication boundaries

No application settings or favorites were reset. Screenshot and integration checks use isolated data directories. The only application-source change for publication is version metadata; matching algorithms and the interface are unchanged.

MIT licensing is approved with Copyright (c) 2026 redbone labs. Future author, committer and tagger identity is redbone labs <20893831+redbonelabs@users.noreply.github.com>. The original 11 checkpoint commits are intentionally preserved without rewriting. GitHub CLI was absent during preparation; authentication and account ownership must be verified before publishing. No remote creation, push, upload, profile change or public visibility change has occurred.
