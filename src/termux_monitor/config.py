import os


class WifiConfig:
    DELAY = int(os.getenv("WIFI_RESTART_DELAY", 5))


class GetCountryConfig:
    MAX_RETRIES = int(os.getenv("GET_COUNTRY_MAX_RETRIES", 3))
    TIMEOUT = int(os.getenv("GET_COUNTRY_TIMEOUT", 30))
    URL = os.getenv("GET_COUNTRY_URL", "https://ipinfo.io/json")


class TelephonyConfig:
    TARGET_OPERATOR_NAME = os.getenv("TARGET_OPERATOR_NAME", "IND airtel")
