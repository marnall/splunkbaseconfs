"""
Custom persistent REST handler: deploy the S3 -> Splunk HEC ingest Lambda.

Invoked by the "Deploy" tab in the add-on's Configuration UI. It reads the AWS
credentials and deployment settings that the admin saved (secrets decrypted from
Splunk's encrypted storage/passwords via solnlib), then performs the whole
deployment IN-PROCESS with the AWS API (boto3). No AWS console, no `aws` CLI,
no subprocess -- so it passes Splunk Cloud AppInspect vetting.

Ported step-for-step from infra/deploy.sh:
  1. IAM execution role (+ basic-exec managed policy + inline S3 read)
  2. zip the Lambda payload (bin/lambda_payload/handler.py) in memory
  3. create or update the Lambda function
  4. reserved concurrency
  5. S3 -> Lambda invoke permission
  6. S3 bucket ObjectCreated notification (prefix/suffix filtered)

Endpoint (registered in restmap.conf): POST /services/deploy_lambda
Response: JSON {status, function_arn, steps: [{step, ok, detail}], error?}
"""

import base64
import gzip
import importlib.util
import io
import json
import logging
import os
import sys
import time
import urllib.parse
import zipfile

APP_NAME = "TA_s3_lambda_deployer"

# --- module resolution -------------------------------------------------------
# splunkd loads a persistent REST handler (scripttype=persist) by FILE PATH via
# importlib (persistconn/appserver.py::_load_file -> spec_from_file_location), so this
# script's own directory is NOT reliably on sys.path, and UCC's import_declare_test
# REBUILDS sys.path wholesale. If a sibling import (ta_license) then fails, the handler
# never loads; splunkd prints a sys.modules dump to stdout, which corrupts the
# persistent-connection framing and surfaces as "bad character (N) in reply size" -> HTTP 500.
#
# So: (1) add lib/ + bin/ to sys.path (best effort, for the bundled 3rd-party libs), and
#     (2) load OUR OWN sibling modules by explicit file path, which cannot depend on sys.path.


def _candidate_bins():
    """Directories that may hold this add-on's bin/ — never trust __file__ alone."""
    cands = []
    try:
        cands.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:  # noqa: BLE001 - __file__ may be odd under importlib
        pass
    splunk_home = os.environ.get("SPLUNK_HOME")
    if splunk_home:
        cands.append(os.path.join(splunk_home, "etc", "apps", APP_NAME, "bin"))
    seen, out = set(), []
    for c in cands:
        if c and c not in seen and os.path.isdir(c):
            seen.add(c)
            out.append(c)
    return out


def _ensure_paths():
    for _b in _candidate_bins():
        for _p in (os.path.join(os.path.dirname(_b), "lib"), _b):
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)


def _load_sibling(name):
    """Import a module that lives next to this file, BY PATH (sys.path-independent)."""
    if name in sys.modules:
        return sys.modules[name]
    for base in _candidate_bins():
        path = os.path.join(base, name + ".py")
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            return mod
    raise ImportError(f"cannot locate {name}.py next to the handler (bins={_candidate_bins()})")


_ensure_paths()
try:
    import import_declare_test  # noqa: F401,E402  (UCC; rebuilds sys.path)
except ImportError:
    pass
_ensure_paths()  # re-assert: import_declare_test replaces sys.path wholesale

# app root, resolved the same trustworthy way (used for the Lambda payload binary)
_BINS = _candidate_bins()
_TA_ROOT = os.path.dirname(_BINS[0]) if _BINS else os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

import boto3  # noqa: E402
from botocore.config import Config as BotoConfig  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from solnlib import conf_manager  # noqa: E402
from solnlib import log  # noqa: E402
from splunk.persistconn.application import (  # noqa: E402
    PersistentServerConnectionApplication,
)

# our own module: loaded by path, so it cannot fail on sys.path quirks
license_mod = _load_sibling("ta_license")
SETTINGS_CONF = "s3_lambda_deployer_settings"
PAYLOAD_FILE = os.path.join(_TA_ROOT, "bin", "lambda_payload", "bootstrap")

# UCC/solnlib logging: rotating file $SPLUNK_HOME/var/log/splunk/ta_s3_lambda_deployer_deploy.log,
# Splunk key=value format, auto-monitored into index=_internal. Level is driven by the
# Logging tab ([logging] loglevel in the settings conf), read per-request via get_log_level().
log.Logs.set_context(namespace="ta_s3_lambda_deployer")
logger = log.Logs().get_logger("deploy")


def _as_bool(val, default=True):
    if val is None or val == "":
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _parse_tags(raw):
    """'k=v,k2=v2' -> {'k':'v','k2':'v2'} (blank -> {})."""
    tags = {}
    for pair in (raw or "").split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        k, v = k.strip(), v.strip()
        if k:
            tags[k] = v
    return tags


ROUTE_KEYS = {"prefix", "index", "sourcetype", "raw", "skip_header"}


def _routes_env(raw):
    """Validate the per-prefix routing table and return it as compact JSON.

    Shape: [{"prefix": "AWSLogs/", "sourcetype": "aws:cloudtrail",
             "index": "aws", "raw": false, "skip_header": false}, ...]

    Validated HERE, at deploy time, so a typo surfaces as a UI error instead of
    silently forwarding everything to the default sourcetype at 3 a.m. The Lambda
    matches the LONGEST prefix, so list order does not matter.
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ValueError(f"Routing table is not valid JSON: {exc}")
    if not isinstance(parsed, list):
        raise ValueError("Routing table must be a JSON array of route objects.")
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(f"Route #{i + 1} must be a JSON object.")
        unknown = set(item) - ROUTE_KEYS
        if unknown:
            raise ValueError(
                f"Route #{i + 1} has unknown field(s): {', '.join(sorted(unknown))}. "
                f"Allowed: {', '.join(sorted(ROUTE_KEYS))}."
            )
        if not str(item.get("prefix", "")).strip():
            raise ValueError(f"Route #{i + 1} is missing a non-empty 'prefix'.")
        if not (item.get("index") or item.get("sourcetype")):
            raise ValueError(
                f"Route #{i + 1} sets neither 'index' nor 'sourcetype', so it would do nothing."
            )
    return json.dumps(parsed, separators=(",", ":"))


def _mask(secret):
    """Show only the shape of a secret, never the value."""
    if not secret:
        return ""
    s = str(secret)
    return (s[:3] + "…" + s[-2:]) if len(s) > 8 else "****"


def build_cli_preview(account, deployment):
    """Human-readable `aws` CLI commands equivalent to what the boto3 deployer runs.

    For transparency only -- the add-on executes these via the AWS API (boto3),
    not the CLI binary. Secrets (HEC token) are masked; the Lambda source is not shown.
    Account id and role ARN are placeholders (resolved from AWS at deploy time).
    """
    region = account.get("region", "")
    region_opt = f" --region {region}" if region else ""
    bucket = deployment.get("bucket", "")
    fn = deployment.get("function_name", "")
    role = deployment.get("role_name", "")
    prefix = deployment.get("prefix") or ""
    suffix = deployment.get("suffix") or ""
    timeout = deployment.get("lambda_timeout", "900")
    memory = deployment.get("lambda_memory", "512")
    reserved = str(deployment.get("reserved_concurrency", "0"))

    tag_str = ",".join(f"{k}={v}" for k, v in _parse_tags(deployment.get("tags")).items())
    env = {
        "HEC_URL": deployment.get("hec_url", ""),
        "HEC_TOKEN": _mask(deployment.get("hec_token", "")),
        "INDEX": deployment.get("index", ""),
        "SOURCETYPE": deployment.get("sourcetype", ""),
        "BATCH_MAX_BYTES": str(deployment.get("batch_max_bytes", "")),
        "GZIP_POST": "true" if _as_bool(deployment.get("gzip_post")) else "false",
        "VERIFY_SSL": "true" if _as_bool(deployment.get("verify_ssl")) else "false",
        "HEC_RAW": "true" if _as_bool(deployment.get("hec_raw"), False) else "false",
        "ROUTES": _routes_env(deployment.get("routes")),
        "AUTO_SOURCETYPE": "true" if _as_bool(deployment.get("auto_sourcetype"), True) else "false",
        "MISSED_PREFIX": (deployment.get("missed_prefix") or "").strip(),
    }
    env_str = ",".join(f"{k}={v}" for k, v in env.items() if v != "")

    trust = (
        '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
        '"Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
    )
    s3read = (
        '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
        '"Action":["s3:GetObject","s3:ListBucket"],'
        f'"Resource":["arn:aws:s3:::{bucket}","arn:aws:s3:::{bucket}/*"]}}]}}'
    )
    rules = []
    if prefix:
        rules.append(f'{{"Name":"prefix","Value":"{prefix}"}}')
    if suffix:
        rules.append(f'{{"Name":"suffix","Value":"{suffix}"}}')
    filt = f',"Filter":{{"Key":{{"FilterRules":[{",".join(rules)}]}}}}' if rules else ""
    notif = (
        '{"LambdaFunctionConfigurations":[{"Id":"s3-to-splunk-hec",'
        f'"LambdaFunctionArn":"arn:aws:lambda:{region}:<account-id>:function:{fn}",'
        f'"Events":["s3:ObjectCreated:*"]{filt}}}]}}'
    )
    conc = (
        f"aws lambda put-function-concurrency --function-name {fn} "
        f"--reserved-concurrent-executions {reserved}{region_opt}"
    )
    if reserved in ("0", ""):
        conc += "   # skipped (0 = unreserved)"

    return [
        {"step": "iam role", "command": f"aws iam create-role --role-name {role} --assume-role-policy-document '{trust}'{region_opt}"},
        {"step": "iam role", "command": f"aws iam attach-role-policy --role-name {role} --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"},
        {"step": "iam role", "command": f"aws iam put-role-policy --role-name {role} --policy-name s3-read --policy-document '{s3read}'"},
        {"step": "package", "command": "zip function.zip handler.py   # Lambda code is bundled with the add-on"},
        {"step": "lambda", "command": f"aws lambda create-function --function-name {fn} --runtime python3.12 --handler handler.handler --role arn:aws:iam::<account-id>:role/{role} --timeout {timeout} --memory-size {memory} --environment 'Variables={{{env_str}}}' --tags '{tag_str}' --zip-file fileb://function.zip{region_opt}"},
        {"step": "concurrency", "command": conc},
        {"step": "s3 invoke permission", "command": f"aws lambda add-permission --function-name {fn} --statement-id s3invoke --action lambda:InvokeFunction --principal s3.amazonaws.com --source-arn arn:aws:s3:::{bucket} --source-account <account-id>{region_opt}"},
        {"step": "s3 notification", "command": f"aws s3api put-bucket-notification-configuration --bucket {bucket} --notification-configuration '{notif}'{region_opt}"},
    ]


def build_deploy_script(account, deployment):
    """A complete, runnable AWS-CLI deploy script for AIR-GAPPED Splunk.

    When the Splunk host cannot reach AWS at all, the admin exports this script and
    an AWS operator runs it from a machine that DOES have AWS access. It performs the
    exact same 6 steps as the in-Splunk boto3 deployer and is idempotent.

    Unlike build_cli_preview (which masks secrets for on-screen display), this file is
    a deployment artifact and therefore contains the real HEC token + license key.
    """
    dep, acct = deployment, account
    region = acct.get("region", "")
    bucket = dep.get("bucket", "")
    fn = dep.get("function_name", "")
    role = dep.get("role_name", "")
    prefix = dep.get("prefix") or ""
    suffix = dep.get("suffix") or ""
    timeout = dep.get("lambda_timeout", "900")
    memory = dep.get("lambda_memory", "512")
    reserved = str(dep.get("reserved_concurrency", "0"))
    tags = _parse_tags(dep.get("tags"))
    tag_cli = ",".join(f"{k}={v}" for k, v in tags.items())

    env = {
        "HEC_URL": dep.get("hec_url", ""),
        "HEC_TOKEN": dep.get("hec_token", ""),
        "INDEX": dep.get("index", "edr"),
        "SOURCETYPE": dep.get("sourcetype", "edr:json"),
        "BATCH_MAX_BYTES": str(dep.get("batch_max_bytes", "800000")),
        "GZIP_POST": "true" if _as_bool(dep.get("gzip_post")) else "false",
        "VERIFY_SSL": "true" if _as_bool(dep.get("verify_ssl")) else "false",
        "HEC_RAW": "true" if _as_bool(dep.get("hec_raw"), False) else "false",
        "ROUTES": _routes_env(dep.get("routes")),
        "AUTO_SOURCETYPE": "true" if _as_bool(dep.get("auto_sourcetype"), True) else "false",
        "MISSED_PREFIX": (dep.get("missed_prefix") or "").strip(),
        "LICENSE_KEY": dep.get("license_key", ""),
    }
    env_cli = ",".join(f"{k}={v}" for k, v in env.items() if v != "")

    rules = []
    if prefix:
        rules.append({"Name": "prefix", "Value": prefix})
    if suffix:
        rules.append({"Name": "suffix", "Value": suffix})
    # S3 wants the key filter nested under "Filter" (not "Key" at the top of the
    # LambdaFunctionConfiguration) — otherwise put-bucket-notification-configuration
    # rejects it: 'Unknown parameter ... "Key", must be one of: Id, LambdaFunctionArn,
    # Events, Filter'. Mirrors the boto3 in-process path below.
    notif_filter = {"Filter": {"Key": {"FilterRules": rules}}} if rules else {}

    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow",
                       "Principal": {"Service": "lambda.amazonaws.com"},
                       "Action": "sts:AssumeRole"}],
    })
    s3read = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow",
                       "Action": ["s3:GetObject", "s3:ListBucket"],
                       "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"]}],
    })

    # Embed the compiled Lambda binary (gzip + base64) so the exported script is a
    # SINGLE self-contained file — the whole point for air-gapped transfer.
    with open(PAYLOAD_FILE, "rb") as _f:
        _b64 = base64.b64encode(gzip.compress(_f.read(), 9)).decode("ascii")
    boot_b64 = "\n".join(_b64[i:i + 76] for i in range(0, len(_b64), 76))

    return f"""#!/usr/bin/env bash
# =============================================================================
#  S3 -> Splunk HEC : OFFLINE DEPLOYMENT SCRIPT  (air-gapped Splunk)
#
#  SELF-CONTAINED: the compiled Lambda binary is embedded in this file. You need
#  NOTHING else — just AWS CLI v2 configured.
#
#  Run this on a machine that HAS AWS access (e.g. the AWS administrator's PC or a
#  bastion). The Splunk host itself needs no AWS connectivity.
#
#  STEP 1 - set AWS credentials in THIS shell first (pick one):
#     # temporary / STS keys (access key starts with ASIA):
#     export AWS_ACCESS_KEY_ID=...
#     export AWS_SECRET_ACCESS_KEY=...
#     export AWS_SESSION_TOKEN=...          # required for STS keys
#     export AWS_DEFAULT_REGION={region}
#     # or long-term IAM key:  aws configure
#     # or SSO:                aws sso login --profile <p> ; export AWS_PROFILE=<p>
#     # verify:                aws sts get-caller-identity
#
#  STEP 2 - run it:
#     chmod +x deploy_s3_to_splunk.sh && ./deploy_s3_to_splunk.sh
#
#  SECURITY: this file contains your HEC token and license key. Transfer it securely
#            and DELETE it after the deployment.
#
#  Idempotent: re-running updates the existing resources.
# =============================================================================
set -euo pipefail

REGION="{region}"
BUCKET="{bucket}"
FUNCTION="{fn}"
ROLE="{role}"
RESERVED_CONCURRENCY="{reserved}"

command -v aws >/dev/null || {{ echo "ERROR: AWS CLI not found"; exit 1; }}

echo ">> [0/6] extracting the embedded Lambda binary"
# portable base64 decode (GNU --decode, BSD/macOS -D, else openssl)
if echo "aGk=" | base64 --decode >/dev/null 2>&1; then B64D="base64 --decode"
elif echo "aGk=" | base64 -D >/dev/null 2>&1; then B64D="base64 -D"
else B64D="openssl base64 -d"; fi
$B64D <<'__BOOTSTRAP_B64__' | gunzip > bootstrap
{boot_b64}
__BOOTSTRAP_B64__
chmod +x bootstrap
[ -s bootstrap ] || {{ echo "ERROR: failed to extract the Lambda binary"; exit 1; }}
echo "   bootstrap: $(wc -c < bootstrap) bytes"

if ! ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)"; then
  echo ""
  echo "ERROR: no valid AWS credentials in this shell."
  echo "Set them first, e.g. (STS temporary keys):"
  echo "  export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_SESSION_TOKEN=..."
  echo "  export AWS_DEFAULT_REGION=$REGION"
  echo "or 'aws configure' (IAM key) / 'aws sso login' (SSO). Verify with 'aws sts get-caller-identity'."
  rm -f bootstrap
  exit 1
fi
echo ">> AWS account: $ACCOUNT_ID   region: $REGION"

echo ">> [1/6] IAM execution role"
aws iam get-role --role-name "$ROLE" >/dev/null 2>&1 || \\
  aws iam create-role --role-name "$ROLE" \\
    --assume-role-policy-document '{trust}' >/dev/null
aws iam attach-role-policy --role-name "$ROLE" \\
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name "$ROLE" --policy-name s3-read \\
  --policy-document '{s3read}'
ROLE_ARN="arn:aws:iam::${{ACCOUNT_ID}}:role/${{ROLE}}"
sleep 10   # let the new role propagate

echo ">> [2/6] package the Lambda binary"
rm -f function.zip
zip -q -j function.zip bootstrap
chmod +x bootstrap

echo ">> [3/6] create/update the Lambda (provided.al2023, compiled binary)"
if aws lambda get-function --function-name "$FUNCTION" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNCTION" --region "$REGION" \\
    --zip-file fileb://function.zip --publish >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNCTION" --region "$REGION" \\
    --role "$ROLE_ARN" --handler bootstrap --runtime provided.al2023 \\
    --timeout {timeout} --memory-size {memory} \\
    --environment 'Variables={{{env_cli}}}' >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION" --region "$REGION"
else
  aws lambda create-function --function-name "$FUNCTION" --region "$REGION" \\
    --runtime provided.al2023 --handler bootstrap --architectures x86_64 \\
    --role "$ROLE_ARN" --zip-file fileb://function.zip \\
    --timeout {timeout} --memory-size {memory} \\
    --environment 'Variables={{{env_cli}}}' \\
    --tags '{tag_cli}' --publish >/dev/null
  aws lambda wait function-active-v2 --function-name "$FUNCTION" --region "$REGION"
fi
FUNCTION_ARN="arn:aws:lambda:${{REGION}}:${{ACCOUNT_ID}}:function:${{FUNCTION}}"

echo ">> [4/6] reserved concurrency"
if [ "$RESERVED_CONCURRENCY" -gt 0 ] 2>/dev/null; then
  aws lambda put-function-concurrency --function-name "$FUNCTION" --region "$REGION" \\
    --reserved-concurrent-executions "$RESERVED_CONCURRENCY" >/dev/null
fi

echo ">> [5/6] allow S3 to invoke the Lambda"
aws lambda add-permission --function-name "$FUNCTION" --region "$REGION" \\
  --statement-id s3invoke --action lambda:InvokeFunction \\
  --principal s3.amazonaws.com \\
  --source-arn "arn:aws:s3:::${{BUCKET}}" --source-account "$ACCOUNT_ID" >/dev/null 2>&1 || \\
  echo "   (invoke permission already present)"

echo ">> [6/6] S3 ObjectCreated notification -> Lambda"
cat > notification.json <<JSON
{{"LambdaFunctionConfigurations":[{{"Id":"s3-to-splunk-hec",
  "LambdaFunctionArn":"${{FUNCTION_ARN}}",
  "Events":["s3:ObjectCreated:*"]{"," + json.dumps(notif_filter)[1:-1] if notif_filter else ""}}}]}}
JSON
aws s3api put-bucket-notification-configuration --bucket "$BUCKET" --region "$REGION" \\
  --notification-configuration file://notification.json

rm -f function.zip notification.json bootstrap
echo ""
echo "DONE. $FUNCTION_ARN"
echo "Upload a .gz object to s3://$BUCKET/ and check CloudWatch + Splunk index={env['INDEX']}."
echo "NOTE: delete this script (it contains your HEC token and license key)."
"""


def _read_settings(session_key):
    """Return (account, deployment) dicts with encrypted fields decrypted.

    The License tab is stored as its own [license] stanza; fold license_key into
    the deployment dict so callers have one place to read it.
    """
    cfm = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{SETTINGS_CONF}",
    )
    conf = cfm.get_conf(SETTINGS_CONF)
    account = conf.get("aws_account")
    deployment = conf.get("deployment")
    try:
        deployment["license_key"] = (conf.get("license") or {}).get("license_key", "")
    except Exception:  # noqa: BLE001 - license stanza may not exist yet
        deployment["license_key"] = ""
    # Proxy (air-gapped / restricted-egress networks reach AWS through a corporate proxy)
    try:
        account["_proxy"] = conf.get("proxy") or {}
    except Exception:  # noqa: BLE001 - proxy stanza may not exist yet
        account["_proxy"] = {}
    return account, deployment


def _wipe_aws_credentials(session_key):
    """Remove the stored AWS credentials from Splunk.

    The AWS keys are only needed AT deploy time (the deployed Lambda authenticates
    with its own IAM execution role afterwards), so they can — and should — be
    removed once the deploy succeeds. Two places must be cleared, in this order:

      1. the storage/passwords blob (UCC keeps the encrypted secret fields there,
         keyed by realm+stanza; blanking only the conf stanza would let the old
         secret re-surface on the next decrypt-merge), then
      2. the [aws_account] stanza fields themselves (the access key id is stored
         in clear in the conf; the secret fields hold a ****** placeholder).

    `region` and the wipe preference itself are kept so a future re-deploy only
    needs the keys re-entered. Returns (ok, error_message).
    """
    realm = f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{SETTINGS_CONF}"
    try:
        from solnlib import credentials as _creds

        try:
            _creds.CredentialManager(session_key, APP_NAME, realm=realm).delete_password(
                "aws_account"
            )
        except Exception:  # noqa: BLE001 - blob may not exist (nothing saved yet)
            pass
        cfm = conf_manager.ConfManager(session_key, APP_NAME, realm=realm)
        conf = cfm.get_conf(SETTINGS_CONF)
        conf.update(
            "aws_account",
            {
                "aws_access_key_id": "",
                "aws_secret_access_key": "",
                "aws_session_token": "",
            },
        )
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def build_proxies(proxy_cfg):
    """Turn the UCC proxy stanza into a botocore `proxies` dict ({} = direct)."""
    if not proxy_cfg or not _as_bool(proxy_cfg.get("proxy_enabled"), default=False):
        return {}
    host = (proxy_cfg.get("proxy_url") or "").strip()
    if not host:
        return {}
    scheme = (proxy_cfg.get("proxy_type") or "http").strip() or "http"
    port = str(proxy_cfg.get("proxy_port") or "").strip()
    user = (proxy_cfg.get("proxy_username") or "").strip()
    pwd = proxy_cfg.get("proxy_password") or ""
    auth = f"{urllib.parse.quote(user, safe='')}:{urllib.parse.quote(pwd, safe='')}@" if user else ""
    netloc = f"{host}:{port}" if port else host
    url = f"{scheme}://{auth}{netloc}"
    # AWS API calls are HTTPS; route both through the proxy
    return {"http": url, "https": url}


class DeployError(Exception):
    """Carries a user-facing hint alongside the raw error."""

    def __init__(self, message, hint=None):
        super().__init__(message)
        self.hint = hint


class Deployer:
    def __init__(self, account, deployment):
        self.acct = account
        self.dep = deployment
        self.steps = []

        session = boto3.session.Session(
            aws_access_key_id=account.get("aws_access_key_id"),
            aws_secret_access_key=account.get("aws_secret_access_key"),
            aws_session_token=(account.get("aws_session_token") or None),
            region_name=account.get("region"),
        )
        # route AWS API calls through the corporate proxy when configured
        # (restricted-egress / air-gapped Splunk hosts)
        proxies = build_proxies(account.get("_proxy"))
        if proxies:
            logger.info("using proxy for AWS API calls: %s", proxies.get("https", "").split("@")[-1])
        cfg = BotoConfig(
            retries={"max_attempts": 5, "mode": "standard"},
            proxies=proxies or None,
        )
        self.iam = session.client("iam", config=cfg)
        self.lam = session.client("lambda", config=cfg)
        self.s3 = session.client("s3", config=cfg)
        self.sts = session.client("sts", config=cfg)
        self.region = account.get("region")

    def _step(self, name, ok, detail):
        self.steps.append({"step": name, "ok": ok, "detail": detail})
        logger.info("step=%s ok=%s detail=%s", name, ok, detail)

    # --- step 0: identity ------------------------------------------------
    def account_id(self):
        try:
            return self.sts.get_caller_identity()["Account"]
        except ClientError as e:
            raise DeployError(
                f"Could not authenticate to AWS: {e}",
                hint="Check the AWS Access Key ID / Secret Access Key on the AWS Account tab.",
            )

    # --- step 1: IAM role ------------------------------------------------
    def ensure_role(self, role_name, bucket):
        trust = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        created = False
        try:
            role = self.iam.get_role(RoleName=role_name)
            role_arn = role["Role"]["Arn"]
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise DeployError(f"iam:GetRole failed: {e}")
            role_arn = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust),
                Description="Execution role for the S3->Splunk HEC ingest Lambda.",
            )["Role"]["Arn"]
            created = True

        self.iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        s3_read = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:ListBucket"],
                    "Resource": [
                        f"arn:aws:s3:::{bucket}",
                        f"arn:aws:s3:::{bucket}/*",
                    ],
                }
            ],
        }
        # Write access is scoped to the missed-object manifest prefix ONLY — the
        # Lambda records the keys it had to refuse while the license was lapsed so
        # they can be replayed exactly. Nothing else in the bucket is writable.
        missed_prefix = (self.dep.get("missed_prefix") or "").strip()
        if missed_prefix:
            s3_read["Statement"].append({
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/{missed_prefix}*"],
            })
        self.iam.put_role_policy(
            RoleName=role_name,
            PolicyName="s3-read",
            PolicyDocument=json.dumps(s3_read),
        )
        if created:
            # New roles need a few seconds before Lambda can assume them.
            time.sleep(10)
        self._step(
            "iam_role",
            True,
            f"{'created' if created else 'updated'} {role_name} + basic-exec + s3-read inline policy",
        )
        return role_arn

    # --- step 2: package (the compiled Go binary; provided.al2023 needs it named
    #     'bootstrap' with the exec bit set) --------------------------------
    def zip_payload(self):
        with open(PAYLOAD_FILE, "rb") as f:
            code = f.read()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            info = zipfile.ZipInfo("bootstrap")
            info.external_attr = 0o755 << 16  # executable
            z.writestr(info, code)
        self._step("package", True, f"zipped bootstrap ({len(code)} bytes)")
        return buf.getvalue()

    # --- step 3: function ------------------------------------------------
    def deploy_function(self, role_arn, zip_bytes):
        dep = self.dep
        env_vars = {
            "HEC_URL": dep.get("hec_url", ""),
            "HEC_TOKEN": dep.get("hec_token", ""),
            "INDEX": dep.get("index", "edr"),
            "SOURCETYPE": dep.get("sourcetype", "edr:json"),
            "BATCH_MAX_BYTES": str(dep.get("batch_max_bytes", "800000")),
            "GZIP_POST": "true" if _as_bool(dep.get("gzip_post")) else "false",
            "VERIFY_SSL": "true" if _as_bool(dep.get("verify_ssl")) else "false",
            # post to HEC /raw so Splunk applies the sourcetype's own line breaking
            "HEC_RAW": "true" if _as_bool(dep.get("hec_raw"), False) else "false",
            # per-prefix index/sourcetype overrides ("" = single destination)
            "ROUTES": _routes_env(dep.get("routes")),
            # auto-detect AWS log sourcetypes by S3 key path (default on)
            "AUTO_SOURCETYPE": "true" if _as_bool(dep.get("auto_sourcetype"), True) else "false",
            # where objects refused by an expired license are recorded for replay
            "MISSED_PREFIX": (dep.get("missed_prefix") or "").strip(),
            # subscription/node-lock: the Go binary verifies this per invocation
            "LICENSE_KEY": dep.get("license_key", ""),
        }
        fn = dep.get("function_name")
        timeout = int(dep.get("lambda_timeout", "900"))
        memory = int(dep.get("lambda_memory", "512"))
        tags = _parse_tags(dep.get("tags"))

        exists = True
        try:
            self.lam.get_function(FunctionName=fn)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                exists = False
            else:
                raise DeployError(f"lambda:GetFunction failed: {e}")

        try:
            if exists:
                self.lam.update_function_code(
                    FunctionName=fn, ZipFile=zip_bytes, Publish=True
                )
                self.lam.get_waiter("function_updated").wait(FunctionName=fn)
                self.lam.update_function_configuration(
                    FunctionName=fn,
                    Role=role_arn,
                    Handler="bootstrap",
                    Runtime="provided.al2023",
                    Timeout=timeout,
                    MemorySize=memory,
                    Environment={"Variables": env_vars},
                )
                self.lam.get_waiter("function_updated").wait(FunctionName=fn)
                arn = self.lam.get_function(FunctionName=fn)["Configuration"][
                    "FunctionArn"
                ]
                self._step("lambda", True, f"updated {fn}")
            else:
                arn = self.lam.create_function(
                    FunctionName=fn,
                    Runtime="provided.al2023",
                    Role=role_arn,
                    Handler="bootstrap",
                    Architectures=["x86_64"],
                    Code={"ZipFile": zip_bytes},
                    Timeout=timeout,
                    MemorySize=memory,
                    Environment={"Variables": env_vars},
                    Tags=tags,
                    Publish=True,
                )["FunctionArn"]
                self.lam.get_waiter("function_active_v2").wait(FunctionName=fn)
                self._step("lambda", True, f"created {fn} with tags {list(tags)}")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            msg = e.response["Error"].get("Message", str(e))
            if "explicit deny" in msg.lower() or code == "AccessDeniedException":
                raise DeployError(
                    f"Lambda create/update denied: {msg}",
                    hint="Likely a Service Control Policy requiring resource tags. "
                    "Set the mandatory key=value tags on the Deployment tab and retry.",
                )
            raise DeployError(f"lambda deploy failed ({code}): {msg}")
        return arn

    # --- step 4: concurrency --------------------------------------------
    def set_concurrency(self, fn, reserved):
        reserved = int(reserved)
        if reserved <= 0:
            self._step("concurrency", True, "skipped (0 = unreserved)")
            return
        self.lam.put_function_concurrency(
            FunctionName=fn, ReservedConcurrentExecutions=reserved
        )
        self._step("concurrency", True, f"reserved={reserved}")

    # --- step 5: invoke permission --------------------------------------
    def add_s3_permission(self, fn, bucket, account_id):
        try:
            self.lam.add_permission(
                FunctionName=fn,
                StatementId="s3invoke",
                Action="lambda:InvokeFunction",
                Principal="s3.amazonaws.com",
                SourceArn=f"arn:aws:s3:::{bucket}",
                SourceAccount=account_id,
            )
            self._step("s3_invoke_permission", True, "granted s3invoke")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceConflictException":
                self._step("s3_invoke_permission", True, "already present")
            else:
                raise DeployError(f"lambda:AddPermission failed: {e}")

    # --- step 6: bucket notification ------------------------------------
    def wire_notification(self, fn_arn, bucket, prefix, suffix):
        rules = []
        if prefix:
            rules.append({"Name": "prefix", "Value": prefix})
        if suffix:
            rules.append({"Name": "suffix", "Value": suffix})
        cfg = {
            "LambdaFunctionConfigurations": [
                {
                    "Id": "s3-to-splunk-hec",
                    "LambdaFunctionArn": fn_arn,
                    "Events": ["s3:ObjectCreated:*"],
                    **({"Filter": {"Key": {"FilterRules": rules}}} if rules else {}),
                }
            ]
        }
        try:
            self.s3.put_bucket_notification_configuration(
                Bucket=bucket, NotificationConfiguration=cfg
            )
        except ClientError as e:
            raise DeployError(
                f"s3:PutBucketNotification failed: {e}",
                hint="The deploy key needs s3:PutBucketNotification on the bucket, "
                "and any pre-existing notifications on this bucket are replaced.",
            )
        self._step(
            "s3_notification",
            True,
            f"ObjectCreated -> {fn_arn} (prefix={prefix or '*'}, suffix={suffix or '*'})",
        )

    def run(self):
        bucket = self.dep.get("bucket")
        fn = self.dep.get("function_name")
        acct_id = self.account_id()
        # node-lock: refuse to deploy into an AWS account the license doesn't cover
        lic = license_mod.verify_license(self.dep.get("license_key"))
        if not license_mod.account_allowed(lic.get("aws_account"), acct_id):
            raise DeployError(
                f"License is not valid for AWS account {acct_id}.",
                hint="This license is node-locked to specific AWS account(s). "
                "Request a key issued for this account from your vendor.",
            )
        role_arn = self.ensure_role(self.dep.get("role_name"), bucket)
        zip_bytes = self.zip_payload()
        fn_arn = self.deploy_function(role_arn, zip_bytes)
        self.set_concurrency(fn, self.dep.get("reserved_concurrency", "0"))
        self.add_s3_permission(fn, bucket, acct_id)
        self.wire_notification(fn_arn, bucket, self.dep.get("prefix"), self.dep.get("suffix"))
        return fn_arn

    # --- recovery: replay the objects an expired license refused ---------------
    def backfill_missed(self):
        """Re-invoke the Lambda for exactly the objects recorded in the manifests.

        While the license is lapsed the Lambda cannot forward anything, but it DOES
        record every key it had to refuse. Replaying from that record is exact: no
        guessing a time window, and objects that were ingested normally are never
        sent a second time (there is no de-duplication anywhere downstream, so a
        time-range replay would create duplicate events in Splunk).

        A manifest is deleted only after every key in it has been queued, so an
        interrupted run is safe to repeat -- at worst it replays one manifest twice.
        """
        bucket = self.dep.get("bucket")
        fn = self.dep.get("function_name")
        prefix = (self.dep.get("missed_prefix") or "").strip()
        if not prefix:
            raise DeployError(
                "Missed-object recording is disabled.",
                hint="Set a 'Missed-object manifest prefix' on the Deployment tab and "
                "redeploy, so refused objects can be recovered later.",
            )

        manifests, keys, errors = 0, [], []
        try:
            pages = self.s3.get_paginator("list_objects_v2").paginate(
                Bucket=bucket, Prefix=prefix
            )
            for page in pages:
                for obj in page.get("Contents", []):
                    mkey = obj["Key"]
                    if mkey.endswith("/"):
                        continue
                    body = self.s3.get_object(Bucket=bucket, Key=mkey)["Body"].read()
                    batch = []
                    for line in body.decode("utf-8", "replace").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except ValueError:
                            errors.append(f"{mkey}: unreadable line skipped")
                            continue
                        if rec.get("key"):
                            batch.append((rec.get("bucket") or bucket, rec["key"]))
                    for b, k in batch:
                        self.lam.invoke(
                            FunctionName=fn,
                            InvocationType="Event",  # async -> capped by reserved concurrency
                            Payload=json.dumps({
                                "Records": [{
                                    "eventSource": "backfill:missed",
                                    "s3": {"bucket": {"name": b}, "object": {"key": k}},
                                }]
                            }).encode("utf-8"),
                        )
                        keys.append(k)
                    manifests += 1
                    self.s3.delete_object(Bucket=bucket, Key=mkey)
        except ClientError as e:
            raise DeployError(
                f"Could not read the missed-object manifests: {e}",
                hint="The deploy role needs s3:GetObject/s3:DeleteObject on "
                f"s3://{bucket}/{prefix}* and lambda:InvokeFunction on {fn}.",
            )

        return {
            "manifests": manifests,
            "objects": len(keys),
            "sample_keys": keys[:10],
            "errors": errors[:10],
        }


class DeployLambdaHandler(PersistentServerConnectionApplication):
    """Splunk persistent REST handler entry point."""

    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        # short correlation id so all log lines of one request can be grep'd together
        rid = format(abs(hash(in_string)) % 0xFFFFFF, "06x")
        try:
            req = json.loads(in_string)
        except (ValueError, TypeError):
            logger.error("rid=%s event=bad_request reason=malformed_json", rid)
            return self._resp(400, {"error": "malformed request"})

        session_key = (req.get("session") or {}).get("authtoken")
        user = (req.get("session") or {}).get("user")
        if not session_key:
            logger.error("rid=%s event=unauthorized reason=missing_session_token", rid)
            return self._resp(401, {"error": "missing session token"})

        # action: "preview" | "deploy" | "license_status"
        action = "deploy"
        payload = req.get("payload")
        if payload:
            try:
                action = (json.loads(payload) or {}).get("action", "deploy")
            except (ValueError, TypeError):
                pass
        logger.info("rid=%s event=request action=%s user=%s", rid, action, user)

        # honor the Logging tab's level for this request
        try:
            logger.setLevel(
                conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=APP_NAME,
                    conf_name=SETTINGS_CONF,
                )
            )
        except Exception:  # noqa: BLE001 - never let logging config break the request
            pass

        try:
            account, deployment = _read_settings(session_key)
        except Exception as e:  # noqa: BLE001 - surface config errors to UI
            log.log_exception(logger, e, "read_settings", msg_before=f"rid={rid} event=read_settings_failed")
            return self._resp(
                400,
                {
                    "error": f"Could not read saved configuration: {e}",
                    "hint": "Fill in the AWS Account and Deployment tabs and save before deploying.",
                },
            )

        lic = license_mod.verify_license(deployment.get("license_key"))
        logger.info(
            "rid=%s event=license valid=%s customer=%s expiry=%s reason=%s",
            rid, lic["valid"], lic.get("customer"), lic.get("expiry"), lic["reason"],
        )

        # license_status is the ONLY info action available without a valid license — it
        # just reports validity so the UI can render the banner. No deployment info.
        if action == "license_status":
            return self._resp(200, {"status": "ok", "license": lic})

        # clear_credentials is deliberately NOT license-gated: removing your own stored
        # secrets from Splunk must always be possible (it discloses nothing and the AWS
        # keys are only needed at deploy time — the Lambda runs on its IAM role).
        if action == "clear_credentials":
            ok, err = _wipe_aws_credentials(session_key)
            if ok:
                logger.info("rid=%s event=credentials_wiped trigger=manual", rid)
                return self._resp(200, {"status": "ok", "credentials_wiped": True})
            logger.warning("rid=%s event=credentials_wipe_failed trigger=manual err=%s", rid, err)
            return self._resp(200, {"status": "error", "credentials_wiped": False,
                                    "error": f"could not remove credentials: {err}"})

        # AUTHORITATIVE SERVER-SIDE GATE: everything else (preview, export_script, deploy)
        # requires a valid license. The UI disables the buttons, but that is cosmetic —
        # this is what actually stops a hand-crafted REST call (e.g. reading the page JS
        # and POSTing {action:"preview"}) from obtaining any deployment information.
        if action not in ("preview", "export_script", "deploy", "backfill_missed"):
            return self._resp(400, {"status": "error", "error": f"unknown action: {action}"})
        if not lic["valid"]:
            logger.warning("rid=%s event=blocked action=%s reason=%s", rid, action, lic["reason"])
            return self._resp(200, {
                "status": "error",
                "error": "A valid license is required. " + lic["reason"],
                "hint": "Enter a valid license key on the Licensing tab.",
                "license": lic,
            })

        # Validate the routing table once, up front: preview, export_script and
        # deploy all embed it, and a bad table should be a clear UI error rather
        # than a traceback from deep inside whichever path the user picked.
        try:
            _routes_env(deployment.get("routes"))
        except ValueError as exc:
            logger.warning("rid=%s event=invalid_routes err=%s", rid, exc)
            return self._resp(200, {
                "status": "error",
                "error": str(exc),
                "hint": 'Example: [{"prefix":"AWSLogs/","sourcetype":"aws:cloudtrail","index":"aws"}]',
            })

        if action == "preview":
            logger.info("rid=%s event=preview bucket=%s function=%s", rid, deployment.get("bucket"), deployment.get("function_name"))
            return self._resp(
                200, {"status": "ok", "commands": build_cli_preview(account, deployment), "license": lic}
            )

        # Air-gapped path: export a runnable AWS-CLI script so an AWS operator can
        # deploy from a machine that has AWS access. Needs NO AWS connectivity from Splunk.
        if action == "export_script":
            missing = [k for k in ("hec_url", "hec_token", "bucket", "function_name", "role_name")
                       if not deployment.get(k)] + \
                      [k for k in ("region",) if not account.get(k)]
            if missing:
                return self._resp(400, {"error": f"missing required settings: {', '.join(missing)}"})
            logger.info("rid=%s event=export_script bucket=%s function=%s",
                        rid, deployment.get("bucket"), deployment.get("function_name"))
            return self._resp(200, {
                "status": "ok",
                "filename": "deploy_s3_to_splunk.sh",
                "script": build_deploy_script(account, deployment),
                "license": lic,
            })

        # (license already enforced by the authoritative gate above)

        # STS temporary keys ('ASIA...') require a session token; give a clear error
        # instead of a confusing AWS auth failure.
        # NOTE: `or ""`, not `.get(k, "")` -- after the post-deploy credential wipe the
        # key is PRESENT but None, so the default never applies and .startswith() would
        # blow up here (HTTP 500) before the friendly "missing settings" check below.
        if (account.get("aws_access_key_id") or "").startswith("ASIA") and not account.get(
            "aws_session_token"
        ):
            logger.warning("rid=%s event=deploy_blocked reason=sts_key_without_token", rid)
            return self._resp(
                200,
                {
                    "status": "error",
                    "error": "Temporary (STS) access keys starting with 'ASIA' require an AWS Session Token.",
                    "hint": "Enter the AWS Session Token on the AWS Account tab, or use a long-term IAM user key (starts with 'AKIA').",
                },
            )

        # backfill_missed needs AWS + the bucket/function, but NOT the HEC settings
        # (the deployed Lambda already holds those).
        need = ("aws_access_key_id", "aws_secret_access_key", "region")
        dep_need = ("bucket", "function_name") if action == "backfill_missed" else \
                   ("hec_url", "hec_token", "bucket", "function_name", "role_name")
        missing = [k for k in need if not account.get(k)] + \
                  [k for k in dep_need if not deployment.get(k)]
        if missing:
            logger.warning("rid=%s event=deploy_blocked reason=missing_settings fields=%s", rid, ",".join(missing))
            return self._resp(
                400,
                {"error": f"missing required settings: {', '.join(missing)}"},
            )

        # Recover the objects that arrived while the license was lapsed. The Lambda
        # recorded each refused key in a manifest, so this replays EXACTLY those
        # objects -- no time-window guessing, and nothing already ingested is sent
        # twice. Replays are async invokes, so the function's reserved concurrency
        # still caps how hard the indexer is hit.
        if action == "backfill_missed":
            logger.info("rid=%s event=backfill_missed_start bucket=%s function=%s",
                        rid, deployment.get("bucket"), deployment.get("function_name"))
            try:
                result = Deployer(account, deployment).backfill_missed()
            except DeployError as e:
                logger.error("rid=%s event=backfill_missed_failed error=%s", rid, e)
                return self._resp(200, {"status": "error", "error": str(e), "hint": e.hint})
            except Exception as e:  # noqa: BLE001
                log.log_exception(logger, e, "backfill_missed",
                                  msg_before=f"rid={rid} event=backfill_missed_error")
                return self._resp(200, {"status": "error", "error": f"unexpected error: {e}"})
            logger.info("rid=%s event=backfill_missed_done manifests=%s objects=%s",
                        rid, result["manifests"], result["objects"])
            return self._resp(200, dict(result, status="ok", license=lic))

        logger.info(
            "rid=%s event=deploy_start customer=%s region=%s bucket=%s function=%s",
            rid, lic.get("customer"), account.get("region"),
            deployment.get("bucket"), deployment.get("function_name"),
        )
        deployer = Deployer(account, deployment)
        try:
            fn_arn = deployer.run()
        except DeployError as e:
            logger.error("rid=%s event=deploy_failed error=%s", rid, e)
            return self._resp(
                200,
                {
                    "status": "error",
                    "error": str(e),
                    "hint": e.hint,
                    "steps": deployer.steps,
                },
            )
        except Exception as e:  # noqa: BLE001
            log.log_exception(logger, e, "deploy", msg_before=f"rid={rid} event=deploy_unexpected_error")
            return self._resp(
                200,
                {
                    "status": "error",
                    "error": f"unexpected error: {e}",
                    "steps": deployer.steps,
                },
            )

        logger.info("rid=%s event=deploy_done function_arn=%s steps=%d", rid, fn_arn, len(deployer.steps))

        # Post-deploy credential hygiene: the AWS keys were only needed for this deploy
        # (the Lambda authenticates with its IAM execution role from now on). If the
        # admin opted in, remove them from Splunk. A wipe failure must NOT fail the
        # deploy — the pipeline is already live; report it instead.
        result = {
            "status": "ok",
            "function_arn": fn_arn,
            "steps": deployer.steps,
        }
        if _as_bool(account.get("wipe_credentials"), default=False):
            ok, err = _wipe_aws_credentials(session_key)
            result["credentials_wiped"] = ok
            if ok:
                logger.info("rid=%s event=credentials_wiped trigger=post_deploy", rid)
            else:
                logger.warning("rid=%s event=credentials_wipe_failed trigger=post_deploy err=%s", rid, err)
                result["wipe_error"] = (
                    "Deploy succeeded but the AWS credentials could not be removed: "
                    f"{err}. Remove them manually on the AWS Account tab."
                )
        return self._resp(200, result)

    def handleStream(self, handle, in_string):
        raise NotImplementedError()

    def done(self):
        pass

    @staticmethod
    def _resp(status, payload):
        return {"payload": json.dumps(payload), "status": status}
