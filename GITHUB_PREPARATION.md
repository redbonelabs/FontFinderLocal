# GitHub publication readiness

## Release prepared locally

Public project identity: **redbone75**. MIT notice: `Copyright (c) 2026 redbone75`.
Future author, committer and annotated-tag identity: `redbone75 <20893831+redbone75@users.noreply.github.com>`.
Intended repository: **redbone75/FontFinderLocal**, PRIVATE initially.

The original 11 commits through `6b7c346` are preserved without rewriting. Their neutral checkpoint author/committer metadata contains no personal email. The final release commit adds the reviewed source metadata, documentation, license, screenshots, ignore rules and packaging preparation; matching algorithms, frontend functionality and user settings/favorites are unchanged.

## Version 1.0.0 artifact

- ZIP: `releases/FontFinderLocal-1.0.0-Windows-x64-portable.zip`
- ZIP bytes: 80,802,210
- SHA-256: `0efd0a27607c912954f2fb5ab809f9b81ed70383ef8c0ff8828dc5c0f862755a`
- Checksum: the adjacent `.zip.sha256` file.
- Executable: `dist/FontFinderLocal/FontFinderLocal.exe`; retain the whole folder.
- Original Step 4 unversioned ZIP is preserved and is not the publication attachment.

The package includes the exact confirmed MIT license, dependency notices, complete frontend and embedded runtime. BUILD_INFO records the build's parent checkpoint and uncommitted state truthfully; all 36 recorded source-file hashes were verified against the final reviewed files. The release commit records those same source contents, so committing them does not require another binary rebuild.

## Final validation

- 43 Python regression tests passed in 16.85 seconds; 1 Node preview-row test passed. One existing Starlette/httpx deprecation warning remains.
- All ten external portable integration checks passed against the newly built ZIP: independent launch, port fallback, instance reuse, complete frontend, installed and custom fonts, native matching, comparisons/alignment/cancellation, dependency isolation, persistence/restart and clean shutdown.
- 642 installed faces plus 3 custom fixtures; sample matching completed in 5.529 seconds.
- Health endpoint and manifest report 1.0.0; packaged LICENSE.txt exactly matches LICENSE.
- ZIP integrity and checksum passed; no font binaries, runtime database, personal settings, reference images or development-user paths found.
- 1,414 embedded Python code filenames inspected without private-path findings.
- Prior 11-commit/131-blob history privacy audit preserved; no secret finding required history remediation.
- Screenshots use neutral demonstration content, contain no private paths or EXIF, and were captured with isolated test settings.

Detailed local reports are ignored under `test-results/`. They and local absolute-path build summaries must not be uploaded. Only the versioned ZIP and checksum are release attachments.

## Local release reference and publication

The intended annotated tag is `v1.0.0`, attached to the final release-preparation commit. Verify with `git rev-parse HEAD` and `git rev-parse v1.0.0^{commit}`; the IDs must match. `git status --short` must be empty. The tag and commit use the confirmed noreply identity. No remote, push or upload is part of preparation.

GitHub CLI was absent during preparation. Install and authenticate it, verify the account is redbone75, and obtain explicit authorization before creating PRIVATE redbone75/FontFinderLocal, pushing the reviewed branch/tag or uploading the release. Follow `docs/GITHUB_PUBLICATION.md`. Making it public requires separate approval. No GitHub profile/account was modified.

Remaining limitations: unsigned Windows x64 executable; Windows 11 validated, Windows 10 and a second clean machine unverified. Existing font/rendering and matching limitations remain documented. GitHub Actions is deferred for the first release.
