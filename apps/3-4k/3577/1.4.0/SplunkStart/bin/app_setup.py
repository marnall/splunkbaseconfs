# Created by: David MacDonald

from controller_services import file_operations as fo
import os
import sys
import json
import cherrypy
import traceback
import defusedxml.ElementTree as ET
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page

bin_dir = os.path.join(util.get_apps_dir(), __file__.split('.')[-2], 'bin')
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
            self.cur_app_dir, "default", "data", "ui", "views")
        self.local_xml_dir = os.path.join(
            self.cur_app_dir, "local", "data", "ui", "views")

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

    # Handles getting macros from savedsearches.conf
    @expose_page(must_login=True, methods=['GET'])
    def get_chart_macros(self):
        try:
            if os.path.exists(os.path.join(self.cur_app_dir, "local", "savedsearches.conf")):
                macro_file = open(os.path.join(
                    self.cur_app_dir, "local", "savedsearches.conf"), "r")
            else:
                macro_file = open(os.path.join(
                    self.cur_app_dir, "default", "savedsearches.conf"), "r")

            macro_list = []
            for line in macro_file:
                line = line.strip()
                if line.startswith("search =") or line.startswith("search="):
                    macro_list.append(line.split('`')[1])

            macro_file.close()
            return self.render_json(macro_list)

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Handles returning a specified macros.txt file
    @expose_page(must_login=True, methods=['GET'])
    def get_whole_macro_file(self, file_name):
        try:
            macro_file = open(os.path.join(
                self.cur_app_dir, "src", "macros", file_name))

            contents = ""
            for line in macro_file:
                contents += line

            macro_file.close()
            return contents

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Currently not being used
    @expose_page(must_login=True, methods=['GET'])
    def get_dashboard_titles(self):
        try:
            return self.render_json(fo.get_titles_from_files())

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Handles getting panel data
    @expose_page(must_login=True, methods=['GET'])
    def get_dashboard_data(self):
        try:
            return self.render_json(fo.get_panel_data())

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Get all files found in the src/macros directory
    @expose_page(must_login=True, methods=['GET'])
    def get_existing_macro_files(self):
        try:
            return self.render_json(os.listdir(os.path.join(self.cur_app_dir, "src", "macros")))

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Determines if the "Show SPL" buttons are present in the xml or not
    @expose_page(must_login=True, methods=['GET'])
    def do_spl_btns_exist(self):
        try:
            return self.render_json(fo.do_spl_btns_exist())

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Gets info to display for the "Show SPL" buttons
    @expose_page(must_login=True, methods=['GET'])
    def get_panel_spl_info(self, report_name=None, macro=None):
        try:
            if macro is None:
                panel_search = fo.get_search_reference(report_name)
            else:
                panel_search = macro

            macro_name = panel_search.split('(')[0]
            macro_name += '(' + \
                str(len(panel_search.split('(')[1].split(','))) + ')'
            macro_info = fo.get_macro_from_name(macro_name)
            definition = macro_info["definition"]
            args = macro_info["args"]

            if args == "" and definition == "":
                full_search = "Macro Definition Not Found"
            else:
                search_args_list = panel_search.split(
                    '(')[1].rstrip(')').split(',')
                args_list = args.split(',')
                def_split = definition.split('$')

                for i in range(0, len(def_split)):
                    if i % 2 == 1:
                        for j in range(0, len(args_list)):
                            args_list[j] = args_list[j].strip()
                            if def_split[i] == args_list[j]:
                                def_split[i] = search_args_list[j].strip()
                                break

                full_search = ""
                for item in def_split:
                    full_search += item

            return self.render_json({"panel_search": panel_search, "full_search": full_search})

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Handles the submission of a macros.txt file
    @expose_page(must_login=True, methods=['POST'])
    def submit_macro_file(self, file_name, fc):
        try:
            file_content = json.loads(fc)

            # Save macro_file to src/macros directory
            macro_file = open(os.path.join(self.cur_app_dir,
                              "src", "macros", file_name), "w")
            macro_file.write(file_content)
            macro_file.close()

            # Get macros from newly saved my_macros file and update savedsearches.conf
            macro_list = fo.get_macros_from_file(os.path.join(
                self.cur_app_dir, "src", "macros", file_name))
            return self.render_json(fo.update_searches_from_macro_list(macro_list))

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Handles the submission of a list of new macros from input boxes
    @expose_page(must_login=True, methods=['POST'])
    def submit_macro_list(self, ml):
        try:
            macro_list = json.loads(ml)
            return self.render_json(fo.update_searches_from_macro_list(macro_list))
        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Handles the submission of title data, including the title's file from input boxes
    @expose_page(must_login=True, methods=['POST'])
    def submit_titles(self, title_data):
        try:
            # title_data format {file: "file", titles: ["title1", "title2", ...]}
            new_titles = json.loads(title_data)

            return fo.save_new_titles(new_titles)

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Handles the submission of a titles.csv file
    @expose_page(must_login=True, methods=['POST'])
    def submit_titles_from_file(self, td):
        try:
            title_data = json.loads(td)

            if len(title_data["titles"]) != 0:
                # Write title file to src/titles directory
                csv = open(os.path.join(self.cur_app_dir, "src",
                           "titles", title_data["csv_name"]), "w")
                for title_pair in title_data["titles"]:
                    csv.write(title_pair[0] + "," + title_pair[1] + '\n')
                csv.close()

                return fo.save_new_titles_from_file(title_data["titles"])
            else:
                return "No titles to update"

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # Writes to a new app.conf file indicating that the app is configured
    @expose_page(must_login=True, methods=['POST'])
    def finish_setup(self):
        try:
            # Indicate app is configured by adding the stanza below to local/app.conf
            local_dir = os.path.join(self.cur_app_dir, "local")
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)

            old_app_conf = open(os.path.join(
                self.cur_app_dir, "default", "app.conf"), "r")
            new_app_conf = open(os.path.join(
                self.cur_app_dir, "local", "app.conf"), "w")

            for line in old_app_conf:
                if "is_configured" in line:
                    line = "is_configured = 1\n"
                new_app_conf.write(line)

            old_app_conf.close()
            new_app_conf.close()

            return "local/app.conf created and is_configured = 1"

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=['POST'])
    def remove_show_spl_btns(self):
        try:
            dashboard_list = fo.get_dashboard_files()

            for f in dashboard_list:
                if os.path.exists(os.path.join(self.local_xml_dir, f)):
                    tree = ET.parse(os.path.join(self.local_xml_dir, f))
                else:
                    tree = ET.parse(os.path.join(self.default_xml_dir, f))

                root = tree.getroot()
                for row in root.iter("row"):
                    for panel in row.iter("panel"):
                        for html in panel.iter("html"):
                            if html.find("button") is not None and html.find("button").text == "Show SPL":
                                panel.remove(html)
                            if html.get("src") is not None and html.get("src") == "views/panel_search_popup.html":
                                row.remove(panel)

                if not os.path.exists(self.local_xml_dir):
                    fo.create_local_xml_directory()

                tree.write(os.path.join(self.local_xml_dir, f))

            return "SPL Buttons Removed"

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    @expose_page(must_login=True, methods=['POST'])
    def add_show_spl_btns(self):
        try:
            dashboard_list = fo.get_dashboard_files()

            for f in dashboard_list:
                if os.path.exists(os.path.join(self.local_xml_dir, f)):
                    tree = ET.parse(os.path.join(self.local_xml_dir, f))
                else:
                    tree = ET.parse(os.path.join(self.default_xml_dir, f))

                root = tree.getroot()

                # Insert toggle button and modal into xml
                first_row = ET.Element("row")
                panel = ET.SubElement(first_row, "panel")
                html = ET.SubElement(panel, "html")
                html.set("src", "views/panel_search_popup.html")
                root.insert(0, first_row)

                # Insert "Show SPL" buttons
                for panel in root.iter("panel"):
                    for child in panel:
                        if child.find("search") is not None:
                            search = child.find("search")
                            if search.get("ref") is not None:
                                html = ET.SubElement(panel, "html")
                                button = ET.SubElement(html, "button")
                                button.set("id", search.get("ref"))
                                button.set("class", "btn btn-default")
                                button.set("style", "float: right;")
                                button.text = "Show SPL"

                if not os.path.exists(self.local_xml_dir):
                    fo.create_local_xml_directory()

                tree.write(os.path.join(self.local_xml_dir, f))

            return "SPL Buttons Added"

        except:
            return self.render_error_json(500, str(traceback.format_exc()))

    # A method for testing
    @expose_page(must_login=True, methods=['GET'])
    def test(self):
        try:
            # ret = ""
            # for root, dirs, files in os.walk(self.cur_app_dir):
            #     for file in files:
            #         if file.endswith(".txt"):
            #             ret += " " + str(os.path.join(root, file))

            return "Hey Bro"
        except:
            return str(traceback.format_exc())
