import json
from unittest.mock import patch

import boto3
from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_operations.aws.zombie_cluster import run_zombie_cluster_resources
from cloud_governance.policy.policy_operations.aws.zombie_cluster.run_zombie_cluster_resources import (
    zombie_cluster_resource, GLOBAL_ZOMBIE_CLUSTER_RESOURCES)

CLUSTER_PREFIX = ["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"]
GLOBAL_REGION = 'us-east-1'
NON_GLOBAL_REGION = 'us-west-2'


def _create_zombie_cluster_role():
    """Create an IAM worker role (global resource) tagged to a cluster that has no instances."""
    iam = boto3.client('iam')
    assume = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},
                       "Action": "sts:AssumeRole"}]
    })
    iam.create_role(RoleName='unittest-guard-worker-role', AssumeRolePolicyDocument=assume,
                    Tags=[{'Key': 'kubernetes.io/cluster/unittest-guard-cluster', 'Value': 'owned'}])


def _run(region):
    environment_variables.environment_variables_dict['CLUSTER_PREFIX'] = CLUSTER_PREFIX
    with patch.object(run_zombie_cluster_resources, 'ElasticSearchOperations') as es:
        es.return_value.check_elastic_search_connection.return_value = False
        return zombie_cluster_resource(delete=False, region=region)


def test_global_resources_constant_contains_role_and_s3():
    assert 'zombie_cluster_role' in GLOBAL_ZOMBIE_CLUSTER_RESOURCES
    assert 'zombie_cluster_s3_bucket' in GLOBAL_ZOMBIE_CLUSTER_RESOURCES


@mock_aws
def test_global_resource_skipped_in_non_global_region():
    """A zombie IAM role must NOT be scanned/counted in a non-global region (prevents 17x inflation)."""
    _create_zombie_cluster_role()
    result = _run(NON_GLOBAL_REGION)
    assert 'zombie_cluster_role' not in result


@mock_aws
def test_global_resource_processed_in_global_region():
    """The same zombie IAM role IS scanned once, in the global region."""
    _create_zombie_cluster_role()
    result = _run(GLOBAL_REGION)
    assert 'zombie_cluster_role' in result
