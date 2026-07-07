from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Dict
import splunk.rest as rest
import json

from thousandeyes_constant import THOUSANDEYES_TA_NAME
from thousandeyes_send_itsi_event import ITSIEventSender


_ENDPOINT = f'/servicesNS/nobody/{THOUSANDEYES_TA_NAME}/storage/collections/data/itsi_episodes'

_TEST_ID_FIELD = 'thousandeyes_test_id'

@dataclass
class SamplingConfig:
    min_interval: timedelta
    track_changes: List[str] = field(default_factory=list)

class ITSISampler:
    def __init__(self, config: Dict[str, str], session_key: str, logger):
        self.sampling_config = self._build_sampling_config(config)
        self.logger = logger
        self.session_key = session_key
        self.logger.debug(f'ISI Sampler config={self.sampling_config}')

    def select_and_send(self, event: Dict[str, str]):
        episode_id = event.get('itsi_group_id')
        if self._is_last_event(event):
            self._handle_last_event(event, episode_id)
        elif self._is_first_event(event):
            self._handle_first_event(event, episode_id)
        else:
            self._handle_regular_event(event, episode_id)
    
    def _is_last_event(self, event):
        return str(event.get('itsi_is_last_event', 'false')).lower() == 'true'

    def _is_first_event(self, event):
        return str(event.get('itsi_is_first_event', 'false')).lower() == 'true'

    def _handle_last_event(self, event, episode_id):
        self._log('info', f'Last event for episode {episode_id}')
        try:
            status = self._get_existing_status(episode_id)
        except Exception as e:
            # Episode not found (404) - use minimal status (we delete it anyway)
            if '404' in str(e):
                self._log('info', f'Episode {episode_id} not found in KV store (404) for last event, using minimal status')
                status = {'first_ts': event['orig_time']}
            else:
                raise
        self._cleanup_status(episode_id)
        self._send_event(event, status, True)

    def _handle_first_event(self, event, episode_id):
        self._log('info', f'First event for episode {episode_id}')
        status = self._generate_new_status(event)
        self._insert_status(status)
        self._send_event(event, status)

    def _handle_regular_event(self, event, episode_id):
        status_exists = True
        try:
            status = self._get_existing_status(episode_id)
            self._log('debug', f'Existing status for episode {episode_id}: {status}')
        except Exception as e:
            # Episode not found (404) - treat as first event
            # This can happen if a last event was processed and deleted the episode,
            # but then more events arrive for the same episode
            if '404' in str(e):
                self._log('info', f'Episode {episode_id} not found in KV store (404), treating as first event')
                status = self._generate_new_status(event)
                status_exists = False
            else:
                raise

        # If episode doesn't exist, always send (like first event)
        # Otherwise, check if we should select based on sampling rules
        if not status_exists or self._should_select(event, status):
            if not status_exists:
                self._insert_status(status)
            self._log('info', f'Selecting event {event.get("event_id")} for episode {episode_id} for sampling')
            self._send_event(event, status)
        
    def _send_event(self, event, status, last_event = False):
        self._log('debug', f'Send event for episode {event.get("itsi_group_id")}')
        test_ids = self._extract_test_ids(event, status)
        if len(test_ids) == 0:
            self._log('debug', f'No test IDs found for episode {event.get("itsi_group_id")}, skipping sending')
            return
        sender = ITSIEventSender(self.session_key, self.logger)
        self._log('debug', f'Sending event {event.get("event_id")} for episode {event.get("itsi_group_id")} to tests {test_ids}')
        if last_event:
            sender.send_event_for_tests(event, status.get('first_ts'), test_ids)
        else:
            sent_test_ids = sender.send_event_for_tests(event, status.get('first_ts'), test_ids)
            self._check_and_update_status(event, sent_test_ids)

    def _check_and_update_status(self, event: Dict[str, str], sent_test_ids: List[str]):
        if len(sent_test_ids) == 0:
            self._log('debug', f'Event {event.get("event_id")} is not successfully sent to any test, skipping status update')
            return
        sent_test_ids = set(sent_test_ids)
        episode_id = event.get('itsi_group_id')
        status = self._get_existing_status(episode_id)
        new_status = self._generate_new_status(event, status)
        sent_test_ids.update(status.get(_TEST_ID_FIELD, []))
        new_status[_TEST_ID_FIELD] = list(sent_test_ids)
        new_status['last_sent_ts'] = float(event['orig_time'])
        self._update_status(new_status)

    def _extract_test_ids(self, event, status):
        if _TEST_ID_FIELD in event:
            return [event[_TEST_ID_FIELD]]
        return status.get(_TEST_ID_FIELD, [])

    def _parse_duration(self, interval_str: str) -> timedelta:
        units = {
            's': 'seconds',
            'm': 'minutes',
            'h': 'hours',
            'd': 'days'
        }

        num = int(interval_str[:-1])
        unit = interval_str[-1]

        if unit not in units:
            raise ValueError(f'Invalid interval unit: {unit}')
        return timedelta(**{units[unit]: num})

    def _build_sampling_config(self, params: Dict[str, str]) -> SamplingConfig:
        return SamplingConfig(
            min_interval=self._parse_duration(params.get('sampling_min_interval', '60s')),
            track_changes=[x.strip() for x in params.get('sampling_track_changes', '').split(',') if x.strip()],
        )
                
    def _get_existing_status(self, episode_id) -> Dict[str, str]:
        self._log('debug', f'Get existing status for episode {episode_id}')
        _, content = rest.simpleRequest(
            f'{_ENDPOINT}/{episode_id}',
            method='GET',
            sessionKey=self.session_key,
            getargs={'output_mode': 'json'},
            raiseAllErrors=True
        )
        return json.loads(content)
    
    def _insert_status(self, status):
        self._log('debug', f'Insert status for episode {status}')
        _, _ = rest.simpleRequest(
            _ENDPOINT,
            method='PUT',
            sessionKey=self.session_key,
            raiseAllErrors=True,
            jsonargs=json.dumps(status)
        )

    def _update_status(self, status):
        self._log('debug', f'Update status for episode {status}')
        try:
            episode_id = status['itsi_group_id']
            _, _ = rest.simpleRequest(
                f'{_ENDPOINT}/{episode_id}',
                method='PUT',
                sessionKey=self.session_key,
                raiseAllErrors=True,
                jsonargs=json.dumps(status)
            )
        except Exception as e:
            self._log('error', f'Failed to update status for episode: {e}')

    def _cleanup_status(self, episode_id):
        try:
            self._log('debug', f'Delete status for episode {episode_id}')
            rest.simpleRequest(
                f'{_ENDPOINT}/{episode_id}',
                method='DELETE',
                sessionKey=self.session_key,
                raiseAllErrors=True
            )
        except Exception as e:
            pass


    def _generate_new_status(self, event, old_status = {}):
        new_status = {
            '_key': event['itsi_group_id'],
            'itsi_group_id': event['itsi_group_id'],
            'first_ts': old_status.get('first_ts', event['orig_time'])
        }
        for field in self.sampling_config.track_changes:
            new_status[field] = event.get(field, None)

        new_status[_TEST_ID_FIELD] = old_status.get(_TEST_ID_FIELD, [])
        return new_status


    def _should_select(self, event, status):
        self._log('debug', f'Check if should select: event={event}, status={status}')
        return (
            self._detect_changes(event, status) or
            self._detect_new_test_id(event, status) or
            self._check_interval(event, status)
        )
    
    def _detect_changes(self, event, status):
        for field in self.sampling_config.track_changes:
            existing = status.get(field, None)
            value = event.get(field, None)
            if existing != value:
                self._log('debug', f'Detect change in field {field} for episode {event["itsi_group_id"]}: existing={existing}, new={value}')
                return True
        return False

    def _detect_new_test_id(self, event, status):
        if (_TEST_ID_FIELD in event) and (event[_TEST_ID_FIELD] not in status.get(_TEST_ID_FIELD, [])):
            self._log('debug', f'Detect new {_TEST_ID_FIELD} for episode {event["itsi_group_id"]}: new_value={event[_TEST_ID_FIELD]}')
            return True
        return False

    def _check_interval(self, event, status):
        if 'last_sent_ts' not in status:
            return True
        time_diff = float(event['orig_time']) - status['last_sent_ts']
        if time_diff > self.sampling_config.min_interval.total_seconds():
            self._log('debug', f'Detect min interval for episode {event["itsi_group_id"]}: time_diff={time_diff}, min_interval={self.sampling_config.min_interval}')
            return True
        return False
    
    def _log(self, level, msg, *args, **kwargs):
        getattr(self.logger, level)(f"ITSISampler - {msg}", *args, **kwargs)
    