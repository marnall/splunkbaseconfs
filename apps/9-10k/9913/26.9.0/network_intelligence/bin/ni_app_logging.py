import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from splunk.clilib.bundle_paths import make_splunkhome_path

APP_NAME = "network_intelligence"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5
LOG_FORMAT = (
    "%(asctime)s pid=%(process)d thread_id=%(thread)d "
    "%(levelname)s [%(name)s] [%(module)s:%(lineno)d] [%(funcName)s] %(message)s"
)
COMPONENT_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def validate_log_component(component: str) -> str:
    normalized = str(component or "").strip()
    if not normalized:
        raise ValueError("Log component must not be empty")
    if normalized.endswith(".log"):
        raise ValueError("Log component must not include the .log suffix")
    if not COMPONENT_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid log component: {component!r}")
    return normalized


def component_log_path(component: str) -> Path:
    component = validate_log_component(component)
    return Path(make_splunkhome_path(["var", "log", "splunk", f"{APP_NAME}.{component}.log"]))


def component_logger_name(component: str) -> str:
    component = validate_log_component(component)
    return f"{APP_NAME}.{component}"


def replace_handlers(logger: logging.Logger):
    for handler in logger.handlers:
        handler.close()
    logger.handlers = []


def rotating_file_handler(
    log_path: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    log_format: str = LOG_FORMAT,
) -> logging.Handler:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    handler.setFormatter(logging.Formatter(log_format))
    return handler


def configure_component_logger(
    component: str,
    log_level: int = logging.INFO,
    log_path=None,
    log_format: str = LOG_FORMAT,
    fallback_handler: logging.Handler = None,
    fallback_description: str = "fallback logging handler",
) -> logging.Logger:
    component = validate_log_component(component)
    logger = logging.getLogger(component_logger_name(component))
    replace_handlers(logger)
    logger.propagate = False
    logger.setLevel(log_level)

    target_log_path = Path(log_path) if log_path is not None else component_log_path(component)
    try:
        handler = rotating_file_handler(target_log_path, log_format=log_format)
    except OSError as error:
        if fallback_handler is None:
            raise
        logger.addHandler(fallback_handler)
        logger.warning(
            f"Could not open {target_log_path} for {component} logging: {error}; using {fallback_description}"
        )
        return logger

    logger.addHandler(handler)
    return logger
