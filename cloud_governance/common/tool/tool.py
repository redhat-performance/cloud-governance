import os


def is_empty_file(file_path):
    """
    This method check for empty file and raise as exception
    @param file_path:
    @return:
    """
    if os.stat(file_path).st_size == 0:
        raise Exception(f'File is empty: {file_path}')
