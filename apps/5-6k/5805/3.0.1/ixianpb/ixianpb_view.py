# File: ixianpb_view.py
#
# Copyright (c) 2019-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
def _get_ctx_result(result, provides):
    ctx_result = {}
    data_final = {}
    processed_data = []

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param
    ctx_result["action_name"] = provides
    if summary:
        ctx_result["summary"] = summary

    if not data:
        ctx_result["data"] = {}
        return ctx_result

    for item in data:
        ipv4_src = []
        ipv4_dst = []
        ipv4_src_or_dst = []
        mac_src_1 = []
        mac_dst_1 = []
        mac_src_2 = []
        mac_dst_2 = []
        mac_src_or_dst = []
        port_src = []
        port_dst = []
        port_src_or_dst = []
        for criteria in item.get("criteria"):
            if criteria == "ipv4_src":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    ip_addr = " or ".join(temp.get("addr"))
                    ipv4_src.append(ip_addr)
                else:
                    for i in temp:
                        ip_addr = " or ".join(i.get("addr"))
                        ipv4_src.append(ip_addr)

                data_final["ipv4_src"] = ipv4_src

            elif criteria == "ipv4_dst":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    ip_addr = " or ".join(temp.get("addr"))
                    ipv4_dst.append(ip_addr)
                else:
                    for i in temp:
                        ip_addr = " or ".join(i.get("addr"))
                        ipv4_dst.append(ip_addr)

                data_final["ipv4_dst"] = ipv4_dst

            elif criteria == "ipv4_src_or_dst":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    ip_addr = " or ".join(temp.get("addr"))
                    ipv4_src_or_dst.append(ip_addr)
                else:
                    for i in temp:
                        ip_addr = " or ".join(i.get("addr"))
                        ipv4_src_or_dst.append(ip_addr)

                data_final["ipv4_src_or_dst"] = ipv4_src_or_dst

            elif str(criteria) == "ipv4_flow":
                flow_list = []
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    uni_list = []
                    flow_type = temp.get("flow_type")
                    for i in temp.get("address_sets"):
                        src = "or".join(i.get("addr_a"))
                        dst = "or".join(i.get("addr_b"))
                        uni = f"{src} {flow_type} {dst}"
                        uni_list.append(uni)

                    uni = " or ".join(uni_list)
                    flow_list.append(uni)
                else:
                    for i in temp:
                        uni_list = []
                        flow_type = i.get("flow_type")
                        for j in i.get("address_sets"):
                            src = "or".join(j.get("addr_a"))
                            dst = "or".join(j.get("addr_b"))
                            uni = f"{src} {flow_type} {dst}"
                            uni_list.append(uni)

                        uni = " or ".join(uni_list)
                        flow_list.append(uni)

                data_final["ipv4_flow"] = flow_list

            elif criteria == "layer4_src_port":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    port_src.append(temp.get("port"))
                else:
                    for i in temp:
                        port_src.append(i.get("port"))

                data_final["port_src"] = port_src

            elif criteria == "layer4_dst_port":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    port_dst.append(temp.get("port"))
                else:
                    for i in temp:
                        port_dst.append(i.get("port"))

                data_final["port_dst"] = port_dst

            elif criteria == "layer4_src_or_dst_port":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    port_src_or_dst.append(temp.get("port"))
                else:
                    for i in temp:
                        port_src_or_dst.append(i.get("port"))

                data_final["port_src_or_dst"] = port_src_or_dst

            elif criteria == "layer4_port_flow":
                flow_list = []
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    flow_type = temp.get("flow_type")
                    for i in temp.get("port_sets"):
                        src = i.get("port_a")
                        dst = i.get("port_b")
                        uni = f"{src} {flow_type} {dst}"
                        flow_list.append(uni)
                else:
                    for i in temp:
                        uni_list = []
                        flow_type = i.get("flow_type")
                        for j in i.get("address_sets"):
                            src = j.get("port_a")
                            dst = j.get("port_b")
                            uni = f"{src} {flow_type} {dst}"
                            uni_list.append(uni)

                        uni = "or".join(uni_list)
                        flow_list.append(uni)

                data_final["port_flow"] = flow_list

            elif criteria == "mac_src":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    if temp.get("addr"):
                        mac_src_1.append(temp.get("addr"))
                    elif temp.get("admin_type") == "LOCAL":
                        mac_src_2.append("Any locally administered address")
                    elif temp.get("admin_type") == "UNIVERSAL":
                        mac_src_2.append("Any universally administered address")
                else:
                    for i in temp:
                        if i.get("addr"):
                            mac_src_1.append(" or ".join(i.get("addr")))
                        elif i.get("admin_type") == "LOCAL":
                            mac_src_2.append("Any locally administered address")
                        elif i.get("admin_type") == "UNIVERSAL":
                            mac_src_2.append("Any universally administered address")

                data_final["mac_src_1"] = mac_src_1
                data_final["mac_src_2"] = mac_src_2

            elif criteria == "mac_dst":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    if temp.get("addr"):
                        mac_dst_1.append(" or ".join(temp.get("addr")))
                    else:
                        mac_dst_2.append(
                            "Any {}ly administered {} address".format(temp.get("admin_type").lower(), temp.get("dest_addr_type").lower())
                        )

                else:
                    for i in temp:
                        if i.get("addr"):
                            mac_dst_1.append(" or ".join(i.get("addr")))
                        else:
                            mac_dst_2.append(
                                "Any {}ly administered {} address".format(i.get("admin_type").lower(), i.get("dest_addr_type").lower())
                            )

                data_final["mac_dst_1"] = mac_dst_1
                data_final["mac_dst_2"] = mac_dst_2

            elif criteria == "mac_src_or_dst":
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    if temp.get("addr"):
                        mac_src_or_dst.append(" or ".join(temp.get("addr")))
                else:
                    for i in temp:
                        mac_src_or_dst.append(" or ".join(i.get("addr")))

                data_final["mac_src_or_dst"] = mac_src_or_dst

            elif str(criteria) == "mac_flow":
                flow_list = []
                temp = item.get("criteria").get(criteria)
                if isinstance(temp, dict):
                    flow_type = temp.get("flow_type")
                    for i in temp.get("address_sets"):
                        src = "or".join(i.get("addr_a"))
                        dst = "or".join(i.get("addr_b"))
                        uni = f"{src} {flow_type} {dst}"
                        flow_list.append(uni)
                else:
                    for i in temp:
                        uni_list = []
                        flow_type = i.get("flow_type")
                        for j in i.get("address_sets"):
                            src = " or ".join(j.get("addr_a"))
                            dst = " or ".join(j.get("addr_b"))
                            uni = f"{src} {flow_type} {dst}"
                            uni_list.append(uni)

                        uni = " or ".join(uni_list)
                        flow_list.append(uni)

                data_final["mac_flow"] = flow_list

        processed_data.append(data_final)

    ctx_result["data"] = data
    ctx_result["processed_data"] = processed_data

    return ctx_result


def display_view(provides, all_app_runs, context):
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    return "ixianpb_describe_filter.html"
