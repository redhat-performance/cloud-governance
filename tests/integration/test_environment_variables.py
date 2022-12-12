
from cloud_governance.main.environment_variables import EnvironmentVariables


def __get_test_environment_variable():
    """
    This method generate environment variable for test
    """
    test_environment_variable = {}

    ##################################################################################################
    # dynamic parameters - configure for local run
    test_environment_variable['policy'] = EnvironmentVariables.get_env('policy', '')
    test_environment_variable['AWS_DEFAULT_REGION'] = EnvironmentVariables.get_env('AWS_DEFAULT_REGION', '')
    test_environment_variable['dry_run'] = EnvironmentVariables.get_env('dry_run', '')
    test_environment_variable['KEY_TEST'] = EnvironmentVariables.get_env("KEY_TEST", '')
    test_environment_variable['REGION'] = EnvironmentVariables.get_env("REGION", '')
    test_environment_variable['BUCKET'] = EnvironmentVariables.get_env('BUCKET', '')

    # ElasticSearch
    test_environment_variable['elasticsearch'] = EnvironmentVariables.get_env('ELASTICSEARCH', 'localhost')
    test_environment_variable['elasticsearch_port'] = EnvironmentVariables.get_env('ELASTICSEARCH_PORT', '9200')
    test_environment_variable['timeout'] = int(EnvironmentVariables.get_env('TIMEOUT', '2000'))

    # local vars
    test_environment_variable['INSTANCE_ID'] = EnvironmentVariables.get_env('INSTANCE_ID', '')

    return test_environment_variable


# Global path parameters
test_environment_variable = __get_test_environment_variable()
