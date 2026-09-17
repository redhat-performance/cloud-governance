---
name: git-push
description: Prepare and push reviewed Cloud Governance changes through the repository's upstream branch workflow. Use when creating a branch, staging files, committing changes, preparing a pull-request description, or pushing a branch; do not use for implementation, test design, or pull-request review.
license: Apache-2.0
---

# Git Push Workflow

Read `AGENTS.md` and `CONTRIBUTING.md` before changing repository history. This
skill covers the local git workflow through preparing a pull request and
pushing a branch. It does not require GitHub CLI and does not open or merge a
pull request unless the user separately requests that work.

## Choose or create the branch

Create the branch at the beginning of a new development task, before making
edits, from a clean working tree:

```bash
git checkout -b <branch-name> upstream/main
```

Before using this command, verify the `upstream` remote and inspect
`git status`. If development has already started on another branch, preserve
the current work and use that branch instead of recreating it from
`upstream/main`. Never push implementation work directly to `main`.

At push time, confirm the intended branch with:

```bash
git branch --show-current
git status --short
git remote -v
```

If `upstream/main` may be stale, fetch only when appropriate for the task and
review the resulting branch relationship before rebasing or merging. Do not
rewrite history or rebase automatically.

## Review scope and sensitive information

Separate the files for this pull request from unrelated user work. Inspect the
working tree and stage only the files that implement or validate the requested
change:

```bash
git status --short
git add <relevant-files>
git diff --cached
git diff --cached --check
```

If an unrelated file was staged, remove it from the index without deleting the
file:

```bash
git restore --staged <unrelated-file>
```

Review all text that will be published before committing:

```bash
git diff --cached
```

Check the staged diff, commit message, and planned pull-request description
for credentials, tokens, private endpoints, account or subscription IDs,
customer data, internal URLs, internal project names, private issue links, and
other organization-specific details. Replace such details with public-safe
language or remove them. Do not publish local configuration, generated output,
debug logs, or unrelated files. Run `git diff --check` and the repository's
relevant tests and validation before committing.

## Commit

Use a concise commit message that describes the resulting public change:

```bash
git commit -m "<Commit Message>"
```

Check that the commit message contains no sensitive or internal information.
If hooks fail, report the failure and fix it without bypassing hooks.

## Prepare the pull-request description

Prepare a short description that explains the change without reproducing the
whole implementation. It should normally contain:

```markdown
## Summary
- <What changed and why>

## Validation
- <Focused tests or checks that passed>
```

Add one brief risk or compatibility note only when it helps reviewers. Check
the description for sensitive or internal information before publishing it.
The description can be pasted into the GitHub web interface or used with any
available GitHub client; do not require `gh` to be installed.

## Push

Confirm the commit and working tree, then push the branch to the configured
upstream remote:

```bash
git log -1 --oneline
git status --short
git push upstream <branch-name>
```

Treat `git push` as an external repository mutation. Run it only when the user
has requested the push or has clearly authorized it in the current task. Do
not force-push, delete remote branches, push tags, amend commits, or bypass
hooks unless explicitly requested.

After a successful push, report the branch, commit, remote, validation, and
the prepared pull-request description. If the push is rejected, preserve the
local commit and explain the remote response before proposing a recovery
action.
