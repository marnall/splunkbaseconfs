import json
import os
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Type, TypeVar, Optional

import constants

if os.getenv(constants.splunk_home_env_variable):
    CONFIG_DIR = os.getenv(constants.splunk_home_env_variable) + '/etc/apps/akamai_mfa/config'
else:
    CONFIG_DIR = os.path.join(Path(__file__).resolve().parent.parent, "config")

T = TypeVar('T', bound='BaseConfig')


class BaseConfig:
    CONFIG_FILE: str

    @classmethod
    def ensure_config(cls):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if not os.path.exists(cls.CONFIG_FILE):
            default_data = {f.name: "" for f in fields(cls)}
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_data, f)

    @classmethod
    def load_from_file(cls: Type[T]) -> T:
        cls.ensure_config()
        with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        init_kwargs = {f.name: data.get(f.name, "") for f in fields(cls)}
        return cls(**init_kwargs)

    def save_to_file(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=4)

    def to_pretty_json(self) -> str:
        return json.dumps(self.__dict__, indent=4)


@dataclass
class AkamaiMfaConfig(BaseConfig):
    app_id: str
    signing_key: str
    host: str
    CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")


@dataclass
class AuthsConfig(BaseConfig):
    # Remove this field when 1.x is no longer in use or support is formally dropped
    after: str = ""
    min_time: str = ""
    max_time: Optional[str] = None
    page_size: int = constants.auths_page_size
    continuation_token: Optional[str] = None
    CONFIG_FILE = os.path.join(CONFIG_DIR, "auths.json")

    # Convert default values from string to int
    def __post_init__(self):
        if isinstance(self.page_size, str):
            self.page_size = int(self.page_size) if self.page_size else constants.auths_page_size


@dataclass
class SessionHistoryConfig(BaseConfig):
    min_time: str = ""
    max_time: Optional[str] = None
    max_items: int = constants.session_history_page_size
    page: int = 1
    CONFIG_FILE = os.path.join(CONFIG_DIR, "session_history.json")

    # Convert default values from string to int
    def __post_init__(self):
        if isinstance(self.max_items, str):
            self.max_items = int(self.max_items) if self.max_items else constants.session_history_page_size
        if isinstance(self.page, str):
            self.page = int(self.page) if self.page else 1


@dataclass
class ResourceConfig(BaseConfig):
    min_time: str = ""
    max_time: Optional[str] = None
    max_items: int = constants.resource_page_size
    page: int = 1
    CONFIG_FILE = os.path.join(CONFIG_DIR, "resource.json")

    # Convert default values from string to int
    def __post_init__(self):
        if isinstance(self.max_items, str):
            self.max_items = int(self.max_items) if self.max_items else constants.resource_page_size
        if isinstance(self.page, str):
            self.page = int(self.page) if self.page else 1
