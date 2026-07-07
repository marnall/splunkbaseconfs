#!/usr/bin/env python
# coding=utf-8
#
# © Presidio 2020-2023. All Rights Reserved.
#
# Neither this software, nor any portion thereof, may be copied, modified, adapted, or distributed without the express written permission of Presidio You may not obscure, remove, or alter any proprietary legends or notices.

import os, sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class QueueSearches(GeneratingCommand):
    """
    The runchecks command runs the specified searches in the given order.
    Base searches can be configured by beginning their post-process searches with the queued_search_base(1) macro.

    Example:
    Saved search "My Base Search" with query of:
        index=_internal sourcetype=splunkd

    Saved search "My Post Search" with query of:
        | `queued_search_base("My Base Search")` | stats c by component

    Queue search with query of:
        | runchecks searches="My Base Search, My Post Search"

    
    """

    # Command options
    searches = Option(require=True, validate=validators.List())
    global_tokens = Option(require=False, name='tokens', validate=validators.List())
    max_time = Option(require=False, default=0, validate=validators.Integer())
    timeout = Option(require=False, default=600, validate=validators.Integer())

    # NOTE: Assuming for now that default namespace / time range is sufficient.
    # earliest_time = Option(require=False)
    # latest_time = Option(require=False)
    # owner = Option(require=False)
    # app = Option(require=False)
    # sharing = Option(require=False)

    @staticmethod
    def _parse_tokens(token_list):
        parsed_tokens = {}
        for token in token_list or []:
            if '=' not in token:
                continue
            key, value = token.split('=', 1)
            parsed_tokens[key] = value
        return parsed_tokens

    def generate(self):
        # Extract metadata values
        sid = self.search_results_info.__dict__.get('sid', '')
        app = self.search_results_info.__dict__.get('ppc_app', '')
        user = self.search_results_info.__dict__.get('ppc_user', '')
        earliest_time = self.search_results_info.__dict__.get('search_et', '0')
        latest_time = self.search_results_info.__dict__.get('search_lt', 'now')
        start_time = self.search_results_info.__dict__.get('timestamp', str(time.time()))
        global_tokens = self._parse_tokens(self.global_tokens)
        timerange = global_tokens.get('timerange', '')

        audit_log = {
            'action': 'Queued Search',
            'sid': sid,
            'app': app,
            'user': user,
            'options': str(self.options),
            'earliest_time': earliest_time,
            'latest_time': latest_time,
            'start_time': start_time,
            'searches' : []
        }

        final_status = 'done'
        job_kvstore_data = None

        try:
            # Connect to kvstore and remove entries of expired jobs
            kvstore = self.service.kvstore["queued_searches"]
            kvstore_data = kvstore.data
            kvstore_data.delete('{"expiration": {"$lt": '+str(start_time)+'}}')

            # connect to kvstore "assessment_job"
            job_kvstore = self.service.kvstore["assessment_job"]
            job_kvstore_data = job_kvstore.data

            # Reset the job kvstore
            job_kvstore_data.delete()
            job_kvstore_data.insert({
                '_key': '0',
                'sid': sid,
                'timerange': timerange,
                'updated': time.time(),
                'status': 'running'
            })

            # Validate searches exist
            saved_searches = self.service.saved_searches
            valid_searches = []
            success_count = 0
            for (i, search_name) in enumerate(self.searches):
                # Extract any tokens
                tokens_string = f'parent_sid="{sid}" '
                if search_name[-1] == '>':
                    sni = search_name.index('<')
                    tokens = search_name[sni+1:-1].split('|')
                    search_name = search_name[0:sni]
                    tokens_string += ' '.join(
                        f'{k}="{v}"' for k, v in [token.split('=', 1) for token in tokens if '=' in token]
                    )

                try:
                    order = i+1
                    search_data = {'_key': f'{sid} {search_name} {order}', 'name': search_name, 'order': order, 'status': 'Pending', 'parent_sid': sid, 'timeout': self.timeout, 'updated': time.time()}
                    search = saved_searches[search_name]
                    valid_searches.append((search_data, tokens_string, search["search"]))
                except:
                    self.logger.info(f'Queued search "{search_name}" not found."')
                    continue

            if len(valid_searches):
                # Populate the KVStore
                kvstore_data.batch_save(*[data for (data, t, s) in valid_searches])

                # Run the searches
                base_tokens = '' + ' '.join(f'{k}="{v}"' for k, v in global_tokens.items())
                for (search_data, search_tokens, search_query) in valid_searches:

                    # Discontinue running child searches if parent search is marked cancelled by frontend cancel button
                    # Will never interrupt for scheduled assessment as that sid will not be in the kvstore
                    current_job = job_kvstore_data.query_by_id("0")
                    if current_job.get('status') == 'cancelled' and str(current_job.get('sid')) == str(sid):
                        final_status = 'cancelled'
                        audit_log['searches'].append({
                            'name': search_data["name"],
                            'order': search_data["order"],
                            'tokens': base_tokens + ' ' + search_tokens,
                            'status': 'Cancelled',
                            'messages': {"fatal":["Parent search cancelled, child search not run."]},
                            'query': search_query
                        })
                        break
                    try:
                        search_name = search_data["name"]

                        # Update the KVStore
                        search_data.update({'status': 'In Progress', 'updated': time.time()})
                        kvstore_data.update(search_data["_key"], search_data)
                        search_start_time = time.time()

                        # Run blocking (synchronous) search; code does not continue until search has finalized
                        # Use time range of parent search for all queued searches
                        search_job_kwargs = {
                            'exec_mode': 'blocking',
                            'now': search_start_time,
                            'earliest_time': earliest_time,
                            'latest_time': latest_time,
                            'max_time': self.max_time,
                            'timeout': self.timeout
                        }
                        search_job = self.service.jobs.create(f'| savedsearch "{search_name}" {base_tokens} {search_tokens}', **search_job_kwargs)
                        search_end_time = time.time()
                        search_expiration_time = search_end_time + self.timeout

                        # Update KVStore with sid
                        # NOTE: Improve status parsing?
                        search_status = 'Failed' if search_job["isFailed"] == '1' else 'Timed Out' if search_job["messages"].get('info') and search_job["messages"].get('info')[0] == 'Search finalized.' else 'Success'
                        search_data.update({'sid': search_job["sid"], 'status': search_status, 'expiration': search_expiration_time, 'updated': time.time()})
                        kvstore_data.update(search_data["_key"], search_data)

                        # Add search metrics to report
                        if (search_status == 'Success'):
                            success_count += 1
                        audit_log['searches'].append({
                            'name': search_name,
                            'order': search_data["order"],
                            'tokens': base_tokens + ' ' + search_tokens,
                            'sid': search_job["sid"],
                            'status': search_status,
                            'runDuration': round(float(search_job["runDuration"]),3),
                            'runDurationIndexingTier': round(float(search_job["performance"].get("dispatch.stream.remote", {}).get("duration_secs", 0)),3),
                            'runDurationSearchTier': round(float(search_job["performance"].get("dispatch.stream.local", {}).get("duration_secs", 0)),3),
                            'performance': search_job["performance"],
                            'start_time': search_start_time,
                            'end_time': search_end_time,
                            'eventCount': float(search_job["eventCount"]),
                            'resultCount': float(search_job["resultCount"]),
                            'messages': search_job["messages"],
                            'query': search_query
                        })
                        # yield {'_time': time.time(), '_raw': audit_log}
                        # yield {'_time': time.time(), '_raw': f'Queued search finalized:[timestamp={time.time()}, name=\'{search_name}\', order={order}, sid={search_job["sid"]}, status=\'{status}\', dispatchState={search_job["dispatchState"]}, runDuration={search_job["runDuration"]}, eventCount={search_job["eventCount"]}, resultCount={search_job["resultCount"]}, messages={search_job["messages"]}, search=\'{search_query}\']'}

                    except:
                        audit_log['searches'].append({
                            'name': search_name,
                            'order': search_data["order"],
                            'tokens': base_tokens + ' ' + search_tokens,
                            'status': 'Failed',
                            'messages': {"fatal":["Fatal error in saved search, most likely invalid SPL syntax. Run the search from the UI to see verbose errors."]},
                            'query': search_query
                        })

            # End metrics
            end_time = time.time()
            audit_log['search_count'] = len(audit_log['searches'])
            audit_log['search_success_count'] = success_count
            audit_log['end_time'] = end_time
            audit_log['runDuration'] = round(end_time - start_time, 3)

            # Return final report as a single JSON formatted event
            # NOTE: Consider breaking up into multiple events
            yield {'_time': time.time(), '_raw': audit_log}
        except:
            final_status = 'failed'
            raise
        finally:
            if not job_kvstore_data:
                return

            try:
                current_job = job_kvstore_data.query_by_id("0")
            except:
                current_job = None

            if current_job and str(current_job.get('sid')) != str(sid):
                return

            if current_job and current_job.get('status') == 'cancelled':
                final_status = 'cancelled'

            final_payload = {
                '_key': '0',
                'sid': sid,
                'timerange': timerange,
                'updated': time.time(),
                'status': final_status
            }

            if current_job:
                job_kvstore_data.update("0", final_payload)
            else:
                job_kvstore_data.insert(final_payload)


dispatch(QueueSearches, sys.argv, sys.stdin, sys.stdout, __name__)
