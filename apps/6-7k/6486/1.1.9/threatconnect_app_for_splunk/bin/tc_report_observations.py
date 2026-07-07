#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import sys
import time
from collections import OrderedDict

# third-party
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, dispatch


@Configuration()
class ReportObservation(BaseGeneratingCommand):
    """Playbook download command.

    This command is run via a saved search.

    Usage:
    | tcobservations
    """

    # properties
    _command = 'tcobservations'
    execution_summary = {'count_success': 0, 'count_failure': 0, 'count_observations': 0}

    def add_result(self, indicator, indicator_type, observation_count, status):
        """Return ordered dict for results."""
        result_data = OrderedDict()
        result_data['Action'] = 'Report'
        result_data['Indicator'] = indicator
        result_data['Indicator Type'] = indicator_type
        result_data['Observation Count'] = observation_count
        result_data['Status'] = status
        self.results.append(result_data)

    def consolidate_observations(self):
        """Delete owners that have been removed from ThreatConnect"""
        start_time = time.time()

        observations = {}
        counter = 0
        for observation in self.tcs.collections.observations.paginate():
            if not observation.get('indicator') or not observation.get('type'):
                continue
            key = f'''{observation.get('indicator')}-{observation.get('type')}'''
            counter += 1
            observations.setdefault(key, []).append(observation)

        self.log_execution_time('consolidate-observations', start_time, {'count': counter})

        return observations

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve owner data from ThreatConnect
        observations = self.consolidate_observations()

        self.report_observations(observations)
        # display the results
        for r in self.results:
            yield r

    def report_observations(self, consolidated_observations):
        start_time = time.time()

        for consolidated_observation in consolidated_observations.values():
            if not consolidated_observation:
                continue
            count = 0
            multiple_observations = len(consolidated_observation) > 1
            indicator = type_ = None
            for observation in consolidated_observation:
                count += int(observation.get('observationCount'))
                indicator = observation.get('indicator')

                type_ = observation.get('type')
                if multiple_observations:
                    observation['delete'] = True
                    self.tcs.collections.observations.batch_data(observation)

            if not indicator or not type_ or count == 0:
                continue

            # update execution summary for observations count
            self.execution_summary['count_observations'] += 1
            response = self.tcs.request.report_observation(indicator, type_, count)
            if response is None:
                delete_observations = True
                status = 'Failure'
                msg = 'Indicator could not be found, possibly removed from ThreatConnect.'
                self.log_data(
                    'ERROR',
                    'report-observations',
                    {'ioc': indicator, 'ioc_type': type_, 'count': count, 'message': msg},
                )
                # update execution summary for failure count
                self.execution_summary['count_failure'] += 1
            else:
                status = response.json().get('status')
                delete_observations = response.ok
                if not response.ok:
                    # update execution summary for failure count
                    self.execution_summary['count_failure'] += 1
                    if response.status_code == 401:
                        msg = 'Permissions issue reporting observations.'
                        delete_observations = True
                    elif response.status_code == 404:
                        msg = 'Indicator could not be found, possibly removed from ThreatConnect.'
                        delete_observations = True
                    else:
                        msg = 'Generic issue reporting observations.'

                    log_data = {
                        'ioc': indicator,
                        'ioc_type': type_,
                        'count': count,
                        'message': msg,
                        'response': response.text,
                        'status-code': response.status_code
                    }
                    self.log_data('ERROR', 'report-observations', log_data)
                else:
                    # update execution summary for success count
                    self.execution_summary['count_success'] += 1

            if delete_observations:
                if multiple_observations:
                    self.tcs.collections.observations.batch_save()
                    self.tcs.collections.observations.delete(query={'delete': True})
                else:
                    self.tcs.collections.observations.delete_by_id(
                        consolidated_observation[0].get('_key')
                    )

            # results
            self.add_result(
                indicator=indicator,
                indicator_type=type_,
                observation_count=count,
                status=status,
            )

        self.log_execution_time('report-observations', start_time)


if __name__ == '__main__':
    try:
        dispatch(ReportObservation, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
