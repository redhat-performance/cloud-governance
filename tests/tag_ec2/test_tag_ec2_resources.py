
from cloud_governance.tag_ec2.tag_ec2_resources import TagEc2Resources


def test_update_update_ec2():
    header = {'content-type': 'application/json'}
    update_tags = TagEc2Resources(region='us-east-2')
    response = update_tags.update_ec2(headers=header, data={'Name': "@@@@####@@@@"})
    assert response is not None