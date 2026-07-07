import logging
import os
import platform
import subprocess
from urllib.parse import urlencode
import constants
import configparser

LOG = logging.getLogger(__name__)


def _get_splunk_server_version():
    """Get Splunk server info, preferring local splunk.version file over CLI subprocess."""
    splunk_home = os.getenv(constants.splunk_home_env_variable)
    if not splunk_home:
        return None

    # Primary: read from splunk.version
    try:
        version_file = os.path.join(splunk_home, "etc", "splunk.version")
        data = {}
        with open(version_file) as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    data[key] = value
        if data.get("VERSION"):
            # Match the expected {"raw": ...} structure
            return {"raw": f"Splunk {data['VERSION']} (build {data.get('BUILD', '')})"}
    except Exception:
        LOG.error("Exception while getting version from splunk.version, falling back to CLI")

    # Fallback: use CLI subprocess
    try:
        splunk_bin = os.path.join(splunk_home, "bin", "splunk")
        result = subprocess.run(
            [splunk_bin, "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Output looks like: "Splunk 9.1.2 (build abc123)"
            return {"raw": result.stdout.strip()}
    except Exception:
        LOG.error("Exception while try to get Splunk version via subprocess")

    return None


def _parse_splunk_version():
    """Extract version from a raw splunk version string.
    """
    server_info = _get_splunk_server_version()
    raw = server_info.get("raw", None) if server_info else None
    if raw:
        parts = raw.split()
        if len(parts) >= 2:
            version = parts[1]
            if version:
                return version
    return None


def _get_platform_system():
    """Return a friendly OS name (Windows, Linux, macOS)."""
    try:
        system = platform.system()
        if system:
            return "macOS" if system == "Darwin" else system
    except Exception:
        pass

    return None


def _get_platform_version():
    """Return a semver-ish OS version string.

    Examples: 'NT 10.0.19041', '5.15.0-76-generic', '23.5.0'
    """
    try:
        system = platform.system()
        if system:
            if system == "Windows":
                release = platform.release()  # 'NT'
                version = platform.version()  # '10.0.19041'
                if release and version:
                    return f"{release} {version}"
            # Linux/macOS: kernel or darwin version
            release = platform.release()
            if release:
                return release
    except Exception:
        pass

    return None


def _get_os_info():
    """Return the most verbose OS version info available.

    Examples: 'Windows Server 2016', 'Ubuntu 22.04.3 LTS',
              'macOS 14.5', 'Red Hat Enterprise Linux 9.2'
    """
    try:
        system = platform.system()

        if system == "Darwin":
            mac_ver = platform.mac_ver()[0]  # e.g. '14.5'
            return f"macOS {mac_ver}" if mac_ver else "macOS"

        if system == "Windows":
            edition = platform.win32_edition()  # e.g. 'ServerStandard', 'Enterprise'
            version = platform.version()
            if edition and version:
                return f"{system} {edition} {version}"
            return f"{system} {version}" if version else system

        # Linux: read /etc/os-release for distro details
        with open("/etc/os-release") as f:
            os_release = {}
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, _, value = line.partition("=")
                    os_release[key] = value.strip('"')
            pretty = os_release.get("PRETTY_NAME")
            if pretty:
                return pretty

        platform_info = platform.platform()
        if platform_info:
            return platform_info
    except Exception:
        pass

    return None


def _get_splunk_platform_type():
    """Determine Splunk platform type from local config files."""
    splunk_home = os.getenv(constants.splunk_home_env_variable)
    if not splunk_home:
        return None

    try:
        # Read active license group from server.conf
        server_conf = os.path.join(splunk_home, "etc", "system", "local", "server.conf")
        config = configparser.ConfigParser()
        config.read(server_conf)

        active_group = config.get("license", "active_group", fallback="").strip()

        if active_group:
            return f"Splunk {active_group}"  # "Splunk Enterprise", "Splunk Free", "Splunk Cloud".

    except Exception:
        LOG.error("Error reading Splunk platform type from server.conf")

    return None


def get_user_agent_details():
    """Return a query-string of user-agent fields describing this Splunk plugin environment.

    Fields with None or empty string values are omitted.

    Returns:
        A string like 'client=Splunk&client_version=2.0.8&platform=Linux&...'
    """
    try:
        details = {
            "client": "Splunk",
            "client_version": constants.app_version,
        }

        splunk_version = _parse_splunk_version()
        if splunk_version:
            details['platform_version'] = splunk_version

        platform_type = _get_splunk_platform_type()
        if platform_type:
            details['platform'] = platform_type

        os_info = _get_os_info()
        LOG.info(f"Server details: {os_info}")

        return urlencode({k: v for k, v in details.items() if v})
    except Exception:
        return None
