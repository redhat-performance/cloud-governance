from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client
from tests.unittest.configs import AWS_DEFAULT_REGION, DEFAULT_AMI_ID, INSTANCE_TYPE_T2_MICRO, VOLUME_SIZE


def get_tags(cluster_tag: str = None):
    tags = [{'Key': 'Name', 'Value': 'unitest'}]
    if cluster_tag:
        tags.append({'Key': cluster_tag, 'Value': 'owned'})
    return tags


def create_ec2_instance(cluster_tag: str = None):
    tags = get_tags(cluster_tag)
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    resource = ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                                        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}],
                                        MaxCount=1, MinCount=1)['Instances'][0]
    return resource


def create_volume(cluster_tag: str = None):
    tags = get_tags(cluster_tag)
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    resource = ec2_client.create_volume(AvailabilityZone='f{AWS_DEFAULT_REGION}a', Size=VOLUME_SIZE,
                                        TagSpecifications=[{'ResourceType': 'volume', 'Tags': tags}])
    return resource


def create_vpc(cluster_tag: str = None):
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = get_tags(cluster_tag)
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16",
                                TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])['Vpc']
    return vpc


def create_subnet(vpc_id: str, cluster_tag: str = None, cidr_block: str = '10.0.1.0/24'):
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = get_tags(cluster_tag)
    return ec2_client.create_subnet(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'subnet', 'Tags': tags}],
                                    CidrBlock=cidr_block)['Subnet']


def create_network_interface(subnet_id: str, cluster_tag: str = None, group_ids: list = None):
    group_ids = [] if not group_ids else group_ids
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = get_tags(cluster_tag)
    return ec2_client.create_network_interface(TagSpecifications=[{'ResourceType': 'interface', 'Tags': tags}],
                                               SubnetId=subnet_id, Groups=group_ids)['NetworkInterface']


def create_nat_gateway(subnet_id: str, cluster_tag: str = None):
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = get_tags(cluster_tag)
    return ec2_client.create_nat_gateway(TagSpecifications=[{'ResourceType': 'nat-gateway', 'Tags': tags}],
                                         SubnetId=subnet_id, ConnectivityType='Public')


def create_security_group(vpc_id: str, cluster_tag: str = None, group_name: str = ''):
    tags = get_tags(cluster_tag)
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)

    return ec2_client.create_security_group(
        Description='Test Security Group', GroupName=f'test-group-{group_name}',
        VpcId=vpc_id,
        TagSpecifications=[{
            'ResourceType': 'security-group',
            'Tags': tags
        }])


def create_security_group_rule(security_group_id: str, ip_permissions: list):
    ec2_client = get_boto3_client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_client.authorize_security_group_ingress(GroupId=security_group_id, IpPermissions=ip_permissions)
