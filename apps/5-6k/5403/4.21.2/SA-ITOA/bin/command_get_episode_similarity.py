# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import time
import hashlib

# Core Splunk Imports
from splunk.clilib.bundle_paths import make_splunkhome_path
from functools import reduce

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path

from SA_ITOA_app_common.splunklib import results
from SA_ITOA_app_common.splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

SELECTED_EPISODE_SEARCH_TIMEOUT = 300


@Configuration(distributed=False)
class GetEpisodeSimilarity(StreamingCommand):
    """
    Calculates the similiarity between episodes
    """

    itsi_group_id = Option(
        doc='''
        **Syntax:** **itsi_group_id=***<itsi_group_id>*
        **Description:** The id of the episode to compare with other episodes''',
        require=True
    )

    episode_fields = Option(
        doc='''
        **Syntax:** **episode_field=***<episode_field>*
        **Description:** The fields used to compare with other episodes''',
        require=True,
        validate=validators.List()
    )

    earliest_time = Option(
        doc='''
        **Syntax:** **earliest_time=***<earliest_time>*
        **Description:** The earliest time of the episode to compare with other episodes''',
        require=True
    )

    latest_time = Option(
        doc='''
        **Syntax:** **latest_time=***<latest_time>*
        **Description:** The earliest time of the episode to compare with other episodes''',
        require=True
    )

    selected_episode_search = "search `itsi_event_management_group_index` itsi_group_id=\"{}\" | stats {}"

    def jaccard_similarity(self, list1, list2):
        """
        Calculates the Jaccard similarity index between two lists
        """
        intersection_cardinality = len(set.intersection(*[set(list1), set(list2)]))
        union_cardinality = len(set.union(*[set(list1), set(list2)]))
        return intersection_cardinality / float(union_cardinality) * 100.0

    def wait_for_job(self, searchjob, maxtime=-1):
        """
        Wait up to maxtime seconds for searchjob to finish.  If maxtime is
        negative (default), waits forever.  Returns true, if job finished.
        """
        pause = 0.2
        lapsed = 0.0
        while not searchjob.is_done():
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        return searchjob.is_done()

    def get_search_job(self):
        """
        Creates search job for current episode.
        """
        fields = ''
        for field in self.episode_fields:
            fields += ' values({}) as {}_values'.format(field, field)
        selected_episode_search = self.selected_episode_search.format(self.itsi_group_id, fields)

        current_episode_search_job = self.service.jobs.create(
            selected_episode_search,
            earliest_time=self.earliest_time,
            latest_time=self.latest_time
        )

        return current_episode_search_job

    def stream(self, records):
        try:
            current_episode_search_job = self.get_search_job()
            if not self.wait_for_job(current_episode_search_job, SELECTED_EPISODE_SEARCH_TIMEOUT):
                raise Exception("Search for selected episode field values timed out")

            current_episode = next(results.ResultsReader(current_episode_search_job.results()))
            for record in records:
                similarity_scores = []
                similar_fields = dict()
                for field_name in self.episode_fields:
                    values_field_name = field_name + '_values'
                    current_episode_field_values = current_episode[values_field_name]
                    if not isinstance(current_episode_field_values, list):
                        current_episode_field_values = [current_episode_field_values]
                    other_episode_field_values = record[values_field_name]
                    if not isinstance(other_episode_field_values, list):
                        other_episode_field_values = [other_episode_field_values]
                    jaccard_similarity_index = self.jaccard_similarity(current_episode_field_values, other_episode_field_values)
                    similarity_scores.append(jaccard_similarity_index)
                    if jaccard_similarity_index > 0:
                        similar_fields[field_name] = list(set(current_episode_field_values) & set(other_episode_field_values))
                record['similarity'] = sum(similarity_scores) / len(similarity_scores)
                record['similar_fields'] = similar_fields
                if record['similarity'] > 0:
                    yield record

        except Exception as e:
            self.error_exit(e)


dispatch(GetEpisodeSimilarity, sys.argv, sys.stdin, sys.stdout, __name__)
