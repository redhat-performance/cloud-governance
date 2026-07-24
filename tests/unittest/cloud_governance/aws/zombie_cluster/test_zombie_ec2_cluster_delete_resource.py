import boto3
import pytest
from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources
from cloud_governance.policy.policy_operations.aws.zombie_cluster.delete_ec2_resources import DeleteEC2Resources
from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from tests.unittest.configs import DRY_RUN_YES, DRY_RUN_NO, DEFAULT_AMI_ID

tags = [
    {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
    {'Key': 'Owner', 'Value': 'unitest'}
]
region_name = 'us-east-2'
DAYS = 7
FOUR_DAYS = 4


@mock_aws
def test_force_delete_ec2_ami():
    """
    This method tests the deletion of AMI image force
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    instance_id = ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)[0].instance_id
    image_name = ec2_client.create_image(TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}],
                                         InstanceId=instance_id, Name='test-image').get('ImageId')
    ec2_resource.instances.filter(InstanceIds=[instance_id]).terminate()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_ami', force_delete=True)
    zombie_cluster_resources.zombie_cluster_ami()
    assert not EC2Operations(region_name).find_ami(image_name)


@mock_aws
def test_not_delete_ec2_ami():
    """
    This method tests the not deletion of AMI image
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    instance_id = ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)[0].instance_id
    image_name = ec2_client.create_image(TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}],
                                         InstanceId=instance_id, Name='test-image').get('ImageId')
    ec2_resource.instances.filter(InstanceIds=[instance_id]).terminate()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_ami')
    zombie_cluster_resources.zombie_cluster_ami()
    assert EC2Operations(region_name).find_ami(image_name)


@mock_aws
def test_delete_ec2_ami_after_seven():
    """
    This method tests the deletion of AMI image after seven days
    :return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    ec2_client = boto3.client('ec2', region_name=region_name)
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    instance_id = ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)[0].instance_id
    image_name = ec2_client.create_image(TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}],
                                         InstanceId=instance_id, Name='test-image').get('ImageId')
    ec2_resource.instances.filter(InstanceIds=[instance_id]).terminate()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_ami')
    for i in range(DAYS):
        zombie_cluster_resources.zombie_cluster_ami()
    assert not EC2Operations(region_name).find_ami(image_name)


@mock_aws
def test_not_delete_ec2_ami_after_four():
    """
    This method tests the not deletion of AMI image after four days
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    instance_id = ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)[0].instance_id
    image_name = ec2_client.create_image(TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}],
                                         InstanceId=instance_id, Name='test-image').get('ImageId')
    ec2_resource.instances.filter(InstanceIds=[instance_id]).terminate()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_ami')
    for i in range(FOUR_DAYS):
        zombie_cluster_resources.zombie_cluster_ami()
    assert EC2Operations(region_name).find_ami(image_name)


@mock_aws
def test_force_delete_ec2_elastic_load_balancer():
    """
    This method tests the force deletion of Elastic Load Balancer
    :return:
    """
    elb = boto3.client('elb', region_name=region_name)
    elb.create_load_balancer(Listeners=[{
        'InstancePort': 80, 'InstanceProtocol': 'HTTP',
        'LoadBalancerPort': 80, 'Protocol': 'HTTP'
    }], LoadBalancerName='test-load-balancer', Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_load_balancer', force_delete=True)
    zombie_cluster_resources.zombie_cluster_load_balancer()
    assert not EC2Operations(region_name).find_load_balancer(elb_name='test-load-balancer')


@mock_aws
def test_not_delete_ec2_elastic_load_balancer():
    """
    This method tests the not deletion of Elastic Load Balancer
    :return:
    """
    elb = boto3.client('elb', region_name=region_name)
    elb.create_load_balancer(Listeners=[{
        'InstancePort': 80, 'InstanceProtocol': 'HTTP',
        'LoadBalancerPort': 80, 'Protocol': 'HTTP'
    }], LoadBalancerName='test-load-balancer', Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_load_balancer')
    zombie_cluster_resources.zombie_cluster_load_balancer()
    assert EC2Operations(region_name).find_load_balancer(elb_name='test-load-balancer')


@mock_aws
def test_delete_ec2_elastic_load_balancer_after_seven_days():
    """
    This method tests the deletion of Elastic Load Balancer after seven days
    :return:
    """
    elb = boto3.client('elb', region_name=region_name)
    elb.create_load_balancer(Listeners=[{
        'InstancePort': 80, 'InstanceProtocol': 'HTTP',
        'LoadBalancerPort': 80, 'Protocol': 'HTTP'
    }], LoadBalancerName='test-load-balancer', Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_load_balancer')
    for i in range(DAYS):
        zombie_cluster_resources.zombie_cluster_load_balancer()
    assert not EC2Operations(region_name).find_load_balancer(elb_name='test-load-balancer')


@mock_aws
def test_not_delete_ec2_elastic_load_balancer_after_four_days():
    """
    This method tests the non deletion of Elastic Load Balancer after four days
    :return:
    """
    elb = boto3.client('elb', region_name=region_name)
    elb.create_load_balancer(Listeners=[{
        'InstancePort': 80, 'InstanceProtocol': 'HTTP',
        'LoadBalancerPort': 80, 'Protocol': 'HTTP'
    }], LoadBalancerName='test-load-balancer', Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_load_balancer')
    for i in range(FOUR_DAYS):
        zombie_cluster_resources.zombie_cluster_load_balancer()
    assert EC2Operations(region_name).find_load_balancer(elb_name='test-load-balancer')


@mock_aws
def test_delete_ec2_elastic_load_balancer_v2():
    """
    This method tests the deletion Elastic Load balancer V2
    :return:
    """
    ec2_resource = boto3.client('ec2', region_name=region_name)
    elbv2 = boto3.client('elbv2', region_name=region_name)
    vpc_response = ec2_resource.create_vpc(CidrBlock='10.0.0.0/16')
    subnet_response = ec2_resource.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc_response['Vpc']['VpcId'])

    elbv2.create_load_balancer(Name='test-load-balancer-v2', Tags=tags, Subnets=[subnet_response['Subnet']['SubnetId']])
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_load_balancer_v2', force_delete=True)
    zombie_cluster_resources.zombie_cluster_load_balancer_v2()

    assert not EC2Operations(region_name).find_load_balancer_v2(elb_name='test-load-balancer-v2')


@pytest.mark.skip(reason="Handled by ebs_unattached")
@mock_aws
def test_delete_ebs_volume():
    """
    This method tests the deletion  of Volume
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    volume = ec2_client.create_volume(AvailabilityZone='us-east-2', Size=123)
    ec2_client.create_tags(Resources=[volume['VolumeId']], Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_volume', force_delete=True)
    zombie_cluster_resources.zombie_cluster_volume()
    assert EC2Operations(region_name).find_volume()


@mock_aws
def test_delete_snapshots():
    """
    This method tests the deletion of Snapshots
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    volume = ec2_client.create_volume(AvailabilityZone='us-east-2', Size=123)
    snapshots = ec2_client.create_snapshot(VolumeId=volume['VolumeId'])
    ec2_client.create_tags(Resources=[snapshots['SnapshotId']], Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_snapshot', force_delete=True)
    zombie_cluster_resources.zombie_cluster_snapshot()
    assert not EC2Operations(region_name).find_snapshots(snapshots['SnapshotId'])


@mock_aws
def test_delete_ec2_vpc_endpoints():
    """
    This method tests the deletion of VPC endpoints
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_endpoint_id = ec2_client.create_vpc_endpoint(VpcEndpointType='Interface', VpcId=vpc_response['Vpc']['VpcId'],
                                                     TagSpecifications=[{'ResourceType': 'vpc', 'Tags': tags}],
                                                     ServiceName='com.amazonaws.us-east-2.s3').get('VpcEndpoint').get('VpcEndpointId')
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_vpc_endpoint', force_delete=True)
    zombie_cluster_resources.zombie_cluster_vpc_endpoint()
    assert EC2Operations(region_name).find_vpc_endpoints(vpc_endpoint_id)


@mock_aws
def test_delete_dhcp_option_set():
    """
    This method tests the deletion of DHCP Options Sets
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    dhcp = ec2_client.create_dhcp_options(TagSpecifications=[{'ResourceType': 'dhcp-options', 'Tags': tags}],
                                          DhcpConfigurations=[{'Key': 'domain-name-servers',
                                                               'Values': ['10.2.5.1', '10.2.5.2']}])
    ec2_client.associate_dhcp_options(VpcId=vpc_response['Vpc']['VpcId'],
                                      DhcpOptionsId=dhcp['DhcpOptions']['DhcpOptionsId'])
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_dhcp_option', force_delete=True)
    zombie_cluster_resources.zombie_cluster_dhcp_option()
    assert EC2Operations(region_name).find_dhcp_options(dhcp_id=dhcp['DhcpOptions']['DhcpOptionsId'])


@pytest.mark.skip(reason="Already created in VPC, Creating Route Table as Main Route Table by default")
@mock_aws
def test_delete_route_table():
    """
    This method tests the deletion of route table in the vpc
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_id = ec2_client.create_vpc(CidrBlock='10.1.0.0/16',
                                   TagSpecifications=[{'ResourceType': 'vpc', 'Tags': tags}]).get('Vpc')['VpcId']
    subnet1 = ec2_client.create_subnet(TagSpecifications=[{'ResourceType': 'subnet', 'Tags': tags}],
                                       CidrBlock='10.1.1.0/24', VpcId=vpc_id)['Subnet']['SubnetId']
    route_table_id = ec2_client.create_route_table(VpcId=vpc_id, TagSpecifications=[
        {'ResourceType': 'route-table', 'Tags': tags}]).get('RouteTable').get('RouteTableId')
    ec2_client.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet1)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_route_table', force_delete=True)
    zombie_cluster_resources.zombie_cluster_route_table()
    assert not EC2Operations(region_name).find_route_table(route_table_id)


@mock_aws
def test_delete_security_group():
    """
    This methos tests the deletion of Security Groups
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing the security groups',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-testing')['GroupId']
    ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1], Description='Created for testing')
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_security_group', force_delete=True)
    zombie_cluster_resources.zombie_cluster_security_group()
    assert not EC2Operations(region_name).find_security_group(sg1)


@mock_aws
def test_delete_nat_gateway():
    """
    This method tests the deletion Nat Gateway
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
    nat_gateway_id = ec2_client.create_nat_gateway(TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}],
                                                   SubnetId=subnet1)['NatGateway']['NatGatewayId']
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_nat_gateway', force_delete=True)
    zombie_cluster_resources.zombie_cluster_nat_gateway()
    assert EC2Operations(region_name).find_nat_gateway(nat_gateway_id)


@mock_aws
def test_delete_network_acl():
    """
    This method tests the deletion of Network ACL
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16', TagSpecifications=[{'ResourceType': 'vpc', 'Tags': tags}])
    vpc_id = vpc_response['Vpc']['VpcId']
    network_acl_id = ec2_client.create_network_acl(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'network-acl',
                                                                                     'Tags': tags}])['NetworkAcl']['NetworkAclId']
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_network_acl', force_delete=True)
    zombie_cluster_resources.zombie_cluster_network_acl(vpc_id)
    assert not EC2Operations(region_name).find_network_acl(network_acl_id)


@mock_aws
def test_delete_network_interface():
    """
    This method tests the deletion of Network Interface
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing the security groups',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-testing')['GroupId']
    network_interface_id = ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1],
                                                               Description='testing the internet gateway')['NetworkInterface']['NetworkInterfaceId']
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_network_interface', force_delete=True)
    zombie_cluster_resources.zombie_cluster_network_interface()
    assert EC2Operations(region_name).find_network_interface(network_interface_id)


@mock_aws
def test_delete_internet_gateway():
    """
    This method tests the deletion of Internet Gateway
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    ing_id = ec2_client.create_internet_gateway()['InternetGateway']['InternetGatewayId']
    ec2_client.create_tags(Resources=[ing_id], Tags=tags)
    ec2_client.attach_internet_gateway(InternetGatewayId=ing_id, VpcId=vpc_id)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_internet_gateway', force_delete=True)
    zombie_cluster_resources.zombie_cluster_internet_gateway()
    assert not EC2Operations(region_name).find_internet_gateway(ing_id)


@mock_aws
def test_delete_subnet():
    """
    This method tests the deletion of Subnet
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24', TagSpecifications=[{
        'ResourceType': 'subnet', 'Tags': tags
    }])['Subnet']['SubnetId']
    ec2_client.create_network_interface(SubnetId=subnet1, Description='testing the internet gateway')
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_subnet', force_delete=True)
    zombie_cluster_resources.zombie_cluster_subnet()
    assert not EC2Operations(region_name).find_subnet(subnet1)


@mock_aws
def test_delete_elastic_ip():
    """
    This method tests the deletion of Elastic Ip
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']

    allocation_id = ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])['AllocationId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing the security groups',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-testing')['GroupId']
    network_interface_id = ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1],
                                                               Description='testing the internet gateway')['NetworkInterface']['NetworkInterfaceId']
    ec2_client.associate_address(NetworkInterfaceId=network_interface_id, AllocationId=allocation_id)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_elastic_ip', force_delete=True)
    zombie_cluster_resources.zombie_cluster_elastic_ip()
    assert EC2Operations(region_name).find_elastic_ip()


@mock_aws
def test_delete_vpc():
    """
    This method tests the deletion VPC and its dependencies are deleted.
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_id = ec2_client.create_vpc(CidrBlock='10.0.0.0/16', TagSpecifications=[{'ResourceType': 'vpc', 'Tags': tags}])['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc_id)['Subnet']['SubnetId']
    ec2_client.create_subnet(CidrBlock='10.0.2.0/24', VpcId=vpc_id)

    volume = ec2_client.create_volume(AvailabilityZone='us-east-2', Size=123)
    ec2_client.create_tags(Resources=[volume['VolumeId']], Tags=tags)

    elb = boto3.client('elb', region_name=region_name)
    elb.create_load_balancer(Listeners=[{'InstancePort': 80, 'InstanceProtocol': 'HTTP','LoadBalancerPort': 80,
                                         'Protocol': 'HTTP'}], LoadBalancerName='test-load-balancer', Tags=tags)
    elbv2 = boto3.client('elbv2', region_name=region_name)
    elbv2.create_load_balancer(Name='test-load-balancer-v2', Tags=tags, Subnets=[subnet1])

    dhcp = ec2_client.create_dhcp_options(TagSpecifications=[{'ResourceType': 'dhcp-options', 'Tags': tags}],
                                          DhcpConfigurations=[{'Key': 'domain-name-servers',
                                                               'Values': ['10.2.5.1', '10.2.5.2']}])
    ec2_client.associate_dhcp_options(VpcId=vpc_id, DhcpOptionsId=dhcp['DhcpOptions']['DhcpOptionsId'])

    # route_table_id = ec2_client.create_route_table(VpcId=vpc_id,
    #                                                TagSpecifications=[{'ResourceType': 'route-table',
    #                                                                    'Tags': tags}])['RouteTable']['RouteTableId']

    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing the security groups',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-testing')['GroupId']

    ec2_client.create_vpc_endpoint(VpcEndpointType='Interface', VpcId=vpc_id,
                                   TagSpecifications=[{'ResourceType': 'vpc', 'Tags': tags}],
                                   ServiceName='com.amazonaws.us-east-2.s3')

    ec2_client.create_nat_gateway(TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}],
                                  SubnetId=subnet1)

    ec2_client.create_network_acl(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'network-acl', 'Tags': tags}])

    ing_id = ec2_client.create_internet_gateway()['InternetGateway']['InternetGatewayId']
    ec2_client.create_tags(Resources=[ing_id], Tags=tags)
    ec2_client.attach_internet_gateway(InternetGatewayId=ing_id, VpcId=vpc_id)

    allocation_id = ec2_client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': tags}])['AllocationId']

    network_interface_id = ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1],
                                                               Description='testing the internet gateway')['NetworkInterface']['NetworkInterfaceId']
    ec2_client.associate_address(NetworkInterfaceId=network_interface_id, AllocationId=allocation_id)

    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_vpc', force_delete=True)
    zombie_cluster_resources.zombie_cluster_vpc()
    assert not EC2Operations(region_name).find_vpc('kubernetes.io/cluster/unittest-test-cluster')


@mock_aws
def test_zombie_security_group_delete_after_seven_days():
    """
    This method test the zombie resource delete
    """
    days = 7
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing the security groups',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-testing')['GroupId']
    ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1], Description='Created for testing')
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_security_group')
    for i in range(days):
        zombie_cluster_resources.zombie_cluster_security_group()
    assert not EC2Operations(region_name).find_security_group(sg1)


@mock_aws
def test_zombie_security_group_not_delete_after_four_days():
    """
    This method test the zombie resource not delete after four days
    """
    days = 4
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing the security groups',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-testing')['GroupId']
    ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1], Description='Created for testing')
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_security_group')
    for i in range(days):
        zombie_cluster_resources.zombie_cluster_security_group()
    assert EC2Operations(region_name).find_security_group(sg1)


@mock_aws
def test_zombie_security_group_force_delete():
    """
    This method test the zombie resource delete
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing the security groups',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-testing')['GroupId']
    ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1], Description='Created for testing')
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_security_group', force_delete=True)
    zombie_cluster_resources.zombie_cluster_security_group()
    assert not EC2Operations(region_name).find_security_group(sg1)


@mock_aws
def test_delete_security_group_with_all_traffic_rule():
    """
    This method tests the successful deletion of a security group when the referencing rule in the
    default SG is 'All Traffic' (Protocol -1), which leads to None for FromPort/ToPort.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']

    # 1. Cluster SG (to be deleted)
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing All Traffic rule fix',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-all-traffic-test')['GroupId']

    # 2. Default SG (to be modified)
    default_sg_id = ec2_client.describe_security_groups(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}, {'Name': 'group-name', 'Values': ['default']}]
    )['SecurityGroups'][0]['GroupId']

    # 3. Add an "All Traffic" rule (Protocol -1) to the default SG referencing the cluster SG
    ec2_client.authorize_security_group_ingress(
        GroupId=default_sg_id,
        IpPermissions=[{
            'IpProtocol': '-1',  # All protocols
            'UserIdGroupPairs': [{'GroupId': sg1}]
        }]
    )

    ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1], Description='Created for testing')

    zombie_cluster_resources = ZombieClusterResources(
        cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
        cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
        region=region_name,
        resource_name='zombie_cluster_security_group', force_delete=True)

    zombie_cluster_resources.zombie_cluster_security_group()
    assert not EC2Operations(region_name).find_security_group(sg1)


@mock_aws
def test_delete_security_group_with_icmp_rule():
    """
    This method tests the successful deletion of a security group when the referencing rule in the
    default SG is 'ICMP' (Protocol 1), which leads to None for FromPort/ToPort in some rules.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']

    # 1. Cluster SG (to be deleted)
    sg1 = ec2_client.create_security_group(VpcId=vpc_id, Description='Testing ICMP rule fix',
                                           TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}],
                                           GroupName='sg-icmp-test')['GroupId']

    # 2. Default SG (to be modified)
    default_sg_id = ec2_client.describe_security_groups(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}, {'Name': 'group-name', 'Values': ['default']}]
    )['SecurityGroups'][0]['GroupId']

    # 3. Add an "All ICMP" rule (Protocol 1, Type/Code -1/-1) to the default SG referencing the cluster SG
    # For ICMP, FromPort is Type, ToPort is Code. Using -1 for both means "All ICMP".
    ec2_client.authorize_security_group_ingress(
        GroupId=default_sg_id,
        IpPermissions=[{
            'IpProtocol': 'icmp',
            'FromPort': -1,
            'ToPort': -1,
            'UserIdGroupPairs': [{'GroupId': sg1}]
        }]
    )

    ec2_client.create_network_interface(SubnetId=subnet1, Groups=[sg1], Description='Created for testing')

    zombie_cluster_resources = ZombieClusterResources(
        cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
        cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
        region=region_name,
        resource_name='zombie_cluster_security_group', force_delete=True)

    zombie_cluster_resources.zombie_cluster_security_group()
    assert not EC2Operations(region_name).find_security_group(sg1)


# ---------------------------------------------------------------------------
# F12: Elastic IP dict merge fix
# ---------------------------------------------------------------------------

CLUSTER_PREFIX = ['kubernetes.io/cluster', 'sigs.k8s.io/cluster-api-provider-aws/cluster']
K8S_TAG_EIP = 'kubernetes.io/cluster/unittest-test-cluster-abc123'


@mock_aws
def test_f12_elastic_ip_includes_association_zombies():
    """
    Elastic IP associated with an ENI that carries a cluster tag.
    The EIP should appear in the returned zombies dict — association-based
    entries must not be dropped by the dict merge.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    subnet = ec2_client.create_subnet(VpcId=vpc['Vpc']['VpcId'], CidrBlock='10.0.1.0/24')

    eip = ec2_client.allocate_address(Domain='vpc')
    allocation_id = eip['AllocationId']

    eni = ec2_client.create_network_interface(
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'network-interface',
                           'Tags': [{'Key': K8S_TAG_EIP, 'Value': 'owned'}]}]
    )
    association_resp = ec2_client.associate_address(
        AllocationId=allocation_id,
        NetworkInterfaceId=eni['NetworkInterface']['NetworkInterfaceId']
    )
    association_id = association_resp['AssociationId']
    ec2_client.create_tags(Resources=[allocation_id], Tags=[{'Key': K8S_TAG_EIP, 'Value': 'owned'}])

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=region_name)
    zombies, _ = zcr.zombie_cluster_elastic_ip()

    assert association_id in zombies


# ---------------------------------------------------------------------------
# F6: VPC-expanded siblings are checked per-resource before deletion
# ---------------------------------------------------------------------------

@mock_aws
def test_f6_vpc_sibling_with_fewer_days_not_deleted():
    """
    F6: When one zombie SG in a VPC reaches the 7-day deletion threshold, VPC siblings must
    be checked individually. A sibling at 3 days must survive even though the trigger zombie
    hit the threshold. Before the fix, any zombie reaching the threshold caused all VPC
    siblings to be deleted regardless of their individual counters.
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    try:
        ec2_client = boto3.client('ec2', region_name=region_name)

        vpc_id = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']['VpcId']
        subnet_id = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']

        # sg1 at day 6 — becomes 7 after one policy run → should be deleted
        sg1 = ec2_client.create_security_group(
            VpcId=vpc_id, Description='trigger zombie', GroupName='sg-f6-trigger',
            TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}]
        )['GroupId']
        ec2_client.create_tags(Resources=[sg1], Tags=[{'Key': 'ClusterDeleteDays', 'Value': '6'}])
        ec2_client.create_network_interface(SubnetId=subnet_id, Groups=[sg1], Description='eni-sg1')

        # sg2 at day 3 — becomes 4 after one policy run → must NOT be deleted
        sg2 = ec2_client.create_security_group(
            VpcId=vpc_id, Description='sibling zombie', GroupName='sg-f6-sibling',
            TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}]
        )['GroupId']
        ec2_client.create_tags(Resources=[sg2], Tags=[{'Key': 'ClusterDeleteDays', 'Value': '3'}])
        ec2_client.create_network_interface(SubnetId=subnet_id, Groups=[sg2], Description='eni-sg2')

        # No running instances — both SGs are zombie
        ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=True, region=region_name).zombie_cluster_security_group()

        ec2_ops = EC2Operations(region_name)
        assert not ec2_ops.find_security_group(sg1), "sg1 (7 days) should have been deleted"
        assert ec2_ops.find_security_group(sg2), "sg2 (4 days) must not be deleted"
    finally:
        environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES


# ---------------------------------------------------------------------------
# F14: non-numeric ClusterDeleteDays tag must not crash the policy
# ---------------------------------------------------------------------------

@mock_aws
def test_f14_corrupt_cluster_delete_days_does_not_crash():
    """
    F14: A non-numeric ClusterDeleteDays tag value must not raise ValueError and crash the
    policy. The corrupt value is treated as day 1 (reset), so the resource is not deleted
    and the policy completes without error. Before the fix, int() on a corrupt tag value
    propagated an unhandled ValueError.
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    try:
        ec2_client = boto3.client('ec2', region_name=region_name)

        vpc_id = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']['VpcId']
        subnet_id = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']
        sg_id = ec2_client.create_security_group(
            VpcId=vpc_id, Description='F14 test', GroupName='sg-f14-test',
            TagSpecifications=[{'ResourceType': 'security-group', 'Tags': tags}]
        )['GroupId']
        ec2_client.create_tags(Resources=[sg_id], Tags=[{'Key': 'ClusterDeleteDays', 'Value': 'not-a-number'}])
        ec2_client.create_network_interface(SubnetId=subnet_id, Groups=[sg_id], Description='eni-f14')

        # No running instances — SG is zombie; corrupt tag must not raise
        ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=True, region=region_name).zombie_cluster_security_group()

        # Corrupt tag resets to 1 (day 1 of 7) → SG must still exist
        assert EC2Operations(region_name).find_security_group(sg_id), \
            "SG must survive when ClusterDeleteDays is corrupt (treated as day 1)"
        # Tag must be repaired to '1' — not left as 'not-a-number' (which would freeze the counter)
        sg_tags = ec2_client.describe_security_groups(GroupIds=[sg_id])['SecurityGroups'][0].get('Tags', [])
        repaired_days = next((t['Value'] for t in sg_tags if t['Key'] == 'ClusterDeleteDays'), None)
        assert repaired_days == '1', f"Expected ClusterDeleteDays='1' after corrupt reset, got {repaired_days!r}"
    finally:
        environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES


# ---------------------------------------------------------------------------
# PR3: Deletion Safety — F7, F16, B2a
# All tests marked "Fails before PR3" FAIL before the fixes are implemented
# and PASS after.  Tests marked "Regression" already pass and must continue to.
# ---------------------------------------------------------------------------

PR3_CLUSTER_TAG_A = 'kubernetes.io/cluster/cluster-pr3-a'
PR3_CLUSTER_TAG_B = 'kubernetes.io/cluster/cluster-pr3-b'


def _make_delete_ec2(region):
    """Helper: build a DeleteEC2Resources instance wired to real moto boto3 clients."""
    return DeleteEC2Resources(
        client=boto3.client('ec2', region_name=region),
        elb_client=boto3.client('elb', region_name=region),
        elbv2_client=boto3.client('elbv2', region_name=region),
        region=region,
    )


def _default_sg_id(ec2_client, vpc_id):
    """Return the default security group ID for a VPC."""
    return ec2_client.describe_security_groups(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]},
                 {'Name': 'group-name', 'Values': ['default']}]
    )['SecurityGroups'][0]['GroupId']


def _sg_still_references(ec2_client, sg_id, referenced_sg_id):
    """True if sg_id has any ingress rule UserIdGroupPair pointing to referenced_sg_id."""
    rules = ec2_client.describe_security_groups(GroupIds=[sg_id])['SecurityGroups'][0]['IpPermissions']
    return any(
        pair.get('GroupId') == referenced_sg_id
        for rule in rules
        for pair in rule.get('UserIdGroupPairs', [])
    )


# ── F7: ENI dependency guard before SG ingress revocation ─────────────────
#
# The P1 incident: __delete_security_group REVOKES ingress rules in the default
# SG BEFORE calling delete_security_group.  The revocation succeeds even when a
# running instance still uses the zombie SG, severing its network connectivity.
# AWS then refuses delete_security_group (SG in use), so the SG survives but
# ingress rules have been permanently torn out — the actual observable damage.
#
# F7 is reached via the VPC cascade path (zombie_cluster_vpc → __delete_vpc →
# pending_resource → zombie_cluster_security_group(vpc_id=...)).  In this path
# _filter_zombies_by_vpc (F2) filters the SG out of the initial zombie set, but
# __get_zombies_by_vpc_id then re-adds it — bypassing F2.  F7 guards this gap
# by checking ENI attachments at the start of __delete_security_group.
#
# Tests are at the DeleteEC2Resources level (bypassing the scan stage) so that
# F2 doesn't mask the missing F7 guard.

@mock_aws
def test_f7_ingress_rule_not_revoked_when_running_instance_uses_sg():
    """
    F7 (P1 scenario): the default SG's ingress rule referencing the zombie SG must
    NOT be revoked when a running instance uses that SG.  Tested at the
    DeleteEC2Resources level to bypass the scan-time F2 guard.
    Without F7: revoke_security_group_ingress is called → rule removed → FAIL.
    After F7: ENI check causes early return → rule preserved → PASS.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    vpc_id = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']['VpcId']
    subnet_id = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']

    sg_id = ec2_client.create_security_group(
        VpcId=vpc_id, Description='zombie SG', GroupName='sg-pr3-f7-running',
        TagSpecifications=[{'ResourceType': 'security-group',
                            'Tags': [{'Key': PR3_CLUSTER_TAG_A, 'Value': 'owned'}]}],
    )['GroupId']

    # Add cross-SG ingress rule in the default SG — the rule the code will try to revoke
    default_sg = _default_sg_id(ec2_client, vpc_id)
    ec2_client.authorize_security_group_ingress(
        GroupId=default_sg,
        IpPermissions=[{'IpProtocol': '-1', 'UserIdGroupPairs': [{'GroupId': sg_id}]}],
    )

    # Running instance uses the zombie SG — its primary ENI has Attachment.Status='attached'
    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet_id, SecurityGroupIds=[sg_id],
    )

    # Simulate the VPC cascade call: delete_zombie_resource is called directly
    _make_delete_ec2(region_name).delete_zombie_resource(
        resource='security_group', resource_id=sg_id, vpc_id=vpc_id, cluster_tag=PR3_CLUSTER_TAG_A,
    )

    assert _sg_still_references(ec2_client, default_sg, sg_id), \
        'F7: ingress rule must not be revoked when the zombie SG has a live ENI attachment'


@mock_aws
def test_f7_ingress_rule_not_revoked_when_stopped_instance_uses_sg():
    """
    F7: Same scenario with a stopped instance.
    Stopped instances keep their primary ENI attached; ingress rule must be preserved.
    Without F7: rule revoked → FAIL.  After F7: early return → rule preserved → PASS.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    vpc_id = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']['VpcId']
    subnet_id = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']

    sg_id = ec2_client.create_security_group(
        VpcId=vpc_id, Description='zombie SG stopped', GroupName='sg-pr3-f7-stopped',
        TagSpecifications=[{'ResourceType': 'security-group',
                            'Tags': [{'Key': PR3_CLUSTER_TAG_A, 'Value': 'owned'}]}],
    )['GroupId']

    default_sg = _default_sg_id(ec2_client, vpc_id)
    ec2_client.authorize_security_group_ingress(
        GroupId=default_sg,
        IpPermissions=[{'IpProtocol': '-1', 'UserIdGroupPairs': [{'GroupId': sg_id}]}],
    )

    instance = ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet_id, SecurityGroupIds=[sg_id],
    )[0]
    ec2_client.stop_instances(InstanceIds=[instance.id])

    _make_delete_ec2(region_name).delete_zombie_resource(
        resource='security_group', resource_id=sg_id, vpc_id=vpc_id, cluster_tag=PR3_CLUSTER_TAG_A,
    )

    assert _sg_still_references(ec2_client, default_sg, sg_id), \
        'F7: ingress rule must not be revoked when zombie SG has a stopped instance ENI'


@mock_aws
def test_f7_sg_deleted_and_ingress_revoked_when_no_eni_attached():
    """
    F7 regression: when no instance uses the SG, F7 must not block deletion.
    The ingress rule should be revoked and the SG deleted normally.
    Currently passes; must stay passing after F7 is added.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_id = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']['VpcId']

    sg_id = ec2_client.create_security_group(
        VpcId=vpc_id, Description='zombie SG no instance', GroupName='sg-pr3-f7-clean',
        TagSpecifications=[{'ResourceType': 'security-group',
                            'Tags': [{'Key': PR3_CLUSTER_TAG_A, 'Value': 'owned'}]}],
    )['GroupId']

    _make_delete_ec2(region_name).delete_zombie_resource(
        resource='security_group', resource_id=sg_id, vpc_id=vpc_id, cluster_tag=PR3_CLUSTER_TAG_A,
    )

    assert not EC2Operations(region_name).find_security_group(sg_id), \
        'F7 regression: SG with no live ENI attachments must still be deleted'


# ── F16: Pre-deletion cluster instance re-check ───────────────────────────

@mock_aws
def test_f16_snapshot_not_deleted_when_cluster_has_live_instance():
    """
    F16: delete_zombie_resource must re-verify that no running instances exist for
    the cluster before deleting any resource.  This guards against the race where
    the policy scan labelled a resource as zombie but a cluster instance appeared
    before the deletion window ran.
    Tested at the DeleteEC2Resources level (bypassing ZombieClusterResources scan)
    because the scan's own _cluster_instance() check would prevent the zombie from
    ever being classified in the first place — we need to simulate the stale result.
    Fails before F16 (resource is deleted); passes after F16 (deletion aborted).
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    cluster_tag_key = 'kubernetes.io/cluster/cluster-f16-snap'

    vol = ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10)
    snap_id = ec2_client.create_snapshot(VolumeId=vol['VolumeId'])['SnapshotId']
    ec2_client.create_tags(Resources=[snap_id], Tags=[{'Key': cluster_tag_key, 'Value': 'owned'}])

    # Cluster has a live running instance (appeared after the scan produced a stale zombie list)
    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        TagSpecifications=[{'ResourceType': 'instance',
                            'Tags': [{'Key': cluster_tag_key, 'Value': 'owned'}]}],
    )

    # Simulate what the policy would do when it acts on the stale zombie result
    _make_delete_ec2(region_name).delete_zombie_resource(
        resource='ebs_snapshots', resource_id=snap_id, cluster_tag=cluster_tag_key,
    )

    assert EC2Operations(region_name).find_snapshots(snap_id), \
        'F16: snapshot must not be deleted when cluster has a running instance'


@mock_aws
def test_f16_dhcp_options_not_deleted_when_cluster_has_live_instance():
    """
    F16: Same re-check guard for the dhcp_options resource type.
    Fails before F16; passes after.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    cluster_tag_key = 'kubernetes.io/cluster/cluster-f16-dhcp'

    dhcp_id = ec2_client.create_dhcp_options(
        DhcpConfigurations=[{'Key': 'domain-name-servers', 'Values': ['10.0.0.1']}],
        TagSpecifications=[{'ResourceType': 'dhcp-options',
                            'Tags': [{'Key': cluster_tag_key, 'Value': 'owned'}]}],
    )['DhcpOptions']['DhcpOptionsId']

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        TagSpecifications=[{'ResourceType': 'instance',
                            'Tags': [{'Key': cluster_tag_key, 'Value': 'owned'}]}],
    )

    _make_delete_ec2(region_name).delete_zombie_resource(
        resource='dhcp_options', resource_id=dhcp_id, cluster_tag=cluster_tag_key,
    )

    assert EC2Operations(region_name).find_dhcp_options(dhcp_id=dhcp_id), \
        'F16: DHCP options must not be deleted when cluster has a running instance'


@mock_aws
def test_f16_deletion_proceeds_when_no_live_instances():
    """
    F16 regression: when the cluster has no live instances, F16 must not block
    deletion.  The guard must only fire when instances actually exist.
    Currently passes (no F16 to interfere); must continue to pass after F16.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    cluster_tag_key = 'kubernetes.io/cluster/cluster-f16-pass'

    vol = ec2_client.create_volume(AvailabilityZone=f'{region_name}a', Size=10)
    snap_id = ec2_client.create_snapshot(VolumeId=vol['VolumeId'])['SnapshotId']
    ec2_client.create_tags(Resources=[snap_id], Tags=[{'Key': cluster_tag_key, 'Value': 'owned'}])

    # No instances for this cluster → F16 must not block
    _make_delete_ec2(region_name).delete_zombie_resource(
        resource='ebs_snapshots', resource_id=snap_id, cluster_tag=cluster_tag_key,
    )

    assert not EC2Operations(region_name).find_snapshots(snap_id), \
        'F16 regression: snapshot must be deleted when the cluster has no live instances'


# ── B2a: Fix TagSet → Tags in __delete_elastic_ip ─────────────────────────

@mock_aws
def test_b2a_eni_deleted_via_elastic_ip_disassociate_path():
    """
    B2a: __delete_elastic_ip checks network_interface.get('TagSet'), but EIP records
    from describe_addresses carry 'Tags' (never 'TagSet').  The mismatch silently
    skipped ENI cleanup on every disassociate-path run.
    Also requires B2 (pass cluster_tag at the elastic_ip disassociate call sites in
    zombie_cluster_resource.py) so that self.cluster_tag is non-empty when the check runs.
    Without B2/B2a: ENI survives (tag lookup returns None, __is_cluster_resource skipped).
    After B2+B2a: ENI is deleted via __delete_network_interface.
    Fails before the fix; passes after.
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    vpc_id = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']['VpcId']
    subnet_id = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')['Subnet']['SubnetId']

    # Allocate EIP and tag it with cluster-A
    allocation_id = ec2_client.allocate_address(
        Domain='vpc',
        TagSpecifications=[{'ResourceType': 'elastic-ip',
                            'Tags': [{'Key': PR3_CLUSTER_TAG_A, 'Value': 'owned'}]}],
    )['AllocationId']

    # Create a standalone ENI and associate the EIP with it
    eni_id = ec2_client.create_network_interface(
        SubnetId=subnet_id, Description='pr3-b2a-eni',
    )['NetworkInterface']['NetworkInterfaceId']
    ec2_client.associate_address(NetworkInterfaceId=eni_id, AllocationId=allocation_id)

    # No cluster-A instances → EIP enters the zombies_ass (association) path
    ZombieClusterResources(
        cluster_prefix=CLUSTER_PREFIX, delete=True,
        region=region_name, resource_name='zombie_cluster_elastic_ip', force_delete=True,
    ).zombie_cluster_elastic_ip()

    # After B2+B2a the disassociate path must have deleted the ENI
    assert not EC2Operations(region_name).find_network_interface(eni_id), \
        'B2a: ENI must be deleted via the elastic_ip disassociate path after Tags/TagSet fix'
