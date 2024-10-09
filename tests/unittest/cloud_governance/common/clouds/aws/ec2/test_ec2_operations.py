import boto3
from moto import mock_ec2, mock_elb, mock_elbv2

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client
from tests.unittest.configs import DEFAULT_AMI_ID, INSTANCE_TYPE_T2_MICRO, TEST_USER_NAME

AWS_DEFAULT_REGION = 'ap-south-1'


@mock_ec2
def test_get_ec2_instance_list():
    """
    This method returns the list of ec2 instances
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    assert type(ec2_operations.get_ec2_instance_list()[0]) == dict


@mock_ec2
def test_get_ec2_instance_ids():
    """
    This method tests the return the list instance_ids
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    assert type(ec2_operations.get_ec2_instance_ids()[0]) == str


@mock_ec2
def test_tag_ec2_resources():
    """
    This method tests the method tagged instances by batch wise
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    default_ami_id = 'ami-03cf127a'
    for i in range(25):
        ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)
    resource_ids = ec2_operations.get_ec2_instance_ids()
    assert ec2_operations.tag_ec2_resources(client_method=ec2_client.create_tags, resource_ids=resource_ids,
                                            tags=tags) == 2


@mock_ec2
def test_delete_volumes():
    """
    This method tests the method delete_volume
    :return:
    """
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': 'cloud-governance'},
            {'Key': 'kubernetes.io/cluster/mock-test', 'Value': 'owned'}]
    volume = ec2_client.create_volume(AvailabilityZone=f'{AWS_DEFAULT_REGION}a',
                                      Size=10,
                                      TagSpecifications=[{
                                          'ResourceType': 'volume',
                                          'Tags': tags
                                      }])
    assert ec2_operations.delete_volumes([volume.get('VolumeId')])


@mock_ec2
def test_delete_security_group():
    """
    This method tests the method delete security group
    :return:
    """
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    security_group = ec2_client.create_security_group(
        Description='Test Security Group',
        GroupName='test-group',
        TagSpecifications=[{
            'ResourceType': 'security-group',
            'Tags': tags
        }])
    assert ec2_operations.delete_security_group([security_group.get('GroupId')])


@mock_ec2
def test_deregister_ami():
    """
    This method tests the method deregister ami
    :return:
    """
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    instance_id = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                                           MaxCount=1, MinCount=1
                                           )['Instances'][0]['InstanceId']
    image_id = ec2_client.create_image(InstanceId=instance_id, Name=TEST_USER_NAME).get('ImageId')
    assert ec2_operations.deregister_ami([image_id])


@mock_ec2
def test_delete_snapshot():
    """
    This method tests the method delete_snapshot
    :return:
    """
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    instance_id = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                                           MaxCount=1, MinCount=1
                                           )['Instances'][0]['InstanceId']
    image_id = ec2_client.create_image(InstanceId=instance_id, Name=TEST_USER_NAME).get('ImageId')
    snapshot_id = (ec2_client.describe_images(ImageIds=[image_id])['Images'][0].get('BlockDeviceMappings')[0]
                   .get('Ebs').get('SnapshotId'))
    ec2_operations.deregister_ami([image_id])
    assert ec2_operations.delete_snapshot([snapshot_id])


@mock_elb
def test_delete_load_balancer():
    """
    This method tests the method delete_load_balancer
    :return:
    """
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_operations.elb1_client.create_load_balancer(LoadBalancerName='TEST',
                                                    Listeners=[{'Protocol': 'HTTP',
                                                                'LoadBalancerPort': 80,
                                                                'InstancePort': 8080}])
    load_balancers = ec2_operations.get_load_balancers()
    resource_ids = []
    for load_balancer in load_balancers:
        resource_ids.append(load_balancer.get('LoadBalancerName'))
    assert ec2_operations.delete_load_balancer_v1(resource_ids=resource_ids)


@mock_ec2
@mock_elbv2
def test_delete_load_balancer_v2():
    """
    This method tests the method delete_load_balancer_v2
    :return:
    """
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc_response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']

    subnet_response = ec2_client.create_subnet(
        CidrBlock='10.0.1.0/24',
        VpcId=vpc_id
    )
    subnet_id = subnet_response['Subnet']['SubnetId']
    ec2_operations.elbv2_client.create_load_balancer(Name='TEST', Subnets=[subnet_id])
    load_balancers = ec2_operations.get_load_balancers_v2()

    resource_ids = []
    for load_balancer in load_balancers:
        resource_ids.append(load_balancer.get('LoadBalancerArn'))
    assert ec2_operations.delete_load_balancer_v2(resource_ids=resource_ids)


@mock_ec2
def test_delete_nat_gateway():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc)['Subnet']['SubnetId']
    allocation = ec2_client.allocate_address(Domain='vpc')
    allocation_id = allocation['AllocationId']
    response = ec2_client.create_nat_gateway(SubnetId=subnet, AllocationId=allocation_id)
    nat_gateway_id = response['NatGateway']['NatGatewayId']
    assert ec2_operations.delete_nat_gateway([nat_gateway_id])


@mock_ec2
def test_delete_network_interface():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc)['Subnet']['SubnetId']
    eni = ec2_client.create_network_interface(SubnetId=subnet)['NetworkInterface']['NetworkInterfaceId']
    assert ec2_operations.delete_network_interface([eni])


@mock_ec2
def test_delete_internet_gateway():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    igw = ec2_client.create_internet_gateway()['InternetGateway']['InternetGatewayId']
    assert ec2_operations.delete_internet_gateway([igw])


@mock_ec2
def test_release_address():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    allocation = ec2_client.allocate_address(Domain='vpc')
    allocation_id = allocation['AllocationId']
    assert ec2_operations.release_address([allocation_id])


@mock_ec2
def test_delete_dhcp():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    dhcp = ec2_client.create_dhcp_options(DhcpConfigurations=[{
        'Key': 'domain-name',
        'Values': ['example.com']
    }])['DhcpOptions']['DhcpOptionsId']
    assert ec2_operations.delete_dhcp([dhcp])


@mock_ec2
def test_delete_nacl():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    nacl = ec2_client.create_network_acl(VpcId=vpc)['NetworkAcl']['NetworkAclId']
    assert ec2_operations.delete_nacl([nacl])


@mock_ec2
def test_delete_vpc_endpoint():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    endpoint = \
        ec2_client.create_vpc_endpoint(VpcId=vpc, VpcEndpointType='Interface',
                                       ServiceName='com.amazonaws.us-east-1.s3')[
            'VpcEndpoint'][
            'VpcEndpointId']
    assert ec2_operations.delete_vpc_endpoint([endpoint])


@mock_ec2
def test_disassociate_route_table():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc)['Subnet']['SubnetId']
    route_table = ec2_client.create_route_table(VpcId=vpc)['RouteTable']['RouteTableId']
    association = ec2_client.associate_route_table(SubnetId=subnet, RouteTableId=route_table)['AssociationId']
    assert ec2_operations.disassociate_route_table(association)


@mock_ec2
def test_delete_vpc_route_table():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    route_table = ec2_client.create_route_table(VpcId=vpc)['RouteTable']['RouteTableId']
    assert ec2_operations.delete_vpc_route_table([route_table])


@mock_ec2
def test_delete_vpc_subnet():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc)['Subnet']['SubnetId']
    assert ec2_operations.delete_vpc_subnet([subnet])


@mock_ec2
def test_delete_vpc():
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    ec2_client = ec2_operations.ec2_client
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    assert ec2_operations.delete_vpc([vpc])
