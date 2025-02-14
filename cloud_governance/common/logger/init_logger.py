import os
import sys
import logging

logger_category_name = 'cloud_governance'
logger = logging.getLogger(logger_category_name)  # instantiating a logger
handler = logging.StreamHandler(sys.stdout)

account_name = os.environ.get('account')
log_format = f'[%(levelname)s] %(asctime)s {account_name} - %(message)s'
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)
logger.addHandler(handler)

# log for output only
log_path = '/tmp'
if os.environ.get('LOG_FILE_PATH'):
    log_path = os.environ.get('LOG_FILE_PATH')
fileHandler = logging.FileHandler(filename=f'{log_path}/cloud_governance.log', mode='w+')
fileHandler.setFormatter(fmt=formatter)
# logger.addHandler(fileHandler)

# def get_pyperf_log_path():
#     return f'{log_path}/py_perf.log'
