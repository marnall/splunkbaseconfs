import json
from multiprocessing import Pool
import urllib
from urllib.error import URLError
import urllib.request
import urllib.parse

import logging
import logger_manager

logger = logger_manager.setup_logging("search", logging.DEBUG)


class DocoDocoAdvanceReq:
    def __init__(self, apiConnInfo):
        self.apiConnInfo = apiConnInfo

    def reqDocodoco(self, target_ip):
        # IPアドレスが取得できない場合は空のdictionaryを返す
        if not target_ip:
            return {}

        route = self.apiConnInfo.get("route")
        headers = self.apiConnInfo.get("headers", {}) or {}
        http_method = self.apiConnInfo.get("http_method", "GET").upper()
        timeout_sec = self.apiConnInfo.get("timeout_sec")

        # URL 組み立て
        if route == "docodoco":
            base_url = self.apiConnInfo["base_url"]
            path = self.apiConnInfo["endpoint_path"]
            key_param = self.apiConnInfo["client_id_param_key"]
            fmt_param = self.apiConnInfo["format_param_key"]
            fmt_value = self.apiConnInfo["format_param_value"]
            ip_param = self.apiConnInfo["param_ip_key"]
            client_id = self.apiConnInfo["client_id"]

            url = (
                f"{base_url}{path}"
                f"?{key_param}={urllib.parse.quote(client_id)}"
                f"&{fmt_param}={fmt_value}"
                f"&{ip_param}={urllib.parse.quote(str(target_ip))}"
            )

        elif route == "apihub":
            base_url = self.apiConnInfo["base_url"]
            path = self.apiConnInfo["path_template"].format(
                service_id=self.apiConnInfo["service_id"],
                resource=self.apiConnInfo["resource"],
                version=self.apiConnInfo["version"],
                last_segment=self.apiConnInfo["last_segment"],
            )
            ip_param = self.apiConnInfo["param_ip_key"]
            url = f"{base_url}{path}?{ip_param}={urllib.parse.quote(str(target_ip))}"

        else:
            logger.error(f"[req] Unknown route: {route}")
            return {"IP": target_ip, "status": "error"}

        # リクエスト作成・送信
        # "api_key" is sensitive information, so it should be passed in the headers.
        req = urllib.request.Request(url, method=http_method)
        for k, v in headers.items():
            req.add_header(k, v)

        # --- ここから: デバッグ ---
        try:
            masked_headers = {k: ('***' if k.lower() in ('authorization', 'x-sbiapi-user-appkey') else v)
                              for k, v in headers.items()}
            logger.debug("[req][debug] route=%s method=%s timeout=%s url=%s headers=%s",
                         route, http_method, timeout_sec, url, masked_headers)
        except Exception:
            pass
        # --- ここまで: デバッグ ---

        try:
            if timeout_sec is not None:
                raw = urllib.request.urlopen(req, timeout=timeout_sec).read()
            else:
                raw = urllib.request.urlopen(req).read()
            
        # --- ここから: デバッグ ---
        #     try:
        #         preview = raw[:200].decode("utf-8", errors="ignore")
        #     except Exception:
        #         preview = "<non-text>"
        #     logger.debug('[resp][debug] status=200 preview=%s', preview)

        #     response = json.loads(raw)
        #     if "IP" in response:
        #         response["status"] = "success"
        #     else:
        #         response["IP"] = target_ip
        #         response["status"] = "error"
        #     return response

        # except urllib.error.HTTPError as e:
        #     try:
        #         body = e.read()  # HTTPError は read() でボディが取れる
        #         body_preview = body[:300].decode("utf-8", errors="ignore")
        #     except Exception:
        #         body_preview = "<unreadable>"
        #     logger.error("[resp][http-error] code=%s reason=%s body=%s",
        #                  getattr(e, "code", None), getattr(e, "reason", None), body_preview)
        #     return {"IP": target_ip, "status": "error"}

        # except urllib.error.URLError as e:
        #     logger.error("[resp][url-error] reason=%s", getattr(e, "reason", e))
        #     return {"IP": target_ip, "status": "error"}

        # except Exception as e:
        #     logger.exception("[resp][unexpected-error] %s", e)
        #     return {"IP": target_ip, "status": "error"}
        # --- ここまで: デバッグ ---

            response = json.loads(raw)

            if "IP" in response:
                response["status"] = "success"
            else:
                response["IP"] = target_ip
                response["status"] = "error"

            return response

        except URLError as e:
            e_response = {"IP": target_ip, "status": "error"}
            return e_response


class DocoDocoAdvanceReqPool:
    apiConnInfo = {}

    def __init__(self, apiConnInfo):
        self.apiConnInfo = apiConnInfo
        self.pool = Pool(processes=10)

    def reqDocodocoW(self, ip_list):
        req = DocoDocoAdvanceReq(self.apiConnInfo)
        return self.pool.map(req.reqDocodoco, ip_list)
