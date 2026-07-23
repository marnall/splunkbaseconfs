#!/usr/bin/env python3
"""
CIM Assessment Report Generator

Machine Data Insights Inc.

Copyright 2025-2026 Machine Data Insights Inc.
Licensed under the Apache License, Version 2.0
See LICENSE file for details.

Generates a professional Word document from CAT v2.7.5 Splunk search results.
Uses only Python standard library (zipfile + XML) -- no external dependencies.

Usage:
    python generate_report.py --env "Production" --data-dir ./report_data --output report.docx

Expected CSV files in data-dir:
    compliance_summary.csv   - From ds_table_compliance_detail query
    compliance_detail.csv    - From ds_table_dm_summary query
    field_gaps.csv           - From ds_table_field_detail (gaps only)
    unmapped.csv             - From ds_unmapped_table query
    mapped.csv               - From ds_mapped_table query
    remediation.csv          - From ds_priority_table query
    acceleration.csv         - From ds_accel_table query
    kpi.csv                  - From KPI summary query
    cim_coverage.csv         - From CIM Coverage tstats query
    cim_coverage_prior.csv   - From prior CIM Coverage summary index snapshot
    trends.csv               - From trend comparison query
"""

import argparse
import csv
import json
import os
import sys
import zipfile
from datetime import datetime

# ---------------------------------------------------------------------------
# CLI Args
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CIM Assessment Report Generator")
parser.add_argument("--env", default="Production", help="Environment name")
parser.add_argument("--data-dir", default="./report_data", help="CSV data directory")
parser.add_argument("--output", default="CIM_Assessment_Report.docx", help="Output path")
parser.add_argument("--trend-days", type=int, default=7, help="Trend comparison window")
parser.add_argument("--scope", default="all", help="Category scope filter")
parser.add_argument("--excluded-count", type=int, default=0, help="Excluded sourcetypes count")
args, _ = parser.parse_known_args()

ENV_NAME = args.env
DATA_DIR = args.data_dir
OUTPUT = args.output
TREND_DAYS = args.trend_days
SCOPE = args.scope.lower()
SCOPE_LABEL = "" if SCOPE == "all" else f" ({SCOPE[0].upper()}{SCOPE[1:]})"
EXCLUDED_COUNT = args.excluded_count
REPORT_DATE = datetime.now().strftime("%B %d, %Y")

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
C = {
    "navy": "1B2A4A", "blue": "2E75B6", "ltBlue": "D5E8F0",
    "green": "53A051", "ltGreen": "E2F0D9",
    "yellow": "F8BC06", "ltYellow": "FFF2CC",
    "red": "DC4E41", "ltRed": "FCE4EC",
    "gray": "F2F2F2", "darkGray": "3C3C3C",
    "white": "FFFFFF", "black": "000000",
}

# ---------------------------------------------------------------------------
# CSV Parser
# ---------------------------------------------------------------------------
def parse_csv(filepath):
    if not os.path.isfile(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return [{k.strip(): v.strip() for k, v in row.items() if k}
                    for row in reader]
    except Exception as e:
        print(f"  Warning: Could not parse {filepath}: {e}")
        return []

# ---------------------------------------------------------------------------
# Data (populated by generate_report())
# ---------------------------------------------------------------------------
kpi = []
cim_coverage = []
cim_coverage_prior = []
compliance_summary = []
compliance_detail = []
field_gaps = []
unmapped = []
mapped = []
remediation = []
acceleration = []
trends = []
inventory_version = {}  # sourcetype inventory sidecar (changelog/"as of")

# ---------------------------------------------------------------------------
# KPI Helpers
# ---------------------------------------------------------------------------
def kpi_num(field):
    if not kpi:
        return 0.0
    return float(kpi[0].get(field, "0") or "0")

def kpi_color(val):
    if val >= 90: return C["green"]
    if val >= 70: return C["yellow"]
    return C["red"]

def kpi_bg(val):
    if val >= 90: return C["ltGreen"]
    if val >= 70: return C["ltYellow"]
    return C["ltRed"]

def rating_text(val):
    if val >= 90: return "Excellent"
    if val >= 70: return "Good"
    if val >= 50: return "Fair"
    return "Needs Improvement"

def get_field(row, *keys):
    for k in keys:
        v = row.get(k, "")
        if v:
            return v
    return ""


# ---------------------------------------------------------------------------
# XML Helpers -- OOXML building blocks
# ---------------------------------------------------------------------------
PAGE_W = 10080  # US Letter 12240 - 2*1080 margins

def esc(text):
    """XML-escape text."""
    if not text:
        return ""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def _run(text, sz=22, bold=False, italic=False, color=None, font="Arial"):
    """w:r element with text."""
    rpr = (f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>'
           f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>')
    if bold:
        rpr += '<w:b/><w:bCs/>'
    if italic:
        rpr += '<w:i/><w:iCs/>'
    if color:
        rpr += f'<w:color w:val="{color}"/>'
    return (f'<w:r><w:rPr>{rpr}</w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>')


def _tab():
    return '<w:r><w:tab/></w:r>'


def _page_break():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def _page_field(sz=14, color="3C3C3C"):
    """PAGE number field (three runs: begin, instrText, end)."""
    rpr = (f'<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
           f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
           f'<w:color w:val="{color}"/></w:rPr>')
    return (f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r>{rpr}<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
            f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>')


def _para(runs, align=None, before=None, after=None, line=240,
          style=None, numpr=False, bdr_bottom=None, bdr_top=None, tabs=None):
    """w:p element."""
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if numpr:
        ppr.append('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>')
    if tabs:
        ppr.append('<w:tabs>' +
                   ''.join(f'<w:tab w:val="{v}" w:pos="{p}"/>' for v, p in tabs) +
                   '</w:tabs>')
    sp_attrs = f' w:line="{line}" w:lineRule="auto"'
    if before is not None:
        sp_attrs += f' w:before="{before}"'
    if after is not None:
        sp_attrs += f' w:after="{after}"'
    ppr.append(f'<w:spacing{sp_attrs}/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    if bdr_bottom or bdr_top:
        bdr = '<w:pBdr>'
        if bdr_top:
            sz, col, sp = bdr_top
            bdr += f'<w:top w:val="single" w:sz="{sz}" w:color="{col}" w:space="{sp}"/>'
        if bdr_bottom:
            sz, col, sp = bdr_bottom
            bdr += f'<w:bottom w:val="single" w:sz="{sz}" w:color="{col}" w:space="{sp}"/>'
        bdr += '</w:pBdr>'
        ppr.append(bdr)
    ppr_xml = f'<w:pPr>{"".join(ppr)}</w:pPr>' if ppr else ''
    return f'<w:p>{ppr_xml}{runs}</w:p>'


def _cell(paras, width=None, fill=None, borders=True, margins=(20, 20, 60, 60),
          valign="center"):
    """w:tc element."""
    tcp = []
    if width:
        tcp.append(f'<w:tcW w:w="{width}" w:type="dxa"/>')
    # Borders
    if borders:
        bdr = '<w:tcBorders>'
        for s in ('top', 'bottom', 'left', 'right'):
            bdr += f'<w:{s} w:val="single" w:sz="4" w:color="CCCCCC" w:space="0"/>'
        bdr += '</w:tcBorders>'
    else:
        bdr = '<w:tcBorders>'
        for s in ('top', 'bottom', 'left', 'right'):
            bdr += f'<w:{s} w:val="none" w:sz="0" w:color="auto" w:space="0"/>'
        bdr += '</w:tcBorders>'
    tcp.append(bdr)
    if fill:
        tcp.append(f'<w:shd w:fill="{fill}" w:val="clear"/>')
    t, b, l, r = margins
    tcp.append(f'<w:tcMar>'
               f'<w:top w:w="{t}" w:type="dxa"/>'
               f'<w:bottom w:w="{b}" w:type="dxa"/>'
               f'<w:left w:w="{l}" w:type="dxa"/>'
               f'<w:right w:w="{r}" w:type="dxa"/>'
               f'</w:tcMar>')
    tcp.append(f'<w:vAlign w:val="{valign}"/>')
    return f'<w:tc><w:tcPr>{"".join(tcp)}</w:tcPr>{paras}</w:tc>'


def _row(cells):
    return f'<w:tr>{"".join(cells)}</w:tr>'


def _table(rows, col_widths):
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)
    return (f'<w:tbl><w:tblPr>'
            f'<w:tblW w:w="{sum(col_widths)}" w:type="dxa"/>'
            f'<w:jc w:val="center"/>'
            f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
            f'{"".join(rows)}</w:tbl>')


# ---------------------------------------------------------------------------
# High-level cell formatters
# ---------------------------------------------------------------------------
def _cell_p(text, sz=17, bold=False, color=None, align=None):
    """Single-paragraph cell content (returns just the w:p)."""
    return _para(_run(text or "\u2014", sz=sz, bold=bold,
                      color=color or C["darkGray"]),
                 align=align, before=0, after=0)


def hdr_cell(text, w):
    return _cell(_cell_p(text, sz=16, bold=True, color=C["white"]),
                 width=w, fill=C["navy"], margins=(30, 30, 60, 60))


def d_cell(text, w, fill=None, color=None, bold=False, align=None):
    return _cell(_cell_p(text, color=color, bold=bold, align=align),
                 width=w, fill=fill)


def pct_cell(text, w):
    try:
        val = float(text)
    except (ValueError, TypeError):
        return d_cell(text or "\u2014", w, align="center")
    if val >= 90:
        fill, clr = C["ltGreen"], C["darkGray"]
    elif val >= 70:
        fill, clr = C["ltYellow"], C["darkGray"]
    else:
        fill, clr = C["ltRed"], C["red"]
    return d_cell(f"{val:.1f}%", w, fill=fill, color=clr, align="center")


def num_cell(text, w):
    return d_cell(text, w, align="right")


# ---------------------------------------------------------------------------
# High-level document helpers
# ---------------------------------------------------------------------------
def add_heading(body, text, level=1):
    style = "Heading1" if level == 1 else "Heading2"
    body.append(_para(_run(text), style=style))


def add_text(body, text, color=None, italic=False, sz=22):
    body.append(_para(_run(text, sz=sz, color=color or C["darkGray"],
                           italic=italic), after=200))


def add_bullet(body, text):
    body.append(_para(_run(text, sz=22), numpr=True, after=80))


def add_data_table(body, headers, widths, data, row_fn):
    rows = [_row([hdr_cell(h, w) for h, w in zip(headers, widths)])]
    for r in data:
        rows.append(_row(row_fn(r, widths)))
    body.append(_table(rows, widths))


# ===========================================================================
# Build Document Body
# ===========================================================================
def build_body():
    body = []

    mapping_val = kpi_num("mapping_quality")
    data_qual_val = kpi_num("data_quality")
    value_comp_val = kpi_num("value_compliance")
    overall_val = kpi_num("overall_quality")

    # CIM Coverage from separate tstats query
    cim_cov_val = 0.0
    if cim_coverage:
        cim_cov_val = float(cim_coverage[0].get("cim_coverage", "0") or "0")

    # ── COVER PAGE ────────────────────────────────────────────────────
    # Spacer
    body.append(_para('', before=360))

    # Title
    body.append(_para(
        _run("CIM ASSESSMENT REPORT", sz=52, bold=True,
             color=C["navy"]),
        align="center", after=200))

    # Scope (only shown when not "all")
    if SCOPE != "all":
        body.append(_para(
            _run(f"Scope: {SCOPE[0].upper()}{SCOPE[1:]}", sz=28,
                 color=C["blue"]),
            align="center", after=100))

    # Environment
    body.append(_para(
        _run(f"Environment: {ENV_NAME}", sz=28, color=C["blue"]),
        align="center", after=100))

    # Date
    body.append(_para(
        _run(REPORT_DATE, sz=24, color=C["darkGray"]),
        align="center", after=600))

    # Horizontal rule
    body.append(_para('', after=600,
                       bdr_bottom=(12, C["blue"], 1)))

    # KPI Score Boxes
    kpi_items = [
        ("CIM Coverage", cim_cov_val),
        ("Mapping Quality", mapping_val),
        ("Data Quality", data_qual_val),
        ("Value Compliance", value_comp_val),
        ("Overall Quality", overall_val),
    ]
    kw = 2016
    score_cells = []
    label_cells = []
    for label, val in kpi_items:
        score = "N/A" if val == 0 else f"{val:.1f}%"
        bg = C["gray"] if val == 0 else kpi_bg(val)
        tc = C["darkGray"] if val == 0 else kpi_color(val)
        score_cells.append(
            _cell(_para(_run(score, sz=36, bold=True, color=tc),
                        align="center", before=0, after=0),
                  width=kw, fill=bg, borders=False, margins=(120, 20, 100, 100)))
        label_cells.append(
            _cell(_para(_run(label, sz=16, color=C["darkGray"]),
                        align="center", before=0, after=0),
                  width=kw, fill=bg, borders=False, margins=(20, 120, 100, 100)))
    body.append(_table([_row(score_cells), _row(label_cells)],
                       [kw] * 5))

    # KPI scope note
    body.append(_para(
        _run("Mapping Quality, Data Quality, Value Compliance, and Overall Quality "
             "reflect only sourcetypes mapped to CIM data models.",
             sz=18, italic=True, color=C["darkGray"]),
        align="center", before=80, after=0))

    # Overall rating -- capped by CIM Coverage so that unmapped data drags the
    # headline rating down even when mapped-data quality is high. The four
    # quality KPIs only score sourcetypes already mapped to CIM models, so on
    # their own they can read "Excellent" while a quarter of the environment is
    # invisible to CIM. CIM Coverage is the key high-level metric, so it gates.
    rating_val = min(cim_cov_val, overall_val) if cim_cov_val > 0 else overall_val
    body.append(_para(
        _run(f"Overall Rating: {rating_text(rating_val)}", sz=28, bold=True,
             color=kpi_color(rating_val)),
        align="center", before=320))

    # How to Read This Report
    body.append(_para(
        _run("How to Read This Report", sz=22, bold=True, color=C["navy"]),
        align="center", before=200,
        bdr_top=(4, C["blue"], 8)))

    guide = [
        ("Executive Summary",
         "Start here. Key findings and overall compliance posture at a glance."),
        ("Compliance Trends",
         f"Are things getting better? {TREND_DAYS}-day comparison with improvement indicators."),
        ("Compliance by Data Model",
         "Which data models have gaps? Focus on scores below 90%."),
        ("Compliance by Data Source",
         "Which specific index/sourcetype combinations need attention?"),
        ("Data Source Mapping Status",
         "Are there sourcetypes in your environment not mapped to any CIM model?"),
        ("Remediation Priorities",
         "Where to focus first. Ranked by impact: low quality on high-volume sources."),
        ("Field-Level Gaps",
         "The specific fields to fix. Actionable targets for TA development."),
        ("Acceleration Health",
         "Are data models fully accelerated? Incomplete acceleration causes missing data."),
    ]
    guide_rows = []
    for sec, desc in guide:
        guide_rows.append(_row([
            _cell(_para(_run(sec, sz=18, bold=True, color=C["blue"]),
                        before=0, after=0),
                  width=2900, borders=False, margins=(20, 20, 80, 80)),
            _cell(_para(_run(desc, sz=18, color=C["darkGray"]),
                        before=0, after=0),
                  width=7180, borders=False, margins=(20, 20, 80, 80)),
        ]))
    body.append(_table(guide_rows, [2900, 7180]))

    # Spacer after How to Read This Report
    body.append(_para('', before=200))

    body.append(_page_break())

    # ── EXECUTIVE SUMMARY ─────────────────────────────────────────────
    add_heading(body, "Executive Summary")

    total_models = len(compliance_detail)
    total_sources = len(compliance_summary)
    total_gaps = len(field_gaps)
    gap_count = sum(1 for f in field_gaps
                    if f.get("Count", f.get("field_count", "0")) in ("0", ""))

    parts = (
        f"This report assesses CIM (Common Information Model) compliance "
        f"for the {ENV_NAME} environment as of {REPORT_DATE}. "
    )
    if SCOPE != "all":
        parts += f"Scope: {SCOPE} data models only. "
    parts += (
        f"The analysis covers {total_models} data model/dataset combinations "
        f"across {total_sources} data source configurations. "
        f"{total_gaps} field-level gaps were identified requiring remediation."
    )
    body.append(_para(_run(parts, sz=22), after=200))

    # Scope note
    body.append(_para(
        _run("Note: ", sz=20, bold=True, italic=True, color=C["darkGray"]) +
        _run("Quality scores reflect only data sources that are mapped to CIM data models. "
             "Unmapped sourcetypes are not included in these metrics. "
             "See the Data Source Mapping Status section for unmapped sourcetype details.",
             sz=20, italic=True, color=C["darkGray"]),
        after=200))

    # Key Findings
    body.append(_para(_run("Key Findings", sz=24, bold=True, color=C["navy"]),
                      before=200, after=100))

    if overall_val >= 90:
        add_bullet(body, f"Overall CIM Quality is excellent at {overall_val:.1f}%.")
    elif overall_val >= 70:
        add_bullet(body, f"Overall CIM Quality is good at {overall_val:.1f}%, with room for improvement.")
    else:
        add_bullet(body, f"Overall CIM Quality requires attention at {overall_val:.1f}%.")
    if mapping_val < data_qual_val:
        add_bullet(body, f"Field mapping ({mapping_val:.1f}%) is the primary improvement area -- unmapped fields reduce ES detection coverage.")
    if gap_count > 0:
        add_bullet(body, f"{gap_count} required/recommended fields are unmapped or have zero data coverage.")
    if cim_cov_val > 0:
        mapped_count = int(cim_coverage[0].get("mapped", "0") or "0")
        total_count = int(cim_coverage[0].get("total", "0") or "0")
        add_bullet(body, f"CIM Coverage is {cim_cov_val:.1f}% -- {mapped_count} of {total_count} active sourcetypes are mapped to at least one CIM data model.")
    if unmapped:
        excl = f" ({EXCLUDED_COUNT} additional reviewed and excluded.)" if EXCLUDED_COUNT > 0 else ""
        add_bullet(body, f"{len(unmapped)} sourcetype(s) are present in the environment but not mapped to any CIM data model.{excl}")

    # ── COMPLIANCE TRENDS ─────────────────────────────────────────────
    if trends and compliance_detail:
        prior_map = {}
        for r in trends:
            key = (f"{r.get('Data Model', r.get('modelName', ''))}/"
                   f"{r.get('Dataset', r.get('dataset', ''))}")
            prior_map[key] = float(
                r.get("Prior Overall %", r.get("prior_overall_pct", "0")) or "0")

        trend_rows_data = []
        for r in compliance_detail:
            model = get_field(r, "Data Model", "modelName")
            dataset = get_field(r, "Dataset", "dataset")
            key = f"{model}/{dataset}"
            current = float(r.get("Overall %", r.get("overall_pct", "0")) or "0")
            prior = prior_map.get(key)
            change = (current - prior) if prior is not None else None
            trend_rows_data.append({
                "model": model, "dataset": dataset,
                "prior": prior, "current": current, "change": change
            })
        trend_rows_data.sort(key=lambda x: (1, 0) if x["change"] is None else (0, -x["change"]))

        add_heading(body, f"Compliance Trends ({TREND_DAYS}-Day Comparison)")
        add_text(body, f"Overall quality scores compared to {TREND_DAYS} days ago. Improvements are shown in green, declines in red.")

        # CIM Coverage trend summary
        if cim_cov_val > 0:
            prior_cov = 0.0
            if cim_coverage_prior:
                prior_cov = float(cim_coverage_prior[0].get("prior_cim_coverage", "0") or "0")
            if prior_cov > 0:
                cov_change = cim_cov_val - prior_cov
                if cov_change > 0.5:
                    arrow, color = "\u25B2", C["green"]
                    change_str = f"+{cov_change:.1f}%"
                elif cov_change < -0.5:
                    arrow, color = "\u25BC", C["red"]
                    change_str = f"{cov_change:.1f}%"
                else:
                    arrow, color = "\u2014", C["darkGray"]
                    change_str = f"{cov_change:.1f}%"
                body.append(_para(
                    _run("CIM Coverage: ", sz=22, bold=True, color=C["navy"]) +
                    _run(f"{cim_cov_val:.1f}%", sz=22, bold=True, color=kpi_color(cim_cov_val)) +
                    _run(f"  (was {prior_cov:.1f}%, change {change_str} {arrow})",
                         sz=22, color=color),
                    after=200))
            else:
                body.append(_para(
                    _run("CIM Coverage: ", sz=22, bold=True, color=C["navy"]) +
                    _run(f"{cim_cov_val:.1f}%", sz=22, bold=True, color=kpi_color(cim_cov_val)) +
                    _run(f"  (no prior data for comparison)", sz=22, italic=True, color=C["darkGray"]),
                    after=200))

        tw = [2400, 2000, 1500, 1500, 1400, 1280]
        th = ["Data Model", "Dataset", f"{TREND_DAYS} Days Ago", "Current", "Change", "Trend"]

        def fmt_trend(r, w):
            prior_t = f"{r['prior']:.1f}%" if r["prior"] is not None else "\u2014"
            if r["change"] is None:
                ct, cc, ts = "\u2014", C["darkGray"], "(new)"
            elif r["change"] > 0.5:
                ct, cc, ts = f"+{r['change']:.1f}%", C["green"], "\u25B2"
            elif r["change"] < -0.5:
                ct, cc, ts = f"{r['change']:.1f}%", C["red"], "\u25BC"
            else:
                ct, cc, ts = f"{r['change']:.1f}%", C["darkGray"], "\u2014"
            return [
                d_cell(r["model"], w[0]), d_cell(r["dataset"], w[1]),
                num_cell(prior_t, w[2]), pct_cell(str(r["current"]), w[3]),
                d_cell(ct, w[4], color=cc, bold=True, align="center"),
                d_cell(ts, w[5], color=cc, bold=True, align="center"),
            ]
        add_data_table(body, th, tw, trend_rows_data, fmt_trend)

    elif not trends and compliance_detail:
        add_heading(body, f"Compliance Trends ({TREND_DAYS}-Day Comparison)")
        add_text(body,
                 f"Compliance trends will appear after {TREND_DAYS} days of collection data. "
                 f"The collection search runs daily and stores historical scores in the summary index.",
                 italic=True)

    # ── COMPLIANCE BY DATA MODEL ──────────────────────────────────────
    add_heading(body, "Compliance by Data Model")
    add_text(body,
             "Quality scores aggregated by data model and dataset. Mapping % measures "
             "required/recommended field coverage. Data Quality % measures average data "
             "population across mapped fields. Overall % is the combined score.")

    if compliance_detail:
        cw = [2200, 2200, 1420, 1420, 1420, 1420]
        def fmt_detail(r, w):
            return [
                d_cell(get_field(r, "Data Model", "modelName"), w[0]),
                d_cell(get_field(r, "Dataset", "dataset"), w[1]),
                num_cell(get_field(r, "indexes", "sourcetypes"), w[2]),
                pct_cell(get_field(r, "Mapping %", "mapping_pct"), w[3]),
                pct_cell(get_field(r, "Data Quality %", "data_quality_pct"), w[4]),
                pct_cell(get_field(r, "Overall %", "overall_pct"), w[5]),
            ]
        add_data_table(body, ["Data Model", "Dataset", "Indexes", "Mapping %",
                               "Data Quality %", "Overall %"], cw, compliance_detail, fmt_detail)

    # ── COMPLIANCE BY DATA SOURCE ─────────────────────────────────────
    add_heading(body, "Compliance by Data Source")
    add_text(body,
             "Per index/sourcetype compliance breakdown. This view reveals which "
             "specific data sources have the greatest compliance gaps.")

    if compliance_summary:
        cw = [1350, 1050, 1100, 1280, 1300, 1400, 1300, 1300]
        def fmt_summary(r, w):
            return [
                d_cell(get_field(r, "Data Model", "modelName"), w[0]),
                d_cell(get_field(r, "Dataset", "dataset"), w[1]),
                d_cell(get_field(r, "index", "Index"), w[2]),
                d_cell(get_field(r, "sourcetype", "Sourcetype"), w[3]),
                pct_cell(r.get("Mapping %", ""), w[4]),
                pct_cell(r.get("Data Quality %", ""), w[5]),
                pct_cell(r.get("Overall %", ""), w[6]),
                num_cell(get_field(r, "Events", "event_count"), w[7]),
            ]
        add_data_table(body, ["Data Model", "Dataset", "Index", "Sourcetype",
                               "Mapping %", "Data Quality %", "Overall %", "Events"],
                       cw, compliance_summary, fmt_summary)

    # ── DATA SOURCE MAPPING STATUS ────────────────────────────────────
    add_heading(body, "Data Source Mapping Status")

    if inventory_version.get("last_updated"):
        by = inventory_version.get("updated_by", "")
        note = inventory_version.get("note", "")
        base_cat = inventory_version.get("base_catalog_last_updated", "")
        as_of = (f"Sourcetype classifications (vendor, relevance, scope) "
                 f"are drawn from a reference inventory last updated "
                 f"{inventory_version['last_updated']}"
                 + (f" by {by}" if by else "") + "."
                 + (f" Base sourcetype catalog as of {base_cat}."
                    if base_cat else "")
                 + (f" {note}" if note else ""))
        add_text(body, as_of, italic=True, color=C["darkGray"], sz=18)

    add_heading(body, "Unmapped Sourcetypes", level=2)

    if not unmapped:
        excl = (f" ({EXCLUDED_COUNT} additional sourcetypes were reviewed and excluded "
                f"-- see the cim_sourcetype_exclusions lookup.)" if EXCLUDED_COUNT > 0 else "")
        add_text(body,
                 f"All sourcetypes in the environment are mapped to at least one CIM data model.{excl}",
                 color=C["green"], italic=True)
    else:
        excl = (f" ({EXCLUDED_COUNT} additional sourcetypes were reviewed and excluded.)"
                if EXCLUDED_COUNT > 0 else "")
        add_text(body,
                 f"{len(unmapped)} sourcetype(s) are not mapped to any CIM data model. "
                 f"These represent potential gaps in security monitoring coverage.{excl}")
        has_vendor = any(r.get("Vendor") or r.get("vendor") for r in unmapped)
        if has_vendor:
            cw = [3200, 1800, 1300, 1180, 1200, 1400]
            def fmt_unmap_e(r, w):
                return [
                    d_cell(get_field(r, "sourcetype", "Sourcetype"), w[0]),
                    d_cell(get_field(r, "Vendor", "vendor"), w[1]),
                    d_cell(get_field(r, "Tech Category", "tech_category"), w[2]),
                    d_cell(get_field(r, "Relevance", "security_relevance"), w[3]),
                    d_cell(get_field(r, "Scope", "scope"), w[4]),
                    num_cell(get_field(r, "Events", "event_count"), w[5]),
                ]
            add_data_table(body, ["Sourcetype", "Vendor", "Tech Category", "Relevance", "Scope", "Events"],
                           cw, unmapped, fmt_unmap_e)
        else:
            cw = [5040, 5040]
            def fmt_unmap_s(r, w):
                return [
                    d_cell(get_field(r, "sourcetype", "Sourcetype"), w[0]),
                    num_cell(get_field(r, "Events", "event_count"), w[1]),
                ]
            add_data_table(body, ["Sourcetype", "Events"], cw, unmapped, fmt_unmap_s)

    add_heading(body, "Mapped Sourcetypes", level=2)
    if mapped:
        has_vendor = any(r.get("Vendor") or r.get("vendor") for r in mapped)
        if has_vendor:
            cw = [2400, 1400, 1200, 1100, 1200, 2780]
            def fmt_mapped(r, w):
                return [
                    d_cell(get_field(r, "sourcetype", "Sourcetype"), w[0]),
                    d_cell(get_field(r, "Vendor", "vendor"), w[1]),
                    d_cell(get_field(r, "Relevance", "security_relevance"), w[2]),
                    d_cell(get_field(r, "Scope", "scope"), w[3]),
                    num_cell(get_field(r, "Events", "event_count"), w[4]),
                    d_cell(get_field(r, "Mapped To", "mapped_models"), w[5]),
                ]
            add_data_table(body, ["Sourcetype", "Vendor", "Relevance", "Scope",
                                   "Events", "Mapped To"],
                           cw, mapped, fmt_mapped)
        else:
            cw = [3400, 1680, 5000]
            def fmt_mapped(r, w):
                return [
                    d_cell(get_field(r, "sourcetype", "Sourcetype"), w[0]),
                    num_cell(get_field(r, "Events", "event_count"), w[1]),
                    d_cell(get_field(r, "Mapped To", "mapped_models"), w[2]),
                ]
            add_data_table(body, ["Sourcetype", "Events", "Mapped To"],
                           cw, mapped, fmt_mapped)

    # ── REMEDIATION PRIORITIES ────────────────────────────────────────
    add_heading(body, "Remediation Priorities")
    add_text(body,
             "Data sources ranked by remediation impact. Priority score combines "
             "quality deficit with event volume -- low quality on high-volume sources is prioritized.")

    if remediation:
        cw = [1200, 1080, 1280, 1100, 1100, 1080, 1040, 1000, 1200]
        def fmt_remed(r, w):
            return [
                d_cell(get_field(r, "Data Model", "modelName"), w[0]),
                d_cell(get_field(r, "Dataset", "dataset"), w[1]),
                d_cell(get_field(r, "sourcetype", "Sourcetype"), w[2]),
                pct_cell(get_field(r, "Overall %", "overall_quality_pct"), w[3]),
                pct_cell(get_field(r, "Mapping %", "rec_field_coverage_pct"), w[4]),
                num_cell(get_field(r, "Events", "event_count"), w[5]),
                num_cell(get_field(r, "Priority", "priority_score"), w[6]),
                num_cell(get_field(r, "Missing #", "missing_rec_count"), w[7]),
                d_cell(get_field(r, "Required Tags", "required_tags"), w[8]),
            ]
        add_data_table(body, ["Data Model", "Dataset", "Sourcetype", "Overall %",
                               "Mapping %", "Events", "Priority", "Missing #",
                               "Required Tags"],
                       cw, remediation, fmt_remed)

    # ── FIELD-LEVEL GAPS ──────────────────────────────────────────────
    add_heading(body, "Field-Level Gaps")
    add_text(body,
             "Required and recommended fields that are either unmapped (zero count) or have "
             "non-compliant prescribed values. These represent specific remediation targets "
             "for TA development or field extraction configuration.")

    if field_gaps:
        cw = [1500, 1500, 1300, 1500, 880, 780, 1000, 1620]
        def fmt_gaps(r, w):
            cnt = r.get("Count", r.get("field_count", "0")) or "0"
            rf = C["ltRed"] if cnt in ("0", "") else None
            return [
                d_cell(get_field(r, "Data Model", "modelName"), w[0], fill=rf),
                d_cell(get_field(r, "Dataset", "dataset"), w[1], fill=rf),
                d_cell(get_field(r, "sourcetype", "Sourcetype"), w[2], fill=rf),
                d_cell(get_field(r, "Field", "field"), w[3], fill=rf, bold=True),
                d_cell(get_field(r, "Class", "field_class"), w[4], fill=rf),
                num_cell(cnt, w[5]),
                pct_cell(get_field(r, "Coverage %", "percent_coverage"), w[6]),
                d_cell(get_field(r, "Value Compliance", "value_compliance_pct") or "\u2014",
                       w[7], fill=rf, align="center"),
            ]
        add_data_table(body, ["Data Model", "Dataset", "Sourcetype", "Field",
                               "Class", "Count", "Coverage %", "Value Compliance"],
                       cw, field_gaps, fmt_gaps)
    else:
        add_text(body, "No field-level gaps identified.", color=C["green"], italic=True)

    # ── ACCELERATION HEALTH ───────────────────────────────────────────
    add_heading(body, "Data Model Acceleration Health")
    add_text(body,
             "Acceleration status for CIM data models. Models not accelerated or with errors "
             "will not produce reliable data for CIM analysis. Complete acceleration is required "
             "for accurate field coverage assessment.")

    if acceleration:
        cw = [2400, 1300, 1400, 1300, 1300, 1300, 1080]
        def fmt_accel(r, w):
            st = get_field(r, "status", "Status") or "Unknown"
            sf = {
                "Complete": C["ltGreen"], "Building": C["ltYellow"],
                "Error": C["ltRed"]
            }.get(st, C["gray"])
            return [
                d_cell(get_field(r, "Data Model", "modelName"), w[0]),
                d_cell(st, w[1], fill=sf, bold=True, align="center"),
                pct_cell(get_field(r, "Complete %", "complete_pct"), w[2]),
                d_cell(get_field(r, "Earliest", "earliest_time"), w[3]),
                d_cell(get_field(r, "Latest", "latest_time"), w[4]),
                d_cell(get_field(r, "Retention (days)", "retention_days"), w[5], align="center"),
                num_cell(get_field(r, "Searches", "access_count"), w[6]),
            ]
        add_data_table(body, ["Data Model", "Status", "Complete %", "Earliest",
                               "Latest", "Retention", "Searches"],
                       cw, acceleration, fmt_accel)
    else:
        add_text(body,
                 "No acceleration data available. Export acceleration.csv manually using the "
                 "SPL query in README_Report.md, or run the acceleration health search directly "
                 "in Splunk: Settings > Data Models > check Acceleration column.",
                 italic=True)

    return '\n'.join(body)


# ===========================================================================
# Build Header & Footer
# ===========================================================================
def build_header():
    runs = (_run(f"CIM Assessment Report{SCOPE_LABEL} \u2014 {ENV_NAME}",
                 sz=16, color=C["blue"], italic=True) +
            _tab() +
            _run(REPORT_DATE, sz=16, color=C["darkGray"], italic=True))
    p = _para(runs, bdr_bottom=(8, C["blue"], 1),
              tabs=[("right", str(PAGE_W))], before=0, after=100)
    return p


def build_footer():
    runs = (_run("Machine Data Insights Inc. \u2014 CIM Assessment Toolkit v2.10.0",
                 sz=14, color=C["darkGray"], italic=True) +
            _tab() +
            _run("Page ", sz=14, color=C["darkGray"]) +
            _page_field(sz=14, color=C["darkGray"]))
    p = _para(runs, bdr_top=(8, C["blue"], 1),
              tabs=[("right", str(PAGE_W))], before=100, after=0)
    return p


# ===========================================================================
# Assemble .docx ZIP
# ===========================================================================
CONTENT_TYPES = '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/numbering.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
  <Override PartName="/word/header1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
  <Override PartName="/word/footer1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>'''

TOP_RELS = '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>'''

DOC_RELS = '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"
    Target="styles.xml"/>
  <Relationship Id="rId2"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering"
    Target="numbering.xml"/>
  <Relationship Id="rId4"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"
    Target="header1.xml"/>
  <Relationship Id="rId5"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"
    Target="footer1.xml"/>
</Relationships>'''

STYLES = f'''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
      <w:sz w:val="22"/><w:szCs w:val="22"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr>
      <w:spacing w:after="0" w:before="0" w:line="240" w:lineRule="auto"/>
    </w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="240" w:after="200"/><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
      <w:b/><w:bCs/>
      <w:color w:val="{C["navy"]}"/>
      <w:sz w:val="32"/><w:szCs w:val="32"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="180" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
      <w:b/><w:bCs/>
      <w:color w:val="{C["blue"]}"/>
      <w:sz w:val="26"/><w:szCs w:val="26"/>
    </w:rPr>
  </w:style>
</w:styles>'''

NUMBERING = '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="0">
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="bullet"/>
      <w:lvlText w:val="\u2022"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
      <w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:hint="default"/></w:rPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="1">
    <w:abstractNumId w:val="0"/>
  </w:num>
</w:numbering>'''


def save_docx(body_xml, header_xml, footer_xml, filepath):
    """Assemble all parts into a .docx ZIP file."""
    NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    document_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:document xmlns:w="{NS_W}" xmlns:r="{NS_R}">\n'
        f'<w:body>\n'
        f'{body_xml}\n'
        f'<w:sectPr>\n'
        f'  <w:headerReference w:type="default" r:id="rId4"/>\n'
        f'  <w:footerReference w:type="default" r:id="rId5"/>\n'
        f'  <w:pgSz w:w="12240" w:h="15840"/>\n'
        f'  <w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"'
        f' w:header="720" w:footer="720" w:gutter="0"/>\n'
        f'</w:sectPr>\n'
        f'</w:body>\n'
        f'</w:document>'
    )

    header1_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:hdr xmlns:w="{NS_W}">\n{header_xml}\n</w:hdr>'
    )

    footer1_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:ftr xmlns:w="{NS_W}">\n{footer_xml}\n</w:ftr>'
    )

    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', CONTENT_TYPES)
        zf.writestr('_rels/.rels', TOP_RELS)
        zf.writestr('word/_rels/document.xml.rels', DOC_RELS)
        zf.writestr('word/document.xml', document_xml)
        zf.writestr('word/styles.xml', STYLES)
        zf.writestr('word/numbering.xml', NUMBERING)
        zf.writestr('word/header1.xml', header1_xml)
        zf.writestr('word/footer1.xml', footer1_xml)


# ===========================================================================
# Main Entry Point
# ===========================================================================
def generate_report(env_name=None, data_dir=None, output_path=None,
                    trend_days=None, scope=None, excluded_count=None):
    """Generate the report. Callable from Python or CLI."""
    global ENV_NAME, DATA_DIR, OUTPUT, TREND_DAYS, SCOPE, SCOPE_LABEL
    global EXCLUDED_COUNT, REPORT_DATE
    global kpi, cim_coverage, cim_coverage_prior, compliance_summary, compliance_detail, field_gaps
    global unmapped, mapped, remediation, acceleration, trends, inventory_version

    if env_name is not None:
        ENV_NAME = env_name
    if data_dir is not None:
        DATA_DIR = data_dir
    if output_path is not None:
        OUTPUT = output_path
    if trend_days is not None:
        TREND_DAYS = trend_days
    if scope is not None:
        SCOPE = scope.lower()
    if excluded_count is not None:
        EXCLUDED_COUNT = excluded_count

    SCOPE_LABEL = ("" if SCOPE == "all"
                   else f" ({SCOPE[0].upper()}{SCOPE[1:]})")
    REPORT_DATE = datetime.now().strftime("%B %d, %Y")

    # Load data
    kpi = parse_csv(os.path.join(DATA_DIR, "kpi.csv"))
    cim_coverage = parse_csv(os.path.join(DATA_DIR, "cim_coverage.csv"))
    cim_coverage_prior = parse_csv(os.path.join(DATA_DIR, "cim_coverage_prior.csv"))
    compliance_summary = parse_csv(os.path.join(DATA_DIR, "compliance_summary.csv"))
    compliance_detail = parse_csv(os.path.join(DATA_DIR, "compliance_detail.csv"))
    field_gaps = parse_csv(os.path.join(DATA_DIR, "field_gaps.csv"))
    unmapped = parse_csv(os.path.join(DATA_DIR, "unmapped.csv"))
    mapped = parse_csv(os.path.join(DATA_DIR, "mapped.csv"))
    remediation = parse_csv(os.path.join(DATA_DIR, "remediation.csv"))
    acceleration = parse_csv(os.path.join(DATA_DIR, "acceleration.csv"))
    trends = parse_csv(os.path.join(DATA_DIR, "trends.csv"))

    inventory_version = {}
    iv_path = os.path.join(DATA_DIR, "inventory_version.json")
    if os.path.isfile(iv_path):
        try:
            with open(iv_path, "r", encoding="utf-8") as ivf:
                inventory_version = json.load(ivf)
        except (ValueError, OSError):
            inventory_version = {}

    print("Data loaded:")
    print(f"  kpi: {len(kpi)} | cim_coverage: {len(cim_coverage)} "
          f"| compliance_detail: {len(compliance_detail)} "
          f"| compliance_summary: {len(compliance_summary)}")
    print(f"  field_gaps: {len(field_gaps)} | unmapped: {len(unmapped)} "
          f"| mapped: {len(mapped)}")
    print(f"  remediation: {len(remediation)} "
          f"| acceleration: {len(acceleration)} | trends: {len(trends)}")

    body_xml = build_body()
    header_xml = build_header()
    footer_xml = build_footer()
    save_docx(body_xml, header_xml, footer_xml, OUTPUT)

    file_size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"Report generated: {OUTPUT} ({file_size_kb:.0f} KB)")
    return OUTPUT


if __name__ == "__main__":
    generate_report()
