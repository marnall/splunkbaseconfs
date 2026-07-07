# Created by: David MacDonald

import os
from posixpath import split
import sys
import json
import traceback
import cherrypy
import defusedxml.ElementTree as ET
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
from controller_services import file_operations as fo
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page

bin_dir = os.path.join(util.get_apps_dir(), __file__.split(".")[-2], "bin")
if bin_dir not in sys.path:
    sys.path.append(dir)


class AppSetupController(controllers.BaseController):
    """
    App Setup Controller
    """

    # TODO: Be able to save search strings back to xml files
    def __init__(self):
        self.cur_app_dir = os.path.join(util.get_apps_dir(), "SplunkStart")
        self.default_xml_dir = os.path.join(
            self.cur_app_dir, "default", "data", "ui", "views"
        )
        self.local_xml_dir = os.path.join(
            self.cur_app_dir, "local", "data", "ui", "views"
        )

    # Useful function for returning error messages
    def render_error_json(self, status, msg):
        """
        Render JSON that describes an error state.
        """
        cherrypy.response.status = status
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        return self.render_json(output)

    @expose_page(must_login=True, methods=["GET"])
    def get_report_names(self):
        try:
            return self.render_json(fo.get_report_names())

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=["GET"])
    def get_macro_names(self):
        try:
            checked_default = False
            if os.path.exists(os.path.join(self.cur_app_dir, "local", "macros.conf")):
                target = open(
                    os.path.join(self.cur_app_dir, "local", "macros.conf"), "r"
                )
            else:
                target = open(
                    os.path.join(self.cur_app_dir, "default", "macros.conf"), "r"
                )
                checked_default = True

            macro_list = []
            for line in target:
                line = line.strip()
                if line.startswith("["):
                    line = line.lstrip("[")
                    line = line.rstrip("]")
                    macro_list.append(line)

            target.close()

            if not checked_default:
                target = open(os.path.join(self.cur_app_dir, "default", "macros.conf"))
                for line in target:
                    line = line.strip()
                    if line.startswith("["):
                        line = line.lstrip("[")
                        line = line.rstrip("]")
                        macro_list.append(line)

                target.close()
                macro_list = list(sorted(set(macro_list)))

            return self.render_json(macro_list)

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=["GET"])
    def get_macro_from_name(self, macro_name):
        try:
            checked_default = False
            if os.path.exists(os.path.join(self.cur_app_dir, "local", "macros.conf")):
                target = open(
                    os.path.join(self.cur_app_dir, "local", "macros.conf"), "r"
                )
            else:
                target = open(
                    os.path.join(self.cur_app_dir, "default", "macros.conf"), "r"
                )
                checked_default = True

            macro_found = False
            macro_args = ""
            macro_definition = ""
            for line in target:
                line = line.strip()
                if line.startswith("["):
                    line = line.lstrip("[")
                    line = line.rstrip("]")
                    if macro_name == line:
                        macro_found = True
                elif macro_found and line.startswith("args"):
                    line = line.replace("args =", "").replace("args=", "").strip()
                    macro_args = line
                elif macro_found and line.startswith("definition"):
                    line = (
                        line.replace("definition =", "", 1)
                        .replace("definition=", "", 1)
                        .strip()
                    )
                    macro_definition = line
                    break
            target.close()

            if not macro_found and not checked_default:
                target = open(
                    os.path.join(self.cur_app_dir, "default", "macros.conf"), "r"
                )
                for line in target:
                    line = line.strip()
                    if line.startswith("["):
                        line = line.lstrip("[")
                        line = line.rstrip("]")
                        if macro_name == line:
                            macro_found = True
                    elif macro_found and line.startswith("args"):
                        line = line.replace("args =", "").replace("args=", "").strip()
                        macro_args = line
                    elif macro_found and line.startswith("definition"):
                        line = (
                            line.replace("definition =", "", 1)
                            .replace("definition=", "", 1)
                            .strip()
                        )
                        macro_definition = line
                        break
                target.close()

            return self.render_json(
                {"args": macro_args, "definition": macro_definition}
            )

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=["GET"])
    def get_dashboard_names(self):
        try:
            return self.render_json(fo.get_panel_data())
        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Create a new dashboard .xml file
    @expose_page(must_login=True, methods=["POST"])
    def create_new_dashboard(self, dash_file_name, dash_label):
        try:

            file_name = json.loads(dash_file_name)
            label = json.loads(dash_label)

            if not os.path.exists(self.local_xml_dir):
                fo.create_local_xml_directory()

            need_html = False
            if fo.do_spl_btns_exist() is True:
                need_html = True

            target = open(os.path.join(self.local_xml_dir, file_name), "w")
            content = ""
            content += (
                '<dashboard script="toggle.js" stylesheet="comment.css">\n\t<label>'
                + label
                + "</label>\n"
            )
            if need_html:
                content += (
                    "\t<row>"
                    + "\n\t\t<panel>"
                    + '\n\t\t\t<html src="views/panel_search_popup.html"></html>'
                    + "\n\t\t</panel>"
                    + "\n\t</row>\n"
                )
            content += "</dashboard>"

            target.write(content)
            target.close()

            return "Dashboard Added"
        except:
            self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=["POST"])
    def add_panel_to_dash(self, file_name, report, panel_type, panel_name):
        try:
            file_name = json.loads(file_name)
            report = json.loads(report)
            panel_type = json.loads(panel_type)
            panel_name = json.loads(panel_name)

            tree = ET.parse(os.path.join(self.local_xml_dir, file_name))

            root = tree.getroot()
            row = ET.SubElement(root, "row")
            panel = ET.SubElement(row, "panel")
            p_type = ET.SubElement(panel, panel_type)
            title = ET.SubElement(p_type, "title")
            title.text = panel_name
            search = ET.SubElement(p_type, "search", {"ref": report})

            if fo.do_spl_btns_exist() is True:
                html = ET.SubElement(panel, "html")
                button = ET.SubElement(html, "button")
                button.set("id", search.get("ref"))
                button.set("class", "btn btn-default")
                button.set("style", "float: right;")
                button.text = "Show SPL"

            tree.write(os.path.join(self.local_xml_dir, file_name))

            return "Panel Added"

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=["POST"])
    def add_macro(self, macro_entry):
        try:
            macro_entry = json.loads(macro_entry)

            if not fo.does_macro_exist(macro_entry.lstrip("[").split("(")[0]):
                if not os.path.exists(os.path.join(self.cur_app_dir, "local")):
                    os.mkdir(os.path.join(self.cur_app_dir, "local"))

                target = open(
                    os.path.join(self.cur_app_dir, "local", "macros.conf"), "a"
                )
                target.write(macro_entry + "\n")
                target.close()

                return "Macro Added"

            else:
                return self.render_error_json(
                    409, "Macro with that name already exists"
                )

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=["POST"])
    def add_saved_search(self, report_name, search_string):
        try:
            report_name = json.loads(report_name)
            search_string = json.loads(search_string)

            if not os.path.exists(os.path.join(self.cur_app_dir, "local")):
                os.mkdir(os.path.join(self.cur_app_dir, "local"))

            target = open(
                os.path.join(self.cur_app_dir, "local", "savedsearches.conf"), "a"
            )

            content = "[" + report_name + "]\n"
            content += "search = `" + search_string + "`\n\n"

            target.write(content)
            target.close()

            return "Added Saved Search"

        except:
            return self.render_error_json(500, str(traceback.format_exc()))
