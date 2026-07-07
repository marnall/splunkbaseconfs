import os
from datetime import datetime
import sys
import uuid
from RESTClient import RESTClient


class netskope_client(RESTClient):

    def _build_url(self, endpoint):
        return "https://{}/api/v1/{}".format(self._hostname, endpoint)

    def updateFileHashList(self, hashes=[], name="splunk_file_hash_list"):
        try:
            self._log.info("logic=rest before_url")
            update_url = "{}?{}".format(self._build_url("updateFileHashList"),
                                        self._payload(**{"list": ",".join(hashes).lower(), "name": name, "token": self.get_token()}))
            self._log.debug("logic=rest update_url={}".format(update_url))
            return self._read(update_url, payload=None)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            jsondump = "message={} exception_type={} exception_arguments={} filename={} exception_line={}".format(
                str((e)), type(e).__name__, e, fname, exc_tb.tb_lineno
            )
            self._log.error("exception={} {}".format(e, jsondump))
            raise(e)

    def updateUrlList(self, urls=[], name="splunk_file_hash_list"):
        update_url = "{}?{}".format(self._build_url("updateUrlList"),
                                    self._payload(
                                        **{"list": ",".join(urls), "name": name, "token": self.get_token()}))
        self._log.debug("logic=rest update_url={}".format(update_url))
        return self._read(update_url, payload=None)

    def _call(self, **kwargs):
        url_args = kwargs.copy()
        for x in ["tenanturl", "modularinput", "parent_tracker"]:
            if x in url_args:
                del url_args[x]
        if url_args["type"] != "alert":
            payload = self._payload(**url_args)
        else:
            del url_args["type"]
            payload = self._payload(**url_args)
        self._log.debug("logic=rest payload={0}".format(payload))
        fullUrl = "{}?{}".format(self._build_url(url_args["endpoint"]), payload)
        return self._read(fullUrl, payload=None)

    def next_page(self, **kwargs):
        try:
            pagination_event_id = "{}".format(uuid.uuid4())
            if "parent_tracker" in kwargs:
                pagination_event_id = "{} parent_tracker={}".format(pagination_event_id, kwargs["parent_tracker"])
            self._log.debug(
                "logic=pagination tracker={} action=start kwargs_no_token={}".format(pagination_event_id,
                                                                                     {x: kwargs[x] for x in kwargs if
                                                                                      x != "token"}))
            if "skip" not in kwargs:
                self._log.debug("logic=pagination tracker={} skip=not_present action=set_default value=0".format(
                    pagination_event_id))
                kwargs["skip"] = 0
            kwargs["endpoint"] = "alerts" if kwargs["type"] == "alert" else "events"

            if kwargs["type"] == "web":
                kwargs["type"] = "page"

            if kwargs["type"] == "clients":
                kwargs["endpoint"] = "clients"
            self._log.debug(
                "logic=pagination tracker={} action=start endpoint={} ".format(pagination_event_id, kwargs["endpoint"]))
            self._log.debug(
                "logic=pagination tracker={} msg=performing_partial_call action=start".format(pagination_event_id))
            tmp_call_start = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            partial_events = self._call(**kwargs)
            tmp_call_end = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            partial_events_length = 0
            is_next_page = False
            if partial_events is not None:
                self._log.debug(
                    "logic=pagination tracker={} msg=partial_events_call action=complete partial_events_length={} call_execution_time_seconds={}".format(
                        pagination_event_id, len(partial_events["data"]), (tmp_call_end - tmp_call_start)))
            else:
                self._log.debug(
                    "logic=pagination tracker={} msg=partial_events_call action=complete partial_events_length={} call_execution_time_seconds={}".format(
                        pagination_event_id, "None", (tmp_call_end - tmp_call_start)))
            if partial_events is not None and "error" not in partial_events["status"]:
                self._log.debug("logic=pagination tracker={} partial_events=not_None".format(pagination_event_id))
                partial_events_length = len(partial_events["data"])
            elif partial_events is not None and "error" in partial_events["status"]:
                raise Exception(
                    "API Error: {}: {}".format(partial_events["errorCode"], ",".join(partial_events["errors"])))
            else:
                self._log.debug(
                    "logic=pagination tracker={} partial_events=None action=return".format(pagination_event_id))
                self._log.debug("logic=pagination tracker={} action=stop endpoint={} ".format(pagination_event_id,
                                                                                              kwargs["endpoint"]))
                return partial_events
            limit = int(kwargs.get("limit", 5000))
            self._log.debug("logic=pagination tracker={} action=set_limit value={}".format(pagination_event_id, limit))
            self._log.debug(
                "logic=pagination tracker={} type={} found limit={} partial_events_length={}".format(
                    pagination_event_id, kwargs["type"], limit,
                    partial_events_length))
            if int(partial_events_length) < int(limit) or partial_events["status"] == "error":
                self._log.debug(
                    "action=error tracker={} evaluates_to={} msg=partial_events_length_less_than_limit  limit={} partial_events_length={} status={}".format(
                        pagination_event_id, partial_events_length < limit,
                        partial_events_length,
                        limit,
                        partial_events["status"]))

                self._log.debug("logic=pagination tracker={} action=stop endpoint={} ".format(pagination_event_id,
                                                                                              kwargs["endpoint"]))
            if partial_events_length > limit:
                self._log.debug(
                    "logic=pagination tracker={} action=error msg=partial_events_length_greater_than_limit limit={} partial_events_length={}").format(
                    pagination_event_id, limit, partial_events_length
                )
                raise Exception("Partial Events Length Greater Than Limit.")
            if partial_events_length == limit:
                is_next_page = True
            self.log(
                "logic=pagination tracker={} action=continue partial_events_length={} limit={} has_next_page={}".format(
                    pagination_event_id, partial_events_length,
                    limit, is_next_page))
            return partial_events, is_next_page
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            jsondump = "message={} exception_type={} exception_arguments={} filename={} exception_line={}".format(
                str((e)), type(e).__name__, e, fname, exc_tb.tb_lineno
            )
            self._log.error("exception={} {}".format(e, jsondump))
            return None, False

    def get_events(self, **kwargs):
        try:
            # NET-46
            total_events = {"status": "", "data": []}
            pagination_event_id = "{}".format(uuid.uuid4())
            self._log.debug("logic=pagination tracker={} action=start kwargs={}".format(pagination_event_id,
                                                                                        {x: kwargs[x] for x in kwargs if
                                                                                         x != "token"}))
            limit = int(kwargs.get("limit", 5000))
            page_events, do_next = self.next_page(parent_tracker=pagination_event_id, **kwargs)
            if page_events is None:
                return total_events
            total_events["data"].extend(page_events["data"])
            if not do_next:
                return total_events
            partial_events_length = len(page_events["data"])
            page_count = 0
            skip = limit
            while do_next:
                self._log.debug(
                    "action=start logic=pagination tracker={} focus=while page_count={} current_skip={}".format(
                        pagination_event_id, page_count, skip))
                kwargs["skip"] = skip
                partial_events, do_next = self.next_page(parent_tracker=pagination_event_id, **kwargs)
                if partial_events is not None:
                    partial_events_length = len(partial_events["data"])
                    total_events["data"].extend(partial_events["data"])
                    self._log.debug(
                        "action=extend_total_set logic=pagination tracker={} method=sum_me partial_events_length={} total_length={}".format(
                            pagination_event_id, partial_events_length, len(total_events["data"])))
                    total_events["status"] = partial_events["status"]
                    skip = skip + limit
                    page_count = page_count + 1
                    self._log.debug(
                        "logic=pagination tracker={} page_count={} current_skip= {}".format(pagination_event_id,
                                                                                            page_count, skip))
                    self._log.debug(
                        "logic=pagination tracker={} partial_events_length={} limit={} compare={}".format(
                            pagination_event_id, partial_events_length,
                            limit,
                            int(
                                partial_events_length) == int(
                                limit)))
                else:
                    self._log.debug(
                        "action=set_breakout logic=pagination tracker={} partial_events=None value=False do_next=False".format(
                            pagination_event_id))
                    do_next = False
            self._log.debug("logic=pagination tracker={} total_length={} method=sum_me".format(pagination_event_id, len(
                total_events["data"])))
            self._log.debug(
                "logic=pagination tracker={} action=stop endpoint={} ".format(pagination_event_id, kwargs["endpoint"]))
            return total_events

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            jsondump = "message={} exception_type={} exception_arguments={} filename={} line={}".format(
                str((e)), type(e).__name__, e, fname, exc_tb.tb_lineno
            )
            self._log.error("Error occured making REST API call : {} {}".format(e, jsondump))
