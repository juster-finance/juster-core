import json


class Container:
    """ Abstract container that allows to easy experiment with different variables
        that can be saved in data storage """

    name = 'Container'

    def __init__(self, **kwargs):

        self.attributes = list(kwargs.keys())
        for k, v in kwargs.items():
            copied_v = v.copy() if hasattr(v, 'copy') else v
            setattr(self, k, v)

    def to_dict(self):
        dct = {k: getattr(self, k) for k in self.attributes}
        return {
            k: v.to_dict() if hasattr(v, 'to_dict') else v
            for k, v in dct.items()}

    def __repr__(self):
        return (f'<{self.name}>\n{json.dumps(self.to_dict(), indent=4)}')

