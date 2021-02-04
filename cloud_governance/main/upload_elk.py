
from cloud_governance.common.elk.elk_operations import ElkOperations

regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
policies = ['ec2_idle', 'ebs_unattached', 'ec2_untag']


def upload_elk(regions: list, policies:list):
    """
    This method upload data to local ELK
    @param regions:
    @param policies:
    """
    for region in regions:
        for policy in policies:
            print(policy)
            elk_operations = ElkOperations(region=region)
            index = 'json_ec2_timestamp_index'
            doc_type = 'json_doc_type'
            add_items = {'policy': policy, 'region': region}
            assert elk_operations.upload_last_policy_to_es(policy=policy, region=region, index=index, doc_type=doc_type,
                                                           add_items=add_items)


upload_elk(regions= regions, policies= policies)