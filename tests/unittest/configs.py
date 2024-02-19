import datetime


# Common Variables

DRY_RUN_YES = 'yes'
DRY_RUN_NO = 'no'
CURRENT_DATE = datetime.datetime.utcnow().date()


# AWS
AWS_DEFAULT_REGION = 'us-west-2'
DEFAULT_AMI_ID = 'ami-03cf127a'
INSTANCE_TYPE = 't2.micro'


# Azure
SUBSCRIPTION_ID = 'unitest-subscription'
RESOURCE_GROUP = 'unittest'
SUB_ID = f'/subscription/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}'
NETWORK_PROVIDER = f'providers/Microsoft.Network'
COMPUTE_PROVIDER = 'providers/Microsoft.Compute'


# ES
ES_INDEX = 'test-unittest-index'
TEST_INDEX_ID = 'test-unittest-index-01'
