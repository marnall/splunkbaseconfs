# Input-config helpers: whole-number interval parsing, range checks, checkbox truthiness, and global-namespace conf stanza reads.
try:
    import import_declare_test
except ImportError:
    pass


def _whole_number(raw, message):
    if not (raw.isascii() and raw.isdigit()):
        raise ValueError(message)
    return int(raw)


def parse_interval(parameters):
    raw = str(parameters.get("interval") or "").strip()
    return _whole_number(raw, "interval must be a whole number of seconds")


def validate_interval(parameters, lo, hi):
    value = parse_interval(parameters)
    if not lo <= value <= hi:
        raise ValueError("interval must be between %d and %d seconds" % (lo, hi))
    return value


def validate_whole_number(parameters, field, lo, hi, default=None):
    raw = str(parameters.get(field) or "").strip()
    if not raw and default is not None:
        return default
    value = _whole_number(raw, field + " must be a whole number")
    if not lo <= value <= hi:
        raise ValueError("%s must be between %d and %d" % (field, lo, hi))
    return value


def clamp(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def clamp_param(logger, input_name, param, value, lo, hi):
    used = clamp(value, lo, hi)
    if used != value and logger is not None:
        import netkit_logging
        logger.warning(netkit_logging.kv(
            event="param_clamped", input=input_name, param=param,
            configured=value, clamped=used))
    return used


_GLOBAL_NS = "-"


def read_stanza(session_key, conf_name, stanza_name):
    from solnlib import conf_manager
    manager = conf_manager.ConfManager(session_key, _GLOBAL_NS)
    return manager.get_conf(conf_name).get(stanza_name)


_TRUE_VALUES = ("1", "true", "yes", "on")


def is_true(value):
    return str(value or "").strip().lower() in _TRUE_VALUES
