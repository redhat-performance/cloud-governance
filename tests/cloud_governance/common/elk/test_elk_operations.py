from cloud_governance.common.elk.elk_operations import ElkOperations


def test_get_s3_latest_policy_file():
    elk_operations = ElkOperations(region='us-east-1')
    assert elk_operations._ElkOperations__get_s3_latest_policy_file(policy='ec2-idle')


def test_get_last_s3_policy_content():
    elk_operations = ElkOperations(region='us-east-1')
    assert elk_operations._ElkOperations__get_last_s3_policy_content(policy='ec2-idle')


# def test_upload_last_policy_to_es():
#     regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
#     policies = ['ec2_idle', 'ebs_unattached', 'ec2_untag']
#     region = 'us-east-2'
#     for policy in policies:
#         print(policy)
#         elk_operations = ElkOperations(region=region)
#         index = 'json_ec2_timestamp_index'
#         doc_type = 'json_doc_type'
#         add_items = {'policy': policy, 'region': region}
#         assert elk_operations.upload_last_policy_to_es(policy=policy, index=index, doc_type=doc_type,
#                                                        add_items=add_items)