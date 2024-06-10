import datetime

PROJECT_NAME = 'cloud_governance'

# Common Variables

DRY_RUN_YES = 'yes'
DRY_RUN_NO = 'no'
CURRENT_DATE = datetime.datetime.now(datetime.UTC.utc).date()
CURRENT_DATE_TIME = datetime.datetime.now(datetime.UTC.utc)
TEST_USER_NAME = 'unit-test'

# AWS
AWS_DEFAULT_REGION = 'us-west-2'
DEFAULT_AMI_ID = 'ami-03cf127a'
INSTANCE_TYPE = 't2.micro'
INSTANCE_TYPE_T2_MICRO = 't2.micro'
NAT_GATEWAY_NAMESPACE = 'AWS/NATGateway'
EC2_NAMESPACE = 'AWS/EC2'
CLOUD_WATCH_METRICS_DAYS = 14
# AWS RDS
DB_INSTANCE_CLASS = 'db.t3.small'
DB_ENGINE = 'postgres'

# Azure
SUBSCRIPTION_ID = 'unitest-subscription'
RESOURCE_GROUP = 'unittest'
SUB_ID = f'/subscription/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}'
NETWORK_PROVIDER = f'providers/Microsoft.Network'
COMPUTE_PROVIDER = 'providers/Microsoft.Compute'
AZURE_RESOURCE_ID = f'{SUB_ID}/{COMPUTE_PROVIDER}/cloud-governance-unittest'
NAT_GATEWAY_NAME = 'test-cloud-governance-nat-1'

# ES
ES_INDEX = 'test-unittest-index'
TEST_INDEX_ID = 'test-unittest-index-01'
