def signum(n):
    if n < 0:
        return -1
    
    if n > 0:
        return 1
    
    return 0

def is_int(value: str):
    try:
        int(value)
        return True
    except ValueError:
        return False

def is_float(value: str):
    try:
        float(value)
        return True
    except ValueError:
        return False

def is_number(value: str):
    return is_int(value) or is_float(value)
