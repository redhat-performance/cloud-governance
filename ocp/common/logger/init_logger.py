import sys
import os
import logging


logger_category_name = 'ocp'
logger = logging.getLogger(logger_category_name)  # instantiating a logger
handler = logging.StreamHandler(sys.stdout)
log_path = os.getcwd()
fileHandler = logging.FileHandler(filename=f'{log_path}/ocp.log', mode='w+')
logger.addHandler(handler)
logger.addHandler(fileHandler)

logger.setLevel(logging.INFO)
