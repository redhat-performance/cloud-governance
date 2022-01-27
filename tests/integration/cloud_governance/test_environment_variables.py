import os


def __get_test_environment_variables():
    test_environment_variable = {}

    test_environment_variable['KEY_TEST'] = os.environ.get("KEY_TEST", '')
    test_environment_variable['REGION'] = os.environ.get("REGION", '')
    test_environment_variable['BUCKET'] = os.environ.get('BUCKET', '')
    # ElasticSearch
    test_environment_variable['elasticsearch'] = os.environ.get('ELASTICSEARCH', 'elasticsearch.intlab.perf-infra.lab.eng.rdu2.redhat.com')
    test_environment_variable['elasticsearch_port'] = os.environ.get('ELASTICSEARCH_PORT', '80')
    test_environment_variable['timeout'] = int(os.environ.get('TIMEOUT', '2000'))

    # ElasticSearch url
    if test_environment_variable.get('elasticsearch_password', ''):
        test_environment_variable['elasticsearch_url'] = f"http://{test_environment_variable.get('elasticsearch_user', '')}:{test_environment_variable.get('elasticsearch_password', '')}@{test_environment_variable.get('elasticsearch', '')}:{test_environment_variable.get('elasticsearch_port', '')}"
    else:
        if test_environment_variable['elasticsearch'] and test_environment_variable.get('elasticsearch_port', ''):
            test_environment_variable['elasticsearch_url'] = f"http://{test_environment_variable.get('elasticsearch', '')}:{test_environment_variable.get('elasticsearch_port', '')}"
        else:
            test_environment_variable['elasticsearch_url'] = ''

    return test_environment_variable


test_environment_variable = __get_test_environment_variables()