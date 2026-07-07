# bin/betterpdfHandler.py

"""Rest service providing a PDF file presenting the data passed as saved search name or job id in tabular or chart form."""

import logging
import time
import json
import subprocess
import sys
import os
import fnmatch
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
import splunk
from splunk import entity
import splunk.auth
from future.moves.urllib.parse import unquote

#############################
# v 1.0.21
#############################

app_name = "betterpdf"
SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")


# load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Initialize logger
def setup_logging() -> logging.Logger:
    """Set up the logging."""
    logger = logging.getLogger("betterpdf")
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, "var", "log", "splunk", f"{app_name}.log"),
        mode="a",
        maxBytes=25000000,
        backupCount=2,
    )
    formatter = logging.Formatter(
        "%(created)f log_level=%(levelname)s, pid=%(process)d, line=%(lineno)d, %(message)s"
    )
    file_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
    logger.setLevel("DEBUG")
    return logger

logger = setup_logging()


try:
    from splunklib import client
    from splunklib import results
    from solnlib import credentials
    import jsonpickle
    import pygal
    from pygal.style import Style
    from pygal import Config
    from fpdf.fonts import FontFace
    from fpdf import FPDF
    from fpdf.template import FlexTemplate

    # Import the data transformation and PDF generation modules
    from data_transform import (
        transform_records,
        generate_error_svg,
        serialize_chart,
    )
    from pdf_generator import (
        MyPDF,
        create_cover_page,
        create_search_results_page,
        create_lookup_pages,
    )
    from utils import safe_open_w, safe_open_wb

except Exception as e:
    logger.info(e)

# Define a custom style
custom_style = Style(
    background='transparent',  # Set background color to transparent
    plot_background='transparent',  # Set plot background color to transparent
    value_font_size=30,
    value_colors=('white',),
    # Define other style properties as needed
)

# Global default config for charts
chartconfig = Config()
chartconfig.show_legend = True
chartconfig.human_readable = True
chartconfig.margin_top = 0
chartconfig.margin = 0
chartconfig.style = custom_style
# chartconfig.print_values=True

# Paths
resourcepath = os.path.dirname(__file__)
localpath = os.path.join(os.path.dirname(__file__), "local")
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

class ArgError(Exception):
    """Handle argument errors."""
    def __init__(self, message):
        super(ArgError, self).__init__(message)

    def __str__(self):
        return repr(self.value)

class betterpdfHandler(splunk.rest.BaseRestHandler):
    """Main class handling the REST calls."""
    _title = "BetterPDFHandler"

    def handle_GET(self):
        """Handle GET requests."""
        logger.info("Received GET request.")
        self._handleRequest()

    def handle_POST(self):
        """Handle POST requests."""
        logger.info("Received POST request.")
        self._handleRequest()

    def _handleRequest(self):
        """Main request handling logic."""
        userName = self.request.get("userName", "unknown_user")
        logger.info(f"Request method: {self.method}")
        transaction = str(time.time())

        try:
            # Verify License
            license_info = self.verify_license()
            if not license_info["is_valid"] or not license_info["has_pdf_feature"]:
                raise ArgError("Invalid license or missing 'pdf' feature.")

            # Set up PDF generation parameters
            formating = self.get_formating_settings(license_info)
            logopath = self.get_logopath()

            # Initialize PDF
            pdf = MyPDF(formating, logopath, license_info["triallicense"], license_info["cn"], logger)
            pdf.alias_nb_pages()
            pdf.set_font(formating["font"], "B", int(formating["fontsize"]))

            if self.method == "POST":
                self.handle_post_request(pdf, license_info)
            elif self.method == "GET":
                self.handle_get_request(pdf, license_info)

        except ArgError as ae:
            logger.error(f"Argument error: {str(ae)}")
            self.respond_with_error("Invalid request parameters.", ae)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self.respond_with_error("An unexpected error occurred.", e)

    def verify_license(self) -> Dict[str, Any]:
        """Verify the license and return license information."""
        try:
            license_path = os.path.join(resourcepath, "license")
            if not os.path.isfile(license_path):
                raise ArgError("License file not found.")

            with open(license_path, "rb") as f:
                license_data = f.read()

            # Verify license using openssl
            process = subprocess.Popen(
                ["openssl", "verify", "-verbose"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            verify_output, verify_err = process.communicate(input=license_data)
            if process.returncode != 0:
                raise ArgError("License verification failed.")

            # Check license validity
            process = subprocess.Popen(
                ["openssl", "x509", "-in", license_path, "-noout", "-checkend", "30"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, _ = process.communicate()
            is_valid = process.returncode == 0

            # Check for 'pdf' feature in license
            process = subprocess.Popen(
                [
                    "openssl",
                    "x509",
                    "-text",
                    "-noout",
                    "-in",
                    license_path,
                    "-certopt",
                    "no_subject,no_header,no_version,no_serial,no_signame,no_validity,no_issuer,no_pubkey,no_sigdump,no_aux",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            cert_text, _ = process.communicate()
            features = []
            for line in cert_text.decode("utf-8").split("\n"):
                line = line.strip()
                if line.startswith("DNS:"):
                    features.append(line[4:])
            has_pdf_feature = 'pdf' in features

            # Extract license subject
            process = subprocess.Popen(
                ["openssl", "x509", "-in", license_path, "-noout", "-subject"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subject, _ = process.communicate()
            subject = subject.decode("utf-8").strip().split("CN=")[-1]

            # Extract license end date
            process = subprocess.Popen(
                ["openssl", "x509", "-in", license_path, "-noout", "-enddate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            enddate, _ = process.communicate()
            enddate = enddate.decode("utf-8").strip().split("=")[1]

            # Determine if it's a trial license based on CN
            triallicense = "trial" in subject.lower()

            license_info = {
                "licensestatus": "pass" if is_valid else "fail",
                "cn": subject,
                "installdate": "2023-01-01",  # Placeholder
                "validtill": enddate,
                "triallicense": triallicense,
                "is_valid": is_valid,
                "has_pdf_feature": has_pdf_feature
            }

            return license_info

        except ArgError as ae:
            logger.error(f"License error: {str(ae)}")
            raise
        except Exception as e:
            logger.error(f"Error during license verification: {str(e)}")
            raise ArgError("License verification encountered an error.")

    def get_formating_settings(self, license_info: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve and prepare formatting settings."""
        authToken = self.get_auth_token()
        resp = splunk.entity.getEntity(
            ["configs", "conf-betterpdfformating"],
            "settings",
            sessionKey=authToken,
            namespace="-",
            owner="-",
        )
        formating = {str(k): (str(v) if str(v) != "None" else "") for k, v in resp.items()}
        # Remove unnecessary keys
        for key in ["eai:acl", "eai:appName", "eai:attributes", "eai:userName"]:
            formating.pop(key, None)
        # Set chart style
        set_chart_style(formating.get("style", "custom_style"))
        logger.info(f"Formatting settings: {formating}")
        return formating

    def get_logopath(self) -> str:
        """Determine the path to the logo."""
        logopath = "./splunk_logo_smaller.png"  # Default logo
        custom_logo_path = os.path.join(localpath, "customlogo")
        if os.path.isfile(custom_logo_path):
            logopath = custom_logo_path
        logger.info(f"Using logo path: {logopath}")
        return logopath

    def get_auth_token(self) -> str:
        """Retrieve the authentication token from the request."""
        headers = self.request.get("headers", {})
        cookies = {}
        if "cookie" in headers:
            cookies = dict(
                i.split("=", 1)
                for i in headers["cookie"].split("; ")
            )
        authToken = ""
        for key, value in cookies.items():
            if fnmatch.fnmatch(key, "splunkd_*"):
                authToken = value
                break
        if not authToken and self.request.get("systemAuth"):
            authToken = self.request["systemAuth"]
        logger.debug(f"Auth Token: {authToken}")
        return authToken

    def handle_post_request(self, pdf: MyPDF, license_info: Dict[str, Any]):
        """Handle POST requests."""
        try:
            payload = json.loads(self.request.get("payload", "{}"))
            records = payload.get("rows", [])
            charttype = payload.get("config", {}).get(
                "display.visualizations.custom.viz_tutorial_app.betterpdf.charttype", "pie"
            )
            subtype = payload.get("config", {}).get(
                "display.visualizations.custom.viz_tutorial_app.betterpdf.chartsubtype", "none"
            )

            # Transform records and generate chart
            chart = transform_records(records, charttype, subtype)

            # Serialize chart to SVG
            chart_svg = serialize_chart(chart, output_format="svg")

            # Set response headers
            self.response.setHeader(
                "content-disposition",
                'inline; filename="tmpchart.svg"',
            )
            self.response.setHeader("content-type", "image/svg+xml")
            self.response.setHeader("cache-control", "max-age=0, must-revalidate")

            # Write SVG to response
            self.response.write(chart_svg)
            self.response.setStatus(200)
            logger.info("Served SVG chart successfully.")

        except ValueError as ve:
            # Handle unsupported chart types
            error_svg = generate_error_svg(str(ve))
            self.response.setHeader("content-type", "image/svg+xml")
            self.response.write(error_svg)
            self.response.setStatus(400)
            logger.error(f"Chart generation error: {ve}")

        except Exception as e:
            # Handle other exceptions
            error_svg = generate_error_svg("An unexpected error occurred while generating the chart.")
            self.response.setHeader("content-type", "image/svg+xml")
            self.response.write(error_svg)
            self.response.setStatus(500)
            logger.error(f"Unexpected error: {e}")

    def handle_get_request(self, pdf: MyPDF, license_info: Dict[str, Any]):
        """Handle GET requests."""
        try:
            query = self.request.get("query", {})
            if "chart" in query:
                chart_type = query.get("chart")
                subtype = query.get("subtype", "none")
                records = self.fetch_records(query)
                
                # Transform records and generate chart
                chart = transform_records(records, chart_type, subtype)

                # Determine output format
                output_format = "svg"
                if "png" in query:
                    output_format = "png"

                # Serialize chart
                serialized_chart = serialize_chart(chart, output_format=output_format)

                # Set response headers
                if output_format == "svg":
                    content_type = "image/svg+xml"
                    disposition = 'inline; filename="chart.svg"'
                elif output_format == "png":
                    content_type = "image/png"
                    disposition = 'inline; filename="chart.png"'

                self.response.setHeader("content-disposition", disposition)
                self.response.setHeader("content-type", content_type)
                self.response.setHeader("cache-control", "max-age=0, must-revalidate")

                # Write chart to response
                self.response.write(serialized_chart)
                self.response.setStatus(200)
                logger.info(f"Served {chart_type} chart successfully.")

            elif "table" in query:
                records = self.fetch_records(query)
                fields = self.get_fields(records)
                create_search_results_page(pdf, records, fields)
                # Serialize PDF
                pdf_output = pdf.output(dest='S').encode('latin1')  # dest='S' returns string
                # Set response headers
                self.response.setHeader(
                    "content-disposition",
                    'inline; filename="table.pdf"',
                )
                self.response.setHeader("content-type", "application/pdf")
                self.response.setHeader("cache-control", "max-age=0, must-revalidate")
                # Write PDF to response
                self.response.write(pdf_output)
                self.response.setStatus(200)
                logger.info("Served PDF table successfully.")

            else:
                # Handle other GET request scenarios
                self._respond()
        except Exception as e:
            stack_trace_html = generate_error_svg(str(e))
            self.response.setHeader("content-type", "image/svg+xml")
            self.response.write(stack_trace_html)
            self.response.setStatus(500)
            logger.error(f"GET request handling failed: {e}")

    def fetch_records(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch records based on the query parameters."""
        # This function should implement fetching records from Splunk based on the query
        # Placeholder implementation
        return []

    def get_fields(self, records: List[Dict[str, Any]]) -> List[str]:
        """Extract field names from records."""
        if not records:
            return []
        return list(records[0].keys())

    def respond_with_error(self, message: str, exception: Exception):
        """Respond with an error message."""
        error_svg = generate_error_svg(message)
        self.response.setHeader("content-type", "image/svg+xml")
        self.response.write(error_svg)
        self.response.setStatus(400)
        logger.error(f"Responded with error: {message} Exception: {exception}")

    def _initialize(self) -> bool:
        """Initialize global settings."""
        logger.info("Initializing betterpdfHandler.")
        return True

    def _respond(self):
        """Legacy method from the sample; no operation."""
        logger.info("Handling response.")
        return True

def set_chart_style(style: str):
    """Set chart style from configuration."""
    from pygal.style import (
        DefaultStyle, LightStyle, DarkStyle, NeonStyle, DarkSolarizedStyle,
        LightSolarizedStyle, CleanStyle, RedBlueStyle, DarkColorizedStyle,
        LightColorizedStyle, TurquoiseStyle, LightGreenStyle, DarkGreenStyle,
        DarkGreenBlueStyle, BlueStyle
    )

    style_mapping = {
        "custom_style": CUSTOM_STYLE,
        "defaultstyle": DefaultStyle,
        "lightstyle": LightStyle,
        "darkstyle": DarkStyle,
        "neonstyle": NeonStyle,
        "darksolarizedstyle": DarkSolarizedStyle,
        "lightsolarizedstyle": LightSolarizedStyle,
        "cleanstyle": CleanStyle,
        "redbluestyle": RedBlueStyle,
        "darkcolorizedstyle": DarkColorizedStyle,
        "lightcolorizedstyle": LightColorizedStyle,
        "turquoisestyle": TurquoiseStyle,
        "lightgreenstyle": LightGreenStyle,
        "darkgreenstyle": DarkGreenStyle,
        "darkgreenbluestyle": DarkGreenBlueStyle,
        "bluestyle": BlueStyle,
    }

    selected_style = style_mapping.get(style.lower())
    if selected_style:
        chartconfig.style = selected_style
        logger.info(f"Chart style set to {style}.")
    else:
        logger.warning(f"Style '{style}' not recognized. Using default style.")

def remove_temp_files(sid: str):
    """Remove temporary files associated with a SID."""
    logger.info(f"Cleaning up temp files for SID: {sid}")
    for ext in ['.pdf', '.svg', '.png']:
        temp_file = f"{sid}{ext}"
        try:
            Path(temp_file).unlink()
            logger.debug(f"Removed temporary file: {temp_file}")
        except FileNotFoundError:
            logger.debug(f"Temporary file not found, skipping: {temp_file}")
