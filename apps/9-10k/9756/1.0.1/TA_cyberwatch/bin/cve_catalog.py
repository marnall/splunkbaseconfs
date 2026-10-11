#
# Copyright 2026 Process-IT
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
#
"""CVE catalog input.
"""

import import_declare_test  # noqa: F401  isort:skip -- must run first, it fixes sys.path

import sys

from splunklib import modularinput as smi

from ta_cyberwatch import runner

INPUT_NAME = "cve_catalog"
TITLE = "CVE catalog"
EXTRA_ARGUMENTS = ['scope']


class Input(smi.Script):
    def get_scheme(self) -> smi.Scheme:
        return runner.build_scheme(INPUT_NAME, TITLE, EXTRA_ARGUMENTS)

    def validate_input(self, definition: smi.ValidationDefinition) -> None:
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
        runner.stream(INPUT_NAME, inputs, event_writer)


if __name__ == "__main__":
    sys.exit(Input().run(sys.argv))
