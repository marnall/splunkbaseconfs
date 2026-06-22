"""Hardened validator for the user-supplied SSL/TLS CA certificate path.

Mitigates the symlink-aware path-traversal class of issue flagged in the
v1.2.4 security audit (Medium severity: cert_location unvalidated).

Rejects:
  * relative paths
  * paths containing ``..`` segments
  * paths containing control characters or null bytes
  * paths that resolve to anything other than a regular file
    (directories, sockets, device nodes, FIFOs)

The returned canonical path (``os.path.realpath`` of the input) is the form
that should be handed to TLS libraries — it eliminates ambiguity about
what target file is actually loaded as a CA.
"""
import os


def validate_cert_path(path):
    """Return the canonical safe path, ``None`` if no path was supplied,
    or raise ``ValueError`` if the input fails any safety check.
    """
    if path is None:
        return None
    if not isinstance(path, str):
        raise ValueError(
            "cert_location must be a string path; "
            f"got {type(path).__name__}."
        )
    stripped = path.strip()
    if not stripped:
        return None

    # 1. No control characters anywhere in the input. This includes the
    #    null byte (used to truncate paths on some platforms) and newline
    #    (used to inject fake log entries via the error message).
    for ch in stripped:
        if ord(ch) < 32 or ord(ch) == 127:
            raise ValueError(
                "cert_location contains a control character; refuse to load."
            )

    # 2. Reject any explicit ``..`` path segment. We do this on both
    #    forward- and back-slash views so Windows hand-crafted paths are
    #    also caught.
    normalized = stripped.replace("\\", "/")
    if ".." in [seg for seg in normalized.split("/") if seg]:
        raise ValueError(
            "cert_location must not contain '..' path traversal segments."
        )

    # 3. Require an absolute path so the resolution is deterministic
    #    regardless of where the modular input process happens to be
    #    rooted.
    if not os.path.isabs(stripped):
        raise ValueError(
            "cert_location must be an absolute path "
            f"(got: {stripped!r})."
        )

    # 4. Resolve the canonical form. This dereferences symlinks once;
    #    we still accept the result, but we reject below if the final
    #    target is not a regular file.
    canonical = os.path.realpath(stripped)

    # 5. The final target must exist AND be a regular file. ``os.path.isfile``
    #    follows symlinks (which is what we want — we've already taken the
    #    canonical view) and returns False for directories, devices, FIFOs,
    #    and sockets.
    if not os.path.isfile(canonical):
        raise ValueError(
            f"cert_location does not point to a regular file: {stripped!r}."
        )

    return canonical
