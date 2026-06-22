import asyncio
from collections import OrderedDict
import csv
import json
import logging
import random
import sys
import argparse
from datetime import datetime
from pathlib import Path

from constants import (
    DAY_IN_SECONDS,
    ESP_ALERT_THRESHOLDS,
    ESP_NORMAL_THRESHOLDS,
    INTERVAL_SECONDS,
    TIME_DEPENDENT_FIELDS,
    WELL_BORE_CODES,
    WELL_FILE_MAP,
    WELL_NUMERIC_FIELDS,
)
from event_logger import file_handler

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_DIR = SCRIPT_DIR.parent / "samples" / "wells_data"


def get_random_from_range(rng):
    subranges = rng if isinstance(rng[0], (list, tuple)) else [rng]
    chosen_range = random.choice(subranges)
    return round(random.uniform(*chosen_range), 2)


def generate_random_esp_values(
    fields_normal=ESP_NORMAL_THRESHOLDS,
    fields_alert=ESP_ALERT_THRESHOLDS,
    alert_chance=0.03,
):
    result = {}

    for field in fields_normal:
        is_alert = random.random() < alert_chance
        if is_alert:
            rng = fields_alert[field]
        else:
            rng = fields_normal[field]
        value = get_random_from_range(rng)
        result[field] = value

    return result


def normalize_number(value):
    if not value:
        return None
    return float(value.replace(",", ""))


async def write_event(event_data: dict):
    # Ensure _time is the first key
    ordered = OrderedDict()
    if "_time" in event_data:
        ordered["_time"] = event_data["_time"]
    for k, v in event_data.items():
        if k != "_time":
            ordered[k] = v
    sys.stdout.write(json.dumps(ordered) + "\n")
    sys.stdout.flush()


def parse_date_str(date_str):
    return datetime.strptime(date_str, "%d-%b-%y").date()


def adjust_for_interval(value):
    normalized = normalize_number(value)
    if normalized is None:
        return None
    batch = normalized / DAY_IN_SECONDS * INTERVAL_SECONDS
    return round(batch, 2)


def add_random_variation(value: float, percent: float = 3.0) -> float:
    if value is None:
        return None
    variation = random.uniform(-percent / 100, percent / 100)
    return round(value * (1 + variation), 3)


row_cache = {}


async def process_file(well_bore_code: str, target_timestamp: datetime = None):
    file_path = CSV_DIR / f"{WELL_FILE_MAP[well_bore_code]}.csv"
    if not file_path.exists():
        logger.error(f"⚠️ File not found: {file_path}")
        return  # skip this well

    # Use target_timestamp if provided, else use now
    today = target_timestamp if target_timestamp else datetime.now()
    current_day = today.day
    current_month = today.strftime("%b")
    current_date_key = f"{current_day}-{current_month}"

    cached = row_cache.get(well_bore_code)
    if cached and cached[0] == current_date_key:
        matched_row = cached[1]
    else:
        matched_row = None
        with file_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row_day = int(row["DATEPRD"].split("-")[0])
                    row_month = row["DATEPRD"].split("-")[1]
                except Exception as exc:
                    logger.warning(f"Couldn't get date from DATEPRD: {exc}")
                    continue

                if (
                    row_day == current_day
                    and row_month.lower() == current_month.lower()
                ):
                    matched_row = row
                    break

        if not matched_row:
            logger.warning(
                f"⚠️ Data for {today.strftime('%d-%b-%Y')} was not found in {file_path.name}, skipping."
            )
            return  # skip this well

        row_cache[well_bore_code] = (current_date_key, matched_row)

    metrics = {}
    # EVENT_TIMESTAMP will be set by backfill_loop for backfill, else here
    if target_timestamp:
        metrics["_time"] = target_timestamp.isoformat()
    else:
        metrics["_time"] = today.isoformat()
    for key in WELL_NUMERIC_FIELDS:
        raw_value = matched_row.get(key)
        if not raw_value:
            continue
        if key in TIME_DEPENDENT_FIELDS:
            adjusted = adjust_for_interval(raw_value)
        else:
            adjusted = normalize_number(raw_value)
        value = add_random_variation(adjusted)
        if value is None:
            continue

        metrics[key] = value

    if int(metrics.get("BORE_WI_VOL", 0)) == 0:
        esp_data = generate_random_esp_values()
        metrics.update(esp_data)

    metrics["WELL_BORE_CODE"] = well_bore_code
    await write_event(metrics)


async def main_loop():
    while True:
        logger.info(f"🕒 Start: {datetime.now().isoformat()}")
        tasks = [process_file(code) for code in WELL_BORE_CODES]
        await asyncio.gather(*tasks)
        logger.info("⏳ Wait 5 minutes...")
        await asyncio.sleep(300)


async def backfill_loop(start_datetime: datetime, end_datetime: datetime):
    from datetime import timedelta
    interval_seconds = 300  # 5 minutes
    current_time = start_datetime
    while current_time <= end_datetime:
        logger.info(f"🕒 Backfill: {current_time.isoformat()}")
        tasks = [process_file(code, target_timestamp=current_time) for code in WELL_BORE_CODES]
        await asyncio.gather(*tasks)
        current_time += timedelta(seconds=interval_seconds)

# to backfill, run the script with:
# $SPLUNK_HOME/bin/splunk cmd python $SPLUNK_HOME/etc/apps/oilgas_splunk_app/bin/event_generator.py --start 2025-01-01T00:00:00 --end 2025-07-12T00:00:00.000 > /tmp/backfill.txt
# then import file /tmp/backfill.txt into Splunk as file input
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oil & Gas Event Generator")
    parser.add_argument("--start", type=str, help="Start datetime (YYYY-MM-DDTHH:MM:SS)")
    parser.add_argument("--end", type=str, help="End datetime (YYYY-MM-DDTHH:MM:SS)")
    args = parser.parse_args()

    if args.start and args.end:
        from datetime import timedelta
        try:
            start_datetime = datetime.fromisoformat(args.start)
            end_datetime = datetime.fromisoformat(args.end)
        except Exception as exc:
            logger.error(f"Invalid datetime format: {exc}")
            sys.exit(1)
        asyncio.run(backfill_loop(start_datetime=start_datetime, end_datetime=end_datetime))
    else:
        asyncio.run(main_loop())
