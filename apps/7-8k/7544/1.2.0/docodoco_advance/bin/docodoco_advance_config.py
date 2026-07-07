import json
import splunk.admin as admin
import splunk.rest as rest
from docodoco_advance_utils import (
    MASKED_PASSWORD,
    APP_NAME,
    CONF_FILE,
    CONF_STANZA,
    DOCODOCO_API_KEY_IN_PASSWORD_STORE,
    X_SBIAPI_KEY_IN_PASSWORD_STORE,
    CredentialManager,
)
import re
import unicodedata

import logging
import logger_manager

logger = logger_manager.setup_logging("config", logging.DEBUG)
VALID_ROUTES = {"docodoco", "apihub"}


# === 入力値ヘルパー & バリデーション ===
def _normalize(s: str) -> str:
    # 正規化して制御文字を除去し、前後空白を除去
    #   - NFC 正規化で同一視
    #   - CR/LF/NUL を拒否
    s = unicodedata.normalize("NFC", s)
    if any(c in s for c in ("\r", "\n", "\x00")):
        raise ValueError("invalid control character")
    return s.strip()

# 文字種/長さは用途に合わせて保守的に
_RE_CLIENT_ID = re.compile(r"^[\x21-\x7E]{8,128}$") # スペース以外のASCII印字可能文字, 8 ~ 128 文字以内
_RE_API_KEY   = re.compile(r"^[\x21-\x7E]{8,128}$") # スペース以外のASCII印字可能文字, 8 ~ 128 文字以内

def _validate_client_id(v: str) -> str:
    v = _normalize(v)
    if not v:
        return ""  # 空は未設定として許容
    if not _RE_CLIENT_ID.match(v):
        raise ValueError("client_id contains invalid characters")
    return v

def _validate_secret(v: str) -> str:
    v = _normalize(v)
    if not v:
        return ""  # 空は「更新なし」扱い
    if not _RE_API_KEY.match(v):
        raise ValueError("secret contains invalid characters or length")
    return v


# REST handler for Docodoco Advance app configuration.
#   - list: route/client_id（非秘匿）を返す。秘匿値は返さない（AppInspect対策）
#   - edit: route/client_id を conf に保存。秘匿値は storage/passwords に upsert（値あり時のみ）
#   - 選択していない route のスタンザは削除して、常に1つに保つ
class DocoDocoAdvanceConfigHandler(admin.MConfigHandler):
    def setup(self):
        # JS は data= に JSON 文字列を載せて POST
        self.supportedArgs.addOptArg("data")

    def app_configured(self):
        sessionKey = self.getSessionKey()
        try:
            logger.info("Configuring app.conf is_configured.")

            rest.simpleRequest(
                f"/servicesNS/nobody/{APP_NAME}/configs/conf-app/install",
                sessionKey=sessionKey,
                getargs={"output_mode": "json"},
                postargs={"is_configured": "true"},
                method="POST",
                raiseAllErrors=True,
            )
            rest.simpleRequest(
                f"/apps/local/{APP_NAME}/_reload",
                sessionKey=sessionKey,
            )

            logger.info("Storing app.conf is_configured was successful.")
        except Exception as e:
            err_msg = f"Unable to set is_configured parameter in local app.conf file. msg={e}"
            logger.error(err_msg)
            raise

    # === GET /DocoDocoAdvanceConfig ===
    # 非秘匿のみ返す:
    #   - route（未設定は docodoco）
    #   - client_id（存在すれば）
    #   - 秘匿値は存在有無のみで MASKED_PASSWORD か "" を返す
    def handleList(self, conf_info):
        try:
            logger.info("Get Docodoco Advance route/client_id config.")

            _, serverContent = rest.simpleRequest(
                f"/servicesNS/nobody/{APP_NAME}/configs/conf-{CONF_FILE}/{CONF_STANZA}",
                sessionKey=self.getSessionKey(),
                getargs={"output_mode": "json"},
                raiseAllErrors=True
            )
            entries = json.loads(serverContent).get("entry", [])

            route = "docodoco"
            client_id = None

            for e in entries:
                if e.get("name") == CONF_STANZA:
                    content = e.get("content", {}) or {}
                    route = content.get("route", route)
                    client_id = content.get("client_id", None)
                    break

            if route not in VALID_ROUTES:
                route = "docodoco"

            # 存在フラグだけ返す
            cm = CredentialManager(self.getSessionKey())
            has_api_key = cm.is_password(DOCODOCO_API_KEY_IN_PASSWORD_STORE)
            has_x_sbiapi_key = cm.is_password(X_SBIAPI_KEY_IN_PASSWORD_STORE)

            # 返却
            conf_info["action"]["route"] = route
            if client_id is not None:
                conf_info["action"]["client_id"] = client_id
            conf_info["action"]["api_key"] = MASKED_PASSWORD if has_api_key else ""
            conf_info["action"]["x_sbiapi_key"] = MASKED_PASSWORD if has_x_sbiapi_key else ""


        except Exception as e:
            err_msg = f"Unable to fetch config. {e}"
            logger.exception(err_msg)
            conf_info["action"]["error"] = err_msg


    # === POST /DocoDocoAdvanceConfig/config ===
    # 受信ペイロード:
    #   - route: 'docodoco' or 'apihub'（必須）| { VALID_ROUTE } で許容値をリストアップ
    #   - route=docodoco: client_id(非秘匿), api_key（秘匿）
    #   - route=apihub  : x_sbiapi_key（秘匿）
    # 保存:
    #   - 非秘匿（route/client_id）は conf へ POST
    #   - 秘匿値は値が来た時だけ upsert
    #   - 選択していない側のスタンザは削除（常に1つを担保)
    def handleEdit(self, conf_info):
        logger.info("Post user configuration to server.")

        # 入力パース
        try:
            payload_raw = self.callerArgs["data"][0]
            data = json.loads(payload_raw or "{}")

            route = (data.get("route") or "docodoco").strip()
            if route not in VALID_ROUTES:
                raise ValueError(f"invalid route: {route}")
            
            client_id = _validate_client_id(data.get("client_id") or "")
            api_key = _validate_secret(data.get("api_key") or "")
            x_sbiapi_key = _validate_secret(data.get("x_sbiapi_key") or "")
        
        except Exception as e:
            err_msg = f"Data is not in proper format. {e}"
            logger.error(err_msg)
            conf_info["action"]["error"] = "入力値が不正です。値の形式を確認してください。"
            return


        # 保存処理
        try:
            # 1) 非秘匿値 -> conf
            stanza_update = {"route": route}
            if client_id:
                stanza_update["client_id"] = client_id
            
            logger.info("Storing route/client_id to conf.")
            rest.simpleRequest(
                f"/servicesNS/nobody/{APP_NAME}/configs/conf-{CONF_FILE}/{CONF_STANZA}",
                postargs=stanza_update,
                method="POST",
                sessionKey=self.getSessionKey(),
                getargs={"output_mode": "json"},
            )
            logger.info("Storing route/client_id was successful.")


            # 2) 秘匿値 -> storage/passwords
            cm = CredentialManager(self.getSessionKey())

            if route == "docodoco":
                # 反対側（apihub）を削除して一意に保つ
                if cm.is_password(X_SBIAPI_KEY_IN_PASSWORD_STORE):
                    logger.info("Removing X-SBIAPI-Key because route=docodoco.")
                    cm.delete_password(X_SBIAPI_KEY_IN_PASSWORD_STORE)

                # 指定あれば upsert
                if api_key and api_key != MASKED_PASSWORD:
                    logger.info("Upserting API Key (docodoco).")
                    cm.upsert_password(DOCODOCO_API_KEY_IN_PASSWORD_STORE, api_key)

            elif route == "apihub":
                # 反対側（docodoco）を削除して一意に保つ
                if cm.is_password(DOCODOCO_API_KEY_IN_PASSWORD_STORE):
                    logger.info("Removing Docodoco API Key because route=apihub.")
                    cm.delete_password(DOCODOCO_API_KEY_IN_PASSWORD_STORE)
                    
                    # docodoco の client_id も削除
                    try:
                        logger.info("Removing Docodoco client_id because route=apihub.")
                        rest.simpleRequest(
                            f"/servicesNS/nobody/{APP_NAME}/configs/conf-{CONF_FILE}/{CONF_STANZA}",
                            sessionKey=self.getSessionKey(),
                            method="POST",
                            postargs={"client_id": ""},  # 空文字で上書き＝削除と同じ扱い
                            getargs={"output_mode": "json"},
                            raiseAllErrors=True,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to remove docodoco client_id: {e}")

                # 指定あれば upsert
                if x_sbiapi_key and x_sbiapi_key != MASKED_PASSWORD:
                    logger.info("Upserting X-SBIAPI-Key (apihub).")
                    cm.upsert_password(X_SBIAPI_KEY_IN_PASSWORD_STORE, x_sbiapi_key)

            # 最後に is_configured=true
            self.app_configured()
            conf_info["action"]["success"] = "設定を更新しました。"

        except Exception as e:
            err_msg = f"Error while storing API Connection Info. msg={e}"
            logger.exception(err_msg)
            conf_info["action"]["error"] = err_msg


if __name__ == "__main__":
    admin.init(DocoDocoAdvanceConfigHandler, admin.CONTEXT_APP_AND_USER)
