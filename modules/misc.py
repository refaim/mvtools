import random
import string
import enum

class MyEnum(enum.Enum):
    @staticmethod
    def auto():
        key = '_counter'
        counter = getattr(MyEnum, key, 0)
        counter += 1
        setattr(MyEnum, key, counter)
        return counter

    @classmethod
    def get_names(cls, subset=None):
        if subset is None:
            subset = cls
        return [definition.name.lower() for definition in subset]

    @classmethod
    def get_values(cls):
        return [definition.value for definition in cls]

    @classmethod
    def get_definition(cls, name):
        key = '_defs'
        if not hasattr(cls, key):
            setattr(cls, key, {definition.name.lower(): definition for definition in cls})
        return getattr(cls, key)[name.lower()]

def try_int(value):
    try:
        return int(value)
    except:
        return None

def safe_unsigned_max(sequence):
    result = -1
    for element in sequence:
        if element is None:
            return None
        result = max(result, element)
    if result < 0:
        result = None
    return result

def make_strings_dict(data):
    result = {}
    for key, values in data.iteritems():
        for s in values + [key]:
            result[s.lower()] = key
    return result

def random_printable(length):
    data = list(string.ascii_letters + string.digits)
    random.shuffle(data)
    return u''.join(random.sample(data, length))

def flip_dict(value):
    result = {v: k for k, v in value.iteritems()}
    assert len(value) == len(result)
    return result
