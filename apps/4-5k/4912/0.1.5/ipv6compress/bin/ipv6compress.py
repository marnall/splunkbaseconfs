import sys, os

from IPy import IP

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class Ipv6CompressCommand(StreamingCommand):
    """ Compresses or expands an IPv6 address.

    ##Syntax

    .. code-block::
        ipv6compress [output=<field>] [action=(compress|expand)] <field>

    ##Description

    The :code:`ipv6compress` command takes in records from the event stream and for IPv6 
    addresses that exist will either compress, by default, or expand them depending on 
    the desired :code:`action`.  If the field value of a record is not an IPv6 address, 
    the record is returned unmodified.  

    ##Example

    Compress the value of an IPv6 address from the field `src_ip` and output
    the result into the field `src_ip_compressed`.

    .. code-block::
        | ipv6compress output=src_ip_compressed src_ip

    """
    action = Option(
        doc='''
        **Syntax:** **action=***compress|expand*
        **Description:** The action to take on the provided IPv6 address''',
        require=False, default="compress", validate=validators.Set("compress", "expand"))

    output = Option(
        doc='''
        **Syntax:** **output=***<fieldname>*
        **Description:** Name of field that will hold the resulting IPv6 address''',
        require=False, validate=validators.Fieldname())

    def stream(self, records):
        self.logger.debug('Ipv6CompressCommand: %s', self)  # logs command line

        if self.action == "expand":
            fct = "strFullsize"
        else:
            fct = "strCompressed"

        if not len(self.fieldnames) == 1:
            raise ValueError("Error in '{}' command. Only one field argument can be " \
                             "passed to this command.".format(self.name))
        else:
            field = self.fieldnames[0]

        # If the output option is not set, overwrite the existing values of the provided field
        if self.output:
            field_out = self.output
        else:
            field_out = field

        for record in records:
            if field in record:
                try:
                    ip_obj = IP(record[field])
                    ip_str = getattr(ip_obj, fct)()
                except ValueError as e:
                    # store whatever value is already in the field if it isn't a valid IP
                    ip_str = record[field]

                record[field_out] = ip_str

            yield record

dispatch(Ipv6CompressCommand, sys.argv, sys.stdin, sys.stdout, __name__)
