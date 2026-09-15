#!/bin/sh

set -u

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOOKUPS_DIR="${APP_DIR}/lookups"
KEY_FILE="${APP_DIR}/local/cip_ti_feed.key"
SPLUNK_BIN="${SPLUNK_HOME:-/opt/splunk}/bin/splunk"

now_epoch() { date +%s 2>/dev/null || echo 0; }

seed_missing_lookups() {
  for _d in "${LOOKUPS_DIR}"/*.csv.default; do
    [ -f "${_d}" ] || continue
    _t="${_d%.default}"
    if [ ! -f "${_t}" ]; then

      if cp "${_d}" "${_t}" 2>/dev/null; then
        chmod 600 "${_t}" 2>/dev/null || true
        echo "cip_ti_feedsync event=lookup_seeded file=\"$(basename "${_t}")\" mode=600"
      else
        echo "cip_ti_feedsync event=lookup_seed_failed file=\"$(basename "${_t}")\"" >&2
      fi
    fi
  done
}
seed_missing_lookups

CONFIG_LOOKUPS="internal_networks.csv ti_egress_allowlist.csv"
apply_local_overrides() {
  for _n in ${CONFIG_LOOKUPS}; do
    _src="${APP_DIR}/local/${_n}"
    _dst="${LOOKUPS_DIR}/${_n}"
    [ -f "${_src}" ] || continue

    if [ "$(cat "${_src}" 2>/dev/null)" = "$(cat "${_dst}" 2>/dev/null)" ]; then
      continue
    fi
    if cp "${_src}" "${_dst}" 2>/dev/null; then
      chmod 600 "${_dst}" 2>/dev/null || true
      echo "cip_ti_feedsync event=lookup_override_applied file=\"${_n}\" rows=$(grep -c . "${_dst}" 2>/dev/null || echo 0)"
    else
      echo "cip_ti_feedsync event=lookup_override_failed file=\"${_n}\"" >&2
    fi
  done
}
apply_local_overrides

runpy() {
  if [ -x "${SPLUNK_BIN}" ]; then
    "${SPLUNK_BIN}" cmd python3 "$@"
  else
    PY="$(command -v python3 || echo python3)"
    "${PY}" "$@"
  fi
}

read_conf_val() {
  _k="$1"; _def="$2"; _v=""
  if [ -x "${SPLUNK_BIN}" ]; then
    _v="$("${SPLUNK_BIN}" btool cip_ti_feed list settings --app=TA-cip-ti-feed 2>/dev/null \
        | sed -n "s/^${_k}[[:space:]]*=[[:space:]]*//p" | head -n1 | sed 's/[[:space:]]*$//')"
  fi
  if [ -n "${_v}" ]; then printf '%s' "${_v}"; else printf '%s' "${_def}"; fi
}

CIP_ENV="$(printf '%s' "$(read_conf_val cip_env "${CRIMINALIP_TI_ENV:-LIVE}")" | tr '[:lower:]' '[:upper:]')"
[ "${CIP_ENV}" = "LIVE" ] || [ "${CIP_ENV}" = "TEST" ] || CIP_ENV="LIVE"

CONFIDENCE="$(read_conf_val confidence 70)"
case "${CONFIDENCE}" in ''|*[!0-9]*) CONFIDENCE=70 ;; esac

FEED_LIMIT_RAW="$(read_conf_val feed_limit 50000)"
FEED_LIMIT="${FEED_LIMIT_RAW}"
_bad=0
case "${FEED_LIMIT}" in ''|*[!0-9]*) _bad=1 ;; esac
if [ "${_bad}" -eq 0 ] && [ "${#FEED_LIMIT}" -gt 5 ]; then _bad=1; fi
if [ "${_bad}" -eq 0 ] && { [ "${FEED_LIMIT}" -lt 1 ] || [ "${FEED_LIMIT}" -gt 50000 ]; }; then _bad=1; fi
if [ "${_bad}" -eq 1 ]; then
  echo "cip_ti_feedsync event=config_invalid key=feed_limit value=\"$(printf '%s' "${FEED_LIMIT_RAW}" | tr -d '"\n' | cut -c1-40)\" used=50000"
  FEED_LIMIT=50000
fi

csv_meta() {
  runpy -c 'import csv,sys; r=list(csv.reader(open(sys.argv[1],newline="",encoding="utf-8"))); print("%d\t%s"%(max(0,len(r)-1), r[1][4] if len(r)>1 and len(r[1])>4 else ""))' "$1" 2>/dev/null || printf '%s\t' '-1'
}

read_key_file() {

  _bom="$(printf '\357\273\277')"
  _line="$(tr -d '\r' < "$1" 2>/dev/null | sed "1s/^${_bom}//" | grep -v '^[[:space:]]*#' | sed '/^[[:space:]]*$/d' | head -n1)"
  _line="$(printf '%s' "${_line}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  case "${_line}" in
    *=*)
      _name="$(printf '%s' "${_line%%=*}" | sed 's/[[:space:]]*$//' | tr '[:lower:]' '[:upper:]')"
      case "${_name}" in
        CRIMINALIP_TI_KEY|CRIMINALIP_TI_KEY_LIVE|KEY)
          _line="$(printf '%s' "${_line#*=}" | sed 's/^[[:space:]]*//')" ;;
      esac ;;
  esac
  printf '%s' "${_line}"
}

emit_result() {
  _in=-1; _out=-1; _fv=""
  if [ -f "${LOOKUPS_DIR}/cip_ti_inbound.csv" ]; then
    _m=$(csv_meta "${LOOKUPS_DIR}/cip_ti_inbound.csv")
    _in=$(printf '%s' "${_m}" | cut -f1); _fv=$(printf '%s' "${_m}" | cut -f2-)
  fi
  if [ -f "${LOOKUPS_DIR}/cip_ti_outbound.csv" ]; then
    _m=$(csv_meta "${LOOKUPS_DIR}/cip_ti_outbound.csv")
    _out=$(printf '%s' "${_m}" | cut -f1)
  fi
  _reason=""
  [ -n "${3:-}" ] && _reason=" reason=$3"
  echo "cip_ti_feedsync event=sync_result status=$1 exit=$2${_reason} inbound_rows=${_in} outbound_rows=${_out} feed_version=\"${_fv}\" env=${CIP_ENV} epoch=$(now_epoch)"
}

SESSION_KEY=""
if [ ! -t 0 ]; then

  IFS= read -r SESSION_KEY 2>/dev/null || :
fi

if [ -n "${SESSION_KEY}" ]; then
  printf '%s' "${SESSION_KEY}" \
    | runpy "${APP_DIR}/bin/cip_ti_macro_heal.py" 2>&1 || true
else
  echo "cip_ti_feedsync event=macro_heal action=none reason=no_session_key"
fi

CIP_KEY=""
KEY_SOURCE="none"
if [ -n "${SESSION_KEY}" ]; then
  CIP_KEY="$(printf '%s' "${SESSION_KEY}" | runpy "${APP_DIR}/bin/cip_credential.py" 2>/dev/null || true)"
  [ -n "${CIP_KEY}" ] && KEY_SOURCE="storage"
fi
if [ -z "${CIP_KEY}" ] && [ -f "${KEY_FILE}" ]; then
  CIP_KEY="$(read_key_file "${KEY_FILE}")"
  [ -n "${CIP_KEY}" ] && KEY_SOURCE="file"
fi
if [ -z "${CIP_KEY}" ]; then
  if [ "${CIP_ENV}" = "TEST" ]; then CIP_KEY="${CRIMINALIP_TI_KEY:-}"; else CIP_KEY="${CRIMINALIP_TI_KEY_LIVE:-}"; fi
  [ -n "${CIP_KEY}" ] && KEY_SOURCE="env"
fi
echo "cip_ti_feedsync event=key_source source=${KEY_SOURCE} session_key_present=$([ -n "${SESSION_KEY}" ] && echo 1 || echo 0) key_file_present=$([ -f "${KEY_FILE}" ] && echo 1 || echo 0)"

if [ -z "${CIP_KEY}" ]; then
  emit_result "not_configured" 0
  exit 0
fi

if [ "${CIP_ENV}" = "TEST" ]; then
  export CRIMINALIP_TI_KEY="${CIP_KEY}"
else
  export CRIMINALIP_TI_KEY_LIVE="${CIP_KEY}"
fi

runpy "${APP_DIR}/bin/ti_feed_pull.py" --env "${CIP_ENV}" --confidence "${CONFIDENCE}" --limit "${FEED_LIMIT}" --out-dir "${LOOKUPS_DIR}" 2>&1
RC=$?

if [ "${RC}" -eq 0 ]; then
  emit_result "ok" 0
else
  case "${RC}" in
    2) _r=config_error ;;
    3) _r=kept_stale ;;
    4) _r=wrote_partial ;;
    5) _r=status_unavailable ;;
    *) _r="" ;;
  esac
  emit_result "failed" "${RC}" "${_r}"
fi
exit "${RC}"
