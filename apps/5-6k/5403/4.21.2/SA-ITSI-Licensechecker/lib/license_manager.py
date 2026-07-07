# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

from splunk_message_handler import SplunkMessageHandler
from utils import setup_logging


class LicenseManager:
    """
    Installs and updates ITSI built-in sourcetype licenses.
    Also installs/uninstalls ITSI built-in licenses for suitification signaling to license peers.
    This class is designed to run on LM or self-licensed instance.
    """

    def __init__(self, license_api, license_group):
        self.license_api = license_api
        self.license_group = license_group
        self.itsi_licenses = self.license_api.get_itsi_licenses()
        self.log = setup_logging(log_file='itsi_license_checker.log', logger_name='itsi.license_checker.LicenseManager')

    def internal_license_installed(self):
        return self.license_group.get_itsi_internal_license().among_licenses(self.itsi_licenses)

    def install_internal_license(self):
        try:
            self._delete_old_internal_license()
        except Exception:
            # we should continue even if the removal of the old license fails
            self.log.exception("Failed to delete old license")

        self._install_new_internal_license()

    def _delete_old_internal_license(self):
        """
        In ITSI 4.6.0, we're updating the license (that ITSI had shipped since ITSI 4.0.0) to a new license
        that uses a new sourcetype. Before we do that, we need to make sure we remove the old license (which
        still uses the old sourcetype).
        """
        old_license = self.license_group.get_old_itsi_internal_ea_license().resolve_to_real_license(self.itsi_licenses)

        if old_license is None:
            return

        self.license_api.remove_license(old_license.name)

    def _install_new_internal_license(self):
        """
        For Hulk release (aka 4.0.0) and above, we want to automatically upload our new license

        As of ITSI 4.6.0, license updated to use a generic "itsi*" sourcetype to accommodate more ITSI sourcetypes
        @return:
        """

        self.license_api.install_license(self.license_group.get_itsi_internal_license())

    def manage_plus_license_marker(self):
        if self._itsi_license_installed():
            if self._plus_suite_signaling_license_installed():
                return
            else:
                self.log.info("ITSI license is installed, but Plus marker is not installed. Installing Plus marker")
                self._install_plus_suite_signaling_license()
        elif self._plus_suite_signaling_license_installed():
            self.log.info("ITSI license is not installed, but Plus marker is installed. Removing Plus marker")
            self._remove_plus_suite_signaling_license()

    def _itsi_license_installed(self):
        return any(not lic.among_licenses(self.license_group.get_licenses()) for lic in self.itsi_licenses)

    def _plus_suite_signaling_license_installed(self):
        return self.license_group.get_plus_suite_signaling_license().among_licenses(self.itsi_licenses)

    def _install_plus_suite_signaling_license(self):
        self.license_api.install_license(self.license_group.get_plus_suite_signaling_license())
        self._notify_plus_suite_activation_delay()

    def _remove_plus_suite_signaling_license(self):
        plus_license = self.license_group.get_plus_suite_signaling_license().resolve_to_real_license(self.itsi_licenses)
        self.license_api.remove_license(plus_license)

    def manage_license_expiration_signaling_license(self):
        real_itsi_licenses = list(
            [lic for lic in self.itsi_licenses if not lic.among_licenses(self.license_group.get_licenses())])
        if not real_itsi_licenses:
            self.log.info('No real ITSI license is installed')
            self._remove_license_expiration_signaling_license()
            return

        # Some Real ITSI licenses are installed

        if all(not lic.is_valid() for lic in real_itsi_licenses):
            self.log.info('All real ITSI licenses are expired')
            self._install_license_expiration_signaling_license()
        else:
            self.log.info('There are some real ITSI unexpired licenses')
            self._remove_license_expiration_signaling_license()

    def _remove_license_expiration_signaling_license(self):
        expire_license = self.license_group.get_license_expiration_signaling_license().resolve_to_real_license(
            self.itsi_licenses)
        if expire_license is None:
            return
        self.license_api.remove_license(expire_license)

    def _install_license_expiration_signaling_license(self):
        expire_license = self.license_group.get_license_expiration_signaling_license().resolve_to_real_license(
            self.itsi_licenses)
        if expire_license is not None:
            return
        self.license_api.install_license(self.license_group.get_license_expiration_signaling_license())

    def _notify_plus_suite_activation_delay(self):
        message_text = 'An ITSI license has been detected. It can take up to 3 minutes to upgrade to ITSI.'
        msg_id = 'plus_notification'
        message_handler = SplunkMessageHandler(self.license_api.session_key, self.log)
        message_handler.post_or_update_message(msg_id, SplunkMessageHandler.INFO, message_text)
