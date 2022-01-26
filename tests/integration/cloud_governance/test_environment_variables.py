import os


def __get_test_environment_variables():
    test_environment_variable = {}

    test_environment_variable['KEY_TEST'] = os.environ.get("KEY_TEST", '')
    test_environment_variable['REGION'] = os.environ.get("REGION", '')
    test_environment_variable['BUCKET'] = os.environ.get('BUCKET', '')
    return test_environment_variable


test_environment_variable = __get_test_environment_variables()