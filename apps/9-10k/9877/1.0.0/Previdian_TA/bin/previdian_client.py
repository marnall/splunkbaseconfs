"""Poll the Previdian Pro or Enterprise API. No Splunk imports."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://previdian.com"
TIERS = ("pro", "enterprise")
PER_PAGE = 100
PAGE_PAUSE_SECONDS = 0.15


class PrevidianError(Exception):
  def __init__(self, message, status=None):
    super().__init__(message)
    self.status = status


class PrevidianClient:
  def __init__(self, base_url, token, tier, opener=None, sleep=time.sleep):
    self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
    self.token = token or ""
    self.tier = (tier or "").strip().lower()
    self._opener = opener or urllib.request.urlopen
    self._sleep = sleep
    if self.tier not in TIERS:
      raise PrevidianError("tier must be pro or enterprise")
    if not self.token:
      raise PrevidianError("API token is required")

  def validate(self):
    self._get("/kevs", {"per_page": 1, "page": 1})
    return True

  def iter_kevs(self, modified_since=None):
    params = {}
    if modified_since:
      params["modified_since"] = modified_since
    yield from self._pages("/kevs", "kevs", params)

  def iter_notifications(self, since=None):
    params = {}
    if since:
      params["since"] = since
    yield from self._pages("/watchlist/notifications", "notifications", params)

  def iter_priority_items(self):
    yield from self._pages("/priority_items", "priority_items", {})

  def iter_observations(self, observed_since=None):
    self._require_enterprise("observations")
    params = {}
    if observed_since:
      params["observed_since"] = observed_since
    yield from self._pages("/observations", "observations", params)

  def iter_infrastructures(self, seen_since=None):
    self._require_enterprise("attacker infrastructure")
    params = {}
    if seen_since:
      params["seen_since"] = seen_since
    yield from self._pages("/attacker_infrastructures", "attacker_infrastructures", params)

  def iter_attackers(self):
    self._require_enterprise("attackers")
    yield from self._pages("/attackers", "attackers", {})

  def _require_enterprise(self, name):
    if self.tier != "enterprise":
      raise PrevidianError("%s requires an Enterprise token" % name)

  def _pages(self, path, key, params):
    page = 1
    while True:
      query = dict(params)
      query["page"] = page
      query["per_page"] = PER_PAGE
      body = self._get(path, query)
      rows = body.get(key) or []
      for row in rows:
        yield row
      pagination = body.get("pagination") or {}
      next_page = pagination.get("next_page")
      if not next_page or not rows:
        return
      next_page = int(next_page)
      if next_page <= page:
        return
      page = next_page
      self._sleep(PAGE_PAUSE_SECONDS)

  def _get(self, path, params):
    url = "%s/api/v2/%s%s" % (self.base_url, self.tier, path)
    if params:
      url = url + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
      url,
      headers={
        "X-API-Token": self.token,
        "Accept": "application/json",
        "User-Agent": "Previdian-Splunk/1.0"
      }
    )
    response = None
    last_error = None
    for attempt in range(3):
      try:
        response = self._opener(request, timeout=60)
        break
      except urllib.error.HTTPError as error:
        detail = _read_error(error)
        if error.code == 403:
          raise PrevidianError(
            "403 from %s. The token tier does not match this namespace." % url,
            status=403
          )
        raise PrevidianError("HTTP %s from %s: %s" % (error.code, url, detail), status=error.code)
      except (urllib.error.URLError, TimeoutError) as error:
        last_error = error
        if attempt == 2:
          reason = getattr(error, "reason", error)
          raise PrevidianError("Could not reach %s: %s" % (url, reason))
        self._sleep(1)
    if response is None:
      raise PrevidianError("Could not reach %s: %s" % (url, last_error))
    raw = response.read().decode("utf-8")
    if not raw:
      return {}
    return json.loads(raw)


def _read_error(error):
  try:
    return error.read().decode("utf-8")[:500]
  except Exception:
    return ""
