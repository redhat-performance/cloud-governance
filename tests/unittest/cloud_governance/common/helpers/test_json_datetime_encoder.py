import datetime
import json

from cloud_governance.common.helpers.json_datetime_encoder import JsonDateTimeEncoder


def test_json_datetime_encoder():
    current_date = datetime.datetime.now()
    data_list = [current_date, "Unittest"]
    json_data = json.dumps(data_list, cls=JsonDateTimeEncoder)
    assert json_data == json.dumps([str(current_date.isoformat()), "Unittest"])
