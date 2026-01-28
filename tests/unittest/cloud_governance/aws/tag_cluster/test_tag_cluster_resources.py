# TEST DRY RUN: mandatory_tags = None
import json
import os

import pytest
from moto import mock_ec2, mock_cloudtrail, mock_iam, mock_s3, mock_elb, mock_elbv2
import boto3

from cloud_governance.policy.policy_operations.aws.tag_cluster.tag_cluster_resouces import TagClusterResources

cluster_prefix = ["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"]
cluster_name = ''
os.environ['SLEEP_SECONDS'] = '0'
mandatory_tags = {}


@pytest.fixture(scope="module")
def tag_cluster_resources():
    """Create TagClusterResources under mocks so __init__ (IAM list_users, EC2, etc.) does not hit real AWS."""
    with mock_ec2(), mock_iam(), mock_cloudtrail(), mock_s3(), mock_elb(), mock_elbv2():
        yield TagClusterResources(
            cluster_prefix=cluster_prefix,
            cluster_name=cluster_name,
            input_tags=mandatory_tags,
            region='us-east-2',
        )


def test_init_cluster_name(tag_cluster_resources):
    """
    This method search for full cluster key stamp according to part of cluster name
    :return:
    """
    assert len(tag_cluster_resources._TagClusterResources__init_cluster_name()) >= 0


def test_cluster_instance(tag_cluster_resources):
    """
    This method return all cluster instances
    :return:
    """
    assert len(tag_cluster_resources.cluster_instance()) >= 0


def test_cluster_volume(tag_cluster_resources):
    """
    This method return all cluster volumes
    :return:
    """
    assert len(tag_cluster_resources.cluster_volume()) >= 0


def test_cluster_ami(tag_cluster_resources):
    """
    This method return all cluster ami
    :return:
    """
    assert len(tag_cluster_resources.cluster_ami()) >= 0


def test_cluster_snapshot(tag_cluster_resources):
    """
    This method return all cluster snapshot
    :return:
    """
    assert len(tag_cluster_resources.cluster_snapshot()) >= 0


def test_cluster_security_group(tag_cluster_resources):
    """
    This method return all cluster security_group
    :return:
    """
    print(tag_cluster_resources.cluster_security_group())


def test_cluster_elastic_ip(tag_cluster_resources):
    """
    This method return all cluster elastic_ip
    :return:
    """
    assert len(tag_cluster_resources.cluster_elastic_ip()) >= 0


def test_cluster_network_interface(tag_cluster_resources):
    """
    This method return all cluster network_interface
    :return:
    """
    assert len(tag_cluster_resources.cluster_network_interface()) >= 0


def test_cluster_load_balancer(tag_cluster_resources):
    """
    This method return all cluster load_balancer
    :return:
    """
    assert len(tag_cluster_resources.cluster_load_balancer()) >= 0


def test_cluster_load_balancer_v2(tag_cluster_resources):
    """
    This method return all cluster load_balancer
    :return:
    """
    assert len(tag_cluster_resources.cluster_load_balancer_v2()) >= 0


def test_cluster_vpc(tag_cluster_resources):
    """
    This method return all cluster cluster_vpc
    :return:
    """
    assert len(tag_cluster_resources.cluster_vpc()) >= 0


def test_cluster_subnet(tag_cluster_resources):
    """
    This method return all cluster cluster_subnet
    :return:
    """
    assert len(tag_cluster_resources.cluster_subnet()) >= 0


def test_cluster_route_table(tag_cluster_resources):
    """
    This method return all cluster route_table
    :return:
    """
    assert len(tag_cluster_resources.cluster_route_table()) >= 0


def test_cluster_internet_gateway(tag_cluster_resources):
    """
    This method return all cluster internet_gateway
    :return:
    """
    assert len(tag_cluster_resources.cluster_internet_gateway()) >= 0


def test_cluster_dhcp_option(tag_cluster_resources):
    """
    This method return all cluster dhcp_option
    :return:
    """
    assert len(tag_cluster_resources.cluster_dhcp_option()) >= 0


def test_cluster_vpc_endpoint(tag_cluster_resources):
    """
    This method return all cluster vpc_endpoint
    :return:
    """
    assert len(tag_cluster_resources.cluster_vpc_endpoint()) >= 0


def test_cluster_nat_gateway(tag_cluster_resources):
    """
    This method return all cluster nat_gateway
    :return:
    """
    assert len(tag_cluster_resources.cluster_nat_gateway()) >= 0


def test_cluster_network_acl(tag_cluster_resources):
    """
    This method return all cluster network_acl
    :return:
    """
    assert len(tag_cluster_resources.cluster_network_acl()) >= 0


def test_cluster_role(tag_cluster_resources):
    """
    This method return all cluster role
    :return:
    """
    assert len(tag_cluster_resources.cluster_role()) >= 0


def test_cluster_user(tag_cluster_resources):
    """
    This method return all cluster role
    :return:
    """
    print(tag_cluster_resources.cluster_user())


def test_cluster_s3_bucket(tag_cluster_resources):
    """
    This method return all cluster s3_bucket
    :return:
    """
    assert len(tag_cluster_resources.cluster_s3_bucket()) >= 0


@mock_s3
@mock_iam
@mock_cloudtrail
@mock_ec2
def test_cluster_ec2():
    """
    This method tests the add tags of cluster instance
    @return:
    """
    tags = [
        {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'unitest'}
    ]
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name='us-east-2')
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1, TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': tags
    }])
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1, TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': tags
    }])
    ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1, TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': tags
    }])
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
    iam_client.create_role(RoleName='unittest-test-cluster-master-role', AssumeRolePolicyDocument=json.dumps(assume_role_policy_document), Tags=tags)
    iam_client.create_role(RoleName='unittest-test-cluster-worker-role', AssumeRolePolicyDocument=json.dumps(assume_role_policy_document), Tags=tags)
    tag_resources = TagClusterResources(cluster_prefix=cluster_prefix, cluster_name=cluster_name,
                                        input_tags=mandatory_tags, region='us-east-2')
    assert len(tag_resources.cluster_instance()) == 3
