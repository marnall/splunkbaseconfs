from re import match


def is_url_secure(url):
    if match(r'^https://', url) is None:
        return ValueError("Insecure URL")

    return None


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """
    return "/".join(map(lambda x: str(x).rstrip('/'), args))


def drop_dict_keys(dictionary, *keys):
    _ = [dictionary.pop(key) for key in keys]

    return dictionary


def tranform_data(data, *funcs):
    input = data

    for func in funcs:
        input = func(input)

    return input
