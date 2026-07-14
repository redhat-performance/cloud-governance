import boto3
from moto import mock_aws

from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources
from tests.unittest.configs import DEFAULT_AMI_ID

REGION = 'us-east-2'
CLUSTER_PREFIX = ['kubernetes.io/cluster', 'sigs.k8s.io/cluster-api-provider-aws/cluster']
CLUSTER_NAME = 'unittest-test-cluster-abc123'
K8S_TAG = f'kubernetes.io/cluster/{CLUSTER_NAME}'
CAPA_TAG = f'sigs.k8s.io/cluster-api-provider-aws/cluster/{CLUSTER_NAME}'


@mock_aws
def test_f1_capa_sg_not_zombie_when_instance_has_k8s_tag():
    """
    Instance tagged with kubernetes.io/cluster/X, SG tagged with sigs.k8s.io/.../X.
    Same cluster, different prefix — SG should NOT be detected as zombie.
    """
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'}]}]
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='test-capa-sg',
        Description='CAPA SG with sigs.k8s.io tag',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': CAPA_TAG, 'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id not in zombies


@mock_aws
def test_f1_different_cluster_names_is_zombie():
    """
    Instance tagged with cluster-A, SG tagged with cluster-B in a separate empty VPC.
    SG should be zombie because cluster-B has no instances.
    """
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc_a = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    subnet_a = ec2_client.create_subnet(VpcId=vpc_a['Vpc']['VpcId'], CidrBlock='10.0.1.0/24')

    vpc_b = ec2_client.create_vpc(CidrBlock='10.1.0.0/16')
    vpc_b_id = vpc_b['Vpc']['VpcId']

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet_a['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': 'kubernetes.io/cluster/cluster-A', 'Value': 'owned'}]}]
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc_b_id, GroupName='test-diff-cluster-sg',
        Description='SG from different cluster in empty VPC',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': 'sigs.k8s.io/cluster-api-provider-aws/cluster/cluster-B',
                                     'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id in zombies


@mock_aws
def test_f1_no_instances_capa_sg_is_zombie():
    """No instances at all — SG with CAPA cluster tag should be detected as zombie."""
    ec2_client = boto3.client('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    sg = ec2_client.create_security_group(
        VpcId=vpc['Vpc']['VpcId'], GroupName='test-orphan-sg', Description='Orphaned SG',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': CAPA_TAG, 'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id in zombies


@mock_aws
def test_f1_ipi_cluster_no_regression():
    """IPI cluster: instance and SG both tagged with kubernetes.io/cluster/X — SG should NOT be zombie."""
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')

    ipi_tag = [{'Key': K8S_TAG, 'Value': 'owned'}]
    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': ipi_tag}]
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='test-ipi-sg', Description='IPI SG',
        TagSpecifications=[{'ResourceType': 'security-group', 'Tags': ipi_tag}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id not in zombies


@mock_aws
def test_f1_instance_with_both_tags_sg_with_only_capa_tag():
    """
    Instance has both kubernetes.io and sigs.k8s.io tags; SG has only sigs.k8s.io tag.
    Same cluster — SG should NOT be zombie.
    """
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'},
                                    {'Key': CAPA_TAG, 'Value': 'owned'}]}]
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='test-capa-only-sg', Description='SG with CAPA tag only',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': CAPA_TAG, 'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id not in zombies


@mock_aws
def test_f1_cross_prefix_subnet_not_zombie():
    """Subnet tagged with CAPA prefix, instance with kubernetes.io prefix — same cluster, NOT zombie."""
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.1.0/24',
        TagSpecifications=[{'ResourceType': 'subnet',
                           'Tags': [{'Key': CAPA_TAG, 'Value': 'owned'}]}]
    )
    subnet_id = subnet['Subnet']['SubnetId']

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet_id,
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'}]}]
    )

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_subnet()

    assert subnet_id not in zombies


@mock_aws
def test_f1_mixed_ipi_and_capa_clusters_in_same_account():
    """
    Two clusters in same account — IPI (kubernetes.io tags) and CAPA (sigs.k8s.io on SGs).
    Neither SG should be detected as zombie.
    """
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet['Subnet']['SubnetId']

    ipi_cluster = 'ipi-cluster-def456'
    capa_cluster = 'capa-cluster-ghi789'

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1, SubnetId=subnet_id,
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': f'kubernetes.io/cluster/{ipi_cluster}', 'Value': 'owned'}]}]
    )
    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1, SubnetId=subnet_id,
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': f'kubernetes.io/cluster/{capa_cluster}', 'Value': 'owned'}]}]
    )

    ipi_sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='ipi-sg', Description='IPI SG',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': f'kubernetes.io/cluster/{ipi_cluster}', 'Value': 'owned'}]}]
    )['GroupId']

    capa_sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='capa-sg', Description='CAPA SG',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': f'sigs.k8s.io/cluster-api-provider-aws/cluster/{capa_cluster}',
                                     'Value': 'owned'}]}]
    )['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert ipi_sg not in zombies
    assert capa_sg not in zombies


@mock_aws
def test_f2_sg_in_vpc_with_instances_not_zombie():
    """SG in a VPC with running instances should NOT be zombie (VPC instance safety net)."""
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': 'kubernetes.io/cluster/other-cluster', 'Value': 'owned'}]}]
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='test-vpc-check-sg', Description='SG in VPC with instances',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': 'kubernetes.io/cluster/dead-cluster-xyz', 'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id not in zombies


@mock_aws
def test_f2_sg_in_empty_vpc_is_zombie():
    """SG in a VPC with zero instances should be detected as zombie."""
    ec2_client = boto3.client('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    sg = ec2_client.create_security_group(
        VpcId=vpc['Vpc']['VpcId'], GroupName='test-empty-vpc-sg', Description='SG in empty VPC',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id in zombies


@mock_aws
def test_f2_vpc_filter_applies_to_route_tables():
    """Route table in VPC with running instances should NOT be zombie (VPC filter applies to all VPC-bound types)."""
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': 'kubernetes.io/cluster/alive-cluster', 'Value': 'owned'}]}]
    )
    rt = ec2_client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[{'ResourceType': 'route-table',
                           'Tags': [{'Key': 'kubernetes.io/cluster/dead-cluster', 'Value': 'owned'}]}]
    )
    rt_id = rt['RouteTable']['RouteTableId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_route_table()

    assert rt_id not in zombies


@mock_aws
def test_f3_vpc_tag_no_substring_match():
    """
    VPC tagged with kubernetes.io/cluster/abc-test-cluster.
    Searching for cluster tag kubernetes.io/cluster/abc should NOT match (no substring match).
    """
    ec2_client = boto3.client('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(
        CidrBlock='10.0.0.0/16',
        TagSpecifications=[{'ResourceType': 'vpc',
                           'Tags': [{'Key': 'kubernetes.io/cluster/abc-test-cluster', 'Value': 'owned'}]}]
    )
    vpc_id = vpc['Vpc']['VpcId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    result = zcr._ZombieClusterResources__get_vpc_tags(
        vpc_id=vpc_id, cluster_tag='kubernetes.io/cluster/abc'
    )

    assert result == ''


@mock_aws
def test_f11_resource_name_does_not_override_cluster_id():
    """
    SG has a cluster tag AND a Name tag whose value matches resource_name.
    The cluster ID stored should be the cluster tag key, not 'Name'.
    """
    ec2_client = boto3.client('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='test-override-sg', Description='SG with Name tag',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'},
                                    {'Key': 'Name', 'Value': 'my-special-sg'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(
        cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION,
        resource_name='my-special-sg'
    )
    security_groups = zcr.ec2_operations.get_security_groups()
    result = zcr._ZombieClusterResources__get_cluster_resources(
        resources_list=security_groups, input_resource_id='GroupId'
    )

    if sg_id in result:
        assert result[sg_id] == K8S_TAG


@mock_aws
def test_f13_vpc_endpoint_zombie_ids_are_strings():
    """
    VPC endpoint with no matching instances should be detected as zombie,
    and all keys in the returned dict should be string IDs (not dicts).
    """
    ec2_client = boto3.client('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpce = ec2_client.create_vpc_endpoint(
        VpcId=vpc['Vpc']['VpcId'],
        ServiceName='com.amazonaws.us-east-2.s3',
        TagSpecifications=[{'ResourceType': 'vpc-endpoint',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'}]}]
    )
    vpce_id = vpce['VpcEndpoint']['VpcEndpointId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_vpc_endpoint()

    assert vpce_id in zombies
    for zombie_id in zombies:
        assert isinstance(zombie_id, str)


@mock_aws
def test_stopped_instance_prevents_zombie_detection():
    """Stopped (not terminated) instance should still protect its cluster SG from zombie detection."""
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')

    instances = ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'}]}]
    )
    ec2_client.stop_instances(InstanceIds=[instances[0].instance_id])

    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='test-stopped-cluster-sg', Description='SG for stopped cluster',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id not in zombies


@mock_aws
def test_reverse_cross_prefix_not_zombie():
    """Instance has only sigs.k8s.io tag, SG has only kubernetes.io tag — same cluster, NOT zombie."""
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')

    ec2_resource.create_instances(
        ImageId=DEFAULT_AMI_ID, MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': CAPA_TAG, 'Value': 'owned'}]}]
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='test-reverse-capa-sg', Description='SG with k8s tag',
        TagSpecifications=[{'ResourceType': 'security-group',
                           'Tags': [{'Key': K8S_TAG, 'Value': 'owned'}]}]
    )
    sg_id = sg['GroupId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    zombies, _ = zcr.zombie_cluster_security_group()

    assert sg_id not in zombies


@mock_aws
def test_dead_cluster_resources_detected():
    """Genuinely dead cluster with no instances — both SG and subnet should be detected as zombie."""
    ec2_client = boto3.client('ec2', region_name=REGION)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    dead_tag = [{'Key': 'kubernetes.io/cluster/dead-cluster-xyz789', 'Value': 'owned'}]

    sg = ec2_client.create_security_group(
        VpcId=vpc_id, GroupName='dead-cluster-sg', Description='Dead cluster SG',
        TagSpecifications=[{'ResourceType': 'security-group', 'Tags': dead_tag}]
    )
    sg_id = sg['GroupId']

    subnet = ec2_client.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.1.0/24',
        TagSpecifications=[{'ResourceType': 'subnet', 'Tags': dead_tag}]
    )
    subnet_id = subnet['Subnet']['SubnetId']

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX, delete=False, region=REGION)
    sg_zombies, _ = zcr.zombie_cluster_security_group()
    subnet_zombies, _ = zcr.zombie_cluster_subnet()

    assert sg_id in sg_zombies
    assert subnet_id in subnet_zombies
