from tempfile import TemporaryDirectory

from cloud_governance.cloud_resource_orchestration.monitor.cloud_monitor import CloudMonitor
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


@logger_time_stamp
def run_cloud_management():
    """This method run the cloud management"""
    environment_variables_dict = environment_variables.environment_variables_dict
    with TemporaryDirectory() as cache_temp_dir:
        environment_variables_dict['TEMPORARY_DIRECTORY'] = cache_temp_dir
        environment_variables_dict['policy'] = 'cloud_resource_orchestration'
        return CloudMonitor().run()


def run_cloud_resource_orchestration():
    run_cloud_management()
