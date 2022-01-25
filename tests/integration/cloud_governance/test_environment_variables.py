import os


def __get_test_environment_variables():
    test_environment_variable = {}

    test_environment_variable['KEY_TEST'] = os.environ.get("KEY_TEST", '')
    test_environment_variable['REGION'] = os.environ.get("REGION", '')
    test_environment_variable['OUTPUT_BUCKET'] = os.environ.get('OUTPUT_BUCKET', '')
    return test_environment_variable


test_environment_variable = __get_test_environment_variables()