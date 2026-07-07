def format_bytes(n: int) -> str:
    """Format a byte count as a human-readable string (e.g. 2.0 GB)."""
    val = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024:
            return f"{val:.1f} {unit}"
        val /= 1024
    return f"{val:.1f} PB"
