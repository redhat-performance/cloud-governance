# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Setup
```bash
python3.14 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
pip install -r tests_requirements.txt
```

### Testing
```bash
# Run all tests
python -m pytest

# Run with coverage
coverage run -m pytest

# Run pre-commit hooks
pre-commit run --all-files
```

### Build and Install
```bash
# Install package in development mode
pip install -e .

# Build package
python setup.py sdist bdist_wheel
```

### Container Operations
```bash
# Pull image
podman pull quay.io/cloud-governance/cloud-governance

# Run policy (example)
podman run --rm --name cloud-governance \
  -e policy="zombie_cluster_resource" \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_DEFAULT_REGION="us-east-2" \
  -e dry_run="yes" \
  "quay.io/cloud-governance/cloud-governance"
```

## Architecture

### Core Structure
- **Main Entry Point**: `cloud_governance/main/main.py` - Central orchestrator that routes execution to appropriate policy runners
- **Policy Runners**: Cloud-specific runners in `cloud_governance/policy/policy_operations/`
  - AWS: `aws/` directory with various policy implementations
  - Azure: `azure/azure_policy_runner.py`
  - GCP: `gcp/gcp_policy_runner.py`
  - IBM: `ibm/ibm_operations/ibm_policy_runner.py`
- **Common Operations**: `cloud_governance/policy/policy_runners/common_policy_runner.py` for shared policy logic

### Policy Categories
1. **Cleanup Policies**: Remove unused/idle resources (instances, volumes, snapshots, etc.)
2. **Tagging Policies**: Apply consistent tagging across resources
3. **Cost Management**: Monitor and report on cost expenditure
4. **Security**: Scan for unused access keys, empty roles, git leaks
5. **Zombie Resources**: Clean up orphaned cluster and non-cluster resources

### Cloud Provider Support
- **AWS**: Full feature support (all policy types)
- **Azure**: Basic cleanup policies (instances, volumes, IPs, NAT gateways)
- **IBM**: Tagging policies for baremetal, VMs, and general resources
- **GCP**: Cost reporting and basic resource management

### Environment Configuration
Policies are configured via environment variables:
- Cloud credentials (AWS_ACCESS_KEY_ID, AZURE_CLIENT_SECRET, etc.)
- Policy selection (`policy` env var)
- Execution mode (`dry_run=yes/no`)
- Data upload targets (ElasticSearch, S3 bucket)

### Policy Execution Flow
1. Environment variables loaded via `environment_variables.py`
2. Main orchestrator determines cloud provider and policy type
3. Appropriate policy runner instantiated
4. Policy executed with dry-run or live mode
5. Results uploaded to configured storage/monitoring systems

### Key Design Patterns
- All policies support dry-run mode for safe testing
- Resources can be excluded using tags: `Policy=notdelete` or `skip=not_delete`
- Policies track action days via `DAYS_TO_TAKE_ACTION` environment variable
- Results are structured for upload to ElasticSearch and S3 with standardized formats

## GitHub Workflows and CI/CD

### Linting and Code Quality
```bash
# Linting with flake8 (used in CI)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

### Testing Strategy
- **Unit Tests**: `pytest -v tests/unittest` - Python 3.10-3.14 matrix
- **Integration Tests**: `pytest -v tests/integration` - Requires AWS/Azure/GCP credentials and ElasticSearch
- **E2E Tests**: Cross-region policy validation using containerized deployments
- **Coverage**: Uses coveralls.io for coverage reporting

### Pull Request Workflow (.github/workflows/PR.yml)
- Requires `ok-to-test` label for security (pull_request_target trigger)
- Runs unit tests, integration tests, and E2E validation
- Creates/destroys AWS test infrastructure using Terraform/Terragrunt
- Tests multiple Python versions in parallel

### Main Branch Workflow (.github/workflows/Build.yml)
Complete CI/CD pipeline including:
1. **Testing**: Unit, integration, and E2E tests across Python versions
2. **Infrastructure**: Terraform AWS instance creation/destruction for testing
3. **Publishing**:
   - PyPI package upload and validation
   - Quay.io container image builds (public and private repositories)
4. **Versioning**: Automatic version bumping using bumpversion
5. **Security**: GitLeaks scanning for credential exposure

### Development Dependencies
System requirements for local development and CI:
```bash
# Required for python-ldap
sudo apt-get install build-essential python3-dev libldap2-dev libsasl2-dev

# CI also installs: terraform, terragrunt, flake8, pytest, coverage
```

### Container Publishing
- Public: `quay.io/cloud-governance/cloud-governance:latest`
- Private: Version-tagged releases for internal use
- Multi-stage build process with version validation
