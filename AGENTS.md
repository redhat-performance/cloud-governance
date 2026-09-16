# Cloud Governance Agent Guide

## Repository purpose

Cloud Governance is a Python 3.10+ tool for cloud cost management, resource
cleanup, tagging, security checks, reporting, and cloud-resource orchestration.
It supports AWS, Azure, IBM, and GCP workflows. Provider coverage varies; AWS
currently contains the broadest policy set.

The commands below primarily target the core `cloud_governance` Python package.
The repository also contains separate applications and infrastructure under
`cloud-governance-mcp/`, `cloudsensei/`, `aws_lambda_functions/`, `terraform/`,
`iam/`, `Docker/`, and `docs/`. For changes in those areas, read the component
README, deployment files, and dependency files before choosing commands.

## Before changing code

- Read the relevant README, contributing guidance, tests, and nearby
  implementation before editing.
- Identify whether the change belongs to a provider policy, shared helper,
  policy runner, cloud-resource orchestration workflow, scheduled automation
  job, or deployment manifest.
- Preserve existing behavior outside the requested scope. Do not change cloud
  credentials, deployment targets, or production schedules unless they are
  explicitly included in the requested scope.
- Do not add credentials, tokens, account IDs or names, private hostnames or
  URLs, organization-only email addresses, credential IDs, internal schedules,
  or real billing and resource data to source or documentation. Use placeholders
  and environment variables in examples.
- Verify commands and examples against current source and CI configuration
  before relying on them.

## Repository layout

- `cloud_governance/main/`: application entry points and orchestration.
- `cloud_governance/policy/`: provider policies, shared policies, helpers,
  policy operations, and policy runners.
- `cloud_governance/common/`: shared cloud integrations and utilities,
  external service adapters, logging, and reporting.
- `cloud_governance/cloud_resource_orchestration/`: cloud-resource
  orchestration workflows and provider-specific operations.
- `tests/unittest/`: unit tests that primarily use mocks and Moto rather than
  live cloud services. This directory is not a guarantee of network isolation:
  inspect constructors and runtime calls as well as imports. Configuration
  loading and client initialization can happen during import, so isolate
  credentials and environment configuration, establish mocks before importing
  affected components when necessary, and restore shared environment state
  after each test.
- `tests/integration/`: integration tests; some require cloud credentials or
  external services, create disposable cloud resources, or delete test data.
  Some are intentionally skipped without test data.
- `jenkins/`: scheduled policy jobs and upload workflows.
- `pod_yaml/`: Podman/OpenShift deployment manifests and related scripts.
- `.github/workflows/`: CI, pull-request, approval, build, and other automation
  workflows.
- `grafana/`, `diagrams/`, and `images/`: dashboards and project assets.

## Policy development rules

- Place a new policy under the correct provider and policy category. Reuse
  shared helpers and the provider policy runner where possible.
- For policies that perform cleanup or updates, preserve or implement both
  `dry_run=yes` and `dry_run=no` behavior according to the selected runner.
  Treat `dry_run=yes` as the default for local and exploratory execution, but
  do not assume it is universally read-only: existing paths may update tracking
  tags, upload results, or use a separate action control.
- Never make destructive cloud calls during tests unless the task explicitly
  includes live integration testing and the target account, region, disposable
  resources, and external services have been established. Credentials alone
  are not sufficient.
- For development validation, use mocks or isolated test resources. Execute live
  policies, deployment scripts, or notification workflows only when those
  actions and their targets are included in the requested scope. A dry-run
  setting alone does not establish safe execution.
- Preserve resource exclusion behavior for tags such as
  `Policy=notdelete` and `skip=not_delete`.
- Preserve the relevant action tracking mechanism and its increment/reset
  behavior. Standard policies use `DAYS_TO_TAKE_ACTION`; zombie-cluster
  cleanup has separate `DAYS_TO_DELETE_RESOURCE` and `ClusterDeleteDays`
  behavior.
- Preserve the selected policy's force-delete semantics and resource scoping;
  runners may apply thresholds and exclusions differently.
- When adding a policy, trace discovery and dispatch from `main.py`, update the
  applicable routing or allowlist, follow the runner's module/class naming
  convention, and verify the policy through its intended entry point.
- Keep result formats compatible with existing S3, Elasticsearch, and
  OpenSearch consumers when changing upload-related behavior.
- When adding or changing a policy, update or add focused unit tests for
  dry-run behavior, action thresholds, skipped resources, and provider-specific
  behavior as applicable.

## Development and validation

Use a Python 3.10 or newer virtual environment when possible. The
`python-ldap` dependency may require system LDAP development packages; consult
the CI setup if installation fails:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r tests_requirements.txt
python -m pip install flake8
```

The CI workflows may install additional system build packages, constrain the
setuptools version, or install provider-specific dependencies before the
project requirements. Check the relevant workflow before troubleshooting a
fresh installation.

Run focused tests first, then the broader applicable suite:

```bash
python -m pytest path/to/test_file.py
python -m pytest tests/unittest
```

Run integration tests only when the task includes live integration testing and
the target accounts, regions, disposable resources, and external services have
been established. These tests may require AWS, Azure, GCP, IBM, Elasticsearch,
OpenSearch, or other external configuration and may create, mutate, or delete
resources and test data. Do not invent credentials or silently convert a unit
test into a live-resource operation.

Run repository checks when the change warrants them:

```bash
# Staged files
pre-commit run
# Explicit files, including unstaged or newly created files
pre-commit run --files <changed-files>
# All tracked files; review any automatic edits
pre-commit run --all-files
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

The pre-commit configuration includes formatting and requirements-file fixers,
and some configured hooks may require network access or authentication. Report
checks that cannot run rather than bypassing their results silently.

When changing core dependencies, keep the corresponding declarations in
`setup.py`, `requirements.txt`, and `tests_requirements.txt` consistent.
Auxiliary applications have separate dependency sets; update them according to
their own requirements files.

For packaging changes, use the existing setup configuration and validate with:

```bash
pip install -e .
python setup.py sdist bdist_wheel
```

## Containers and scheduled jobs

- Use `README.md` and the relevant files under `jenkins/` or `pod_yaml/` for
  container and scheduled-job changes.
- Keep policy configuration, secrets, and deployment manifests separate.
- Prefer `dry_run=yes` when validating a container invocation, while inspecting
  the selected policy because dry-run is not a universal guarantee of no writes.
- Inspect the root `Dockerfile` before container validation and confirm that the
  executed Python modules come from the intended checkout or built artifact.
- Review both the Jenkinsfile and its runner script when changing a scheduled
  workflow.

## Change handoff

Before completing a change:

1. Review the diff for unrelated edits, credentials, and accidental live-action
   changes.
2. Run the narrowest meaningful tests and checks available in the environment.
3. Report tests that could not run because external services or credentials
   were unavailable.
4. Update documentation when commands, configuration, supported providers, or
   policy behavior change.

For project contribution conventions, see `CONTRIBUTING.md`. For user-facing
configuration and execution examples, see `README.md`.
