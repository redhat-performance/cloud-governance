
import boto3
import pytest
from cloud_governance.policy.policy_operations.aws.tag_non_cluster.remove_non_cluster_tags import RemoveNonClusterTags

from cloud_governance.policy.policy_operations.aws.tag_non_cluster.tag_non_cluster_resources import TagNonClusterResources
from tests.integration.test_environment_variables import test_environment_variable

INSTANCE_ID = test_environment_variable.get('INSTANCE_ID', '')
ec2_client = boto3.client('ec2', region_name='us-east-1')
mandatory_tags = {'Budget': 'PERF-DEPT'}
instances = [ec2_client.describe_instances(InstanceIds=[INSTANCE_ID])['Reservations'][0]['Instances']]


@pytest.fixture(autouse=True)
def before_after_each_test_fixture():
    """
    This method tag the instance before test, remove the tags after tests
    @return:
    """
    # Tag the instance
    tag_non_custer_resources = TagNonClusterResources(region='us-east-1', dry_run='no', input_tags=mandatory_tags)
    tag_non_custer_resources.non_cluster_update_ec2(instances)
    yield
    # UnTag the instance
    remove_non_cluster_tags = RemoveNonClusterTags(region='us-east-1', dry_run='no', input_tags=mandatory_tags)
    remove_non_cluster_tags.non_cluster_update_ec2(instances)


def test_tag_non_cluster_update_ec2():
    """
    This method tests, tags are updated to the specific instance or not
    @return:
    """
    expected_tags = ['User', 'Budget', 'Email', 'Owner', 'Manager', 'Project', 'Environment', 'LaunchTime', 'cg-Name']
    instance_tags = ec2_client.describe_tags(Filters=[{'Name': 'resource-id',
                                                       'Values': [INSTANCE_ID]}])['Tags']
    actual_tags = [tag.get('Key') for tag in instance_tags]
    assert len(expected_tags) == len(actual_tags)
    assert expected_tags.sort() == actual_tags.sort()
