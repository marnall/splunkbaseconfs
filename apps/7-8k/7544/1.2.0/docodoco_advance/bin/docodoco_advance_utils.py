import json
from typing import List, Dict, Optional
from six.moves.urllib.parse import quote
from splunk import rest

import logging
import logger_manager

logger = logger_manager.setup_logging("utils", logging.DEBUG)


APP_NAME = "docodoco_advance"
CONF_FILE = "docodoco_advance_config"
CONF_STANZA = "api_conn_info"
# どこどこJP直契約のAPIキー
DOCODOCO_API_KEY_IN_PASSWORD_STORE = "docodoco_api_key"
# API HubのX-SBIAPI-Key
X_SBIAPI_KEY_IN_PASSWORD_STORE = "x_sbiapi_key"
MASKED_PASSWORD = "******"

DOCODOCO_REST_RESPONSE_HEADERS = [
    #'ipaddr', IPアドレスは元データについているので不要
    "ContinentCode",
    "CountryCode",
    "CountryAName",
    "CountryJName",
    "PrefCode",
    "RegionCode",
    "PrefAName",
    "PrefJName",
    "PrefLatitude",
    "PrefLongitude",
    "PrefCF",
    "CityCode",
    "CityAName",
    "CityJName",
    "CityLatitude",
    "CityLongitude",
    "CityCF",
    "BCFlag",
    "OrgCode",
    "OrgOfficeCode",
    "OrgIndependentCode",
    "OrgName",
    "OrgPrefCode",
    "OrgCityCode",
    "OrgZipCode",
    "OrgAddress",
    "OrgTel",
    "OrgFax",
    "OrgIpoType",
    "OrgDate",
    "OrgCapitalCode",
    "OrgEmployeesCode",
    "OrgGrossCode",
    "OrgPresident",
    "OrgIndustrialCategoryL",
    "OrgIndustrialCategoryM",
    "OrgIndustrialCategoryS",
    "OrgIndustrialCategoryT",
    "OrgDomainName",
    "OrgDomainType",
    "OrgUrl",
    "OrgLatitude",
    "OrgLongitude",
    "OrgEnglishName",
    "OrgEnglishAddress",
    "LineCode",
    "LineJName",
    "LineCF",
    "TimeZone",
    "ProxyFlag",
    "TelCode",
    "StockTickerNumber",
    "DomainName",
    "DomainType",
    "EncryptedIP",
    "WeatherUpdateTime@WeatherA",
    "TodayWeather@WeatherA",
    "TodayWeatherCode@WeatherA",
    "TomorrowWeather@WeatherA",
    "TomorrowWeatherCode@WeatherA",
    "DayAfterTomorrowWeather@WeatherA",
    "DayAfterTomorrowWeatherCode@WeatherA",
    "TodayHighTemperature@WeatherA",
    "TodayHighTemperatureCode@WeatherA",
    "TomorrowLowTemperature@WeatherA",
    "TomorrowLowTemperatureCode@WeatherA",
    "TomorrowHighTemperature@WeatherA",
    "TomorrowHighTemperatureCode@WeatherA",
    "TodayRainProbability@WeatherA",
    "TomorrowRainProbability@WeatherA",
    "TodayWindDirection@WeatherA",
    "TomorrowWindDirection@WeatherA",
    "ForecastHighTemperature@WeatherA",
    "ForecastHighTemperatureCode@WeatherA",
    "WeatherUpdateTime@WeatherP",
    "Weather@WeatherP",
    "WeatherCode@WeatherP",
    "Temperature@WeatherP",
    "TemperatureCode@WeatherP",
    "Humidity@WeatherP",
    "Rainfall@WeatherP",
    "ForecastUV@WeatherP",
    "OrgCode@HoujinBangou_3",
    "HoujinBangou@HoujinBangou_3",
    "HoujinName@HoujinBangou_3",
    "HoujinAddress@HoujinBangou_3",
    "HoujinLastUpdate@HoujinBangou_3",
    "Name@AnonymousNetwork_5",
    "Score@AnonymousNetwork_5",
    "Info@AnonymousNetwork_5",
]


class CredentialManager(object):
    # passwords.conf の操作を rest.simpleRequest に統一。
    #    - 平文の取得は行わない
    #    - 主キー相当: realm=APP_NAME / username=<stanza名> / name = f"{realm}:{username}:"

    def __init__(self, session_key: str, app: str = APP_NAME):
        self.session_key = session_key
        self.app = app

    # --------- ヘルパー関数 ---------
    @staticmethod
    def _escape_username(username: str) -> str:
        # 個別エンティティURL用に ":" をエスケープ（Splunkの仕様）
        return username.replace(":", r"\:")

    def _realm_q(self, username: str) -> str:
        # URL パス用に quote した realm 部分を返す
        uname = self._escape_username(username)
        realm = f"{self.app}:{uname}:"
        return quote(realm, safe="")

    def _entity_path(self, username: str) -> str:
        return f"/servicesNS/nobody/{self.app}/storage/passwords/{self._realm_q(username)}?output_mode=json"

    def _collection_path(self) -> str:
        return f"/servicesNS/nobody/{self.app}/storage/passwords?output_mode=json"

    # --------- API ---------
    def get_passwords(self) -> List[Dict[str, str]]:
        # 既存の資格情報エンティティを一覧取得。 clear_password は返さない。
        #   - 戻り値: [{"name": "...", "realm": "...", "username": "..."}, ...]
        #   - realm==APP_NAME のみ返す
        _, body = rest.simpleRequest(
            self._collection_path(),
            self.session_key,
            method="GET",
            raiseAllErrors=True
        )
        data = json.loads(body.decode("utf-8"))
        out: List[Dict[str, str]] = []
        for entry in data.get("entry", []):
            content = entry.get("content", {}) or {}
            realm = content.get("realm")
            if realm != self.app:
                continue
            out.append({
                "name": entry.get("name", ""),
                "realm": realm or "",
                "username": content.get("username", "")  # スタンザ名
            })
        return out


    def is_password(self, username: str) -> bool:
        # 指定 username(stanza) のエンティティが存在するか。
        try:
            rest.simpleRequest(
                self._entity_path(username),
                self.session_key,
                method="GET",
                raiseAllErrors=True,
            )
            return True
        except Exception:
            return False


    def upsert_password(self, username: str, clear_password) -> None:
        # 指定 username(stanza) の資格情報を作成 or 更新。
        #   - 空文字/None/MASKED_PASSWORD の場合はスキップ
        #   dict の場合は JSON 文字列化して保存
        if clear_password is None or clear_password == "" or clear_password == MASKED_PASSWORD:
            logger.info(f"[cred] Skip upsert_password (masked/empty): username={username}")
            return

        update_args = {
            "password": (
                json.dumps(clear_password) if isinstance(clear_password, dict) else str(clear_password)
            )
        }

        # まず更新（POST /<entity>）
        try:
            rest.simpleRequest(
                self._entity_path(username),
                self.session_key,
                postargs=update_args,
                method="POST",
                raiseAllErrors=True,
            )
            logger.info(f"[cred] Updated: username={username}")
            return
        except Exception as e:
            logger.warning(f"[cred] Update failed (will create if not exists): username={username}, err={e}")

        # なければ作成（POST /<collection>）
        create_args = {
            "name": username,
            "realm": self.app,
            "password": update_args["password"],
        }
        try:
            rest.simpleRequest(
                self._collection_path(),
                self.session_key,
                postargs=create_args,
                method="POST",
                raiseAllErrors=True,
            )
            logger.info(f"[cred] Created: username={username}")
        except Exception as e:
            # 既存ありで update 失敗など別要因
            if self.is_password(username):
                raise RuntimeError(f"[cred] Exists but update failed: username={username}, err={e}")
            raise


    def delete_password(self, username: str) -> bool:
        # username(stanza) の資格情報を削除。
        #   戻り値: True=削除実行/成功, False=存在せず未実行
        if not self.is_password(username):
            logger.info(f"[cred] Delete skipped (not found): username={username}")
            return False

        try:
            rest.simpleRequest(
                self._entity_path(username),
                self.session_key,
                method="DELETE",
                raiseAllErrors=True,
            )
            logger.info(f"[cred] Deleted successfully: username={username}")
            return True
        except Exception as e:
            logger.error(f"[cred] Delete failed: username={username}, err={e}")
            raise