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
COST_SPREADSHEET_ID = os.environ['COST_SPREADSHEET_ID']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']

es_index_perf = 'cloud-governance-cost-explorer-perf'
es_index_psap = 'cloud-governance-cost-explorer-psap'
es_index_perf_scale = 'cloud-governance-cost-explorer-perf-scale'
es_index_global = 'cloud-governance-cost-explorer-global'
cost_tags = ['PurchaseType', 'ChargeType', 'User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name',
             'Email', 'Environment', 'User:Spot', 'TicketId', 'architecture']

# Cost Explorer upload to ElasticSearch
cost_metric = 'UnblendedCost'  # UnblendedCost/BlendedCost
granularity = 'DAILY'  # DAILY/MONTHLY/HOURLY
os.system(
    f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-dept" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_perf}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(
    f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="psap" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_psap}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(
    f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-scale" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index={es_index_perf_scale} -e cost_explorer_tags="{cost_tags}" -e granularity={granularity} -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")

# @Todo, remove if cost explorer working properly

# os.system(f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-dept" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
# os.system(f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="psap" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
# os.system(f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-scale" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")

es_index_global = 'cloud-governance-cost-explorer-perf-global-cost'
os.system(
    f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-dept" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(
    f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="psap" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
os.system(
    f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-scale" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")

input_vars_to_container = [{'account': 'perf-dept', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF},
                           {'account': 'perf-scale', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE},
                           {'account': 'psap', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PSAP,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PSAP}]

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': 'cloud-governance-global-cost-billing-reports',
                     'log_level': 'INFO', 'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS}
combine_vars = lambda item: f'{item[0]}="{item[1]}"'
common_envs = list(map(combine_vars, common_input_vars.items()))
for input_vars in input_vars_to_container:
    envs = list(map(combine_vars, input_vars.items()))
    os.system(
        f"""podman run --rm --name cloud-governance -e policy="cost_billing_reports" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" quay.io/ebattat/cloud-governance:latest""")
