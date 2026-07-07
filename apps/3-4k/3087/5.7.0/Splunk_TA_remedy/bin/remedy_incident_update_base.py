#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import remedy_consts as c
import remedy_ticket as rt
import wsdl_parser as wp


class RemedyIncidentUpdateBase(rt.RemedyTicket):
    DEFAULT_ACTION = "MODIFY"

    def _prepare(self):
        wsdl_parser = wp.WSDLParser()
        file_path = self.remedy_ws.get(c.MODIFY_WSDL_FILE_PATH)
        wsdl_parser.parse(file_path)
        self.args_lst = wsdl_parser.get_args(
            self.remedy_ws.get(c.MODIFY_OPERATION_NAME)
        )
        self.args_lst.sort()
        self.args_set = set()
        for field in self.args_lst:
            self.args_set.add(field)
        required_str = self.update_incident_fields.get(c.REQUIRED)
        # get required args information from conf file.
        if required_str:
            tmp_lst = required_str.split(c.FIELD_SEP)
            self.required_set = set()
            for field in tmp_lst:
                if field:
                    self.required_set.add(field.strip())
        # get required args information from wsdl file.
        else:
            required_lst = wsdl_parser.get_required_args(
                self.remedy_ws.get(c.MODIFY_OPERATION_NAME)
            )
            self.required_set = set()
            for field in required_lst:
                if field == c.ACTION:
                    continue
                self.required_set.add(field)

    def _prepare_data(self, event):
        event_data = {}
        for field in self.required_set:
            if event.get(field) is None:
                raise Exception(
                    'Field "{}" is required by Remedy for updating incident'.format(
                        field
                    )
                )
        for k, v in list(event.items()):
            if k in self.args_set:
                if v is not None:
                    event_data[k] = v
        self.incident_number = event_data.get(c.INCIDENT_NUMBER)
        if self.incident_number is None:
            raise Exception("Cannot get Incident_Number for update incident")
        # set action
        action = event_data.get(c.ACTION)
        if action is None:
            event_data[c.ACTION] = self.DEFAULT_ACTION
        wsdl_file_path = self.remedy_ws.get(c.MODIFY_WSDL_FILE_PATH)
        operation_name = self.remedy_ws.get(c.MODIFY_OPERATION_NAME)
        return wsdl_file_path, operation_name, event_data

    def _get_result(self, resp):
        if self.incident_number is None:
            raise Exception("Cannot get Incident_Number for update incident")
        wsdl_file_path = self.remedy_ws.get(c.QUERY_WSDL_FILE_PATH)
        return self.remedy_incident_service.get(wsdl_file_path, self.incident_number)
