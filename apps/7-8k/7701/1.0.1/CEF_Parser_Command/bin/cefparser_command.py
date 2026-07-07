import import_utils
import sys
import re
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option


@Configuration()
class CEFParserCommand(StreamingCommand):

    field = Option(name="field", require=False, default="_raw")

    def stream(self, records):
        try:
            for record in records:
                field_value = record.get(self.field, [])

                if field_value:
                    new_fields = self.parse(field_value)
                    if new_fields:
                        record.update(new_fields)

                yield record

        except Exception as err:
            msg = "Error occurred in CEFParserCommand command: {}".format(err)
            self.write_error(msg)


    def parse(self, str_input):
        """
        Parse a string in CEF format and return a dict with the header values
        and the extension data.
        """

        # Create the empty dict we'll return later
        values = dict()

        # This regex separates the string into the CEF header and the extension
        # data.  Once we do this, it's easier to use other regexes to parse each
        # part.
        header_re = r'((CEF:\d+)([^=\\]+\|){,7})(.*)'

        res = re.search(header_re, str_input)

        if res:
            header = res.group(1)
            extension = res.group(4)

            # Split the header on the "|" char.  Uses a negative lookbehind
            # assertion to ensure we don't accidentally split on escaped chars,
            # though.
            spl = re.split(r'(?<!\\)\|', header)

            # If the input entry had any blanks in the required headers, that's wrong
            # and we should return.  Note we explicitly don't check the last item in the 
            # split list because the header ends in a '|' which means the last item
            # will always be an empty string (it doesn't exist, but the delimiter does).
            if "" in spl[0:-1]:
                # logger.warning(f'Blank field(s) in CEF header. Is it valid CEF format?')
                return None

            # Since these values are set by their position in the header, it's
            # easy to know which is which.
            values["DeviceVendor"] = spl[1]
            values["DeviceProduct"] = spl[2]
            values["DeviceVersion"] = spl[3]
            values["DeviceEventClassID"] = spl[4]
            values["Name"] = spl[5]
            values["DeviceName"] = spl[5]
            if len(spl) > 6:
                values["Severity"] = spl[6]
                values["DeviceSeverity"] = spl[6]

            # The first value is actually the CEF version, formatted like
            # "CEF:#".  Ignore anything before that (like a date from a syslog message).
            # We then split on the colon and use the second value as the
            # version number.
            cef_start = spl[0].find('CEF')
            if cef_start == -1:
                return None
            (cef, version) = spl[0][cef_start:].split(':')
            values["CEFVersion"] = version

            # The ugly, gnarly regex here finds a single key=value pair,
            # taking into account multiple whitespaces, escaped '=' and '|'
            # chars.  It returns an iterator of tuples.
            spl = re.findall(r'([^=\s]+)=((?:[\\]=|[^=])+)(?:\s|$)', extension)
            for i in spl:
                # Split the tuples and put them into the dictionary
                values[i[0]] = i[1]

            # Process custom field labels
            for key in list(values.keys()):
                # If the key string ends with Label, replace it in the appropriate
                # custom field
                if key[-5:] == "Label":
                    customlabel = key[:-5]
                    # Find the corresponding customfield and replace with the label
                    for customfield in list(values.keys()):
                        if customfield == customlabel:
                            values[values[key]] = values[customfield]
                            del values[customfield]
                            del values[key]
        else:
            # return None if our regex had no output
            # logger.warning('Could not parse record. Is it valid CEF format?')
            return None

        return values


if __name__ == "__main__":
    dispatch(CEFParserCommand, sys.argv, sys.stdin, sys.stdout, __name__)
