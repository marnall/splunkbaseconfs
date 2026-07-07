import copy
import json
import re

from splunk_api import SplunkApiClient, APP_NAME


severity_map = {'Lowest': 1, 'Low': 2, 'Medium': 3, 'High': 4, 'Highest': 5}
explicitly_mapped_options = [
    'action.email.useNSSubject',
    'action.snapattack.guid',
    'action.snapattack.compilation_target',
    'action.snapattack.name',
    'action.snapattack.description',
    'action.snapattack.logsource',
    'action.snapattack.last_deployed',
    'action.snapattack.last_updated',
    'action.snapattack.tactics',
    'action.snapattack.techniques',
    'action.snapattack.subtechniques',
    'actions',
    'action.summary_index._name',
    'action.summary_index._type',
    'action.summary_index.snapattack_analytic_guid',
    'action.summary_index.snapattack_analytic_last_deployed',
    'action.summary_index.snapattack_analytic_last_updated',
    'action.summary_index.snapattack_analytic_mitre_tactics',
    'action.summary_index.snapattack_analytic_mitre_techniques',
    'action.summary_index.snapattack_analytic_mitre_subtechniques',
    'action.summary_index.snapattack_analytic_name',
    'action.summary_index.snapattack_analytic_version_id',
    'cron_schedule',
    'is_scheduled',
    'realtime_schedule',
    'alert.track',
    'description',
    'dispatch.earliest_time',
    'dispatch.latest_time',
    'display.general.type',
    'display.page.search.tab',
    'display.visualizations.show',
    'request.ui_dispatch_app',
    'request.ui_dispatch_view',
    'search',
]

# Compile the regex pattern
allowed_saved_search_args = re.compile(
    r"^(?:"
    r"action(?:\.\w+(?:\.\w+)?)?|"
    r"action\.summary_index\._type|"
    r"action\.summary_index\.force_realtime_schedule|"
    r"actions|"
    r"alert\.(?:digest_mode|expires|severity|suppress(?:\.\w+)?|track|comparator|condition|threshold|type)|"
    r"allow_skew|"
    r"args\.\*|"
    r"auto_summarize(?:\.\w+)?|"
    r"cron_schedule|"
    r"description|"
    r"disabled|"
    r"dispatch(?:\.\w+)?|"
    r"displayview|"
    r"durable\.(?:backfill_type|lag_time|max_backfill_intervals|track_time_type)|"
    r"is_scheduled|"
    r"is_visible|"
    r"max_concurrent|"
    r"name|"
    r"next_scheduled_time|"
    r"qualifiedSearch|"
    r"realtime_schedule|"
    r"request\.(?:ui_dispatch_app|ui_dispatch_view)|"
    r"restart_on_searchpeer_add|"
    r"run_n_times|"
    r"run_on_startup|"
    r"schedule_priority|"
    r"schedule_window|"
    r"search|"
    r"vsid|"
    r"workload_pool"
    r")$"
)


class AnalyticProcessor(SplunkApiClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_deployed_analytics(self):
        existing_searches = {
            f'{search.content.get("action.snapattack.guid")}_{search.content.get("action.snapattack.compilation_target", 0)}': search
            for search in self.client.saved_searches
            if search.access.get('app') == APP_NAME and search.content.get('action.snapattack.guid')
        }
        deployed_analytics = self.fetch_requested_items(self.RequestType.deployment)
        updated_analytic_count = 0
        new_analytic_count = 0
        deleted_analytic_count = 0
        for identifier, analytic in deployed_analytics.items():
            if identifier in existing_searches and self._parse_date_string(
                analytic['last_deployed']
            ) > self._parse_date_string(
                (
                    # this doesn't exist in earlier deployments
                    existing_searches[identifier].content.get('action.snapattack.last_deployed')
                    or existing_searches[identifier].content.get('action.snapattack.last_updated')
                )
                or 'action.snapattack.subtechniques'
                not in existing_searches[identifier].content  # Force upgrade of old saved search schema
            ):
                updated_analytic_count += 1
                self.logger.debug(f'Replacing {existing_searches[identifier].name}')
                self.client.saved_searches.delete(existing_searches[identifier].name)
            elif identifier in existing_searches:
                is_native = self.is_native_query(analytic)
                deployed_search = (
                    self._build_sanitized_query(
                        analytic['search'], limit=self.max_results, native=self.is_native_query(analytic)
                    )
                    .encode('ascii', 'ignore')
                    .decode('ascii')
                )
                deployed_search = f'`sa_base_index_filter` {deployed_search}' if not is_native else f'{deployed_search}'
                if deployed_search != existing_searches[identifier].content.get('search'):
                    # If search has changed, submit back to SnapAttack
                    payload = self._generate_update_payload(existing_searches[identifier], analytic)
                    self.set_deployment_status(
                        deployment_id=analytic['analytic_deployment_id'], original=analytic, updated=payload
                    )
                continue
            else:
                new_analytic_count += 1
            try:
                self.logger.debug(f'Installing {analytic["name"]}')
                self.client.parse(
                    query=(
                        f"search {analytic['search']}"
                        if self.needs_search_prefix(analytic['search'])
                        else f"{analytic['search']}"
                    ),
                    output_mode='json',
                    enable_lookups=False,
                )
                self._create_saved_search(analytic)
                self.set_deployment_status(deployment_id=analytic['analytic_deployment_id'])
            except Exception as ex:
                self.logger.debug(f'Failed to install {analytic["guid"]} - {str(ex)}')
                self.set_deployment_status(
                    deployment_id=analytic['analytic_deployment_id'],
                    error_message=f'Failed to deploy analytic {analytic["guid"]} - {str(ex)}',
                )
                continue
        for identifier, search in existing_searches.items():
            if identifier not in deployed_analytics:
                deleted_analytic_count += 1
                self.logger.debug(f'Deleting no longer deployed {search.name}')
                self.client.saved_searches.delete(existing_searches[identifier].name)
        resulting_searches = [
            search.content.get('action.snapattack.guid')
            for search in self.client.saved_searches
            if search.access.get('app') == APP_NAME and search.content.get('action.snapattack.guid')
        ]
        for app in self.client.apps:
            if app.name == APP_NAME:
                app.reload()
        return {
            'total_deployed': len(resulting_searches),
            'updated': updated_analytic_count,
            'new': new_analytic_count,
            'deleted': deleted_analytic_count,
        }

    def _valid_dynamic_option(self, key: str):
        return allowed_saved_search_args.match(key) and key not in explicitly_mapped_options

    def _generate_update_payload(self, saved_search, deployed_analytic: dict) -> dict:
        """Converts a saved search into an analytic deployment update payload"""
        result = copy.deepcopy(deployed_analytic)
        result['description'] = saved_search.content.get('description')
        result['search'] = saved_search.content.get('search')
        result['name'] = saved_search.content.get('action.snapattack.name')
        result['dispatch_options'] = dict(
            schedule=saved_search.content.get('cron_schedule'),
            enabled=saved_search.content.get('is_scheduled'),
            save_as_alert=saved_search.content.get('alert.track') == 1,
            dispatch_earliest=saved_search.content.get('dispatch.earliest_time'),
            dispatch_latest=saved_search.content.get('dispatch.latest_time'),
            saved_search_kwargs=[
                dict(key=k, value=v)
                for k, v in saved_search.content.items()
                if self._valid_dynamic_option(k) and v not in (None, 'none', 'auto', 'default')
            ],
            permissions=saved_search.access
            and dict(
                sharing=saved_search.access.get('sharing'),
                owner=saved_search.access.get('owner'),
                read=saved_search.access.get('perms', {}).get('read'),
                write=saved_search.access.get('perms', {}).get('read'),
            ),
        )
        return result

    def _get_dispatch_option(self, item, option, default):
        result = item.get('dispatch_options', {}).get(option)
        return result if result is not None else default

    def _create_saved_search(self, analytic: dict):
        # TODO: Make summary_index configurable
        tactics = [t for t in analytic['attacks'] if t['type'] == 'Tactic'] if analytic['attacks'] else []
        techniques = [t for t in analytic['attacks'] if t['type'] == 'Technique'] if analytic['attacks'] else []
        subtechniques = [t for t in analytic['attacks'] if t['type'] == 'Subtechnique'] if analytic['attacks'] else []
        raise_alert = self._get_dispatch_option(analytic, 'save_as_alert', False)
        is_native = self.is_native_query(analytic)
        search_args = {
            'action.email.useNSSubject': '1',
            'action.snapattack.guid': analytic['guid'],
            'action.snapattack.compilation_target': analytic.get('analytic_compilation_target_id', 0),
            'action.snapattack.name': analytic['name'],
            'action.snapattack.description': analytic['description'],
            'action.snapattack.logsource': analytic['logsource'],
            'action.snapattack.last_deployed': analytic['last_deployed'],
            'action.snapattack.last_updated': analytic['last_updated'],
            'action.snapattack.tactics': json.dumps(
                {'tactics': [{'mitre_id': t['id'], 'name': t['name']} for t in tactics]}
            ),
            'action.snapattack.techniques': json.dumps(
                {'techniques': [{'mitre_id': t['id'], 'name': t['name']} for t in techniques]}
            ),
            'action.snapattack.subtechniques': json.dumps(
                {'subtechniques': [{'mitre_id': t['id'], 'name': t['name']} for t in subtechniques]}
            ),
            'actions': 'summary_index',
            'action.summary_index._name': self.results_index,
            'action.summary_index._type': 'event',
            'action.summary_index.snapattack_analytic_guid': analytic['guid'],
            'action.summary_index.snapattack_analytic_last_deployed': analytic['last_deployed'],
            'action.summary_index.snapattack_analytic_last_updated': analytic['last_updated'],
            'action.summary_index.snapattack_analytic_mitre_tactics': ','.join([t['id'] for t in tactics]),
            'action.summary_index.snapattack_analytic_mitre_techniques': ','.join([t['id'] for t in techniques]),
            'action.summary_index.snapattack_analytic_mitre_subtechniques': ','.join([t['id'] for t in subtechniques]),
            'action.summary_index.snapattack_analytic_name': analytic['name'],
            'action.summary_index.snapattack_analytic_version_id': analytic.get('version_id'),
            'cron_schedule': self._get_dispatch_option(analytic, 'schedule', '*/15 * * * *'),
            'is_scheduled': self._get_dispatch_option(analytic, 'enabled', True),
            'realtime_schedule': '0',
            'alert.track': '1' if raise_alert else '0',
            'description': analytic['description'],
            'dispatch.earliest_time': self._get_dispatch_option(analytic, 'dispatch_earliest', '-15m'),
            'dispatch.latest_time': self._get_dispatch_option(analytic, 'dispatch_latest', 'now'),
            'display.general.type': 'statistics',
            'display.page.search.tab': 'statistics',
            'display.visualizations.show': '0',
            'request.ui_dispatch_app': APP_NAME,
            'request.ui_dispatch_view': 'search',
        }
        if raise_alert:
            search_args['alert.severity'] = severity_map.get(analytic.get('severity', 'Medium'), 3)

        for custom_kwarg in self._get_dispatch_option(analytic, 'saved_search_kwargs', []):
            if self._valid_dynamic_option(custom_kwarg['key']):
                search_args[custom_kwarg['key']] = custom_kwarg['value']

        search_name = f'{analytic.get("prefix").strip() or "SnapAttack -"} {analytic["name"]} ({analytic["guid"]}_{analytic.get("analytic_compilation_target_id", 0)})'.encode(
            'ascii', 'ignore'
        ).decode(
            'ascii'
        )
        search = (
            self._build_sanitized_query(analytic['search'], limit=self.max_results, native=is_native)
            .encode('ascii', 'ignore')
            .decode('ascii')
        )
        search = f'`sa_base_index_filter` {search}' if not is_native else f'{search}'

        self.client.saved_searches.create(search_name[:100], search, **search_args)
        perms = self._get_dispatch_option(analytic, 'permissions', None)
        if perms:
            self.client.saved_searches[search_name[:100]].acl_update(
                sharing=perms['sharing'],
                owner=perms['owner'],
                app=APP_NAME,
                **{"perms.read": perms['read'], "perms.write": perms['write']},
            )
