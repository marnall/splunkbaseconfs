#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Report Observations Command."""
import json
import os
import sys
from collections import OrderedDict
import urllib.parse

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration


@Configuration()
class ReportObservation(BaseGeneratingCommand):
    """Playbook download command.

    This command is run via a saved search.

    Usage:
    | tcobservations
    """

    # properties
    filename = os.path.basename(__file__)

    def add_result(self, action, indicator, observation_count, confidence_reset, status):
        """Return ordered dict for results."""
        self.logger.info(
            f'action="{action}", indicator={indicator}, observation_count="{observation_count}", '
            f'confidence_reset={confidence_reset}, status={status}'
        )
        result_data = OrderedDict()
        result_data['Action'] = action
        result_data['Indicator'] = indicator
        result_data['Observation Count'] = observation_count
        result_data['Confidence Reset'] = confidence_reset
        result_data['Status'] = status
        self.results.append(result_data)

    def generate(self):
        """Implement generate command for reporting a observation on a indicator."""
        current_indicator_summary = current_indicator_type = None
        observations = []
        for ob in self.tcs.collections.observations.paginate(sort='indicator'):
            current_indicator_summary = current_indicator_summary or ob.get('indicator')
            current_indicator_type = current_indicator_type or ob.get('type')
            # Iterating over another instance of the indicator
            if (
                ob.get('indicator') == current_indicator_summary and
                ob.get('type') == current_indicator_type
            ):
                observations.append(ob)
                continue

            # Iterating over a new indicator, report the metrics from the previous one.
            self._report_observations_for_indicator(observations)

            # Set values to new indicator
            observations = [ob]
            current_indicator_summary = ob.get('indicator')
            current_indicator_type = ob.get('type')

        # The previous loop will not report the final observation, that is done here
        self._report_observations_for_indicator(observations)

        # display results
        for r in self.results:
            yield r

    def _report_observations_for_indicator(self, observations):
        """It is expected that all of the observations provided are for the same indicator-type."""
        if not observations:
            return

        count = 0
        confidence = 0
        indicator = observations[0].get('indicator')
        type_ = observations[0].get('type')
        key = None
        for ob in observations:
            key = ob.get('_key')
            count += int(ob.get('observationCount', 0))
            confidence = confidence or ob.get('confidenceRating', 0)

            # If there are more than 1 observation then use a batch delete.
            if len(observations) > 1:
                ob['delete'] = True
                self.tcs.collections.observations.batch_data(ob)
        status = self.report_observation(
            indicator,
            type_,
            count
        )
        if status == 'Success':
            if len(observations) > 1:
                self.tcs.collections.observations.batch_save()
                self.tcs.collections.indicators.delete(query={'delete': True})
            else:
                self.tcs.collections.observations.delete_by_id(key)
            self.logger.info(f'action=post, status={status}')
        else:
            self.logger.error(f'action=post, status={status}')

        confidence_reset = 'No Reset'
        if confidence > 0:
            self.reset_confidence(indicator, confidence)
            confidence_reset = confidence

        # results
        self.add_result(
            action='Report',
            indicator=indicator,
            observation_count=count,
            confidence_reset=confidence_reset,
            status=status,
        )

    def report_observation(self, indicator, indicator_type, count):
        """Report observations method."""
        self.logger.debug(
            f'action=report-observations, indicator={indicator}, indicator_type={indicator_type}, '
            f'count={count}'
        )

        body = {'count': count}

        api_branch = self.tcs.request.indicator_type_branch(indicator_type)
        safe_indicator = urllib.parse.quote(indicator, safe='')
        url = f'/v2/indicators/{api_branch}/{safe_indicator}/observations'
        r = self.tcs.session.post(f'{url}', json=body)
        self.logger.debug(f'url: {r.request.url}')

        if not r.ok:
            if r.status_code == 401:
                self.logger.error(
                    f'Permissions issue reporting observations '
                    f'(status={r.status_code}, response={r.text}).'
                )
                return 'Success'

            if r.status_code == 404:
                if r.json().get('message') == 'The requested resource was not found':
                    self.logger.warning(
                        f'Indicator could not be found, possibly removed from ThreatConnect '
                        f'(status={r.status_code}, response={r.text}).'
                    )
                    return 'Success'

            self.logger.error(
                f'Generic issue reporting observations '
                f'(status={r.status_code}, response={r.text}).'
            )

        return r.json().get('status')

    def reset_confidence(self, indicator, confidence_reset):
        """Reset Confidence Method."""
        # retrieve indicator kv store
        query = {'indicator': indicator}
        indicators = self.service.kvstore['tc_indicators'].data.query(query=json.dumps(query))

        for indicator_data in indicators:
            if int(indicator_data.get('confidence', 0)) < int(confidence_reset):
                body = {'confidence': confidence_reset}
                params = {'owner': indicator_data.get('ownerName')}
                api_branch = self.tcs.request.indicator_type_branch(indicator_data.get('type'))
                safe_indicator = urllib.parse.quote(indicator, safe='')
                url = f'/v2/indicators/{api_branch}/{safe_indicator}'

                # make REST API call
                r = self.tcs.session.put(f'{url}', json=body, params=params)
                self.logger.debug(f'url: {r.request.url}')

                if not r.ok:
                    if r.status_code == 401:
                        self.logger.warning(
                            f'Permissions issue resetting confidence '
                            f'(status={r.status_code}, response={r.text}).'
                        )
                    else:
                        self.logger.warning(
                            f'Generic issue resetting confidence '
                            f'(status={r.status_code}, response={r.text}).'
                        )


if __name__ == '__main__':
    dispatch(ReportObservation, sys.argv, sys.stdin, sys.stdout, __name__)
