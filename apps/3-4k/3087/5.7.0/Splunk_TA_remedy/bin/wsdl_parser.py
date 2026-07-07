#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import urllib.parse
import urllib.request

import suds.client as sc


class ArgsInfo:
    def __init__(self, args_lst=None, required_args_lst=None):
        self.args_lst = args_lst
        self.required_args_lst = required_args_lst


class WSDLParser:
    def __init__(self):
        self.service_args_info = None

    def parse(self, file_path):
        self.service_args_info = {}
        wsdl_url = urllib.parse.urljoin(
            str("file:"), str(urllib.request.pathname2url(file_path))
        )
        client = sc.Client(wsdl_url)
        self._parse_args(client)
        self._parse_required_args(client)

    def _parse_args(self, client):
        for service in client.wsdl.services:
            for port in service.ports:
                methods = list(port.methods.values())
                for method in methods:
                    part = method.soap.input.body.parts[0]
                    part_type = part.type
                    if not part_type:
                        part_type = part.element[0]
                    args = client.factory.create(part_type)
                    if self.service_args_info.get(method.name) is not None:
                        raise Exception(method.name + "is duplicated.")
                    args_lst = []
                    for k, v in args.__dict__.items():
                        if k.startswith("_") or k.startswith("__"):
                            continue
                        args_lst.append(k)
                    args_info = ArgsInfo(args_lst=args_lst)
                    self.service_args_info[method.name] = args_info

    def _parse_required_args(self, client):
        root = client.wsdl.root
        args_type_dict = {}
        self._get_args_type(root, args_type_dict)
        self._get_all_required_args(root, args_type_dict)

    def _get_args_type(self, root, args_type_dict):
        if root.getChildren():
            for child in root:
                name = child.getAttribute("name")
                if name and name.value in self.service_args_info:
                    args_type = child.getAttribute("type")
                    if args_type:
                        args_type_dict[args_type.value] = name.value
                        continue
                self._get_args_type(child, args_type_dict)

    def _get_all_required_args(self, root, args_type_dict):
        if root.getChildren():
            for child in root:
                flag = False
                name = child.getAttribute("name")
                if name:
                    for k, v in args_type_dict.items():
                        if k.find(name.value) == -1:
                            continue
                        args_info = self.service_args_info.get(v)
                        args_info.required_args_lst = self._get_required_args(child)
                        flag = True
                        break
                if not flag:
                    self._get_all_required_args(child, args_type_dict)

    @classmethod
    def _get_required_args(cls, child):
        required_lst = []
        for elem in child.getChild("xsd:sequence").getChildren():
            min_occurs = elem.getAttribute("minOccurs")
            if min_occurs and min_occurs.value == "0":
                continue
            required_lst.append(elem.getAttribute("name").value)
        return required_lst

    def get_args(self, service_name):
        if self.service_args_info is None:
            raise Exception("Need to call the method parse() first.")
        args_info = self.service_args_info.get(service_name)
        if args_info is None:
            raise Exception("Failed to get the args_info for " + service_name)
        return args_info.args_lst

    def get_required_args(self, service_name):
        if self.service_args_info is None:
            raise Exception("Need to call the method parse() first.")
        args_info = self.service_args_info.get(service_name)
        if args_info is None:
            raise Exception("Failed to get the args_info for " + service_name)
        return args_info.required_args_lst
