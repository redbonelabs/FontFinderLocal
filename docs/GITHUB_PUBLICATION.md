# First GitHub publication

Publication is intentionally not performed during local preparation. Create a **private** repository first. Making it public requires separate approval.

## One-time setup

GitHub CLI was not found on PATH or at its standard Program Files location during preparation. Install it from https://cli.github.com/ or, in PowerShell:

```powershell
winget install --id GitHub.cli --exact
```

Open a new terminal, then run:

```powershell
gh auth login --hostname github.com --git-protocol https --web
gh auth status --hostname github.com
```

Complete the browser sign-in yourself. Do not paste passwords or tokens into chat or files. The CLI stores authentication separately from this repository.

## Explicit authorization

After reviewing README, LICENSE, screenshots, release notes and the readiness report, tell the assistant:

> I approve creating a PRIVATE repository named FontFinderLocal under redbonelabs, pushing the prepared source and v1.0.0 tag, and publishing the v1.0.0 release with the versioned portable ZIP and its checksum. Keep the repository private.

This authorization is separate from MIT approval. An organization owner must be specified explicitly. No visibility change is included.

## Commands to run only after authorization

Run from the project root. Verify `git status --short` is empty and `git rev-parse HEAD` equals `git rev-parse v1.0.0^{commit}`. The confirmed display/commit identity is redbone labs (GitHub username redbonelabs) with email 20893831+redbonelabs@users.noreply.github.com; the original 11 commits are preserved. Verify `gh auth status` identifies the intended account before proceeding. No profile or account changes are part of these commands.

```powershell
gh repo create redbonelabs/FontFinderLocal --private --source=. --remote=origin --description "Offline Windows font browser and image font finder"
gh repo view redbonelabs/FontFinderLocal --json nameWithOwner,visibility
```

Confirm the returned repository is PRIVATE before continuing:

```powershell
git push -u origin HEAD
git push origin v1.0.0
gh release create v1.0.0 releases/FontFinderLocal-1.0.0-Windows-x64-portable.zip releases/FontFinderLocal-1.0.0-Windows-x64-portable.zip.sha256 --repo redbonelabs/FontFinderLocal --verify-tag --title "FontFinderLocal v1.0.0" --notes-file docs/RELEASE_NOTES_v1.0.0.md
gh release view v1.0.0 --repo redbonelabs/FontFinderLocal
```

Retain the existing branch name and history; do not use force-push or upload the working folder wholesale. Push only the prepared branch and tag, not `--mirror`. Generated archives belong on the Release, not in Git. Only the versioned ZIP and checksum are release attachments; local audit logs and build-summary files are not.

A Release in a private repository remains restricted to users with repository access. Review the resulting source and assets before requesting a separate public-visibility change.

## Automation

GitHub Actions is deferred for the first release. The local build is already tested, while an automated full-catalog test requires host-specific fonts. The documented build and test commands avoid additional permissions, CI configuration or automatic publication. CI can be added after the first private review.

CLI references: https://cli.github.com/manual/gh_repo_create and https://cli.github.com/manual/gh_release_create.
