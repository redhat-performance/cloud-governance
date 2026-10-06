from cloud_governance.common.elasticsearch.modals.policy_es_data import PolicyEsMetaData


def _base_kwargs(**overrides):
    kwargs = {
        'account': 'unittest-account',
        'resource_id': 'i-123',
        'user': 'jdoe',
        'skip_policy': 'NA',
        'dry_run': 'yes',
        'name': 'test-resource',
        'region_name': 'us-east-1',
        'public_cloud': 'AWS',
        'expire_days': 7,
    }
    kwargs.update(overrides)
    return kwargs


def test_email_is_carried_into_the_es_document():
    """
    This method tests the Email tag value reaches the ES document, so send_aggregated_alerts
    can route the digest without re-querying the cloud for the resource's tags.
    """
    policy_es_data = PolicyEsMetaData(**_base_kwargs(email='team-dl@redhat.com'))
    resource_data = policy_es_data.get_as_dict_title_case()
    assert resource_data['Email'] == 'team-dl@redhat.com'
    assert resource_data['User'] == 'jdoe'


def test_email_is_omitted_when_not_set():
    """
    This method tests an untagged resource produces a document identical to today's -
    get_as_dict_title_case drops empty values, so no new key appears.
    """
    policy_es_data = PolicyEsMetaData(**_base_kwargs())
    resource_data = policy_es_data.get_as_dict_title_case()
    assert 'Email' not in resource_data
    assert resource_data['User'] == 'jdoe'


def test_email_is_a_defaulted_field_so_positional_construction_still_works():
    """
    This method tests that email was added to the defaulted block, not among the required
    fields - a non-defaulted field would silently shift every positional argument.
    """
    policy_es_data = PolicyEsMetaData('unittest-account', 'i-123', 'jdoe', 'NA', 'yes',
                                      'test-resource', 'us-east-1', 'AWS', 7)
    assert policy_es_data.user == 'jdoe'
    assert policy_es_data.email == ''
