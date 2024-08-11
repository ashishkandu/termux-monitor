import json
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import RequestException, Timeout

from src.termux_monitor.config import GetCountryConfig, TelephonyConfig


def lazy_imports():
    global \
        get_country, \
        get_notifications, \
        get_telephony_device_info, \
        is_network_operator_name_as_desired, \
        is_network_up, \
        restart_wifi
    from src.termux_monitor.core import (
        get_country,
        get_notifications,
        get_telephony_device_info,
        is_network_operator_name_as_desired,
        is_network_up,
        restart_wifi,
    )


class MockLoggerFactory(logging.Handler):
    @staticmethod
    def get_logger(name: str):
        logging.disable(100)
        return logging.getLogger("test")


@pytest.fixture(autouse=True)
def setup_and_teardown():
    with patch("src.termux_monitor.tglogging.LoggerFactory", new=MockLoggerFactory):
        # Import modules after mocking is set up
        lazy_imports()
        yield


def lazy_imports():
    global \
        get_country, \
        get_notifications, \
        get_telephony_device_info, \
        is_network_operator_name_as_desired, \
        is_network_up, \
        restart_wifi

    from src.termux_monitor.core import (
        get_country,
        get_notifications,
        get_telephony_device_info,
        is_network_operator_name_as_desired,
        is_network_up,
        restart_wifi,
    )


@pytest.fixture(autouse=True)
def setup_and_teardown():
    with patch(
        "src.termux_monitor.tglogging.LoggerFactory.get_logger",
        return_value=logging.getLogger("test"),
    ):
        # Import modules after mocking is set up
        lazy_imports()
        yield


class TestRestartWifi:
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_wifi_restarts_successfully(self, mock_sleep, mock_run):
        mock_run.side_effect = [None, None]
        mock_sleep.return_value = None
        result = restart_wifi()
        mock_run.assert_any_call(["termux-wifi-enable", "false"], check=True)
        mock_run.assert_any_call(["termux-wifi-enable", "true"], check=True)
        assert result

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_wifi_disable_raises_error(self, mock_sleep, mock_run):
        mock_run.side_effect = [subprocess.CalledProcessError(1, "cmd")]
        mock_sleep.return_value = None
        result = restart_wifi()
        mock_run.assert_called_once_with(["termux-wifi-enable", "false"], check=True)
        assert not result

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_wifi_enable_raises_error(self, mock_sleep, mock_run):
        mock_run.side_effect = [None, subprocess.CalledProcessError(1, "cmd")]
        mock_sleep.return_value = None
        result = restart_wifi()
        mock_run.assert_any_call(["termux-wifi-enable", "false"], check=True)
        mock_run.assert_any_call(["termux-wifi-enable", "true"], check=True)
        assert not result

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_wifi_enable_raises_timeout_error(self, mock_sleep, mock_run):
        mock_run.side_effect = [None, subprocess.TimeoutExpired("cmd", timeout=1)]
        mock_sleep.return_value = None
        result = restart_wifi()
        mock_run.assert_any_call(["termux-wifi-enable", "false"], check=True)
        mock_run.assert_any_call(["termux-wifi-enable", "true"], check=True)
        assert not result


@patch("src.termux_monitor.core.is_internet_connected", return_value=True)
class TestGetCountry:
    @patch("src.termux_monitor.core.requests.get")
    def test_get_country_success(self, mock_get, mock_is_connected):
        mock_response = mock_get.return_value
        mock_response.json.return_value = {"country": "US"}

        country = get_country()

        expected_url = GetCountryConfig.URL
        expected_timeout = GetCountryConfig.TIMEOUT

        assert country == "US"
        assert mock_get.call_args[0][0] == expected_url
        assert mock_get.call_args[1].get("timeout") == expected_timeout

    @patch("src.termux_monitor.core.requests.get")
    @patch("time.sleep")
    def test_get_country_timeout(self, mock_sleep, mock_get, mock_is_connected):
        mock_sleep.return_value = None
        mock_get.side_effect = Timeout

        country = get_country()

        assert country is None
        assert mock_get.call_count == GetCountryConfig.MAX_RETRIES
        mock_get.assert_called_with(
            GetCountryConfig.URL, timeout=GetCountryConfig.TIMEOUT
        )

    @patch("src.termux_monitor.core.requests.get")
    @patch("time.sleep")
    def test_get_country_request_exception(
        self, mock_sleep, mock_get, mock_is_connected
    ):
        mock_sleep.return_value = None
        mock_get.side_effect = RequestException

        country = get_country()

        assert country is None
        assert mock_get.call_count == 1
        mock_get.assert_called_with(
            GetCountryConfig.URL, timeout=GetCountryConfig.TIMEOUT
        )

    @patch("src.termux_monitor.core.requests.get")
    def test_get_country_api_failure(self, mock_get, mock_is_connected):
        mock_response = mock_get.return_value
        mock_response.json.side_effect = ValueError

        country = get_country()

        assert country is None
        mock_get.assert_called_with(
            GetCountryConfig.URL, timeout=GetCountryConfig.TIMEOUT
        )


class TestTelephony:
    @patch("subprocess.run")
    def test_get_telephony_device_info_success(self, mock_run):
        mock_run.return_value.stdout = json.dumps(
            {"network_operator_name": "Desired Operator"}
        )
        result = get_telephony_device_info()
        assert result["network_operator_name"] == "Desired Operator"

    @patch("subprocess.run")
    def test_get_telephony_device_info_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        result = get_telephony_device_info()
        assert result is None

    def test_is_network_operator_name_as_desired(self):
        device_info = {"network_operator_name": TelephonyConfig.TARGET_OPERATOR_NAME}
        result = is_network_operator_name_as_desired(device_info)
        assert result

    def test_is_network_operator_name_not_as_desired(self):
        device_info = {"network_operator_name": "Other"}
        result = is_network_operator_name_as_desired(device_info)
        assert not result


class TestGetNotification:
    example_notification = """[{
    "id": 6,
    "tag": "8",
    "key": "-1|com.android.phone|6|8|1001",
    "group": "",
    "packageName": "com.android.phone",
    "title": "No service",
    "content": "Selected network (Operator 4G) unavailable",
    "when": "2024-08-11 08:08:01"
  }]"""

    @patch("subprocess.run")
    def test_successful_execution(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=TestGetNotification.example_notification
        )
        notifications = get_notifications()
        assert notifications == json.loads(TestGetNotification.example_notification)

    @patch("subprocess.run")
    def test_failed_execution(self, mock_run):
        mock_run.side_effect = Exception("Mocked exception")
        notifications = get_notifications()
        assert notifications is None

    @patch("subprocess.run")
    def test_json_decoding_error(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Invalid JSON")
        notifications = get_notifications()
        assert notifications is None


class TestIsNetworkUp:
    def test_empty_notifications(self):
        assert is_network_up([])

    def test_no_com_android_phone_notifications(self):
        notifications = [{"packageName": "other"}]
        assert is_network_up(notifications)

    def test_com_android_phone_notification_no_content(self):
        notifications = [{"packageName": "com.android.phone"}]
        assert is_network_up(notifications)

    def test_com_android_phone_notification_network_issues(self):
        notifications = [
            {
                "packageName": "com.android.phone",
                "content": "Selected network (Operator 4G) unavailable",
            }
        ]
        assert not is_network_up(notifications)

    def test_multiple_notifications_network_issues(self):
        notifications = [
            {"packageName": "other"},
            {
                "packageName": "com.android.phone",
                "content": "Selected network (Operator 4G) unavailable",
            },
        ]
        assert not is_network_up(notifications)
