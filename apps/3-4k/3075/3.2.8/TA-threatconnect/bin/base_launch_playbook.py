#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Search Module"""
import logging

from requests.auth import HTTPBasicAuth


class BaseLaunchPlaybook:
    """ThreatConnect Search Module"""

    # implement child class / other parent properties
    _playbook_data = None
    tcs = None

    @property
    def auth(self):
        """Return basic auth."""
        auth = None
        if self.playbook_data.basic_auth_enabled:
            auth = HTTPBasicAuth(self.playbook_data.username, self.password)
        return auth

    @property
    def password(self):
        """Return the playbook password."""
        pb_pass = None
        for stored_password in self.service.storage_passwords:  # pylint: disable=no-member
            if stored_password.name == f'tcPlaybooks:{self.playbook_data.id}:':
                pb_pass = stored_password.content['clear_password']
                break
        else:
            self.message(  # pylint: disable=no-member
                f'The proxy password for user ({self.playbook_data.username}) could not be found.',
                status='failure',
                level=logging.CRITICAL,
            )
        return pb_pass

    def launch_playbook(self, method, body=None, params=None, headers=None):
        """Launch playbook.

        .. note:: This method assumes the body is ALWAYS JSON.

        Args:
            method (str): The HTTP method (e.g., GET or POST).
            body (dict, default: None): The JSON body to post.
            params (dict, default: None): The HTTP query params to send.
            headers (dict, default: None): The HTTP headers to send.

        Returns:
            request.Response: The requests Response object.
        """
        return self.tcs.session.request(
            method.upper(),
            url=self.playbook_data.endpoint,
            auth=self.auth,
            json=body,
            params=params,
            headers=headers,
        )

    @property
    def playbook_data(self):
        """Return fields input."""
        if self._playbook_data is None:
            self._playbook_data = self.tcs.collections.playbooks.query_by_id(
                self.playbook_key  # pylint: disable=no-member
            )
        return self._playbook_data
