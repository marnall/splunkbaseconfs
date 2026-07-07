"""Paginate Wiz GraphQL responses and write events to Splunk."""
import json
import time
from enum import Enum
from urllib.parse import urlparse

from wiz_api import DEFAULT_REQUEST_TIMEOUT, call_wiz_api

DEFAULT_MAX_EVENTS_IN_MEMORY = 1000
# Safety cap: defends against hasNextPage=True forever (50M records at vulns' 5000/page).
MAX_PAGES = 10000


class FlushStrategy(Enum):
    BUFFERED = "buffered"  # batch across pages until max_buffer or final page
    PER_PAGE = "per_page"  # flush after every page (detections: cursor saved each time)


def write_events_to_splunk(helper, ew, events, event_name):
    if not events:
        return
    source_name = helper.get_arg('name')
    source_type = f"wiz:{event_name}"
    index = helper.get_output_index()
    wiz_account = helper.get_arg('wiz_account')
    host = urlparse(wiz_account['api_server_url']).netloc or "host"
    total = len(events)
    written = 0
    try:
        for position, eventData in enumerate(events, start=1):
            try:
                ew.write_event(helper.new_event(
                    host=host, source=source_name, index=index,
                    sourcetype=source_type, data=json.dumps(eventData),
                ))
                written += 1
            except Exception as e:
                event_id = eventData.get('id') if isinstance(eventData, dict) else None
                id_part = f" id={event_id}" if event_id else ""
                # Marker accounts for the lost original so cursor can advance;
                # if the marker also fails the sink is broken — raise.
                try:
                    ew.write_event(helper.new_event(
                        host=host, source=source_name, index=index,
                        sourcetype='wiz:ingestion_error',
                        data=json.dumps({
                            'event_type': source_type,
                            'event_id': event_id,
                            'position': position,
                            'total': total,
                            'error': str(e)[:500],
                        }),
                    ))
                except Exception as marker_err:
                    raise RuntimeError(
                        f"Source name = {source_name}. {source_type} event {position}/{total}{id_part} "
                        f"failed to write AND ingestion-error marker also failed"
                    ) from marker_err
    finally:
        helper.log_debug(
            f"Source name = {source_name}. {event_name[:1].upper() + event_name[1:]} written={written}/{total}"
        )


def query_wiz_api_and_write_to_splunk(helper, object_type, access_token, query, variables, ew, *,
                                      prepare_batch=None,
                                      post_write_callback=None,
                                      max_events_in_memory=DEFAULT_MAX_EVENTS_IN_MEMORY,
                                      flush_strategy=FlushStrategy.PER_PAGE,
                                      requests_timeout=DEFAULT_REQUEST_TIMEOUT,
                                      total_query_timeout=None):
    """Paginate Wiz API, prepare each batch, write to Splunk.

    `prepare_batch` (optional) filters/enriches the buffer before writing.
    Mid-pagination exceptions drop the in-flight buffer; the caller owns the
    checkpoint and re-fetches on next poll.
    """
    source_name = helper.get_arg('name')
    api_url = helper.get_arg('wiz_account')['api_server_url']
    cursor = None
    buffer = []
    written = 0
    start = time.monotonic()

    def flush(page_info):
        nonlocal buffer, written
        batch = prepare_batch(buffer) if prepare_batch else buffer
        buffer = []
        if not batch:
            return
        helper.log_debug(f'fetched {len(batch)} {object_type.api_field} events, writing to Splunk')
        write_events_to_splunk(helper, ew, batch, object_type.splunk_event)
        written += len(batch)
        if post_write_callback:
            post_write_callback(page_info)

    try:
        for _ in range(MAX_PAGES):
            page_vars = {**variables, 'after': cursor} if cursor else variables
            if total_query_timeout is not None and (time.monotonic() - start) >= total_query_timeout:
                return written
            data = call_wiz_api(helper, api_url, query, page_vars, access_token,
                                requests_timeout=requests_timeout)
            page = data[object_type.api_field]
            buffer += page['nodes'] or []
            page_info = page.get('pageInfo') or {}
            has_next = page_info.get('hasNextPage', False)

            buffer_full = len(buffer) >= max_events_in_memory
            if flush_strategy is FlushStrategy.PER_PAGE or buffer_full or not has_next:
                flush(page_info)

            if not has_next:
                return written
            cursor = page_info.get('endCursor')
            # Falsy cursor + hasNextPage=True would re-fetch page 1 forever.
            if not cursor:
                raise RuntimeError(
                    f"{object_type.api_field}: hasNextPage=True but endCursor is empty"
                )
        raise RuntimeError(
            f"{object_type.api_field}: exceeded MAX_PAGES={MAX_PAGES}"
        )
    except Exception as e:
        helper.log_error(f"Source name = {source_name}. Got an error when querying Wiz API: {e}")
        raise
