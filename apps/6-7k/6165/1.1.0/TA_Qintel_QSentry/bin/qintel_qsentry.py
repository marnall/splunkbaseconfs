import sys
import app_qintel_qsentry_declare
from utils import get_config_item, setup_logging, regex_match
from constants import ENRICHMENT_ERROR, RE_IP
from qintel_qsentry_ip import QintelQSentryIP
import ipaddress

from splunklib.searchcommands import \
    dispatch, EventingCommand, Configuration, Option, validators

SEARCH_MAP = {
    'ip_field': {'field': 'ip_field', 'regex': RE_IP, 'client': QintelQSentryIP}
}


@Configuration()
class QSentryCommand(EventingCommand):
    
    ip_field = Option(
        doc='''**Syntax:** **ip_field=***<ipaddress field>*
        **Description:** IP field to search in Qintel QSentry''',
        name='ip_field', require=False, default=False
    )

    def __init__(self):
        super(QSentryCommand, self).__init__()

    def _get_search_map(self):

        if self.ip_field:
            return SEARCH_MAP['ip_field']

    def _extract_selectors(self, events):

        field = getattr(self, self.map['field'])

        for e in events:
            # regex match to filter bad data
            field_data = e.get(field)
            if field_data and regex_match(field_data, self.map['regex']):
                # filter reserved IPs
                if self.map['field'] == 'ip_field' \
                        and ipaddress.ip_address(field_data).is_private:
                    continue

                yield e[field]

    def _parse_events(self, events):

        selectors = set()

        for s in self._extract_selectors(events):
            selectors.add(s)

        return list(selectors)

    def transform(self, events):

        session_key = self._metadata.searchinfo.session_key
        logger = setup_logging(session_key)

        events = list(events)

        self.map = self._get_search_map()
        selectors = self._parse_events(events)

        if len(selectors) > 0 and self.map:

            field = getattr(self, self.map['field'])

            cli = self.map['client'](session_key, logger, field)

            try:
                events = cli.enrich(events, selectors)
            except Exception as e:
                logger.exception(f'enrichment error: {str(e)}')
                self.write_error(f'{ENRICHMENT_ERROR}. Message: {str(e)}')

        for e in events:
            yield e


dispatch(QSentryCommand, sys.argv, sys.stdin, sys.stdout, __name__)
