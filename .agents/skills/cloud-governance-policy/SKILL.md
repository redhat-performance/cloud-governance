---
name: cloud-governance-policy
description: Add or modify Cloud Governance policies while preserving provider routing, dry-run behavior, action tracking, resource exclusions, tests, and public-project conventions. Use for policy implementation and policy maintenance; do not use as the primary guide for unrelated infrastructure, documentation, or deployment-only changes.
license: Apache-2.0
---

# Cloud Governance Policy Development

Read the repository's root agent guidance before using this skill. In this
repository, `AGENTS.md` is the shared source of repository-wide commands and
safety rules; this skill supplies the workflow specific to policy changes.

## Understand the policy path

Before editing, identify the provider, policy category, entry point, runner,
shared helper, and existing tests. Inspect nearby implementations rather than
assuming that all providers use the same structure.

For a new or renamed policy, trace its complete route from the requested
`policy` value through `cloud_governance/main/main.py`, the applicable main
operations or allowlist, provider runners, and the policy implementation. Use
the existing module and class naming conventions. A file in a provider
directory is not necessarily reachable without registration or dispatch changes.

## Preserve policy behavior

- Reuse provider runners and shared helpers when they already provide the
  required cloud and reporting behavior.
- Preserve both `dry_run=yes` and `dry_run=no` behavior for policies that clean
  up or update resources. Treat `dry_run=yes` as the normal development mode,
  but inspect the selected code path: it is not a universal guarantee of no
  writes because some paths update tracking tags, upload results, or use a
  separate action control.
- Preserve resource exclusions such as `Policy=notdelete` and
  `skip=not_delete`.
- Preserve the action counter used by the policy. Standard policies commonly
  use `DAYS_TO_TAKE_ACTION`; zombie-cluster cleanup has separate
  `DAYS_TO_DELETE_RESOURCE` and `ClusterDeleteDays` behavior.
- Preserve force-delete semantics, resource scoping, and the selected runner's
  ordering of thresholds, exclusions, and actions.
- Keep result formats compatible with existing S3, Elasticsearch, and OpenSearch
  consumers when changing upload-related behavior.

Do not assume that a dry-run setting makes a live policy, deployment script, or
notification workflow safe. Use mocks or isolated resources for development,
and execute live actions only when their targets and actions are explicitly in
scope.

## Implement and test

Start with a focused change in the provider's existing policy category. Add or
update unit tests for the behavior that can regress:

- dry-run and live-action branches;
- action-threshold increment and reset behavior;
- resource exclusion tags;
- force-delete and resource-scope handling;
- provider-specific responses and error paths;
- result or upload payloads when the policy produces them.

Unit tests primarily use mocks and Moto, but the test directory does not
guarantee network isolation. Inspect constructors and runtime calls as well as
imports. Establish mocks before importing affected components when needed, and
restore environment variables and shared configuration state after each test.

Run a focused test first, then the applicable unit-test suite. Run integration
tests only when the task includes live integration testing and disposable
resources, target accounts and regions, and external services have been
established. Integration tests may create, mutate, or delete cloud resources
and test data.

## Finish the change

Verify that the policy is reachable through its intended entry point, that
documentation reflects any new configuration or behavior, and that dependency
files remain consistent if dependencies changed. Review the final diff for
unrelated edits, credentials, private endpoints, account identifiers, real
resource data, and accidental live-action changes.

Report the focused tests and checks that ran. If an external service,
credential, or configured hook prevented a check, report that limitation
instead of silently treating the check as passed.
