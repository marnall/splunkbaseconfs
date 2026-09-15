#!/usr/bin/env python3
# ==============================================================================
# ZERO TRUST IMS - CRITICAL PATH CALCULATOR (CUSTOM SEARCH COMMAND)
# Algorithms: Directed Acyclic Graph (DAG) CPM, Kahn's Topological Sort,
# Circular Dependency Guard, Federal/DoD Holiday & Working-Day Calendar Engine
# ==============================================================================

import sys
import os
import datetime
import calendar
from collections import defaultdict, deque

# Import splunklib searchcommands SDK from bin/lib
BIN_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BIN_DIR, 'lib')
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


def _get_nth_weekday_of_month(year, month, weekday, n):
    """
    Finds the nth occurrence of a weekday in a given month.
    weekday: 0=Monday, ..., 6=Sunday.
    n: 1=1st, 2=2nd, 3=3rd, 4=4th, -1=last.
    """
    if n > 0:
        count = 0
        for day in range(1, 32):
            try:
                dt = datetime.date(year, month, day)
            except ValueError:
                break
            if dt.weekday() == weekday:
                count += 1
                if count == n:
                    return dt
    else:
        _, last_day = calendar.monthrange(year, month)
        for day in range(last_day, 0, -1):
            dt = datetime.date(year, month, day)
            if dt.weekday() == weekday:
                return dt
    return None


def _apply_weekend_observance(dt):
    """If Saturday -> Friday, if Sunday -> Monday."""
    if dt.weekday() == 5:
        return dt - datetime.timedelta(days=1)
    elif dt.weekday() == 6:
        return dt + datetime.timedelta(days=1)
    return dt


def get_federal_holidays(start_year, end_year):
    """
    Generates all 11 US Statutory Federal / DoD Holidays with weekend observance
    rules across the specified year range.
    """
    holidays = set()
    for year in range(start_year, end_year + 1):
        # 1. New Year's Day (Jan 1)
        holidays.add(_apply_weekend_observance(datetime.date(year, 1, 1)))
        # 2. Martin Luther King Jr. Day (3rd Monday in Jan)
        holidays.add(_get_nth_weekday_of_month(year, 1, 0, 3))
        # 3. Washington's Birthday / Presidents Day (3rd Monday in Feb)
        holidays.add(_get_nth_weekday_of_month(year, 2, 0, 3))
        # 4. Memorial Day (Last Monday in May)
        holidays.add(_get_nth_weekday_of_month(year, 5, 0, -1))
        # 5. Juneteenth National Independence Day (June 19)
        holidays.add(_apply_weekend_observance(datetime.date(year, 6, 19)))
        # 6. Independence Day (July 4)
        holidays.add(_apply_weekend_observance(datetime.date(year, 7, 4)))
        # 7. Labor Day (1st Monday in Sep)
        holidays.add(_get_nth_weekday_of_month(year, 9, 0, 1))
        # 8. Columbus Day / Indigenous Peoples' Day (2nd Monday in Oct)
        holidays.add(_get_nth_weekday_of_month(year, 10, 0, 2))
        # 9. Veterans Day (Nov 11)
        holidays.add(_apply_weekend_observance(datetime.date(year, 11, 11)))
        # 10. Thanksgiving Day (4th Thursday in Nov)
        holidays.add(_get_nth_weekday_of_month(year, 11, 3, 4))
        # 11. Christmas Day (Dec 25)
        holidays.add(_apply_weekend_observance(datetime.date(year, 12, 25)))
    return holidays


def add_working_days(start_date_obj, working_days, excluded_dates):
    """
    Adds working_days to start_date_obj, skipping weekends (Sat/Sun) and excluded
    dates (federal holidays + PTOs).
    """
    curr = start_date_obj
    while curr.weekday() >= 5 or curr in excluded_dates:
        curr += datetime.timedelta(days=1)

    remaining = int(round(working_days))
    if remaining <= 0:
        return curr

    days_counted = 0
    while days_counted < remaining:
        curr += datetime.timedelta(days=1)
        if curr.weekday() < 5 and curr not in excluded_dates:
            days_counted += 1

    return curr


def count_holidays_in_span(start_dt, end_dt, holidays_set):
    """Counts federal holidays falling between start_dt and end_dt inclusive."""
    count = 0
    curr = start_dt
    while curr <= end_dt:
        if curr in holidays_set:
            count += 1
        curr += datetime.timedelta(days=1)
    return count


def calculate_cpm(records, project_start_date=None, pto_dates=None):
    """
    Computes Early Start/Finish, Late Start/Finish, Slack, Critical Path,
    and Calendar Dates factoring in US Federal Holidays and PTOs.
    """
    graph = defaultdict(list)
    rev_graph = defaultdict(list)
    in_degree = defaultdict(int)
    duration = {}
    node_map = {}

    for r in records:
        m_id = str(r.get('milestone_id', r.get('wbs_code', r.get('_key', '')))).strip()
        if not m_id:
            continue

        node_map[m_id] = dict(r)
        dur = float(r.get('duration_days', 5.0) or 5.0)
        duration[m_id] = max(dur, 0.0)

        preds_raw = str(r.get('predecessor_ids', '')).strip()
        preds = [p.strip() for p in preds_raw.split(',') if p.strip()] if preds_raw else []

        for p in preds:
            graph[p].append(m_id)
            rev_graph[m_id].append(p)
            in_degree[m_id] += 1
            if p not in in_degree:
                in_degree[p] = 0

    all_nodes = list(node_map.keys())
    if not all_nodes:
        return records

    # Topological Sort via Kahn's Algorithm
    zero_in = deque([n for n in all_nodes if in_degree[n] == 0])
    topo_order = []

    while zero_in:
        curr = zero_in.popleft()
        topo_order.append(curr)
        for neighbor in graph[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                zero_in.append(neighbor)

    # Cycle Detection Check
    if len(topo_order) < len(all_nodes):
        cycle_nodes = [n for n in all_nodes if n not in topo_order]
        for r in records:
            r['is_critical_path'] = 'False'
            r['cpm_error'] = 'CIRCULAR_DEPENDENCY'
            r['cpm_error_details'] = f"Circular milestone loop detected in nodes: {', '.join(cycle_nodes)}"
        return records

    # Forward Pass: Early Start (ES) and Early Finish (EF)
    es = {n: 0.0 for n in all_nodes}
    ef = {n: 0.0 for n in all_nodes}

    for n in topo_order:
        ef[n] = es[n] + duration[n]
        for neighbor in graph[n]:
            if ef[n] > es[neighbor]:
                es[neighbor] = ef[n]

    max_project_time = max(ef.values()) if ef else 0.0

    # Backward Pass: Late Finish (LF) and Late Start (LS)
    lf = {n: max_project_time for n in all_nodes}
    ls = {n: max_project_time - duration[n] for n in all_nodes}

    for n in reversed(topo_order):
        ls[n] = lf[n] - duration[n]
        for pred in rev_graph[n]:
            if ls[n] < lf[pred]:
                lf[pred] = ls[n]

    # Resolve Base Project Start Date
    base_date = None
    if project_start_date:
        try:
            base_date = datetime.date.fromisoformat(str(project_start_date).strip())
        except (ValueError, TypeError):
            base_date = None

    if not base_date:
        for r in records:
            p_start = r.get('project_start_date', r.get('actual_start_date', ''))
            if p_start:
                try:
                    base_date = datetime.date.fromisoformat(str(p_start).strip())
                    break
                except (ValueError, TypeError):
                    pass

    if not base_date:
        base_date = datetime.date(2026, 10, 1)  # Default: DoD FY2027 Start

    # Parse PTO dates if provided
    pto_set = set()
    if pto_dates:
        for p in str(pto_dates).split(','):
            p = p.strip()
            if p:
                try:
                    pto_set.add(datetime.date.fromisoformat(p))
                except ValueError:
                    pass

    # Build holiday calendar covering relevant year span
    start_year = base_date.year
    end_year = start_year + max(int(max_project_time / 200) + 2, 3)
    fed_holidays = get_federal_holidays(start_year, end_year)
    all_exclusions = fed_holidays.union(pto_set)

    # Calculate Slack, Critical Path, and Calendar Dates with Holiday Skipping
    out_records = []
    for r in records:
        m_id = str(r.get('milestone_id', r.get('wbs_code', r.get('_key', '')))).strip()
        if m_id in node_map:
            slack = round(ls[m_id] - es[m_id], 2)
            is_cp = (slack <= 0.001)

            # Working-day offset calculations
            r['early_start_day'] = es[m_id]
            r['early_finish_day'] = ef[m_id]
            r['late_start_day'] = ls[m_id]
            r['late_finish_day'] = lf[m_id]
            r['slack_days'] = slack
            r['is_critical_path'] = 'True' if is_cp else 'False'
            r['cpm_error'] = 'None'

            # Calendar-aware date conversions (skipping weekends & federal holidays)
            es_dt = add_working_days(base_date, es[m_id], all_exclusions)
            ef_dt = add_working_days(es_dt, duration[m_id], all_exclusions)
            ls_dt = add_working_days(base_date, ls[m_id], all_exclusions)
            lf_dt = add_working_days(ls_dt, duration[m_id], all_exclusions)

            r['early_start_date'] = es_dt.strftime('%Y-%m-%d')
            r['early_finish_date'] = ef_dt.strftime('%Y-%m-%d')
            r['late_start_date'] = ls_dt.strftime('%Y-%m-%d')
            r['late_finish_date'] = lf_dt.strftime('%Y-%m-%d')
            r['federal_holidays_in_window'] = count_holidays_in_span(es_dt, ef_dt, fed_holidays)
            r['calendar_span_days'] = (ef_dt - es_dt).days

        out_records.append(r)

    return out_records


if SDK_AVAILABLE:
    @Configuration()
    class GetCriticalPathCommand(StreamingCommand):
        start_date = Option(require=False, default=None, doc='Project Start Date (YYYY-MM-DD)')
        pto_dates = Option(require=False, default=None, doc='Comma-separated PTO dates (YYYY-MM-DD)')

        def stream(self, records):
            buffer = list(records)
            result = calculate_cpm(buffer, project_start_date=self.start_date, pto_dates=self.pto_dates)
            for item in result:
                yield item

    if __name__ == '__main__':
        dispatch(GetCriticalPathCommand, sys.argv, sys.stdin, sys.stdout, __name__)
else:
    # Standalone execution / unit test mode
    if __name__ == '__main__':
        test_records = [
            {"milestone_id": "M-01", "duration_days": 10, "predecessor_ids": ""},
            {"milestone_id": "M-02", "duration_days": 15, "predecessor_ids": "M-01"},
            {"milestone_id": "M-03", "duration_days": 5, "predecessor_ids": "M-01"},
            {"milestone_id": "M-04", "duration_days": 20, "predecessor_ids": "M-02,M-03"}
        ]
        res = calculate_cpm(test_records, project_start_date="2026-10-01")
        import json
        print(json.dumps(res, indent=2))
