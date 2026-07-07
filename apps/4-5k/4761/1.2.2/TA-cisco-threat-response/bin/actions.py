from abc import ABCMeta, abstractmethod
from collections import defaultdict

import six
import json

from pipe import Pipe, CachedPipe
from constants import OBSERVABLE_TYPES_IDENTIFIERS


class Action(six.with_metaclass(ABCMeta, object)):
    """ Base class for the Threat Response actions. """

    def __init__(self, observable_field):
        self._observable_field = observable_field

    def is_applicable_to(self, record):
        return self._observable_field in record

    @abstractmethod
    def update(self, record):
        pass


class Verdict(Action):
    """ Provides a verdict for an observable in a Splunk record. """

    def __init__(self, tr, observable_field):
        super(Verdict, self).__init__(observable_field)

        self._deliberate = CachedPipe(
            Pipe(
                lambda observable: {'content': observable},
                tr.inspect.inspect,
                tr.enrich.deliberate.observables,
            )
        )

    def update(self, record):
        observable = record[self._observable_field]
        result = self._deliberate(observable)

        docs = [doc
                for data in result['data']
                for doc in data.get('data', {})
                               .get('verdicts', {})
                               .get('docs', [])]

        def add(field, value):
            key = 'cisco:tr:deliberate:{}:{}'.format(
                self._observable_field,
                field
            )

            record[key] = value

        add('module', [data['module'] for data in result['data']])
        add('observable', [doc['observable']['value'] for doc in docs])
        add('disposition', [doc['disposition_name'] for doc in docs])
        add(
            'valid_time_start',
            [doc['valid_time'].get('start_time', '') for doc in docs]
        )
        add(
            'valid_time_end',
            [doc['valid_time'].get('end_time', '') for doc in docs])

        result.update({'command': 'verdict'})
        return json.dumps(result)


class Context(Action):
    """ Contextualizes an observable in a Splunk record. """

    def __init__(self, tr, observable_field, objects):
        super(Context, self).__init__(observable_field)

        self._observe = CachedPipe(
            Pipe(
                lambda observable: {'content': observable},
                tr.inspect.inspect,
                tr.enrich.observe.observables,
            )
        )

        # Should contain items like 'tools', 'indicators', 'judgements' etc.
        self._objects = objects

    def update(self, record):
        observable = record[self._observable_field]
        result = self._observe(observable)

        def add(field, value):
            key = 'cisco:tr:observe:{}:{}'.format(
                self._observable_field,
                field
            )

            record[key] = value

        add('module', [data['module'] for data in result['data']])

        for obj in self._objects:
            add(
                obj,
                [
                    data['data'][obj]
                    for data
                    in result['data'] if obj in data['data']
                ]
            )

        result.update({'command': 'context'})
        return json.dumps(result)


class Targets(Action):
    """ Provides sightings' targets for an observable in a Splunk record. """

    def __init__(self, tr, observable_field):
        super(Targets, self).__init__(observable_field)

        self._observe = CachedPipe(
            Pipe(
                lambda observable: {'content': observable},
                tr.inspect.inspect,
                tr.enrich.observe.observables,
            )
        )

    def update(self, record):
        observable = record[self._observable_field]
        result = self._observe(observable)

        docs = [doc
                for data in result['data']
                for doc in data.get('data', {})
                               .get('sightings', {})
                               .get('docs', [])]

        targets = [target
                   for doc in docs
                   for target in doc.get('targets', [])]

        observables_dict = defaultdict(set)

        for target in targets:
            for observable in target['observables']:
                observables_dict[observable['type']].update(
                    {observable['value']}
                    )

        types = OBSERVABLE_TYPES_IDENTIFIERS

        def add(field, value):
            key = 'cisco:tr:observe:{}:{}'.format(
                self._observable_field,
                field
            )

            record[key] = value

        add('module', [data['module'] for data in result['data']])

        for type_ in types:
            add(
                'target:{}'.format(type_),
                list(observables_dict.get(type_, []))
            )
        add('type', list({target['type'] for target in targets}))

        # optional parameter
        os = list({target['os'] for target in targets if target.get('os')})
        if os:
            add('os', os)

        result.update({'command': 'targets'})
        return json.dumps(result)
