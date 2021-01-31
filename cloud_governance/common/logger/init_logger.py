import sys
import os
import logging


logger_category_name = 'cloud_governance'
logger = logging.getLogger(logger_category_name)  # instantiating a logger
handler = logging.StreamHandler(sys.stdout)
# log for output only
#log_path = os.getcwd()
#fileHandler = logging.FileHandler(filename=f'{log_path}/cloud_governance.log', mode='w+')
logger.addHandler(handler)
#logger.addHandler(fileHandler)


# def get_pyperf_log_path():
#     return f'{log_path}/py_perf.log'

