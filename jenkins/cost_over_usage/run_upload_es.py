
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
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
special_user_mails = os.environ['CLOUD_GOVERNANCE_SPECIAL_USER_MAILS']
IGNORE_MAILS = os.environ['IGNORE_MAILS']


es_index_perf = 'cloud-governance-cost-explorer-perf'
es_index_psap = 'cloud-governance-cost-explorer-psap'
es_index_perf_scale = 'cloud-governance-cost-explorer-perf-scale'

os.system(f"""podman run --rm --name cloud-governance --net=host -e account='perf-dept' -e policy=cost_over_usage -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_DELETE_PERF} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_DELETE_PERF} -e es_host={ES_HOST} -e es_port={ES_PORT} -e es_index={es_index_perf}-user -e LDAP_HOST_NAME={LDAP_HOST_NAME} -e special_user_mails={special_user_mails} -e IGNORE_MAILS={IGNORE_MAILS} -e log_level=INFO quay.io/ebattat/cloud-governance:latest""")
os.system(f"""podman run --rm --name cloud-governance --net=host -e account='psap' -e policy=cost_over_usage -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_DELETE_PSAP} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_DELETE_PSAP} -e es_host={ES_HOST} -e es_port={ES_PORT} -e es_index={es_index_psap}-user -e LDAP_HOST_NAME={LDAP_HOST_NAME} -e special_user_mails={special_user_mails} -e IGNORE_MAILS={IGNORE_MAILS} -e log_level=INFO quay.io/ebattat/cloud-governance:latest""")
os.system(f"""podman run --rm --name cloud-governance --net=host -e account='perf-scale' -e policy=cost_over_usage -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE} -e es_host={ES_HOST} -e es_port={ES_PORT} -e es_index={es_index_perf_scale}-user -e LDAP_HOST_NAME={LDAP_HOST_NAME} -e special_user_mails={special_user_mails} -e IGNORE_MAILS={IGNORE_MAILS} -e log_level=INFO quay.io/ebattat/cloud-governance:latest""")
