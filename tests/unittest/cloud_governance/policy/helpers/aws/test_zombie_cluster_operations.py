from moto import mock_ec2

from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client, get_tag_value_from_tags
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.helpers.aws.policy.zombie_cluster_operations import ZombieClusterOperations
from tests.unittest.cloud_governance.common.clouds.aws.ec2.test_ec2_operations import create_ec2_instance, create_vpc, \
    create_security_group_rule, create_security_group
from tests.unittest.configs import DEFAULT_AMI_ID, AWS_DEFAULT_REGION, INSTANCE_TYPE_T2_MICRO

environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION


@mock_ec2
def test_get_zombie_resources():
    """
    This method returns the zombie_cluster resources
    :return:
    """
    create_ec2_instance()
    create_ec2_instance(cluster_tag='kubernetes.io/cluster/unittest2')
    create_vpc(cluster_tag='kubernetes.io/cluster/unittest3')
    zombie_cluster_operations = ZombieClusterOperations()
    vpc_resources = zombie_cluster_operations._get_cluster_resources(
        zombie_cluster_operations._ec2_operations.get_vpcs(), tags_name='Tags')
    assert len(zombie_cluster_operations.get_zombie_resources(vpc_resources)) == 1


@mock_ec2
def test_update_resource_tags():
    """
    This method tests the update_resource_tags method
    :return:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'

    resource_id = create_ec2_instance()['InstanceId']
    zombie_cluster_operations = ZombieClusterOperations()
    zombie_cluster_operations.update_resource_tags(resource_ids=[resource_id], cleanup_days=2,
                                                   resource_type='ec2_service', tags=[])
    assert '@2' in get_tag_value_from_tags(
        zombie_cluster_operations._ec2_operations.get_ec2_instance_list()[0]['Tags'],
        tag_name='CleanUpDays')


@mock_ec2
def test_delete_resource():
    """
    This method tests the delete_resource method
    :return:
    """
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    cluster_tag = 'kubernetes.io/cluster/unittest2'
    vpc1 = create_vpc(cluster_tag)['VpcId']
    sg1 = create_security_group(vpc_id=vpc1, group_name='sg1', cluster_tag=cluster_tag)['GroupId']
    sg2 = create_security_group(vpc_id=vpc1, group_name='sg2', cluster_tag=cluster_tag)['GroupId']
    ip_permissions = [{
        'IpProtocol': 'tcp',
        'FromPort': 100,
        'ToPort': 80,
        'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
        'UserIdGroupPairs': [{
            'GroupId': sg1,
        }]
    }]
    create_security_group_rule(sg2, ip_permissions)
    zombie_cluster_operations = ZombieClusterOperations()
    zombie_cluster_operations.update_resource_tags(resource_ids=[sg1, sg2], cleanup_days=7,
                                                   resource_type='ec2_service', tags=[])
    total_sgs_exists = len(zombie_cluster_operations._ec2_operations.get_security_groups())

    sgs = zombie_cluster_operations._ec2_operations.get_security_groups()
    sg_resources = zombie_cluster_operations._get_cluster_resources(sgs, tags_name='Tags')
    zombie_cluster_sgs = zombie_cluster_operations.get_zombie_resources(sg_resources)
    zombie_cluster_operations.process_and_delete_resources(zombie_cluster_sgs, resource_id_key='GroupId',
                                                           resource_type='ec2_service', tags_name='Tags',
                                                           create_date='')

    assert len(zombie_cluster_operations._ec2_operations.get_security_groups()) + 2 == total_sgs_exists
