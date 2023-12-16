import json
import datetime


class JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            # Serialize datetime objects to ISO 8601 format
            return obj.isoformat()
        return super(JsonDateTimeEncoder, self).default(obj)
