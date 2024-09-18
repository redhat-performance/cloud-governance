import os

AWS_ACCESS_KEY_ID_APPENG = os.environ['AWS_ACCESS_KEY_ID_APPENG']
AWS_SECRET_ACCESS_KEY_APPENG = os.environ['AWS_SECRET_ACCESS_KEY_APPENG']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
BUCKET_APPENG = os.environ['BUCKET_APPENG']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
LOGS = os.environ.get('LOGS', 'logs')


def get_policies(type: str = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of policies name
    """
    policies = []
    policies_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
        'cloud_governance', 'policy', 'aws')
    for (dirpath, dirnames, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not filename.startswith('__') and (filename.endswith('.yml') or filename.endswith('.py')):
                if not type:
                    policies.append(os.path.splitext(filename)[0])
                elif type and type in filename:
                    policies.append(os.path.splitext(filename)[0])
    return policies


regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-central-1', 'ap-south-1', 'eu-north-1',
           'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-3', 'sa-east-1']

os.system('echo "Upload data to ElasticSearch - ec2 index"')

es_index = 'cloud-governance-appeng-ec2-index'
es_doc_type = '_doc'
for region in regions:
    for policy_types in ['ec2', 'zombie', 'ebs', 'empty_roles', 's3', 'ip', 'nat_gateway_unused']:
        policies = get_policies(type=policy_types)
        for policy in policies:
            if policy in ('empty_roles', 's3_inactive'):
                if region == 'us-east-1':
                    os.system(
                        f"""podman run --rm --name cloud-governance-poc-haim -e upload_data_es="upload_data_es" -e account="APPENG" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_APPENG}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_APPENG}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_APPENG}" -e log_level="INFO" quay.io/cloud-governance/cloud-governance:latest""")
            else:
                os.system(
                    f"""podman run --rm --name cloud-governance-poc-haim -e upload_data_es="upload_data_es" -e account="APPENG" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_APPENG}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_APPENG}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_APPENG}" -e log_level="INFO" quay.io/cloud-governance/cloud-governance:latest""")
