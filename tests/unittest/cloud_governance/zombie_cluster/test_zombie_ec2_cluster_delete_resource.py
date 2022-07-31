import boto3
import pytest
from moto import mock_ec2, mock_elb, mock_elbv2, mock_s3
from cloud_governance.policy.zombie_cluster_resouce import ZombieClusterResources
from cloud_governance.common.aws.ec2.ec2_operations import EC2Operations

tags = [
    {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
    {'Key': 'Owner', 'Value': 'unitest'}
]
region_name = 'us-east-2'


@mock_ec2
def test_delete_ec2_ami():
    """
    This method tests the deletion of AMI image
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    default_ami_id = 'ami-03cf127a'
    ec2_resource = boto3.resource('ec2', region_name=region_name)
    instance_id = ec2_resource.create_instances(ImageId=default_ami_id, MaxCount=1, MinCount=1)[0].instance_id
    image_name = ec2_client.create_image(TagSpecifications=[{'ResourceType': 'image', 'Tags': tags}],
                                         InstanceId=instance_id, Name='test-image').get('ImageId')
    ec2_resource.instances.filter(InstanceIds=[instance_id]).terminate()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_ami')
    zombie_cluster_resources.zombie_cluster_ami()
    assert not EC2Operations(region_name).find_ami(image_name)


@mock_ec2
@mock_elb
def test_delete_ec2_elastic_load_balancer():
    """
    This method tests the deletion of Elastic Load Balancer
    :return:
    """
    elb = boto3.client('elb', region_name=region_name)
    elb.create_load_balancer(Listeners=[{
        'InstancePort': 80, 'InstanceProtocol': 'HTTP',
        'LoadBalancerPort': 80, 'Protocol': 'HTTP'
    }], LoadBalancerName='test-load-balancer', Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_load_balancer')
    zombie_cluster_resources.zombie_cluster_load_balancer()
    assert not EC2Operations(region_name).find_load_balancer(elb_name='test-load-balancer')


@mock_ec2
@mock_elbv2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_load_balancer_v2')
    zombie_cluster_resources.zombie_cluster_load_balancer_v2()

    assert not EC2Operations(region_name).find_load_balancer_v2(elb_name='test-load-balancer-v2')


@mock_ec2
def test_delete_ebs_volume():
    """
    This method tests the deletion  of Volume
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    volume = ec2_client.create_volume(AvailabilityZone='us-east-2', Size=123)
    ec2_client.create_tags(Resources=[volume['VolumeId']], Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_volume')
    zombie_cluster_resources.zombie_cluster_volume()
    assert EC2Operations(region_name).find_volume()


@mock_ec2
def test_delete_snapshots():
    """
    This method tests the deletion of Snapshots
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=region_name)
    volume = ec2_client.create_volume(AvailabilityZone='us-east-2', Size=123)
    snapshots = ec2_client.create_snapshot(VolumeId=volume['VolumeId'])
    ec2_client.create_tags(Resources=[snapshots['SnapshotId']], Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_snapshot')
    zombie_cluster_resources.zombie_cluster_snapshot()
    assert not EC2Operations(region_name).find_snapshots(snapshots['SnapshotId'])


@mock_ec2
@mock_s3
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_vpc_endpoint')
    zombie_cluster_resources.zombie_cluster_vpc_endpoint()
    assert EC2Operations(region_name).find_vpc_endpoints(vpc_endpoint_id)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_dhcp_option')
    zombie_cluster_resources.zombie_cluster_dhcp_option()
    assert EC2Operations(region_name).find_dhcp_options(dhcp_id=dhcp['DhcpOptions']['DhcpOptionsId'])


@pytest.mark.skip(reason="Already created in VPC, Creating Route Table as Main Route Table by default")
@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_route_table')
    zombie_cluster_resources.zombie_cluster_route_table()
    assert not EC2Operations(region_name).find_route_table(route_table_id)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_security_group')
    zombie_cluster_resources.zombie_cluster_security_group()
    assert not EC2Operations(region_name).find_security_group(sg1)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_nat_gateway')
    zombie_cluster_resources.zombie_cluster_nat_gateway()
    assert EC2Operations(region_name).find_nat_gateway(nat_gateway_id)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_network_acl')
    zombie_cluster_resources.zombie_cluster_network_acl(vpc_id)
    assert not EC2Operations(region_name).find_network_acl(network_acl_id)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_network_interface')
    zombie_cluster_resources.zombie_cluster_network_interface()
    assert EC2Operations(region_name).find_network_interface(network_interface_id)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_internet_gateway')
    zombie_cluster_resources.zombie_cluster_internet_gateway()
    assert not EC2Operations(region_name).find_internet_gateway(ing_id)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_subnet')
    zombie_cluster_resources.zombie_cluster_subnet()
    assert not EC2Operations(region_name).find_subnet(subnet1)


@mock_ec2
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_elastic_ip')
    zombie_cluster_resources.zombie_cluster_elastic_ip()
    assert EC2Operations(region_name).find_elastic_ip()


@mock_ec2
@mock_elb
@mock_elbv2
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

    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      region=region_name,
                                                      resource_name='zombie_cluster_vpc')
    zombie_cluster_resources.zombie_cluster_vpc()
    assert not EC2Operations(region_name).find_vpc('kubernetes.io/cluster/unittest-test-cluster')
