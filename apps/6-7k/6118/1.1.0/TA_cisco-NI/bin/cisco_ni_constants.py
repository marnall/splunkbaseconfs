COUNT = 100
NUMBER_OF_THREADS = 16
TIMEOUT = 180
VERIFY_SSL = True

if (
    (isinstance(VERIFY_SSL, bool) and VERIFY_SSL is False)
    or (isinstance(VERIFY_SSL, int) and VERIFY_SSL == 0)
    or (
        isinstance(VERIFY_SSL, str)
        and VERIFY_SSL.lower() in ("0", "false", "f", "n", "no", "none", "")
    )
):
    VERIFY_SSL = False
else:
    VERIFY_SSL = True

API_PREFIX = "/sedgeapi/v1/cisco-nir/api/api/telemetry/"

LOGIN = "login"

INSIGHTS_GROUP_URL = "v2/config/insightsGroup"
ADVISORIES_URL = "advisories/details.json"
ANOMALIES_URL = "anomalies/details.json"
RECOMMENDATION_URL = {
    "advisories": "advisories/recommendations.json",
    "anomalies": "anomalies/recommendations.json",
}


def get_url(endpoint=None, recomd_type=None):
    """Return the entire URL for the required endpoint."""
    if endpoint == "insightsGroup":
        return API_PREFIX + INSIGHTS_GROUP_URL
    if endpoint == "anomalies":
        return API_PREFIX + ANOMALIES_URL
    if endpoint == "advisories":
        return API_PREFIX + ADVISORIES_URL
    if endpoint == "recommendations":
        return API_PREFIX + RECOMMENDATION_URL[recomd_type]
