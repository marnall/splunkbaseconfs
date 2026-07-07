
# encoding = utf-8

from datetime import datetime, timedelta, date
import json
import time


def validate_input(helper, definition):
    pass

def convert_time_epoc(timestamp_str):
    dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
    return int(time.mktime(dt.timetuple()))

def collect_events(helper, ew):

  url = helper.get_arg('digicert_endpoint')
  if url.startswith("http://"):
      helper.log_error("Given URL is not secure.")
      exit(1)

  global_account_id = helper.get_arg('account_id')
  global_api_key = helper.get_arg('api_key')


  final_checkpoint_date = helper.get_check_point("digicert_checkpoint_date")
  state=final_checkpoint_date
  if final_checkpoint_date is None:
      final_checkpoint_date="2020-01-01"
      state=final_checkpoint_date

  final_checkpoint_date_time = helper.get_check_point("digicert_checkpoint_date_time")
  if final_checkpoint_date_time is None:
      final_checkpoint_date_time = "2020-01-01T00:00:00Z"

  final_checkpoint = final_checkpoint_date_time

  count = 0
  offset = 0
  limit = 50
  mul = 0
  itr = 0
  dataPresent = True
  method = "GET"
  headers = {
      'accept': 'application/json',
      'X-API-Key': global_api_key
  }

  while dataPresent:
      parameters = {
          "offset": offset,
          "limit": limit,
          "account_id": global_account_id,
          "from": state
      }

      helper.log_info(f"Hitting API: {url} with offset={offset}, limit={limit}")
      response = helper.send_http_request(
          url, method,
          parameters=parameters,
          payload=None,
          headers=headers,
          cookies=None,
          verify=True,
          cert=None,
          timeout=None,
          use_proxy=True
      )

      r_status = response.status_code
      if r_status != 200:
          helper.log_error(f"API response is not success, status={r_status}")
          response.raise_for_status()

      r_json = response.json()
      helper.log_info("Got a success response from API")

      events_key = None
      if "items" in r_json:
          events_key = "items"
      elif "records" in r_json:
          events_key = "records"
      else:
          helper.log_error("No valid events field found in response (expected 'items' or 'records').")
          break

      total = r_json.get("total", 0)
      helper.log_info(f"Found {total} events for current date")

      mul = mul + 1

      if count == 0 and total > 0:
          first_event = r_json[events_key][0]
          timestamp_field = "timestamp" if "timestamp" in first_event else "created_at"
          timestamp_str = first_event[timestamp_field]

          dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
          dt_plus_one_sec = dt + timedelta(seconds=1)
          final_checkpoint = dt_plus_one_sec.strftime("%Y-%m-%dT%H:%M:%SZ")

          itr = (total / limit) // 1 + 1
          count = 1

      last_ingest_epoc = convert_time_epoc(final_checkpoint_date_time)

      for event in r_json[events_key]:
          timestamp_field = "timestamp" if "timestamp" in event else "created_at"
          event_epoc = convert_time_epoc(event[timestamp_field])

          if event_epoc > last_ingest_epoc:
              data = helper.new_event(
                  json.dumps(event),
                  time=None,
                  host=None,
                  index=None,
                  source=None,
                  sourcetype=None,
                  done=True,
                  unbroken=True
              )
              ew.write_event(data)

      if itr > 0:
          itr = itr - 1
          offset = mul * limit
      else:
          dataPresent = False

  final_checkpoint_date_time = final_checkpoint
  helper.save_check_point("digicert_checkpoint_date_time", final_checkpoint_date_time)
  helper.save_check_point("digicert_checkpoint_date", date.today().strftime("%Y-%m-%d"))

  helper.log_info(f"Checkpoint updated: {final_checkpoint_date_time}")