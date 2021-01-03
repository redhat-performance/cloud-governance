import sys
import os
import logging


logger_category_name = 'cloud_governance'
logger = logging.getLogger(logger_category_name)  # instantiating a logger
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

# log to local file - disable due to limitation to run in container as root, only as normal user
#log_path = os.getcwd()
#fileHandler = logging.FileHandler(filename=f'{log_path}/cloud_governance.log', mode='w+')
#logger.addHandler(fileHandler)

# move det level to main
#logger.setLevel(logging.INFO)
