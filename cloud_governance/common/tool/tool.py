import os


def is_empty_file(file_path):
    """
    This method check for empty file and raise as exception
    @param file_path:
    @return:
    """
    if os.stat(file_path).st_size == 0:
        raise Exception(f'File is empty: {file_path}')


def get_policies(file_type: str = '.py', exclude_policies: list = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of custodian policies name
    """
    exclude_policies = [] if not exclude_policies else exclude_policies
    custodian_policies = []
    root_folder = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    policies_path = os.path.join(root_folder, 'policy', 'aws')
    for (_, _, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not filename.startswith('__') and filename.endswith(file_type):
                if filename.split('.')[0] not in exclude_policies:
                    if not file_type:
                        custodian_policies.append(os.path.splitext(filename)[0])
                    elif file_type and file_type in filename:
                        custodian_policies.append(os.path.splitext(filename)[0])
    return custodian_policies
