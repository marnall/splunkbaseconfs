import os
import json

from pathlib import Path
from logging import (
    debug,
    info,
)
from datetime import datetime
from dataclasses import dataclass
from collections import OrderedDict


@dataclass
class JSONFileDecodeError(Exception):
    """
    JSON File decode error occurred.

    Tried to load JSON file into dict
    """

    fname: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class JSONFileNotFoundError(Exception):
    """
    JSON File not found error occurred.
    """

    fpath: str
    exc_msg: str


def create_json_file_content(type=None, **attributes):
    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    schema = {
        "type": type,
        "created_at": created_at,
        "last_modified_at": None,
        "data": {},
    }

    if attributes:
        schema.update(attributes)

    return OrderedDict(schema)


class JSONFileContent:
    def __init__(self, type, created_at, last_modified_at, data, **kwargs):
        self.type = type
        self.created_at = created_at
        self.last_modified_at = last_modified_at
        self.data = data

        if kwargs:
            self.__dict__.update(kwargs)

    @property
    def datetime_format(self):
        return "%Y-%m-%dT%H:%M:%S.%fZ"

    @property
    def created_at_datetime(self):
        if self.created_at is None:
            return None

        return datetime.strptime(self.created_at, self.datetime_format)

    @property
    def last_modified_at_datetime(self):
        if self.last_modified_at is None:
            return None

        return datetime.strptime(self.last_modified_at, self.datetime_format)

    def dict(self):
        return self.__dict__


class JSONFileManager:
    def __init__(
        self, storage_dir, file_replace_period_in_days=1, file_clean_period_in_days=3
    ):
        self._file_replace_period_in_days = file_replace_period_in_days
        self._file_clean_period_in_days = file_clean_period_in_days
        self._storage_dir = Path(storage_dir)

    def _compose_file_path(self, file_name):
        file_with_ext = f"{file_name}.json"

        return Path(self.dir, Path(file_with_ext))

    @property
    def dir(self):
        return self._storage_dir

    @property
    def file_replace_period(self):
        return self._file_replace_period_in_days

    @property
    def file_clean_period(self):
        return self._file_clean_period_in_days

    @property
    def file_datetime_format(self):
        return "%Y%m%dT%H%M%S"

    def read(self, file_name):
        file_absolute_path = self._compose_file_path(file_name)

        try:
            with open(file_absolute_path, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except FileNotFoundError as file_not_found_err:
            info(f"[EXCEPTION] File not found path={file_absolute_path}")
            info(f"[EXCEPTION] Message raised msg={str(file_not_found_err)}")
            raise JSONFileNotFoundError(
                fpath=file_absolute_path, exc_msg=str(file_not_found_err)
            )
        except json.decoder.JSONDecodeError as json_decode_err:
            debug(f"[EXCEPTION] Failed to load {file_absolute_path} file")
            debug(f"[EXCEPTION] Failed to decode content of {file_absolute_path} file")
            debug(
                f"[EXCEPTION] Message raised msg={str(json_decode_err)} file={file_absolute_path}"
            )
            raise JSONFileDecodeError(fname=file_name, exc_msg=str(json_decode_err))

    def write(self, file_name, content):
        file_absolute_path = self._compose_file_path(file_name)

        with open(file_absolute_path, "w", encoding="utf-8") as json_file:
            # Write the JSON data in most compact representation
            json.dump(content, json_file, ensure_ascii=False, separators=(",", ":"))

        return None

    def delete(self, file_name):
        file_absolute_path = self._compose_file_path(file_name)
        os.remove(file_absolute_path)

        return None

    def rename(self, file_name, new_file_name):
        file_path = self._compose_file_path(file_name)
        new_file_path = self._compose_file_path(new_file_name)
        os.rename(file_path, new_file_path)

        return None

    def is_file_exists(self, file_name):
        file_absolute_path = self._compose_file_path(file_name)

        return os.path.isfile(file_absolute_path)

    def should_replace(self, file_created_at):
        current_datetime = datetime.now()
        substracted_datetime = current_datetime - file_created_at

        if not substracted_datetime.days >= self.file_replace_period:
            return False

        return True

    def list_files(self):
        dir = self.dir
        files = [file for file in os.listdir(dir) if os.path.isfile(Path(dir) / file)]

        return files

    def filter_by_name(self, files, file_name):
        return [Path(file).stem for file in files if file_name in file]


class JSONFileRepository:
    def __init__(self, manager):
        self.manager = manager

    def get(self, file_name):
        if not self.manager.is_file_exists(file_name):
            return None

        json_file_content_dict = self.manager.read(file_name)

        return JSONFileContent(**json_file_content_dict)

    def create(self, file_name, json_file_content: JSONFileContent):
        self.manager.write(file_name, json_file_content.dict())

    def update(self, file_name, json_file_content: JSONFileContent):
        json_file_content.last_modified_at = datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        tmp_file_name = file_name + "_" + datetime.now().strftime("%Y%m%dT%H%M%S%fZ")
        # Save data into a temporary file
        self.manager.write(tmp_file_name, json_file_content.dict())
        # Delete already existing file
        if self.manager.is_file_exists(file_name):
            self.manager.delete(file_name)
        # Rename temporary file with the original file name
        self.manager.rename(tmp_file_name, file_name)

    def delete(self, file_name):
        if not self.manager.is_file_exists(file_name):
            return None

        self.manager.delete(file_name)

        return None


def trim_old_json_file_content_data_entries(
    json_file_content: JSONFileContent, trim_period_in_days=3
):
    fresh_entries = {}

    for key, entry in json_file_content.data.items():
        if "last_ingested_at" not in entry:
            continue

        last_ingested_at_datetime = datetime.strptime(
            entry["last_ingested_at"], json_file_content.datetime_format
        )
        current_datetime = datetime.now()
        substracted_datetime = current_datetime - last_ingested_at_datetime

        if substracted_datetime.days >= trim_period_in_days:
            continue

        fresh_entries[key] = entry

    return fresh_entries


def replace_file(
    file_manager: JSONFileManager,
    file_name: str,
    old_json_file_content: JSONFileContent,
    new_json_file_content: JSONFileContent,
):
    new_file_name = "-".join(
        (
            file_name,
            old_json_file_content.created_at_datetime.strftime(
                file_manager.file_datetime_format
            ),
        )
    )
    file_manager.replace_with_new(
        file_name, new_file_name, new_json_file_content.dict()
    )

    return new_json_file_content
