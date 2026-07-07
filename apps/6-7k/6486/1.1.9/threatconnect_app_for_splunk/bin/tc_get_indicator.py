#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import datetime
import json
import os
import sys
import time

# third-party
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Boolean, Configuration, Option, dispatch


@Configuration(retainsevents=True, streaming=False)
class IndicatorDownloadCommand(BaseGeneratingCommand):
    """Command to download and indicator from ThreatConnect API.

    Usage:
    | tcindicator <indicator>
    """

    # args
    _command = 'tcindicator'
    indicator = Option(doc='The indicator to retrieve.', require=True)
    extract = Option(doc='The fields to extract.', require=False, default=None)
    preserveContext = Option(
        doc='Preserve the context of the indicator.',
        require=False,
        default=False,
        validate=Boolean(),
    )

    pretty = Option(
        doc='Pretty print the output.', require=False, default=False, validate=Boolean()
    )

    # properties
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve owner data from ThreatConnect
        indicators = list(self.retrieve_indicator(self.indicator, cache=not self.extract))
        ids = {i.get('id') for i in indicators}

        unique_indicators = []
        for id_ in ids:
            unique_indicators.append(next(filter(lambda x: x.get('id') == id_, indicators)))

        for indicator in unique_indicators:
            indicator = indicator if not self.pretty else self.prettify_data(indicator)
            if self.extract:
                extracted = indicator.get(self.extract)
                if not extracted:
                    return  # nothing to extract
                if not isinstance(extracted, list):
                    extracted = [extracted]
                if self.preserveContext:
                    yield from [
                        {
                            '_time': time.time(),
                            '_raw': {**indicator, 'extracted': e},
                        }
                        for e in extracted
                    ]
                else:
                    yield from [
                        {
                            '_time': time.time(),
                            '_raw': e,
                        }
                        for e in extracted
                    ]
            else:
                yield {
                    '_time': time.time(),
                    '_raw': indicator,
                }

    def prettify_data(self, data):
        """Prettify the indicator output."""
        if isinstance(data, list):
            return [self.prettify_data(d) for d in data]
        elif isinstance(data, dict):
            # get rid of 'data' key
            if 'data' in data:
                data = data['data']
                return self.prettify_data(data)
            pretty_data = {}
            for key, value in data.items():
                pretty_data[self._normalize_key(key)] = self.prettify_data(value)
            return pretty_data
        else:
            return data

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    def retrieve_indicator(self, indicator, cache=True):
        """Load Owner Data"""
        cached = list(
            filter(
                lambda i: indicator == i,
                self.tcs.collections.ioc_cache.query(),
            )
        )
        if cached:
            # check for old data, and bust cache if any data is too old
            for i in cached:
                if (
                    float(i.get('cached_at'))
                    < (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).timestamp()
                ):
                    break
            else:
                self.tc_logger.info(f'Cache hit for {indicator}.')
                yield from [json.loads(i.data) for i in cached]
                return

            for i in cached:
                self.tc_logger.info(f'Cache miss for {indicator} due to time-out.')
                self.tcs.collections.ioc_cache.delete(f'{{"indicator": "{i.indicator}"}}')
                break

        self.tc_logger.info(f'downloading for {indicator}')
        yield from self._download_indicator(indicator, cache=cache)

    def _download_indicator(self, indicator, cache=True):
        now = datetime.datetime.utcnow().timestamp()
        fields = list(self.tcs.request.indicator_fields_data.keys())

        for i in self.tcs.request.get_indicator(indicator, {'fields': fields}):
            if cache:
                self.tcs.collections.ioc_cache.insert(
                    {'cached_at': now, 'indicator': indicator, 'data': json.dumps(i)}
                )
            yield i

    def _normalize_key(self, key):
        manual_conversions = {
            'Id': 'ID',
            'Ip': 'IP',
            'Owner Id': 'Owner ID',
            'sha256': 'SHA-256',
            'sha1': 'SHA-1',
            'md5': 'MD5',
        }
        normalized_key = ''.join([c if c.islower() else f' {c}' for c in key]).title()
        normalized_key_parts = normalized_key.split(' ')
        normalized_key_parts = [manual_conversions.get(p, p) for p in normalized_key_parts]
        return ' '.join(normalized_key_parts)


if __name__ == '__main__':
    try:
        dispatch(IndicatorDownloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
