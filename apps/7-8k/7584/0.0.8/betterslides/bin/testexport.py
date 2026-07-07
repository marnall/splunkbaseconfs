from __future__ import absolute_import, division, print_function, unicode_literals

import sys, os, requests
from dashboard_exporter import DashboardExporter

#load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Import modules from ../lib
import splunklib.client as client
import splunklib.binding as binding
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

COMMAND_NAME = "spreadsheetcommand"

@Configuration(distributed=False, type="reporting")
class spreadsheetcommand(GeneratingCommand):

    earliest = Option(require=False)
    latest = Option(require=False)
    dashboards = Option(require=True)

    def __init__(self):
        GeneratingCommand.__init__(self)

    def generate(self):
        try:
            self.username = self._metadata.searchinfo.username if hasattr(self._metadata.searchinfo, "username") else False
            self.session_key = self._metadata.searchinfo.session_key if hasattr(self._metadata.searchinfo, "session_key") else False

            if self.username and self.session_key:
                # Split the string by semicolon
                elements = self.dashboards.split(';')
                
                # Remove any empty elements and strip whitespace from each element
                dashboards = [elem.strip() for elem in elements if elem.strip()]

                #dashboards = ["slidedeck_test_1_cover", "slidedeck_test_2_some_md_syntax_stuff", "slidedeck_test_n_closing_slide"]

                exporter = DashboardExporter(self.session_key)
                
                # Initialize the presentation
                exporter.initialize_presentation()

                # Add slides for each dashboard
                for dashboard in dashboards:
                    exporter.add_dashboard_slide(dashboard)

                # Get the final presentation
                pptx_bytes = exporter.get_presentation()

                # Save the presentation to a file
                with open("output_presentation.pptx", "wb") as f:
                    f.write(pptx_bytes.getbuffer())

                event = {"_raw":"exported"}

                yield event

            if not self.username:
                self.write_error(f"[{COMMAND_NAME}]: Lookup failed. No username or session_key found.")
            else:
                self.write_info(f"[{COMMAND_NAME}]: Successfully read lookup")

        except Exception as e:
            import traceback

            # Get the current exception information
            exc_type, exc_value, exc_traceback = sys.exc_info()
            
            # Format the exception and traceback
            exception_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
            
            # Print the formatted exception and traceback to stderr
            print("An exception occurred:", file=sys.stderr)
            print("".join(exception_details), file=sys.stderr)


dispatch(spreadsheetcommand, sys.argv, sys.stdin, sys.stdout, __name__)
