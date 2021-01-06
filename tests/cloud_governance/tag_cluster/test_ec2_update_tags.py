
from cloud_governance.tag_cluster.ec2_update_tags import UpdateEc2Tags


def test_update_update_ec2():
    header = {'content-type': 'application/json'}
    update_tags = UpdateEc2Tags(region='us-east-2')
    response = update_tags.update_ec2(headers=header, data={'Name': "@@@@####@@@@"})
    assert response is not None
