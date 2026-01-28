import datetime
import json
import os
from unittest.mock import MagicMock, patch

from cloud_governance.common.clouds.aws.price.price import AWSPrice


def _make_price_list_response(usd_price: str = "0.05"):
    """Build a PriceList response that AWSPrice.get_price() knows how to parse."""
    return {
        "PriceList": [
            json.dumps({
                "terms": {
                    "OnDemand": {
                        "offer-id": {
                            "priceDimensions": {
                                "dim-id": {"pricePerUnit": {"USD": usd_price}}
                            }
                        }
                    }
                }
            })
        ]
    }


@patch("cloud_governance.common.clouds.aws.price.price.get_boto3_client")
def test_price(mock_get_boto3_client):
    mock_client = MagicMock()
    mock_client.get_products.return_value = _make_price_list_response("0.192")
    mock_get_boto3_client.return_value = mock_client

    __aws_price = AWSPrice()
    ec2_type_cost = __aws_price.get_price(
        region=__aws_price.get_region_name("us-east-1"),
        instance="m5.xlarge",
        os="Linux",
    )
    assert ec2_type_cost


@patch("cloud_governance.common.clouds.aws.price.price.get_boto3_client")
def test_ebs_price(mock_get_boto3_client):
    os.environ["AWS_DEFAULT_REGION"] = "us-east-2"
    mock_client = MagicMock()
    mock_client.get_products.return_value = _make_price_list_response("0.10")
    mock_get_boto3_client.return_value = mock_client

    __aws_price = AWSPrice()
    ec2_type_cost = __aws_price.get_ec2_price(
        resource="ebs", item_data={"VolumeType": "gp2", "Size": 10}
    )
    assert ec2_type_cost


@patch("cloud_governance.common.clouds.aws.price.price.get_boto3_client")
def test_ec2_price(mock_get_boto3_client):
    os.environ["AWS_DEFAULT_REGION"] = "us-east-2"
    mock_client = MagicMock()
    mock_client.get_products.return_value = _make_price_list_response("0.0116")
    mock_get_boto3_client.return_value = mock_client

    __aws_price = AWSPrice()
    item_data = {
        "InstanceType": "t2.micro",
        "LaunchTime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "State": {"Name": "running"},
    }
    ec2_type_cost = __aws_price.get_ec2_price(resource="ec2", item_data=item_data)
    assert ec2_type_cost >= 0
