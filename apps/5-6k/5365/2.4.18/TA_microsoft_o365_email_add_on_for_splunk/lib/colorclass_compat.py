import re


COLOR_TAG_RE = re.compile(r"\{/?[a-zA-Z_][a-zA-Z0-9_]*\}")


def _strip_color_tags(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return COLOR_TAG_RE.sub("", str(value))


class Color(str):
    def __new__(cls, value):
        return str.__new__(cls, _strip_color_tags(value))


class Windows:
    @staticmethod
    def enable(*args, **kwargs):
        return None
