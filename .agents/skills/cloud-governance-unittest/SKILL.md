---
name: cloud-governance-unittest
description: Run and troubleshoot Cloud Governance unit tests with focused pytest selection, mocks, Moto, configuration isolation, and appropriate reporting. Use for tests under tests/unittest; do not use for live integration tests or infrastructure provisioning.
license: Apache-2.0
---

# Cloud Governance Unit Testing

Read the repository's root agent guidance before testing. This skill covers
unit tests under `tests/unittest` and deliberately does not provision cloud
infrastructure, call live cloud services, or run `tests/integration`.

## Select the smallest useful test

1. Inspect the changed source and nearby tests.
2. Run the closest test file or test function first.
3. After focused tests pass, run the applicable provider or package directory.
4. Run the complete unit-test suite when the change crosses shared helpers,
   runners, configuration, or common behavior.

Typical commands are:

```bash
python -m pytest tests/unittest/path/to/test_file.py
python -m pytest tests/unittest/path/to/test_file.py::test_name
python -m pytest tests/unittest
```

Use the repository's virtual environment and install the project and test
dependencies before testing. The test dependencies are listed in
`tests_requirements.txt`; native LDAP build packages may be required by the
Python dependencies.

## Keep tests isolated

- Prefer mocks, Moto, fixtures, and deterministic test data over network calls.
- Inspect imports, constructors, and runtime calls: a unit-test module can
  initialize clients or load configuration before a mock is active.
- Set required environment variables and configuration before importing code
  that reads them at module load time.
- Restore environment variables, shared configuration dictionaries, temporary
  files, and mock state after each test.
- Do not add real credentials, account identifiers, private endpoints, or live
  resource IDs to tests or fixtures.

## Cover policy behavior

For policy changes, tests should cover the behavior that can affect cloud
actions or reported results:

- dry-run and action branches;
- action-threshold increment and reset behavior;
- exclusion tags;
- force-delete and resource-scope behavior;
- provider-specific responses and failures;
- result or upload payloads when applicable.

Do not weaken a test merely because the implementation calls a cloud client.
Mock the client at the boundary used by the code and verify the observable
behavior.

## Report results

Report the exact focused tests and broader suite that ran. If a test requires
external credentials, a service, or configuration that is unavailable, explain
that limitation and keep it separate from the unit-test result. Do not claim
integration coverage from a unit-test run.
