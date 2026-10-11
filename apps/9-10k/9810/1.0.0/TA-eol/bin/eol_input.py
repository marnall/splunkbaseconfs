#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import os
import logging
from logging.handlers import RotatingFileHandler
import traceback

def setup_logging():
    splunk_home = os.environ.get('SPLUNK_HOME')
    if splunk_home:
        log_dir = os.path.join(splunk_home, 'var', 'log', 'splunk')
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = app_dir

    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception:
            pass

    log_file = os.path.join(log_dir, 'ta_eol.log')
    logger = logging.getLogger('ta_eol')
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        try:
            handler = RotatingFileHandler(log_file, maxBytes=5000000, backupCount=5, encoding='utf-8')
        except Exception:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_file = os.path.join(app_dir, 'ta_eol.log')
            handler = RotatingFileHandler(log_file, maxBytes=5000000, backupCount=5, encoding='utf-8')
        
        formatter = logging.Formatter('%(asctime)s %(levelname)s pid=%(process)d line=%(lineno)d - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logging()

def log_error(msg):
    logger.error(msg, stacklevel=2)
    sys.stderr.write("ERROR EolInput: %s\n" % msg)
    sys.stderr.flush()

def log_info(msg):
    logger.info(msg, stacklevel=2)
    sys.stderr.write("INFO EolInput: %s\n" % msg)
    sys.stderr.flush()

def do_scheme():
    scheme_xml = """<scheme>
  <title>End of Life Tracker Input</title>
  <description>Fetches product lifecycle and EOL dates from endoflife.date API.</description>
  <use_external_validation>false</use_external_validation>
  <use_single_instance>false</use_single_instance>
  <streaming_mode>xml</streaming_mode>
  <endpoint>
    <args>
      <arg name="product">
        <title>Product Name</title>
        <description>The product name as recognized by endoflife.date (e.g. ubuntu, python).</description>
        <required_on_create>true</required_on_create>
        <required_on_edit>true</required_on_edit>
      </arg>
    </args>
  </endpoint>
</scheme>"""
    sys.stdout.write(scheme_xml)
    sys.stdout.flush()

def get_config():
    config = {}
    try:
        xml_str = sys.stdin.read()
        if not xml_str:
            return config
        
        root = ET.fromstring(xml_str)
        conf_node = root.find("configuration")
        if conf_node is not None:
            stanzas = conf_node.findall("stanza")
            for stanza in stanzas:
                stanza_name = stanza.get("name")
                name = stanza_name
                if "://" in stanza_name:
                    name = stanza_name.split("://")[1]
                
                params = {}
                for param in stanza.findall("param"):
                    params[param.get("name")] = param.text
                
                if 'product' not in params:
                    params['product'] = name
                config[stanza_name] = params
    except Exception as e:
        log_error("Error parsing XML config from stdin: %s. Traceback: %s" % (str(e), traceback.format_exc()))
    return config

def write_event(event_data, sourcetype, product):
    data_str = json.dumps(event_data)
    # Escape ]]> to prevent CDATA breakout
    data_str = data_str.replace("]]>", "]]]]><![CDATA[>")
    event_xml = """  <event>
    <data><![CDATA[%s]]></data>
    <sourcetype>%s</sourcetype>
    <source>eol_input://%s</source>
  </event>\n""" % (data_str, sourcetype, escape(product))
    sys.stdout.write(event_xml)
    sys.stdout.flush()

def run_input():
    config = get_config()
    if not config:
        return

    # Start the stream
    sys.stdout.write("<stream>\n")
    sys.stdout.flush()
    
    ctx = ssl.create_default_context()
    # ctx.check_hostname = False
    # ctx.verify_mode = ssl.CERT_NONE

    for stanza_name, params in config.items():
        product = params.get("product")
        if not product:
            continue
            
        log_info("Fetching data for product: %s" % product)
        url = "https://endoflife.date/api/v1/products/%s" % urllib.parse.quote(product.strip())
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Splunk EOL App (Mozilla/5.0)'})
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    parsed = json.loads(data)
                    
                    # Ensure schema is what we expect
                    result_data = parsed.get("result", {})
                    if not result_data or not isinstance(result_data, dict):
                        log_error("Invalid API response format for product %s" % product)
                        continue
                        
                    product_name = result_data.get('name', product)
                    product_label = result_data.get('label', product_name.capitalize())
                    releases = result_data.get('releases', [])
                    
                    # 1. Output summary event
                    summary_event = {
                        "product": product_name,
                        "label": product_label,
                        "category": result_data.get("category"),
                        "tags": result_data.get("tags"),
                        "total_releases": len(releases),
                        "last_modified": parsed.get("last_modified"),
                        "generated_at": parsed.get("generated_at")
                    }
                    write_event(summary_event, "eol:product:summary", product_name)
                    
                    # 2. Output event for each release cycle
                    for r in releases:
                        rel_event = {
                            "product": product_name,
                            "product_label": product_label,
                            "cycle": r.get("name"),
                            "codename": r.get("codename"),
                            "releaseDate": r.get("releaseDate"),
                            "isLts": r.get("isLts"),
                            "isEol": r.get("isEol"),
                            "eolFrom": r.get("eolFrom"),
                            "isMaintained": r.get("isMaintained"),
                            "latest": r.get("latest")
                        }
                        write_event(rel_event, "eol:product:release", product_name)
                    log_info("Successfully wrote %d events for product '%s'" % (len(releases) + 1, product_name))
                else:
                    log_error("Received HTTP %d status when fetching %s" % (response.status, product))
        except urllib.error.HTTPError as e:
            log_error("HTTP Error %d fetching product %s: %s. Traceback: %s" % (e.code, product, str(e), traceback.format_exc()))
        except Exception as e:
            log_error("Error fetching product %s: %s. Traceback: %s" % (product, str(e), traceback.format_exc()))

    # End the stream
    sys.stdout.write("</stream>\n")
    sys.stdout.flush()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            sys.exit(0)
        else:
            log_error("Invalid argument: %s" % sys.argv[1])
            sys.exit(1)
    else:
        run_input()
