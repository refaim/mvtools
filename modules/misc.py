import random
import string

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
