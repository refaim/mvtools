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
