# Parsing of json response and validation of userinputs are done using these fucntions.


class Data_Parsing:

    # Flattening of json response for parsing the data and breaking the nested json objects.
    def flatten_data(raw_data):

        out = {}

        def flatten(parse_data, name=""):
            if type(parse_data) is dict:
                for a in parse_data:
                    flatten(parse_data[a], name + a + "_")
            else:
                out[name[:-1]] = parse_data

        flatten(raw_data)
        return out

    def protect_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
            ("Verdict", "verdict", str),
            ("Reasons", "reasons", list),
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result
