import boto3
from moto import mock_ec2

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.cleanup.unattached_volume import UnattachedVolume

region_name = 'us-east-2'


@mock_ec2
def test_unattached_volume_dry_run_yes_0_unattached():
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = region_name
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    default_ami_id = 'ami-03cf127a'
    ec2_client = boto3.client('ec2', region_name=region_name)
    resource = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1,
                                        MinCount=1).get('Instances', [])[0]
    volume = ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10)
    ec2_client.attach_volume(InstanceId=resource.get('InstanceId'), VolumeId=volume.get('VolumeId'), Device='xvdh')
    volume_run = UnattachedVolume()
    response = volume_run.run()
    assert len(response) == 0


@mock_ec2
def test_unattached_volume_dry_run_yes():
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = region_name
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10)
    volume_run = UnattachedVolume()
    response = volume_run.run()
    assert len(response) > 0
    response = response[0]
    assert response.get('ResourceDelete') == 'False'
    assert response.get('SkipPolicy') == 'NA'


@mock_ec2
def test_unattached_volume_dry_run_no():
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = region_name
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'

    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 1
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10)
    volume_run = UnattachedVolume()
    response = volume_run.run()
    assert len(response) > 0
    response = response[0]
    assert response.get('ResourceDelete') == 'True'
    assert response.get('SkipPolicy') == 'NA'


@mock_ec2
def test_unattached_volume_dry_run_no_7_days_action():
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = region_name
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10)
    volume_run = UnattachedVolume()
    response = volume_run.run()
    assert len(response) > 0
    response = response[0]
    assert response.get('ResourceDelete') == 'False'
    assert response.get('SkipPolicy') == 'NA'


@mock_ec2
def test_unattached_volume_dry_run_no_skip():
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = region_name
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    tags = [{'Key': 'Policy', 'Value': 'notdelete'}]
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 1
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10, TagSpecifications=[{
        'ResourceType': 'volume',
        'Tags': tags
    }])
    volume_run = UnattachedVolume()
    response = volume_run.run()
    assert len(response) > 0
    response = response[0]
    assert response.get('ResourceDelete') == 'False'
    assert response.get('SkipPolicy') == 'NOTDELETE'


@mock_ec2
def test_check_exists_cluster():
    """
    This tests verify skip the existing cluster volume
    :return:
    :rtype:
    """
    tags = [{'Key': 'kubernetes.io/cluster/test', 'Value': 'owned'}]
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = region_name
    environment_variables.environment_variables_dict['policy'] = 'unattached_volume'
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 1
    ec2_client = boto3.client('ec2', region_name=region_name)
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1,
                             MinCount=1, TagSpecifications=[{ 'ResourceType': 'instance','Tags': tags}])
    ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10, TagSpecifications=[{
        'ResourceType': 'volume',
        'Tags': tags
    }])
    volume_run = UnattachedVolume().run()
    assert len(volume_run) == 0
