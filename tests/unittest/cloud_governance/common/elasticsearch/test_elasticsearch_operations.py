
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations


def test_get_s3_latest_policy_file():
    es_operations = ElasticSearchOperations(es_host='localhost', es_port='9200', region='us-east-2', bucket='redhat-cloud-governance', logs_bucket_key='logs')
    assert es_operations._ElasticSearchOperations__get_s3_latest_policy_file(policy='ec2-idle')


def test_get_last_s3_policy_content():
    es_operations = ElasticSearchOperations(es_host='localhost', es_port='9200', region='us-east-2', bucket='redhat-cloud-governance', logs_bucket_key='logs')
    assert es_operations._ElasticSearchOperations__get_last_s3_policy_content(policy='ec2-idle', file_name='resources.json')
