from functools import wraps
import datetime
import time

from cloud_governance.common.logger.init_logger import logger

datetime_format = '%Y-%m-%d %H:%M:%S'


def logger_time_stamp(method):
    """
    This method call to wrap method
    @param method:
    @return: method wrapper
    """
    @wraps(method)  # solve method help doc
    def method_wrapper(*args, **kwargs):
        """
        This method wrap the input method
        @param args:
        @param kwargs:
        @return: prefix + input method + suffix
        """
        time_start = time.time()
        date_time_start = datetime.datetime.now().strftime(datetime_format)
        try:
            logger.warn(f'Method name: {method.__name__} , Start time: {date_time_start} ')
            logger.info(f'Method name: {method.__name__} {kwargs}')
            result = method(*args, **kwargs)
            time_end = time.time()
            date_time_end = datetime.datetime.now().strftime(datetime_format)
            total_time = time_end - time_start
            total_time_str = f'Total time: {round(total_time, 2)} sec'
            logger.warn(f'Method name: {method.__name__} , End time: {date_time_end} , {total_time_str}')
        except Exception as err:
            time_end = time.time()
            total_time = time_end - time_start
            date_time_end = datetime.datetime.now().strftime(datetime_format)
            logger.error(f'Method name: {method.__name__} , End time with errors: {date_time_end} , Total time: {round(total_time, 2)} sec')
            raise err  # Exception(method.__name__, err)

        return result
    return method_wrapper
