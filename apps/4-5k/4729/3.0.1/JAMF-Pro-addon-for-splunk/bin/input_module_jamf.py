# encoding = utf-8
import logging
import math
import uuid
import sys
import os
import traceback
import xml.etree.ElementTree as ElementTree


try:
    import jamf_pro_models
except ImportError:
    from . import jamf_pro_models

try:
    from uapi_models import jamfpro
    from account_helper import get_jamf_credentials
    from error_reporting import emit_input_error
    from input_lifecycle import auto_disable_input
except ImportError:
    from .uapi_models import jamfpro
    from .account_helper import get_jamf_credentials
    from .error_reporting import emit_input_error
    from .input_lifecycle import auto_disable_input


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # name_of_the_modular_input = definition.parameters.get('name_of_the_modular_input', None)
    # jss_url = definition.parameters.get('jss_url', None)
    # api_call = definition.parameters.get('api_call', None)
    # search_name = definition.parameters.get('search_name', None)
    # custom_index_name = definition.parameters.get('custom_index_name', None)
    # custom_host_name = definition.parameters.get('custom_host_name', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    pass


def collect_events(helper, ew):
    helper.log_info("jamf collect_events started: input=%r" % helper.get_input_stanza_names())
    # Account lookup via shared helper
    creds = get_jamf_credentials(helper)
    if not (creds.get('jss_url') and creds.get('jss_username') and creds.get('jss_password')):
        account = helper.get_arg('account')
        account_name = account.get('name') if isinstance(account, dict) else account
        emit_input_error(
            helper=helper, ew=ew,
            category="config",
            label="Account configuration",
            target_url="(no request was made)",
            summary="Account %r is missing required credentials (URL, username, or password)" % account_name,
        )
        auto_disable_input(helper, "jamf",
            "This input was disabled because the account is missing a URL, username, or password. "
            "Update the account in Configuration → Accounts, then re-enable this input.")
        return
    url = creds['jss_url']
    username = creds['jss_username']
    password = creds['jss_password']
    api_call = helper.get_arg('api_call', None)
    search_name = helper.get_arg('search_name', None)
    index = helper.get_arg('custom_index_name', 'main')
    host = helper.get_arg('custom_host_name', 'localhost')
    maxCharLength = 9500
    call_uuid = uuid.uuid4()

    headers = {
        'User-Agent': jamfpro.build_user_agent(helper, 'jamfClassic')
    }

    #
    #   Verify JSS URL
    #
    if url.__contains__("http://"):  # NOSONAR — stripping http:// to enforce https
        url = url.replace("http://", "")  # NOSONAR
    if url.__contains__("https://"):
        url = url.replace("https://", "")
    if not url.endswith("/"):
        url = url + "/"

    try:
        helper.log_info("jamf: connecting to Jamf Pro at %r" % url)
        jss = jamfpro.JamfPro(jamf_url=url,
                              jamf_username=username,
                              jamf_password=password,
                              helper=helper,
                              headers=headers)
        helper.log_info("jamf: Jamf Pro connection established")
    except Exception as e:
        # If the account was auto-created by legacy_migration, point the operator
        # at the most likely cause (stale creds carried over from 2.12.x).
        from legacy_migration import migration_auth_failure_hint
        account_arg = helper.get_arg('account')
        account_name = account_arg.get('name') if isinstance(account_arg, dict) else account_arg
        hint = migration_auth_failure_hint(account_name, 'jamf')
        emit_input_error(
            helper=helper, ew=ew,
            category="auth",
            label="Jamf Pro authentication",
            target_url=url or "(account URL not set)",
            summary="Failed to connect to Jamf Pro: %s%s" % (str(e), hint),
        )
        raise  # Re-raises the original exception
    if jss is None:
        raise RuntimeError("Unable to create the Jamf Pro Object")

    def write_string_to_event_with_parsing(DATA):
        root = ElementTree.fromstring(DATA)
        if root.tag == "computer":
            jamf_computer = jamf_pro_models.jamf_pro_computer()
            jamf_computer.build_from_string(DATA, "computer")
            string_list = jamf_computer.paginate(create_event_id=True, max_char_length=maxCharLength)
            for line in string_list:
                write_string_to_event(line)
            # write_string_to_event(DATA)
        elif root.tag == "mobile_device":
            jamf_mobile = jamf_pro_models.jamf_pro_mobile_device()
            jamf_mobile.build_from_string(DATA, "mobile_device")
            string_list = jamf_mobile.paginate(create_event_id=True)
            for line in string_list:
                write_string_to_event(line)
        elif root.tag == "mac_application":
            macapplication = jamf_pro_models.MacApplication()
            macapplication.build_from_string(DATA, "JSSResource")
            string_list = macapplication.paginate()
            for line in string_list:
                write_string_to_event(line)
        else:
            data = ElementTree.fromstring(DATA)
            # write_string_to_event(ElementTree.tostring(data))
            write_string_to_event(DATA)

    def write_string_to_event(event_string):
        #
        #   This class is to help with the writing to the Splunk Event writer
        #
        #
        if event_string.__len__() < maxCharLength:
            xml_event = ElementTree.fromstring(event_string)
            event = helper.new_event(data=ElementTree.tostring(xml_event, encoding="utf-8", method="xml").decode(),
                                     index=index, host=host)
            # event = helper.new_event(data=event_string, index=index, host=host)
            ew.write_event(event)
            return True
        else:
            error_root = ElementTree.Element("Error")
            ElementTree.SubElement(error_root, 'error').text = "The XML was too long"
            write_string_to_event(ElementTree.tostring(error_root))
            event = helper.new_event(data=str(len(event_string)), index=index, host=host)
            ew.write_event(event)

        return False


    api_retries = 0

    def api_get_call(endPoint):
        #
        #   JSSResources API Call. Returns (content, is_permanent) on success/failure:
        #     (bytes, False)  — success
        #     (None, False)   — transient failure (network, 5xx, no response object)
        #     (None, True)    — permanent failure (4xx) that warrants disabling the input
        #
        logging.debug("[start] api_get_Call")
        if not endPoint.__contains__("JSSResource/"):
            logging.error("The Jamf input module does not support this API path: " + endPoint)
            return None, False
        r = jss.get_jss_resource_xml(endpoint=endPoint)
        if r is None:
            logging.error("No response from the Jamf Pro Server: %s" % endPoint)
            return None, False
        if not hasattr(r, "status_code") or r.status_code is None:
            logging.error("No status code from the Jamf Pro Server: %s" % endPoint)
            return None, False
        status_code = r.status_code
        logging.debug("HTTP Status Code: " + str(status_code))
        if not hasattr(r, "content") or r.content is None:
            logging.error("No content from the Jamf Pro Server: %s" % endPoint)
            return None, False
        if status_code == 401:
            _emit_endpoint_error(
                "auth",
                "Classic API authentication",
                endPoint,
                "Jamf Pro returned 401 Unauthorized for %s. The bearer token was rejected." % endPoint,
            )
            return None, True
        if status_code != 200:
            # Non-2xx other than 401. Surface to operators; the outer caller
            # also returns None and stops the loop.
            preview = (r.content[:200].decode("utf-8", errors="replace")
                       if isinstance(r.content, (bytes, bytearray)) else str(r.content)[:200])
            _emit_endpoint_error(
                "endpoint",
                "Classic API endpoint",
                endPoint,
                "Jamf Pro returned HTTP %d for %s; body preview: %s" % (status_code, endPoint, preview),
            )
            return None, True
        logging.debug("[end] api_get_Call")
        return r.content, False

    #
    # API Endpoint Handlers
    #
    def _emit_endpoint_error(category, label, target_url, summary, record_id=None):
        """Thin wrapper around the shared emitter that closes over this
        input's helper/ew/index/host. See error_reporting.emit_input_error
        for the canonical implementation.
        """
        emit_input_error(
            helper=helper, ew=ew,
            category=category,
            label=label, target_url=target_url, summary=summary,
            record_id=record_id,
            index=index, host=host,
        )

    # Pre-flight: a v2-migrated stanza could have api_call set (or
    # auto-normalized to 'computer' / 'mobile_device') but search_name
    # missing — the URL would then be ".../name/" and Jamf would 404 with a
    # confusing "saved search '' not found" message. Catch that here with a
    # message that points at the actual missing field.
    if api_call in ("computer", "mobile_device") and not (search_name or "").strip():
        endpoint_label = (
            "Advanced Computer Search" if api_call == "computer"
            else "Advanced Mobile Device Search"
        )
        _emit_endpoint_error(
            "config",
            endpoint_label,
            "(no request was made)",
            "Endpoint type %r requires a saved-search name in the Search Name field; the field is empty." % api_call,
        )
        return

    if api_call == "computer":
        #
        #   make the API Call
        #
        jss_url = "%sJSSResource/advancedcomputersearches/name/%s" % (url, search_name)
        #response = requests.get(jss_url, auth=(username, password), headers={'Accept': 'application/xml'}, verify=False)
        response = jss.get_jss_resource_xml(endpoint=jss_url)
        if response is None or getattr(response, 'content', None) is None:
            _emit_endpoint_error(
                "endpoint",
                "Advanced Computer Search",
                jss_url,
                "Jamf Pro returned no response (HTTP error or empty body) for saved search %r" % search_name,
            )
            _errs = jss.consume_endpoint_errors()
            if any(perm for (_, _, _, perm) in _errs):
                _status = next((s for (_, s, _, p) in _errs if p), None)
                auto_disable_input(helper, "jamf",
                    "This input was disabled after Jamf Pro returned HTTP %s for the Advanced Computer Search %r. "
                    "Check your URL, saved search name, and account permissions, then re-enable this input."
                    % (_status, search_name))
            return
        try:
            tree = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as parse_err:
            _emit_endpoint_error(
                "endpoint",
                "Advanced Computer Search",
                jss_url,
                "Jamf Pro returned a response that is not valid XML for saved search %r: %s"
                % (search_name, parse_err),
            )
            return
        #
        #   Start Advanced Computer
        #

        #
        #   Chunk list is a list of the XML fields that we want to farm out to their own XML data sets
        #
        chunk_list = list()
        # chunk_list.append("Applications")
        # chunk_list.append("Computer_Group")
        chunk_list.append("Running_Services")

        #
        #   Pull the computers out of the Advanced Computer Search
        #

        computers_list = tree.find('computers')
        computers = computers_list.findall('computer')
        for computer in computers:

            #
            #   keyValue is an Abstract name for the values in Chunk List it will pull it out of the primary XML
            #
            for keyValue in chunk_list:
                if computer.find(keyValue):
                    keyXML = computer.find(keyValue)
                    # Get the lenght of the string representation of the XML document
                    key_char_length = ElementTree.tostring(keyXML).__len__()
                    if key_char_length < maxCharLength:
                        #
                        #   If this is under 10k just go ahead and write to the event reader
                        #
                        root = ElementTree.Element("computer")
                        ElementTree.SubElement(root, 'id').text = computer.find("id").text
                        root.append(keyXML)
                        write_string_to_event(ElementTree.tostring(root))
                    else:
                        #
                        #   This is the area for if the already seperated XML is still too large. It will take the Length and use MOD to give the number of XML files it would need to be cut into. I add an additional one just in c
                        #
                        chunk_ID = str(uuid.uuid4())
                        num_XML = math.ceil(key_char_length / maxCharLength) + 1
                        #
                        #   Create an array of XML documents
                        #
                        root_list = []
                        for i in range(0, int(num_XML)):
                            root = ElementTree.Element(keyValue)
                            root_list.append(root)
                        #
                        #   Get a list of the 1st level children in the XML document keeping the same structure
                        #

                        #   Careful about the below call it is gone after 3.7 python new list function from 3.1 was introduced need to switch the call type
                        key_child = list(keyXML)
                        i = 0
                        for child in key_child:
                            # print("inserting into array number: "+str(int(math.fmod(i,num_XML))))
                            root_list[int(math.fmod(i, num_XML))].append(child)
                            i = i + 1
                        #
                        #   Iterate through the finished XML documents and write to the event writer.
                        #

                        for fin_xml in root_list:
                            root = ElementTree.Element("computer")
                            ElementTree.SubElement(root, 'id').text = computer.find("id").text
                            root.append(fin_xml)
                            chunk_uuid = ElementTree.Element("sub_pagination")
                            ElementTree.SubElement(chunk_uuid, 'uuid').text = chunk_ID
                            ElementTree.SubElement(chunk_uuid, 'chunk_number').text = str(i)
                            ElementTree.SubElement(chunk_uuid, 'chunk_size').text = str(root_list.__len__())
                            root.append(chunk_uuid)

                            # write_string_to_event( ElementTree.tostring(chunk_uuid) )

                            write_string_to_event(ElementTree.tostring(root))

                    #
                    #   Remove the Key Index field from the XML
                    #
                    computer.remove(keyXML)
            #
            #   Post Data chunking... This *should* be under 10k char now, tune it with chunk list
            #

            data = ElementTree.tostring(computer)

            #
            #   Check to see if it needs chunking and if it still needs it chunk it on childs
            #
            if data.__len__() < maxCharLength:
                # print (data)
                write_string_to_event(data)

            else:
                num_XML = math.ceil(data.__len__() / maxCharLength) + 1
                #
                #   Create an array of XML documents
                #
                root_list = []
                chunk_ID = str(uuid.uuid4())
                for i in range(0, int(num_XML)):
                    root = ElementTree.Element("computer")
                    ElementTree.SubElement(root, 'id').text = computer.find("id").text
                    chunk_uuid = ElementTree.Element("pagination")
                    ElementTree.SubElement(chunk_uuid, 'uuid').text = chunk_ID
                    ElementTree.SubElement(chunk_uuid, 'chunk_number').text = str(i + 1)
                    ElementTree.SubElement(chunk_uuid, 'chunk_size').text = str(int(num_XML))
                    root.append(chunk_uuid)

                    root_list.append(root)

                #
                #   Get a list of the 1st level children in the XML document keeping the same structure
                #

                #
                #   Need to remove ID from XML since it will be a duplicate in 1 of them.
                #

                computer.remove(computer.find("id"))
                #   Careful about the below call it is gone after 3.7 python new list function from 3.1 was introduced need to switch the call type
                key_child = list(computer)
                i = 0
                for child in key_child:
                    # print("inserting into array number: "+str(int(math.fmod(i,num_XML))))
                    root_list[int(math.fmod(i, num_XML))].append(child)
                    i = i + 1
                #
                #   Iterate through the finished XML documents and write to the event writer.
                #

                for fin_xml in root_list:
                    write_string_to_event(ElementTree.tostring(fin_xml))

            #
            # End of Computers For Loop
            #
        #
        # End of Advanced Computers Section
        #


    elif api_call == "mobile_device":
        jss_url = "%sJSSResource/advancedmobiledevicesearches/name/%s" % (url, search_name)
        #response = requests.get(jss_url, auth=(username, password), headers={'Accept': 'application/xml'}, verify=False)
        response = jss.get_jss_resource_xml(endpoint=jss_url)
        if response is None or getattr(response, 'content', None) is None:
            _emit_endpoint_error(
                "endpoint",
                "Advanced Mobile Device Search",
                jss_url,
                "Jamf Pro returned no response (HTTP error or empty body) for saved search %r" % search_name,
            )
            _errs = jss.consume_endpoint_errors()
            if any(perm for (_, _, _, perm) in _errs):
                _status = next((s for (_, s, _, p) in _errs if p), None)
                auto_disable_input(helper, "jamf",
                    "This input was disabled after Jamf Pro returned HTTP %s for the Advanced Mobile Device Search %r. "
                    "Check your URL, saved search name, and account permissions, then re-enable this input."
                    % (_status, search_name))
            return
        try:
            tree = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as parse_err:
            _emit_endpoint_error(
                "endpoint",
                "Advanced Mobile Device Search",
                jss_url,
                "Jamf Pro returned a response that is not valid XML for saved search %r: %s"
                % (search_name, parse_err),
            )
            return

        #
        #   Chunk list is a list of the XML fields that we want to farm out to their own XML data sets
        #
        chunk_list = list()
        chunk_list.append("Display_Name")
        chunk_list.append("Capacity_MB")
        chunk_list.append("Device_Locator_Service_Enabled")

        mobile_devices_list = tree.find('mobile_devices')
        mobile_devices = mobile_devices_list.findall('mobile_device')
        for mobile_device in mobile_devices:
            #
            #   keyValue is an Abstract name for the values in Chunk List it will pull it out of the primary XML
            #
            for keyValue in chunk_list:
                if mobile_device.findall(keyValue):
                    # event = helper.new_event(data=keyValue, index=index, host=host)
                    # ew.write_event(event)
                    keyXML = mobile_device.find(keyValue)
                    # Get the lenght of the string representation of the XML document
                    key_char_length = ElementTree.tostring(keyXML).__len__()
                    if key_char_length < maxCharLength:
                        #
                        #   If this is under 10k just go ahead and write to the event reader
                        #

                        root = ElementTree.Element("mobile_device")
                        ElementTree.SubElement(root, 'id').text = mobile_device.find("id").text
                        sub_root = ElementTree.Element(keyValue)
                        root.append(keyXML)
                        # print(ElementTree.tostring(root))
                        write_string_to_event(ElementTree.tostring(root))
                    else:
                        #
                        #   This is the area for if the already seperated XML is still too large. It will take the Length and use MOD to give the number of XML files it would need to be cut into. I add an additional one just in c
                        #

                        num_XML = math.ceil(key_char_length / maxCharLength) + 1

                        #
                        #   Create an array of XML documents
                        #
                        chunk_ID = uuid.uuid4()
                        root_list = []
                        for i in range(0, int(num_XML)):
                            root = ElementTree.Element(keyValue)
                            root_list.append(root)

                        #
                        #   Get a list of the 1st level children in the XML document keeping the same structure
                        #

                        #   Careful about the below call it is gone after 3.7 python new list function from 3.1 was introduced need to switch the call type
                        key_child = list(keyXML)
                        i = 0
                        for child in key_child:
                            # print("inserting into array number: "+str(int(math.fmod(i,num_XML))))
                            root_list[int(math.fmod(i, num_XML))].append(child)
                            i = i + 1
                        #
                        #   Iterate through the finished XML documents and write to the event writer.
                        #

                        for fin_xml in root_list:
                            root = ElementTree.Element("mobile_device")
                            ElementTree.SubElement(root, 'id').text = mobile_device.find("id").text
                            root.append(fin_xml)
                            event = helper.new_event(data=ElementTree.tostring(fin_xml), index=index, host=host)

                            chunk_uuid = ElementTree.Element("sub_pagination")
                            ElementTree.SubElement(chunk_uuid, 'uuid').text = chunk_ID
                            ElementTree.SubElement(chunk_uuid, 'chunk_number').text = str(i + 1)
                            ElementTree.SubElement(chunk_uuid, 'chunk_size').text = str(int(num_XML))

                            # Finally Write it
                            write_string_to_event(ElementTree.tostring(fin_xml))
                    #
                    #   Remove the Key Index field from the XML
                    #
                    mobile_device.remove(keyXML)
            #
            #   Post Data chunking... This *should* be under 10k char now, tune it with chunk list
            #

            data = ElementTree.tostring(mobile_device)

            #
            #   Check to see if it needs chunking and if it still needs it chunk it on childs
            #
            if data.__len__() < maxCharLength:
                write_string_to_event(data)
            else:
                num_XML = math.ceil(data.__len__() / maxCharLength) + 1
                #
                #   Create an array of XML documents
                #
                chunk_ID = str(uuid.uuid4())
                root_list = []
                for i in range(0, int(num_XML)):
                    root = ElementTree.Element("mobile_device")
                    ElementTree.SubElement(root, 'id').text = mobile_device.find("id").text
                    chunk_uuid = ElementTree.Element("pagination")
                    ElementTree.SubElement(chunk_uuid, 'uuid').text = chunk_ID
                    ElementTree.SubElement(chunk_uuid, 'chunk_number').text = str(i + 1)
                    ElementTree.SubElement(chunk_uuid, 'chunk_size').text = str(int(num_XML))
                    root.append(chunk_uuid)
                    root_list.append(root)
                #
                #   Get a list of the 1st level children in the XML document keeping the same structure
                #

                #
                #   Need to remove ID from XML since it will be a duplicate in 1 of them.
                #
                mobile_device.remove(mobile_device.find("id"))
                #   Careful about the below call it is gone after 3.7 python new list function from 3.1 was introduced need to switch the call type
                key_child = list(mobile_device)
                i = 0
                for child in key_child:
                    # print("inserting into array number: "+str(int(math.fmod(i,num_XML))))
                    root_list[int(math.fmod(i, num_XML))].append(child)
                    i = i + 1
                #
                #   Iterate through the finished XML documents and write to the event writer.
                #

                for fin_xml in root_list:
                    # print(ElementTree.tostring(fin_xml))
                    event = helper.new_event(data=ElementTree.tostring(fin_xml), index=index, host=host)
                    write_string_to_event(ElementTree.tostring(fin_xml))

            #
            # End of mobile_devices For Loop
            #
        #
        # End of Advanced mobile_devices Section
        #


    elif api_call == "custom":
        # Normalize path
        if search_name.startswith("/"):
            search_name = search_name.replace("/", "", 1)
        if search_name.endswith("/"):
            search_name = search_name[:-1]

        jss_url = url + search_name

        resp_string, _permanent = api_get_call(jss_url)
        if not resp_string:
            # api_get_call already emitted a category=auth or category=endpoint
            # event for the 401/non-200 case. The bare-None case (no response
            # object at all) only gets a logging.error inside api_get_call, so
            # emit a fallback endpoint event here so the operator still sees it.
            if not _permanent:
                _emit_endpoint_error(
                    "endpoint",
                    "Custom API path",
                    jss_url,
                    "Jamf Pro returned no usable response for %r (see splunkd.log for HTTP detail)" % search_name,
                )
            if _permanent:
                auto_disable_input(helper, "jamf",
                    "This input was disabled after Jamf Pro returned a 4xx error for the Custom API path %r. "
                    "Check your URL, path, and account permissions, then re-enable this input."
                    % search_name)
            return

        try:
            resp_xml = ElementTree.fromstring(resp_string)
        except ElementTree.ParseError as parse_err:
            _emit_endpoint_error(
                "endpoint",
                "Custom API path",
                jss_url,
                "Jamf Pro returned a response that is not valid XML for %r: %s" % (search_name, parse_err),
            )
            return

        if search_name.__contains__("/name/"):
            # This is a record we want to write to splunk
            write_string_to_event(resp_string)
            return
        else:
            # Some endpoints return a list of ids to loop through to get the individual records.
            # Per-item failures are logged + counted; one summary event is emitted at the
            # end of the loop so users searching jamf:input:error see the broken endpoint
            # even when individual record failures are mixed in with successes.
            children = list(resp_xml)
            failed_items = []
            for name in children:
                if name.findall("id"):
                    item_id_node = name.find("id")
                    item_id = (item_id_node.text or "").strip() if item_id_node is not None else ""
                    newCall = jss_url + "/id/" + item_id
                    try:
                        data, sub_permanent = api_get_call(newCall)
                        if data is None:
                            failed_items.append((item_id, "no response from Jamf Pro"))
                            helper.log_error(
                                "Custom endpoint sub-request returned no data: url=%s id=%s"
                                % (newCall, item_id)
                            )
                            if sub_permanent:
                                break
                            continue
                        write_string_to_event_with_parsing(data)
                    except ElementTree.ParseError as e:
                        failed_items.append((item_id, "Jamf returned non-XML for id=%s: %s" % (item_id, e)))
                        helper.log_error(
                            "Custom endpoint sub-request returned non-XML: url=%s id=%s error=%s"
                            % (newCall, item_id, e)
                        )
                    except Exception as e:
                        failed_items.append((item_id, "%s: %s" % (type(e).__name__, e)))
                        helper.log_error(
                            "Custom endpoint sub-request failed: url=%s id=%s error=%s: %s"
                            % (newCall, item_id, type(e).__name__, e)
                        )
            if failed_items:
                preview = ", ".join("id=%s (%s)" % pair for pair in failed_items[:5])
                more = "" if len(failed_items) <= 5 else " (+%d more)" % (len(failed_items) - 5)
                _emit_endpoint_error(
                    "endpoint",
                    "Custom API path",
                    jss_url,
                    "%d sub-request(s) failed while fetching individual records: %s%s"
                    % (len(failed_items), preview, more),
                )

    else:
        # api_call did not match any known endpoint type. Surface this loudly
        # rather than returning silently — silent success on a typo is what
        # made bad config look like the input was working.
        _emit_endpoint_error(
            "config",
            "Unknown endpoint type %r" % api_call,
            "(no request was made)",
            "Endpoint type %r is not one of the supported values: computer, mobile_device, custom" % api_call,
        )

    helper.log_info("jamf collect_events completed: input=%r api_call=%r search_name=%r"
                    % (helper.get_input_stanza_names(), api_call, search_name))

    #
    #   Start Here For Async Tests
    #
