def n_f_a(data):
    if data.isdigit():
        return data
    return ''.join(chr((ord(char) + 3) % 256) for char in data)

def n_f_b(data):
    return ''.join(chr((ord(char) - 3) % 256) for char in data)
