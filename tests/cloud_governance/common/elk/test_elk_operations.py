
from cloud_governance.common.es.es_operations import ESOperations


def test_get_s3_latest_policy_file():
    elk_operations = ESOperations(es_host='localhost', es_port=9200, region='us-east-2', bucket='redhat-cloud-governance', logs_bucket_key='logs')
    assert elk_operations._ElkOperations__get_s3_latest_policy_file(policy='ec2-idle')


def test_get_last_s3_policy_content():
    elk_operations = ESOperations(es_host='localhost', es_port=9200, region='us-east-2', bucket='redhat-cloud-governance', logs_bucket_key='logs')
    assert elk_operations._ElkOperations__get_last_s3_policy_content(policy='ec2-idle')