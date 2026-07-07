"""This files have the logic to parse Response."""
import ta_safebreach_declare  # noqa: F401

import six


def parse(response, mapping, output):
    """Parse the response and return a Key Value pair."""
    if (isinstance(mapping, dict)):
        for left, right in mapping.items():
            if isinstance(left, tuple):
                val = ""
                for name, prefix, suffix in left:
                    if response.get(name) is None:
                        continue
                    val += prefix + str(response.get(name, "")) + suffix
                output[right] = val
            elif isinstance(right, six.string_types):
                if response.get(left) is None:
                    continue
                output[right] = response.get(left, "")
            elif isinstance(right, list):
                if response.get(left) is None:
                    continue
                parse(response.get(left, []), right, output)
            elif isinstance(right, dict):
                parse(response.get(left, {}), right, output)

    elif isinstance(mapping, list):

        tmp = mapping[0]
        if isinstance(tmp, six.string_types):
            # Handle
            # - key: list of str
            output[tmp] = ", ".join(map(str, response))
        elif isinstance(tmp, dict):
            # Handle
            # - key: list of dict
            # - tuple: list of dict
            fields = {}
            for item in response:
                for left, right in tmp.items():
                    val = None
                    if isinstance(left, tuple):
                        val = ""
                        for name, prefix, suffix in left:
                            if item.get(name) is None:
                                continue
                            val += prefix + str(item.get(name, "")) + suffix
                    else:
                        if item.get(left) is None:
                            continue
                        val = item.get(left, "")
                    fields.setdefault(right, []).append(val)

            for key, val in fields.items():
                output[key] = ", ".join(map(str, val))
