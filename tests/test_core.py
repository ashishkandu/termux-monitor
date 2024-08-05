import json
import subprocess
from unittest.mock import patch

from requests.exceptions import RequestException, Timeout

from src.termux_monitor.config import GetCountryConfig, TelephonyConfig
from src.termux_monitor.core import (
    get_country,
    get_telephony_device_info,
    is_network_operator_name_as_desired,
    restart_wifi,
)


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


class TestGetCountry:
    @patch("src.termux_monitor.core.requests.get")
    def test_get_country_success(self, mock_get):
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
    def test_get_country_timeout(self, mock_sleep, mock_get):
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
    def test_get_country_request_exception(self, mock_sleep, mock_get):
        mock_sleep.return_value = None
        mock_get.side_effect = RequestException

        country = get_country()

        assert country is None
        assert mock_get.call_count == GetCountryConfig.MAX_RETRIES
        mock_get.assert_called_with(
            GetCountryConfig.URL, timeout=GetCountryConfig.TIMEOUT
        )

    @patch("src.termux_monitor.core.requests.get")
    def test_get_country_api_failure(self, mock_get):
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
