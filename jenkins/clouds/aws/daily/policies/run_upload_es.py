
import os

AWS_ACCESS_KEY_ID_PERF = os.environ['AWS_ACCESS_KEY_ID_PERF']
AWS_SECRET_ACCESS_KEY_PERF = os.environ['AWS_SECRET_ACCESS_KEY_PERF']
AWS_ACCESS_KEY_ID_DELETE_PERF = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF']
AWS_SECRET_ACCESS_KEY_DELETE_PERF = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF']
AWS_ACCESS_KEY_ID_DELETE_PSAP = os.environ['AWS_ACCESS_KEY_ID_DELETE_PSAP']
AWS_SECRET_ACCESS_KEY_DELETE_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PSAP']
BUCKET_PERF = os.environ['BUCKET_PERF']
AWS_ACCESS_KEY_ID_PSAP = os.environ['AWS_ACCESS_KEY_ID_PSAP']
AWS_SECRET_ACCESS_KEY_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_PSAP']
BUCKET_PSAP = os.environ['BUCKET_PSAP']
AWS_ACCESS_KEY_ID_RH_PERF = os.environ['AWS_ACCESS_KEY_ID_RH_PERF']
AWS_SECRET_ACCESS_KEY_RH_PERF = os.environ['AWS_SECRET_ACCESS_KEY_RH_PERF']
BUCKET_RH_PERF = os.environ['BUCKET_RH_PERF']
AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE']
AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE']
BUCKET_PERF_SCALE = os.environ['BUCKET_PERF_SCALE']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']


def get_policies(type: str = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of policies name
    """
    policies = []
    policies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))), 'cloud_governance', 'policy', 'aws')
    for (dirpath, dirnames, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not filename.startswith('__') and (filename.endswith('.yml') or filename.endswith('.py')):
                if not type:
                    policies.append(os.path.splitext(filename)[0])
                elif type and type in filename:
                    policies.append(os.path.splitext(filename)[0])
    return policies


regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'ap-south-1', 'eu-north-1', 'eu-west-3', 'eu-west-2', 'eu-west-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-northeast-1', 'ca-central-1', 'sa-east-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-central-1']

print("Upload data to ElasticSearch - ec2 index")
policies = get_policies(type='ec2')
es_index = 'cloud-governance-ec2-index'
es_doc_type = '_doc'
for region in regions:
    for policy in policies:
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-DEPT" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PERF}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PSAP" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PSAP}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PSAP}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-SCALE" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF_SCALE}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e log_level=INFO quay.io/ebattat/cloud-governance:latest""")


print("Upload data to ElasticSearch - ebs index")
es_index = 'cloud-governance-ebs-index'
es_doc_type = '_doc'
policies = get_policies(type='ebs')
for region in regions:
    for policy in policies:
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-DEPT" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PERF}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PSAP" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PSAP}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PSAP}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-SCALE" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF_SCALE}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")


print("Upload data to ElasticSearch - zombie index")
es_index = 'cloud-governance-zombie-index'
es_doc_type = '_doc'
policies = get_policies(type='zombie')
for region in regions:
    for policy in policies:
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-DEPT" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PERF}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PSAP" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PSAP}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PSAP}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-SCALE" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF_SCALE}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")


print("Upload data to ElasticSearch - empty index")
es_index = 'cloud-governance-zombie-empty-index'
es_doc_type = '_doc'
region = 'us-east-1'
policies = get_policies(type='empty')
for policy in policies:
    os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-DEPT" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PERF}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
    os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PSAP" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PSAP}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PSAP}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
    os.system(f"""podman run --rm --name cloud-governance -e upload_data_es="upload_data_es" -e account="PERF-SCALE" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF_SCALE}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")

es_index_perf = 'cloud-governance-non-tag-users-perf-dept'
es_index_psap = 'cloud-governance-non-tag-users-psap'
es_index_perf_scale = 'cloud-governance-non-tag-users-perf-scale'
user_tags = ['Budget', 'User', 'Owner', 'Manager', 'Environment', 'Project']

# Validation of user tags
os.system(f"""podman run --rm --name cloud-governance -e account='perf-dept' -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_perf}" -e validate_type="tags" -e user_tags="{user_tags}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(f"""podman run --rm --name cloud-governance -e account='psap' -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_psap}" -e validate_type="tags" -e user_tags="{user_tags}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(f"""podman run --rm --name cloud-governance -e account='perf-scale' -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index={es_index_perf_scale} -e validate_type="tags" -e user_tags="{user_tags}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")

es_index_perf = 'cloud-governance-user-tag-with-space-perf'
es_index_psap = 'cloud-governance-user-tag-with-space-psap'
es_index_perf_scale = 'cloud-governance-user-tag-with-space-perf-scale'

# validation of trailing spaces
os.system(f"""podman run --rm --name cloud-governance -e account='perf-dept' -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_perf}" -e validate_type="spaces"  -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(f"""podman run --rm --name cloud-governance -e account='psap' -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_psap}" -e validate_type="spaces" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(f"""podman run --rm --name cloud-governance -e account='perf-scale' -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_perf_scale}" -e validate_type="spaces" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")


# Gitleaks run on github not related to any aws account
print("Upload data to ElasticSearch - gitleaks index")
es_index = 'cloud-governance-gitleaks'
es_doc_type = '_doc'
region = 'us-east-1'
policy = 'gitleaks'
os.system(f"""podman run --rm --name cloud-governance -e upload_data_es='upload_data_es' -e account='PERF-DEPT' -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index}" -e es_doc_type="{es_doc_type}" -e bucket="{BUCKET_PERF}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_PERF}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
