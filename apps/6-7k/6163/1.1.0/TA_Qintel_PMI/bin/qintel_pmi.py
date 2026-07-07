import sys
import app_qintel_pmi_declare
from utils import get_config_item, setup_logging, regex_match
from constants import ENRICHMENT_ERROR, RE_CVE
from qintel_pmi_cve import QintelCVE
import ipaddress

from splunklib.searchcommands import \
    dispatch, EventingCommand, Configuration, Option, validators

SEARCH_MAP = {
    'cve_field': {'field': 'cve_field', 'regex': RE_CVE, 'client': QintelCVE},
}


@Configuration()
class QintelPMICommand(EventingCommand):

    cve_field = Option(
        doc='''**Syntax:** **cve_field=***<cve field>*
         **Description:** CVE field to search in QIntel''',
        name='cve_field', require=False, default=False
    )

    def __init__(self):
        super(QintelPMICommand, self).__init__()

    def _get_search_map(self):

        if self.cve_field:
            return SEARCH_MAP['cve_field']

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


dispatch(QintelPMICommand, sys.argv, sys.stdin, sys.stdout, __name__)
