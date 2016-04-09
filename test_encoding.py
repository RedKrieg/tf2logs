import json

class Thing:
    def __init__(self, name, *things):
        self.name = name
        self.things = things

    def repr_json(self):
        return {"name": self.name, "things": self.things}

    @classmethod
    def from_json(cls, data):
        return cls(data["name"], *data["things"])

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
        return super().default(o)
    def __init__(self, *args, **kwargs):
        self.encoded = {}
        return super().__init__(*args, **kwargs)

class Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        self.decoded = {}
        self.known_classes = {
            "Thing": Thing
        }
        return super().__init__(*args, object_hook=self.dict_to_obj, **kwargs)

    def dict_to_obj(self, d):
        if '__backref__' in d:
            return self.decoded[d['__backref__']]
        if '__class__' not in d:
            return d
        _class = self.known_classes[d.pop('__class__')]
        _id = d.pop('__id__')
        result = _class.from_json(d)
        self.decoded[_id] = result
        return result
