from multiprocessing import cpu_count


# Returns CPU count or 1 if gets any exception
def get_cpu_count():
    """Return CPU count or 1 if gets any exception."""
    try:
        return cpu_count()
    except Exception:
        return 1


# Process count logic
def get_process_count(process_count):
    """Process count logic."""
    try:
        process_count = int(process_count)
    except Exception:
        process_count = get_cpu_count() // 2

    if process_count < 1:
        process_count = 1

    return process_count
