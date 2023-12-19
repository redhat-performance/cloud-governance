import os.path
import tempfile


from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_runners.aws.policy_runner import PolicyRunner


def test_write_to_file():
    """
    This method writes the data to the file
    :return:
    :rtype:
    """
    with tempfile.TemporaryDirectory() as dir_name:
        environment_variables.environment_variables_dict['SAVE_TO_FILE_PATH'] = dir_name
        environment_variables.environment_variables_dict['policy'] = 'test'
        policy_runner = PolicyRunner()
        data = [{"ResourceId": "i-123"}, {"ResourceId": "i-456"}]
        policy_runner.write_to_file(data=data)
        assert os.path.getsize(f'{dir_name}/test.csv') > 1
