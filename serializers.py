import datetime
import json
import parser
import timeseries

def datetime_repr_json(dt):
    return {
        "timestamp": dt.timestamp() * 1000
    }

def datetime_from_json(data):
    return datetime.datetime.fromtimestamp(data["timestamp"] / 1000)

class Encoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, 'repr_json'):
            if self.encoded.get(id(o), False):
                return {"__backref__": id(o)}
            self.encoded[id(o)] = True
            result = {
                '__class__': o.__class__.__name__,
                '__id__': id(o),
            }
            result.update(o.repr_json())
            return result
        if isinstance(o, datetime.datetime):
            result = {
                "__class__": "datetime",
                "__id__": id(o)
            }
            result.update(datetime_repr_json(o))
            return result
        return super().default(o)
    def __init__(self, *args, **kwargs):
        self.encoded = {}
        return super().__init__(*args, **kwargs)

class Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        self.decoded = {}
        self.known_classes = {
            "datetime": datetime.datetime,
            "SparseTimeSeries": timeseries.SparseTimeSeries,
            "World": parser.World,
            "Counter": parser.Counter,
            "Location": parser.Location,
            "User": parser.User
        }
        return super().__init__(*args, object_hook=self.dict_to_obj, **kwargs)

    def dict_to_obj(self, d):
        if '__backref__' in d:
            return self.decoded[d['__backref__']]
        if '__class__' not in d:
            return d
        _class = self.known_classes[d.pop('__class__')]
        _id = d.pop('__id__')
        if _class is datetime.datetime:
            result = datetime_from_json(d)
        else:
            result = _class.from_json(d)
        self.decoded[_id] = result
        return result
