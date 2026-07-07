import sys,ipaddress, re
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

@Configuration()

class ipv6_search(StreamingCommand):
    ip = Option(
        doc='''**Syntax:** **ipv6=***<ip_range>*
        **Description:** IP range you wish to search''',
        name='ipv6', require=True
    )
    field = Option(
        doc='''**Syntax:** **field=***<ipv6_field>*
        **Description:** Field with IPv6 Addresses''',
        name='field', require=True
    )
    def stream(self, records):
        # Check if is a valid ipv6 with regex
        ipv6re = re.compile("^[0-9a-fA-F\:]{4,45}\/\d{1,3}$")

        # Create ipv6 variable
        ip_range = self.ip
        # If the regex fails push an error message
        if not ipv6re.match(ip_range):
            error_msg = "Invalid ipv6 format of {}.".format(ip_range)
            raise ValueError(error_msg)

        # Specify the unicode IP Address
        unicode_iprange = u'{}'.format(ip_range)

        # Create field_name variable
        field_name = self.field

        # Check to see if the ipv6 network is valid
        is_valid = ipaddress.IPv6Network(unicode_iprange)
        # If it is valid
        if is_valid:
            # For each record
            for record in records:
                # Format the ipv6 address in unicode
                ipv6address = u'{}'.format(record[field_name])
                # If ipaddress from Splunk field is in ip range
                if ipaddress.ip_address(ipv6address) in ipaddress.IPv6Network(unicode_iprange):
                    # Export the results
                    yield record
        else:
            # Throw an error message that the range is invalid
            error_msg = "Invalid ipv6 range of {}.".format(ip_range)
            raise ValueError(error_msg)
        

if __name__ == "__main__":
    dispatch(ipv6_search, sys.argv, sys.stdin, sys.stdout, __name__)

