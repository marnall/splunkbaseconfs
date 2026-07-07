# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import abc

# from typing_extensions import Protocol
from typing import Union

from pydantic import BaseModel, Field


class Row(BaseModel, abc.ABC):
    type: str


class KVRow(BaseModel):
    key: str
    value: str
    type: str = Field(default="kv_row")


class HeadingRow(BaseModel):
    value: str
    type: str = Field(default="heading_row")


class TextRow(BaseModel):
    value: str
    type: str = Field(default="text_row")


class LRRow(BaseModel):
    left: str
    right: str
    type: str = Field(default="lr_row")


class ImageRow(BaseModel):
    cid: str
    type: str = Field(default="image_row")


class Report(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    message: str
    rows: list[Union[KVRow, HeadingRow, TextRow, ImageRow, LRRow]]
