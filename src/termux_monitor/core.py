import json
import subprocess
import time
from typing import Dict, List, Optional

import requests
from requests.exceptions import RequestException, Timeout

from .config import GetCountryConfig, TelephonyConfig, WifiConfig


def restart_wifi(delay=WifiConfig.DELAY) -> bool:
    """
    Restart the Wi-Fi connection.

    Args:
        delay (int): The delay in seconds before re-enabling the Wi-Fi connection. Defaults to WifiConfig.DELAY.

    Returns:
        bool: True if the Wi-Fi connection is successfully restarted, False otherwise.
    """
    try:
        subprocess.run(["termux-wifi-enable", "false"], check=True)
        time.sleep(delay)
        subprocess.run(["termux-wifi-enable", "true"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        error_message = f"Error restarting Wi-Fi: {e}"
        print(error_message)
        return False
    except subprocess.TimeoutExpired as e:
        error_message = f"Timeout expired while restarting Wi-Fi: {e}"
        print(error_message)
        return False


def get_country(
    max_retries=GetCountryConfig.MAX_RETRIES,
    timeout=GetCountryConfig.TIMEOUT,
    url=GetCountryConfig.URL,
) -> Optional[str]:
    """
    Retrieves the country based on the IP address.

    Args:
        max_retries (int): Maximum number of retries in case of API failure. Defaults to GetCountryConfig.MAX_RETRIES.
        timeout (int): Timeout in seconds for the API request. Defaults to GetCountryConfig.TIMEOUT.
        url (str): URL for the API request. Defaults to GetCountryConfig.URL.

    Returns:
        str: The country name if retrieved successfully, otherwise None.
    """
    country = None
    retries = 0

    while retries < max_retries:
        try:
            # Set timeout for the API request
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
            data = response.json()
            country = data.get("country")
            break
        except Timeout as e:
            print(f"Timeout error: {e}")
            retries += 1
            time.sleep(1)  # Wait for 1 second before retrying
        except RequestException as e:
            print(f"Request error: {e}")
            retries += 1
            time.sleep(1)  # Wait for 1 second before retrying
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    return country


def get_telephony_device_info() -> Optional[Dict[str, str]]:
    """
    Executes the termux-telephony-deviceinfo command and returns the parsed JSON data.
    """
    try:
        result = subprocess.run(
            ["termux-telephony-deviceinfo"], check=True, capture_output=True, text=True
        )
        device_info = json.loads(result.stdout)
        return device_info
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None


def is_network_operator_name_as_desired(device_info: Dict[str, str]) -> bool:
    """
    Checks if the network_operator_name is equal to TelephonyConfig.TARGET_OPERATOR_NAME.
    """
    if device_info and "network_operator_name" in device_info:
        return (
            device_info["network_operator_name"] == TelephonyConfig.TARGET_OPERATOR_NAME
        )
    return False


def get_notifications() -> Optional[List[Dict[str, str]]]:
    """
    Retrieves a list of notifications from the termux-notification-list command.

    Returns:
        Optional[List[Dict[str, str]]]: A list of dictionaries containing notification data, or None if an error occurs.
    """
    try:
        result = subprocess.run(
            ["termux-notification-list"], capture_output=True, text=True
        )
        notifications = json.loads(result.stdout)
        return notifications
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    except Exception as e:
        print(f"Error retrieving notifications: {e}")
        return None


def is_network_up(notifications: List[Dict[str, str]]) -> bool:
    """
    Checks if the network is up based on the given notifications.

    Args:
        notifications (List[Dict[str, str]]): A list of dictionaries representing notifications.
            Each dictionary contains information about a notification, including the package name and content.

    Returns:
        bool: True if there are no notifications related to the com.android.phone package with content containing
            "no service" or "unavailable", False otherwise.
    """
    for notification in notifications:
        if notification.get("packageName") == "com.android.phone":
            content = notification.get("content", "").lower()
            if "no service" in content or "unavailable" in content:
                # log the notification
                return False

    return True


def check_and_restart_wifi() -> bool:
    device_info = get_telephony_device_info()
    if not device_info:
        print("Failed to retrieve device info.")
        return False

    notifications = get_notifications()

    if not (
        is_network_operator_name_as_desired(device_info)
        and is_network_up(notifications)
        if notifications
        else True
    ):
        country = get_country()
        if country == "IN":
            print(
                f"Network operator is not {TelephonyConfig.TARGET_OPERATOR_NAME} but country is 'IN'. Restarting Wi-Fi."
            )
            return restart_wifi()
        else:
            print("Country is not 'IN'. Wi-Fi will not be restarted.")
            return False

    else:
        print(
            f"Network operator is {TelephonyConfig.TARGET_OPERATOR_NAME}. No action needed."
        )
        return False
