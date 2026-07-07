from distutils.util import strtobool  # pylint: disable=no-name-in-module,import-error

import pytest
from code42 import Code42ForSplunk
from code42_batch_processor import Code42BatchDataProcessor
from py42.sdk import SDK
from requests import Response


@pytest.fixture
def modular_input_log(mocker):
    return mocker.MagicMock()


@pytest.fixture
def rest_log(mocker):
    return mocker.MagicMock()


@pytest.fixture
def config():
    return {
        "data_keys":  "",
        "report_user": "john.doe",
        "hostname": "example.com",
        "credential_realm": "abcdefg",
        "historical_lookback": 100
    }


@pytest.fixture
def modular_input(mocker):
    return mocker.MagicMock()


@pytest.fixture
def utils(mocker):
    return mocker.MagicMock()


@pytest.fixture
def proxy_loader(mocker):
    return mocker.MagicMock()


@pytest.fixture
def py42_settings(mocker):
    return mocker.patch("py42.settings")


@pytest.fixture
def py42_sdk(mocker):
    return mocker.MagicMock(spec=SDK)


@pytest.fixture
def py42_response(mocker):
    return mocker.MagicMock(spec=Response)


@pytest.fixture
def batch_processor(mocker):
    return mocker.MagicMock(spec=Code42BatchDataProcessor)


def create_get_config_mock(config):
    def get_config(key):
        return config.get(key)
    return get_config


def create_get_config_boolean_mock(config):
    def get_config_boolean(key):
        if key not in config:
            return False
        raw_value = config[key]
        if raw_value is None:
            return False
        return strtobool(str(raw_value))

    return get_config_boolean


def configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk, is_cloud=False):
    modular_input.get_config.side_effect = create_get_config_mock(config)
    modular_input.get_config_boolean.side_effect = create_get_config_boolean_mock(config)
    utils.is_cloud.return_value = is_cloud
    create_using_local_account = mocker.patch("py42.sdk.SDK.create_using_local_account", py42_sdk)
    create_using_local_account.return_value = py42_sdk


class TestCode42ForSplunk(object):

    def test_config_hostname_none_raises_exception(self, mocker, modular_input_log, rest_log, modular_input, config,
                                                   utils, proxy_loader, py42_sdk):
        config["hostname"] = None
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        with pytest.raises(Exception) as e:
            code42.initialize_sdk()

        assert e.value.args[0] == "Hostname is None, and is not configured."

    @pytest.mark.parametrize("hostname", ["http://example.com", "https://example.com"])
    def test_config_hostname_with_scheme_raises_exception(self, mocker, modular_input_log, rest_log, modular_input,
                                                          config, utils, hostname, proxy_loader, py42_sdk):
        config["hostname"] = hostname
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        with pytest.raises(Exception) as e:
            code42.initialize_sdk()

        expected_message = "Hostname cannot start with 'http://' or 'https://'. " + \
                           "Expected format: <hostname>:<port>. " + \
                           "Actual value: {0}. ".format(hostname) + \
                           "Set 'use_http = true' in inputs.conf to force HTTP instead of HTTPS."
        assert e.value.args[0] == expected_message

    def test_initialize_sdk_calls_host_on_modular_input_with_hostname(self, mocker, modular_input_log, rest_log,
                                                                      modular_input, config, utils, proxy_loader,
                                                                      py42_sdk):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        code42.initialize_sdk()
        modular_input.host.assert_called_with(config["hostname"])

    def test_is_cloud_true_and_use_http_false_initialize_sdk_raises_exception(self, mocker, modular_input_log, rest_log,
                                                                              modular_input, config, utils,
                                                                              proxy_loader, py42_sdk):
        config["use_http"] = "true"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk, is_cloud=True)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        with pytest.raises(Exception) as e:
            code42.initialize_sdk()

        assert e.value.args[0] == "Splunk Cloud requires using https."

    @pytest.mark.parametrize("use_http,expected_url", [(False, "https://example.com"),
                                                       (True, "http://example.com")])
    def test_initialize_sdk_calls_create_using_local_account_with_correct_address(self, use_http, expected_url, mocker,
                                                                                  modular_input_log, rest_log,
                                                                                  modular_input, config, utils,
                                                                                  proxy_loader, py42_sdk):
        config["use_http"] = use_http
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        create_using_local_account = mocker.patch("py42.sdk.SDK.create_using_local_account")

        code42.initialize_sdk()

        create_using_local_account.assert_called_with(expected_url, mocker.ANY, mocker.ANY, is_async=mocker.ANY)

    def test_initialize_sdk_sets_proxies(self, mocker, modular_input_log, rest_log, modular_input, utils, config,
                                         proxy_loader, py42_settings, py42_sdk):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        proxy_loader.load.return_value = "proxy-value"
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        mocker.patch("py42.sdk.SDK.create_using_local_account")
        code42.initialize_sdk()

        assert py42_settings.proxies == "proxy-value"

    @pytest.mark.parametrize("ssl_verify,expected", [("False", False), ("True", True)])
    def test_ssl_verify_initialize_sdk_sets_verify_ssl_certs(self, mocker, modular_input_log, rest_log, modular_input,
                                                             utils, config, proxy_loader, ssl_verify, expected,
                                                             py42_settings, py42_sdk):
        config["ssl_verify"] = ssl_verify
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        code42.initialize_sdk()

        assert py42_settings.verify_ssl_certs is expected

    def test_initialize_sdk_sets_global_exception_message_handler(self, mocker, modular_input_log, rest_log,
                                                                  modular_input, utils, config, proxy_loader,
                                                                  py42_settings, py42_sdk):

        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        code42.initialize_sdk()

        assert py42_settings.global_exception_message_receiver == code42.handle_error

    def test_report_user_initialize_sdk_calls_create_using_local_account_with_user(self, mocker, modular_input_log,
                                                                                   rest_log, modular_input, config,
                                                                                   utils, proxy_loader, py42_sdk):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        create_using_local_account = mocker.patch("py42.sdk.SDK.create_using_local_account")

        code42.initialize_sdk()

        create_using_local_account.assert_called_with(mocker.ANY, config["report_user"], mocker.ANY,
                                                      is_async=mocker.ANY)

    def test_report_user_credential_initialize_sdk_calls_create_using_local_account_with_credential(
            self, mocker, modular_input_log, rest_log, modular_input, config, utils, proxy_loader, py42_sdk):

        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        create_using_local_account = mocker.patch("py42.sdk.SDK.create_using_local_account")

        code42.initialize_sdk()

        create_using_local_account.assert_called_with(mocker.ANY, mocker.ANY, utils.get_credential(),
                                                      is_async=mocker.ANY)

    def test_initialize_sdk_calls_create_using_local_account_with_is_async_true(self, mocker, modular_input_log,
                                                                                rest_log, modular_input, config, utils,
                                                                                proxy_loader, py42_sdk):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        create_using_local_account = mocker.patch("py42.sdk.SDK.create_using_local_account")

        code42.initialize_sdk()

        create_using_local_account.assert_called_with(mocker.ANY, mocker.ANY, mocker.ANY, is_async=True)

    def test_handle_generic_response_calls_get_obj_from_response(self, mocker, modular_input_log, rest_log,
                                                                 modular_input, config, utils, proxy_loader, py42_sdk):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        get_obj_from_response = mocker.patch("py42.util.get_obj_from_response")
        response = mocker.MagicMock()
        data_key = mocker.MagicMock()
        sourcetype = mocker.MagicMock()

        code42.handle_generic_response(response, data_key, sourcetype)

        get_obj_from_response.assert_called_with(response, data_key)

    def test_handle_checkpoint_data_response_calls_get_obj_from_response(self, mocker, modular_input_log, rest_log,
                                                                         modular_input, config, utils, proxy_loader,
                                                                         py42_sdk):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        get_obj_from_response = mocker.patch("py42.util.get_obj_from_response")
        response = mocker.MagicMock()
        report_name = mocker.MagicMock()
        data_key = mocker.MagicMock()
        id_property = mocker.MagicMock()
        checkpoint = mocker.MagicMock()

        code42.handle_checkpoint_data_response(response, report_name, data_key, id_property, checkpoint)

        get_obj_from_response.assert_called_with(response, data_key)

    def test_run_computer_enabled_calls_devices_for_each_device(self, mocker, modular_input_log, rest_log,
                                                                  modular_input, config, utils, proxy_loader, py42_sdk):
        config["data_keys"] = "computer"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        code42.run()

        py42_sdk.devices.for_each_device.assert_called_with(include_backup_usage=True, return_each_page=True,
                                                            then=mocker.ANY)

    def test_run_computer_enabled_calls_print_multiple_events_of_sourcetype(self, mocker, modular_input_log, rest_log,
                                                                            modular_input, config, utils, proxy_loader,
                                                                            py42_sdk):
        config["data_keys"] = "computer"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        computers = mocker.MagicMock()

        def for_each_computer(include_backup_usage=None, return_each_page=None, then=None):
            then(computers)

        py42_sdk.devices.for_each_device.side_effect = for_each_computer

        code42.run()

        modular_input.print_multiple_events_of_sourcetype.assert_called_with("code42:computer", computers)

    def test_run_diagnostic_enabled_calls_handle_generic_response(self, mocker, modular_input_log, rest_log,
                                                                  modular_input, config, utils, proxy_loader, py42_sdk,
                                                                  py42_response):
        config["data_keys"] = "diagnostic"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        def get_diagnostics_mock(then=None, catch=None):
            then(py42_response)

        py42_sdk.administration.get_diagnostics.side_effect = get_diagnostics_mock
        handle_generic_response = mocker.patch("code42.Code42ForSplunk.handle_generic_response")

        code42.run()

        handle_generic_response.assert_called_with(py42_response, "data", "diagnostic")

    def test_run_diagnostic_enabled_calls_administration_get_diagnostics(self, mocker, modular_input_log, rest_log,
                                                                         modular_input, config, utils, proxy_loader,
                                                                         py42_sdk):
        config["data_keys"] = "diagnostic"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        code42.run()

        py42_sdk.administration.get_diagnostics.assert_called_with(then=mocker.ANY, catch=mocker.ANY)

    @pytest.mark.parametrize("data_key", ["user", "security"])
    def test_run_user_or_security_enabled_calls_print_multiple_events_of_sourcetype(self, data_key, mocker,
                                                                                    modular_input_log, rest_log,
                                                                                    modular_input, config, utils,
                                                                                    proxy_loader, py42_sdk,
                                                                                    py42_response, batch_processor):
        config["data_keys"] = data_key
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        mocker.patch('code42.Code42ForSplunk._create_splunk_security_event_fetcher_handlers')
        create_batch_processor = mocker.patch('code42.Code42ForSplunk._create_batch_data_processor')
        create_batch_processor.return_value = batch_processor
        batch_processor.get_stats.return_value = {"user_count": 5, "event_count": 10}

        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        code42.run()

        events = [{'total_events': 5, 'endpoint': 'user'}, {'total_events': 10, 'endpoint': 'security'}]
        modular_input.print_multiple_events_of_sourcetype.assert_called_with("code42:api", events, time_field="now")

    @pytest.mark.parametrize("data_key", ["user", "security"])
    def test_run_user_or_security_enabled_calls_start_on_batch_processor(self, data_key, mocker, modular_input_log,
                                                                         rest_log, modular_input, config, utils,
                                                                         proxy_loader, py42_sdk, py42_response,
                                                                         batch_processor):
        config["data_keys"] = data_key
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        mocker.patch('code42.Code42ForSplunk._create_splunk_security_event_fetcher_handlers')
        create_batch_processor = mocker.patch('code42.Code42ForSplunk._create_batch_data_processor')
        create_batch_processor.return_value = batch_processor

        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)
        code42.run()

        batch_processor.start.assert_called()

    def test_run_alertlog_enabled_calls_get_alert_log(self, mocker, modular_input_log, rest_log, modular_input, config,
                                                      utils, proxy_loader, py42_sdk):
        config["data_keys"] = "alertlog"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        code42.run()

        py42_sdk.administration.get_alert_log.assert_called_with(page_size=999999, then=mocker.ANY, catch=mocker.ANY)

    def test_run_alertlog_enabled_calls_handle_checkpoint_data_response(self, mocker, modular_input_log, rest_log,
                                                                        modular_input, config, utils, proxy_loader,
                                                                        py42_sdk):
        config["data_keys"] = "alertlog"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        def get_alert_log(page_size=None, then=None, catch=None):
            then(py42_response)

        py42_sdk.administration.get_alert_log.side_effect = get_alert_log
        handle_checkpoint_data_response = mocker.patch("code42.Code42ForSplunk.handle_checkpoint_data_response")

        code42.run()

        handle_checkpoint_data_response.assert_called_with(py42_response, "alertlog", "log", "id",
                                                           modular_input._get_checkpoint())

    def test_run_restore_enabled_calls_get_current_user_org(self, mocker, modular_input_log, rest_log, modular_input, config,
                                                    utils, proxy_loader, py42_sdk):
        config["data_keys"] = "restore"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        code42.run()

        py42_sdk.orgs.get_current_user_org.assert_called_with(then=mocker.ANY)

    def test_run_restore_enabled_calls_get_restore_history(self, mocker, modular_input_log, rest_log, modular_input,
                                                           config, utils, proxy_loader, py42_sdk, py42_response):
        config["data_keys"] = "restore"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        def get_current_user_org(then=None):
            then(py42_response)

        py42_sdk.orgs.get_current_user_org.side_effect = get_current_user_org
        mocker.patch("py42.util.get_obj_from_response").return_value = {"orgId": 5}

        code42.run()

        py42_sdk.archive.get_restore_history.assert_called_with(mocker.ANY, org_id=5, page_size=999999, then=mocker.ANY)

    def test_run_restore_enabled_calls_handle_checkpoint_data_response(self, mocker, modular_input_log, rest_log,
                                                                       modular_input, config, utils, proxy_loader,
                                                                       py42_sdk, py42_response):
        config["data_keys"] = "restore"
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        def get_current_user_org(then=None):
            then(py42_response)

        def get_restore_history(num_days, org_id=None, page_size=None, then=None):
            then(py42_response)

        py42_sdk.orgs.get_current_user_org.side_effect = get_current_user_org
        mocker.patch("py42.util.get_obj_from_response").return_value = {"orgId": 5}
        py42_sdk.archive.get_restore_history.side_effect = get_restore_history
        handle_checkpoint_data_response = mocker.patch("code42.Code42ForSplunk.handle_checkpoint_data_response")

        code42.run()

        handle_checkpoint_data_response.assert_called_with(py42_response, "restore", "restoreEvents", "restoreId",
                                                           modular_input._get_checkpoint())

    def test_run_calls_sdk_wait(self, mocker, modular_input_log, rest_log, modular_input, config, utils, proxy_loader,
                                py42_sdk):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        code42.run()

        py42_sdk.wait.assert_called()

    @pytest.mark.parametrize("current_timestamp, historical_lookback, expected", [
        (1567732629, None, 1562548629),
        (1567732629, 0, 1567732629),
        (1567732629, 1, 1567646229),
        (1567732629, 30, 1565140629),
        (1567732629, 60, 1562548629)
    ])
    def test_calculate_min_timestamp_for_security_events(self, mocker, modular_input_log, rest_log, modular_input,
                                                         config, utils, proxy_loader, py42_sdk, current_timestamp,
                                                         historical_lookback, expected):
        configure_mock_dependencies_for_code42_for_splunk(config, mocker, modular_input, utils, py42_sdk)
        code42 = Code42ForSplunk(modular_input_log, rest_log, modular_input, utils, proxy_loader)

        def get_config(key):
            assert key == "historical_lookback"
            return historical_lookback

        modular_input.get_config.side_effect = get_config
        mocker.patch("code42_util.get_current_timestamp_in_seconds", lambda: current_timestamp)

        actual = code42._calculate_min_timestamp_for_security_events()
        assert actual == expected
