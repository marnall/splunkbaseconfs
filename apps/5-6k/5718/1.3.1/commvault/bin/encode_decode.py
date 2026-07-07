import base64

def encode_string(password):
    encoded_password = base64.b64encode(password.encode('ascii')).decode('ascii')
    n = len(encoded_password)
    first_half = ""
    for i in range(n//2):
        first_half += encoded_password[i]
    second_half = ""
    for i in range(n//2,n):
        second_half += encoded_password[i]
    return second_half + first_half

def decode_string(encoded_password):
    n = len(encoded_password)
    first_half = ""
    for i in range(n//2):
        first_half += encoded_password[i]
    second_half = ""
    for i in range(n//2,n):
        second_half += encoded_password[i]
    password = second_half + first_half
    password_decoded = base64.b64decode(password.encode('ascii')).decode('ascii')
    return password_decoded

"""
s = encode_string("shashank")
print(s)
print(decode_string(s))
"""
