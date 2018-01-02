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
        for string in values + [key]:
            result[string.lower()] = key
    return result
