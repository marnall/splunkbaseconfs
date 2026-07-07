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
# File: app/secret.py
#
# Author: alexeiyur AT g m 4 i l . c 0 m
# Licensed under the MIT License (https://mit-license.org/)

# Only mask chars (and sep chars if multi-password - below) are sent back to the client, never the actual password
PSWD_MASK_CHAR = "*"

# All passwords should be validated to not contain this control char, in case it's used
# to concatenate multiple passwords for bulk encryption as in the 'proxies' setting
MULTI_PSWD_SEP_CHAR = "\t"


# All special proxy formatting chars are still valid (the re used makes sure of that), except the whitespace
# The re parsing already guarantees whitespace to be excluded so no additional checking is necessary
# INVALID_PSWD_CHARS = '/:@. \t'
INVALID_PSWD_CHARS = " \t"


class Secret:
    """For the sake of 'extra' security echo a dummy string back from the server.
    The dummy value of the same length will pass the form validation so there is no need to retype.
    On the way back to the server, detect it and don't override the value keeping it the same.
    Furthermore, explicitly clear the value when the session goes out.
    """

    def __get__(self, instance, _):  # _ owner
        return (
            ""
            if instance.pswd is None or instance.pswd == ""
            else "".join(MULTI_PSWD_SEP_CHAR if c == MULTI_PSWD_SEP_CHAR else PSWD_MASK_CHAR for c in instance.pswd)
        )

    def __set__(self, instance, value):
        pswd = (
            value
            if any(
                a()
                for a in [
                    lambda: instance.pswd is None,
                    lambda: instance.pswd == "",
                    lambda: len(value) != len(instance.pswd),
                    lambda: not set(value).issubset(set(PSWD_MASK_CHAR + MULTI_PSWD_SEP_CHAR)),
                ]
            )
            else instance.pswd
        )
        if pswd != instance.pswd:
            instance.pswd = pswd
            if instance.pswd != "":
                instance.save(instance.conf)


class Password:
    secret = Secret()

    def __init__(self, name, session=None):
        self.pswd = None
        self.name = name
        self.session = session

    def getUser(self):
        try:
            user = self.session["logged_in"]
        except Exception:
            user = "secret"
        return user

    def simpleHash(self, s):
        import ctypes

        v = ord(s[0]) << 7
        for c in s:
            v = ctypes.c_int32((1000003 * v) & 0xFFFFFFFF).value ^ ord(c)
        v = v ^ len(s)
        if v == -1:
            v = -2
        return int(v)

    def clear(self):
        self.pswd = None

    def load(self, conf):
        """Load from the secure storage"""
        self.conf = conf
        # Must load from scratch as the secret is per-user and should not leak
        self.clear()
        try:
            if not conf._isEnabled("qradar"):
                raise ImportError("Skip qpylib for LSS debug")

            from qpylib.encdec import Encryption, EncryptionError

            try:
                self.pswd = Encryption({"name": self.name, "user": self.simpleHash(self.getUser())}).decrypt()
            except EncryptionError:
                pass
        except ImportError:
            # TODO Implement for LSS app
            pass

    def save(self, conf):
        """Save to the secure storage"""
        try:
            if not conf._isEnabled("qradar"):
                raise ImportError("Skip qpylib for LSS debug")

            from qpylib.encdec import Encryption, EncryptionError

            try:
                Encryption({"name": self.name, "user": self.simpleHash(self.getUser())}).encrypt(self.pswd)
            except EncryptionError:
                pass
        except ImportError:
            # TODO Implement for LSS app
            pass
