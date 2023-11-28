import json
import os
from unittest.mock import patch, MagicMock

import boto3
from moto import mock_ec2, mock_iam, mock_cloudtrail

from cloud_governance.policy.aws.tag_cluster_resources import TagClusterResources

os.environ['account'] = "testing"


@mock_iam
@mock_ec2
@mock_cloudtrail
@patch('cloud_governance.common.clouds.aws.resource_tagging_api.resource_tag_api_operations.ResourceTagAPIOperations.tag_resources_by_tag_key_value')
def test_tag_cluster_resources(session):
    """
    This method tests the tagging of cluster resources
    :return:
    :rtype:
    """
    os.environ['SLEEP_SECONDS'] = "0"
    tag_cluster_resources = TagClusterResources(region_name='us-east-1')
    tags = [
        {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'unitest'}
    ]
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name='us-east-1')
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1, TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': tags
    }])
    session.return_value = ["unittest-test-cluster-master-role", "unittest-test-cluster-worker-role"]
    assume_role_policy_document = {"Version": "2012-10-17",
                                   "Statement": [{"Sid": "", "Effect": "Allow",
                                                  "Principal": {
                                                      "Service": "ec2.amazonaws.com"
                                                  },
                                                  "Action": "sts:AssumeRole"
                                                  }
                                                 ]
                                   }
    iam_client = boto3.client('iam')
    iam_client.create_role(RoleName='unittest-test-cluster-master-role',
                           AssumeRolePolicyDocument=json.dumps(assume_role_policy_document), Tags=tags)
    iam_client.create_role(RoleName='unittest-test-cluster-worker-role',
                           AssumeRolePolicyDocument=json.dumps(assume_role_policy_document), Tags=tags)
    response = tag_cluster_resources.run()
    assert response == {'kubernetes.io/cluster/unittest-test-cluster': {
        'resources': ['unittest-test-cluster-master-role', 'unittest-test-cluster-worker-role'],
        'tags': {'cluster_id': 'unittest-test-cluster', 'Budget': 'PERF-DEPT', 'Key': 'User', 'Value': 'NA'}}}
