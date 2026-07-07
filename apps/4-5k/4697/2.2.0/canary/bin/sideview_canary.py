# -*- coding: utf-8 -*-
#Copyright (C) 2010-2026 Sideview LLC.  All Rights Reserved.
"""
    this contains various functions and classes used by canary endpoints and search commands.
"""
import datetime
try:
    from tzlocal import get_localzone_name
except ImportError:
    # at runtime the code will fall through to get_current_tz_abbreviation
    pass

import logging
import re
import os
import xml.dom.minidom

import copy
import json
import sys
import traceback
from collections import OrderedDict
import lxml.etree as et
from mako import exceptions
from mako.lookup import TemplateLookup
from canary_util import simplecache




APP = "canary"
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
EAI_DATA_KEY = "eai:data"
EAI_TYPE_KEY = "eai:type"
SHOW_WARNINGS = False

if SPLUNK_HOME:
    import splunk
    import splunk.rest as rest
    import splunk.entity as en
    from splunk.clilib import bundle_paths
    ETC_APPS_DIR = bundle_paths.get_base_path()
else:
    import flask

assert(sys.version_info.major >= 3)
import yaml as yaml
from urllib.parse import quote
# we used to ship both a "yaml2" and a "yaml3".
# eg:
#elif sys.version_info.major == 2:
#    import yaml2 as yaml
#    from urllib import quote

if SPLUNK_HOME:
    class ResourceNotFound(splunk.ResourceNotFound):
        pass
else:
    class ResourceNotFound(Exception):
        pass

MAKO_TEMPLATE_LOOKUP = None
def set_mako_template_dirs(app_path):
    """ should be called basically once and only once """
    global MAKO_TEMPLATE_LOOKUP
    MAKO_TEMPLATE_LOOKUP = TemplateLookup(
        input_encoding='utf-8',
        directories=[os.path.join(app_path, "appserver", "templates"),
                     os.path.join(app_path, "appserver", "static", "lib"),]
    )

if SPLUNK_HOME:
    set_mako_template_dirs(os.path.join(SPLUNK_HOME, "etc", "apps", APP))

#TODO - migrate resultsAreaLeft to resultsArea,  and what about "sidebar"
LEGAL_LAYOUT_PANELS = ["appHeader", "navigationHeader", "messaging", "viewHeader", "mainSearchControls", "graphArea", "pageControls", "resultsHeaderPanel", "resultsAreaLeft", "viewFooter", "appFooter"]

HIERARCHY_DIRECTIVES = ["requiresDownstreamModules", "forbidsDownstreamModules", "requiresUpstreamModules", "forbidsUpstreamModules"]

MODULE_ATTRIBUTE_RE = re.compile(r"(\s+)<module ([^/>]+)(/)?>(.+)?")
CDATA_SPACE_BUG_RE = re.compile(r"(.+)?(]]>)(\s+)(</param>)(.?)")
DASHBOARD_PANEL_RE = re.compile(r"panel_row(\d+)_col(\d+)(?:_grp(\d+))?")
ALL_SLASHES_RE = re.compile(r"[/\\\\]")
DEFAULT_LAYOUT_PANEL = "panel_row1_col1"
BLANK_VIEW_XML = """<?xml version="1.0" ?>
<view><label>New View</label>

  <module name="TopNav" layoutPanel="appHeader" />

  <module name="AppNav" layoutPanel="appHeader" />

  <module name="HTML" layoutPanel="viewHeader">
    <param name="html"><![CDATA[
    <h1>Placeholder Page Title</h1>
    ]]></param>
  </module>

  <module name="Search" layoutPanel="panel_row1_col1">
    <param name="search"><![CDATA[
      | eventcount summarize=false index=* | search count>0 | fields index server count
    ]]></param>

    <module name="Pager">

      <module name="Table"/>
    </module>
  </module>
</view>
"""

if SPLUNK_HOME:
    BASE_DIR = os.path.abspath(bundle_paths.get_base_path())
INVALID_PANEL_MESSAGE = "layoutPanel \"%s\" is not a valid layoutPanel value. %s"

# view cache has an invalidation strategy, but.... xml files edited on disk are a problem atm
# at least until there's a page and/or the FreshMaker can invalidate the cache.
VIEW_CACHE_TIME = datetime.timedelta(seconds=60)
view_cache = simplecache.create_cache("viewcache", VIEW_CACHE_TIME)

# No TTL — pattern files only change during development. Use kill=1 to flush.
_pattern_xml_cache = {}

# No TTL — nav XML rarely changes in production. Use kill=1 to flush.
_nav_xml_cache = {}

_NAV_SHUNT_RE = re.compile(
    r'(?:\.\.\/\.\.\/|/)splunkd/__raw/(?:services/)?(.+?)_shunt\?view=([^&]+)', re.I
)
_NAV_MANAGER_RE = re.compile(r'^\.\./\.\./(?P<rest>manager.*)')
_NAV_KNOWN_LABELS = {"home": "Home", "home_redirect": "Home", "search": "Splunk Search"}


def _get_nav_xml(session_key, app):
    if app in _nav_xml_cache:
        return _nav_xml_cache[app]
    try:
        uri = "/servicesNS/nobody/%s/data/ui/nav/default" % app
        content = get_single_rest_api_entry(uri, session_key=session_key)
        xml_str = content.get("eai:data", "")
        _nav_xml_cache[app] = xml_str
        return xml_str
    except Exception:
        logger.warning("Could not fetch nav XML for app %s", app)
        return None


def _rewrite_nav_href(href, current_app, locale, root_endpoint):
    if not href:
        return "#"
    m = _NAV_MANAGER_RE.match(href)
    if m:
        prefix = root_endpoint + "/" + locale + "/" if locale else root_endpoint + "/"
        return prefix + m.group("rest")
    m = _NAV_SHUNT_RE.search(href)
    if m:
        app, view = m.group(1), m.group(2)
        return view if app == current_app else "../%s/%s" % (app, view)
    if href.startswith("/"):
        return root_endpoint + href
    return href


def _render_nav_items(parent_el, buf, app, locale, root_endpoint, top_level=False):
    for item in parent_el:
        tag = item.tag
        if not isinstance(tag, str):
            continue

        if tag == "divider":
            buf.append('<li><div class="divider"></div></li>')

        elif tag == "a":
            href = _rewrite_nav_href(item.get("href", ""), app, locale, root_endpoint)
            label = et.tostring(item, method="text", encoding="unicode").strip()
            ext = ' class="externalLink" target="_blank"' if "http" in href else ""
            top = " topLevel" if top_level else ""
            buf.append('<li class="%s"><a href="%s"%s><span>%s</span></a></li>' % (
                top.strip(), href, ext, label))

        elif tag == "view":
            name = item.get("name", "")
            source = item.get("source", "")
            if source == "unclassified":
                buf.append('<li class="sv-nav-placeholder sv-nav-views-placeholder"></li>')
            else:
                if name == "home_redirect":
                    name = "home"
                label = _NAV_KNOWN_LABELS.get(name, name)
                top = "topLevel" if top_level else ""
                buf.append('<li class="%s"><a href="%s"><span>%s</span></a></li>' % (
                    top, name, label))

        elif tag == "saved":
            buf.append('<li class="sv-nav-placeholder sv-nav-saved-placeholder"></li>')

        elif tag == "collection":
            label = item.get("label", "")
            sub = []
            _render_nav_items(item, sub, app, locale, root_endpoint, top_level=False)
            sub_html = "<ul>%s</ul>" % "".join(sub)
            top = "topLevel " if top_level else ""
            buf.append(
                '<li class="%shasSubMenu"><a class="hasSubMenu" href="#">'
                '<span>%s</span><span class="arrow"> </span></a>%s</li>' % (top, label, sub_html)
            )


def render_nav_html(session_key, app, locale, root_endpoint):
    """Return a pre-rendered <ul class="svMenu"> string for the given app's nav,
    or None if the nav XML can't be fetched. Dynamic slots get Loading placeholders."""
    xml_str = _get_nav_xml(session_key, app)
    if not xml_str:
        return None
    try:
        parser = et.XMLParser(remove_blank_text=True, strip_cdata=False)
        nav_el = et.fromstring(xml_str.encode("utf-8"), parser)
    except Exception:
        logger.warning("Could not parse nav XML for app %s", app)
        return None
    buf = ['<ul class="svMenu">']
    _render_nav_items(nav_el, buf, app, locale, root_endpoint, top_level=True)
    buf.append("</ul>")
    return "\n".join(buf)


def inject_nav_html_if_needed(view_dict, session_key, app, locale, root_endpoint):
    """If the view contains an AppNav module, pre-render the nav HTML and attach
    it to that module's dict so AppNav.html can output it directly."""
    for mod in view_dict.get("modules", []):
        if mod.get("module") == "AppNav":
            mod["navHTML"] = render_nav_html(session_key, app, locale, root_endpoint)
            return


class PatternNotFoundError(Exception):
    """Exception raised when there is no Pattern in the app matching a given name """
    pass

class IncludeFileNotFoundError(Exception):
    """Exception raised when there is no external include file  found in the app matching a given name """
    pass

def setup_logging(log_level):
    """ This will log to a file in Splunk's var/log/splunk  directory.  The log
    will get rotated and it will also get indexed automatically into index=_internal
    """
    if not SPLUNK_HOME:
        logger = logging.getLogger(APP)
        logger.setLevel(log_level)
        return logger
    LOG_FILE_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", APP + ".log")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    our_logger = logging.getLogger(APP)
    if not our_logger.handlers:
        our_logger.propagate = False
        our_logger.setLevel(log_level)
        handler = logging.handlers.RotatingFileHandler(LOG_FILE_PATH, mode="a")
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        our_logger.addHandler(handler)
    return our_logger

logger = setup_logging(logging.DEBUG)


def fixed_writexml(self, writer, indent="", addindent="", newl=""):
    """ patches minidom's writexml method, so it doesnt add tons of whitespace."""
    writer.write(indent+"<" + self.tagName)

    attrs = self._get_attributes()
    a_names = attrs.keys()
    a_names.sort()

    for a_name in a_names:
        writer.write(" %s=\"" % a_name)
        xml.dom.minidom._write_data(writer, attrs[a_name].value)
        writer.write("\"")
    if self.child_nodes:
        if len(self.child_nodes) == 1 \
          and self.child_nodes[0].nodeType == xml.dom.minidom.Node.TEXT_NODE:
            writer.write(">")
            self.child_nodes[0].writexml(writer, "", "", "")
            newl = ""
            writer.write("</%s>%s" % (self.tagName, newl))
            return
        newl = ""
        writer.write(">%s"%(newl))
        for node in self.child_nodes:
            newl = ""
            node.writexml(writer, indent+addindent, addindent, newl)
        newl = ""
        writer.write("%s</%s>%s" % (indent, self.tagName, newl))
    else:
        newl = ""
        writer.write("/>%s"%(newl))

# replace minidom's function with ours
xml.dom.minidom.Element.writexml = fixed_writexml


def patch_xml_for_readability(pretty_xml):
    """
    implements a fairly simple list of cleanups that together improve the
    readability of the XML.
    """

    def attribute_sorter(whole_attribute):
        sort_orders = {
            "name":0,
            "layoutPanel":10,
            "group":20,
            "autoRun":99
        }

        if whole_attribute.find("="):
            order = sort_orders.get(whole_attribute.split("=")[0], 50)
            return str(order)
        return whole_attribute

    lines = pretty_xml.decode().split("\n")
    for i, _line in enumerate(lines):
        ## take off lame whitespace that gets stuck on the end.
        lines[i] = lines[i].rstrip()

        ## reorder the module attributes...
        module_tag_match = re.match(MODULE_ATTRIBUTE_RE, lines[i])
        if module_tag_match:
            whitespace = module_tag_match.group(1)
            att_str = module_tag_match.group(2)
            end_slash = module_tag_match.group(3)
            junk = module_tag_match.group(4)

            attributes = sorted(att_str.split(" "), key=attribute_sorter)
            line = []
            if whitespace:
                line.append(whitespace)
            line.append("<module ")
            line.append(" ".join(attributes))
            if end_slash:
                line.append(" " + end_slash)
            line.append(">")
            if junk:
                line.append(junk)
            lines[i] = "".join(line)

        # add newlines in front of every opening module tag.
        if lines[i].lstrip().find("<module") == 0:
            lines[i] = "\n"+lines[i]

        # fix the problematic spaces that get injected between closing
        # CDATA blocks and closing tags.
        if re.match(CDATA_SPACE_BUG_RE, lines[i]):
            lines[i] = re.sub(CDATA_SPACE_BUG_RE, r"\1\2\4\5", lines[i])

    return "\n".join(lines)



def get_text(node):
    """
    helper function to just grab all the normal text content out of a node
    """
    segments = []
    for child_node in node.child_nodes:
        if child_node.nodeType == child_node.TEXT_NODE:
            segments.append(child_node.data)
        if child_node.nodeType == child_node.CDATA_SECTION_NODE:
            segments.append(child_node.data)
    return ''.join(segments)



def get_commands(spl):
    """
    given an SPL expression, this will parse it and return an array of the command names.
    Note that it treats entire subsearch expressions just as big weird tokens, ignoring all
    the commands within.
    So in other words it gets the "top level" commands only.
    """
    commands = []
    if not spl:
        return []
    i = 0
    inside_quotes = False
    bracket_depth = 0

    while i < len(spl):
        c = spl[i]
        if c == "\\":
            i += 2
            continue
        elif inside_quotes:
            if c == "\"":
                inside_quotes = False
        elif c == "\"":
            inside_quotes = True
        elif c == "[":
            bracket_depth += 1
        elif c == "]":
            # malformed
            if bracket_depth <= 0:
                return []
            bracket_depth = bracket_depth - 1
        elif c == "|" and bracket_depth == 0:
            commands.append(spl[:i].strip())
            spl = spl[i+1: len(spl)]
            i = 0
            continue
        i += 1
    if inside_quotes:
        raise ValueError("unbalanced quotes on search expression.")
    elif bracket_depth != 0:
        raise ValueError("unbalanced brackets on search expression.")
    commands.append(spl.strip())
    return commands


def log_activity(request, description):
    """ standard function to write a descriptive event to canary.log.  Writes out the given
        description and then the  main keys from the request instance"""
    if hasattr(request, "action") and request.action:
        description += " action=\"%s\"" % request.action
    logger.info("%s app=\"%s\" view=\"%s\" user=\"%s\" locale=\"%s\" method=\"%s\"",
                description, request.app, request.view, request.user_name, request.locale,
                request.method)


def migrate_field_picker(module_node, warnings, infos):
    """ super weird - but very limited migration.
    The FieldPicker module expects to get events!  and it gets the
    field names off those rows.
    the Fields module expects to get N rows where each row has a field
    called "field"
    so... this migration sneaks up to the Search module and rewrites
    the SPL that sideview's apps always have there.
    what could go wrong?
    """
    rename_module_to(module_node, "Fields")
    hidden_fields_param = et.SubElement(module_node, "param")
    hidden_fields_param.set("name", "hiddenFields")
    hidden_fields_param.text = "_time"
    module_node.append(hidden_fields_param)

    parent_module = module_node.getparent()
    if parent_module.get("name") == "Search":
        search_param = parent_module.find("./param[@name='search']")
        if search_param is not None:
            spl = search_param.text
            try:
                spl = re.sub(r'(?is)foo NOT foo \| append \[\r?\n?\s+', '', spl)
                spl = re.sub(r'(?is)\s+\| eval foobar="1"\s+\| chart count over foobar by field limit=500\r?\n?\s+\|\sfields - foobar\r?\n?\]\s?\r?\n\| eval _time=0', '', spl)

                search_param.text = spl
                infos.append("in replacing FieldPicker with Fields, we actually rewrote your SPL to match the difference in conventions, and somewhat surprisingly this seems to have worked.")
            except Exception:
                warnings.append("we tried to rewrite the SPL that was feeding the FieldPicker module so that it would match the conventions for the new Fields module but this failed so we did nothing.")

def convert_count_module_to_pulldown(module_node, warnings):
    """ neither SVU nor Canary has a special Count module and instead you're supposed
    to just use a Pulldown. This method attempts to make a generic Pulldown to replace your 'Count'"""
    rename_param_to(module_node, "options", "staticOptions", infos)
    options_param = module_node.find("./param[@name='staticOptions']")
    for node in options_param.findall("list//param[@text]"):
        node.set("name", "label")
    rename_module_to(module_node, "Pulldown")

    name_param = et.SubElement(module_node, "param")
    name_param.set("name", "name")
    name_param.text = "results.count"
    module_node.append(name_param)
    warnings.append("We converted a Count module to a standard Pulldown module.")


def remove_all_params(module_node):
    """kill them all please"""
    for param in module_node.findall("param"):
        module_node.remove(param)

def remove_param(module_node, unwanted_param_names, warnings, suggestion=""):
    """removes any params bearing the given names. If any are found, it writes a warning about it """
    if isinstance(unwanted_param_names, str):
        unwanted_param_names = [unwanted_param_names]
    for param in module_node.findall("param"):
        param_name = param.get("name")
        if param_name in unwanted_param_names:
            module_node.remove(param)
            if warnings:
                warning_text = "%s's %s param has been discarded. %s" % (module_node.get("name"), param_name, suggestion)
                warnings.append(warning_text)

def rename_param_to(module_node, old_name, new_name, message_queue=None):
    """renames the given param name and writes a warning"""
    for param in module_node.findall("param"):
        if param.get("name") == old_name:
            param.set("name", new_name)
            if message_queue:
                message_text = "%s's %s param has been renamed to %s" % (module_node.get("name"), old_name, new_name)
                message_queue.append(message_text)
            return

def set_param_value(module_node, param_name, new_value):
    """ set the given param to the new value.
    NOTE - this only works on simple text params. """
    for param in module_node.findall("param"):
        if param.get("name") == param_name:
            param.text = new_value
            return


def rename_module_to(module_node, new_name):
    """self-explanatory really"""
    module_node.set("name", new_name)


def get_param_value(module_node, given_param_name):
    for param in module_node.findall("param"):
        param_name = param.get("name")
        if param_name == given_param_name:
            return param.text
    return None

def param_has_value(module_node, given_param_name, values, case_sensitive_match=True):
    """checks whether the given param has any of the given values. case-sensitive by default."""
    if not case_sensitive_match:
        values = [x.lower() for x in values]
    param_value = get_param_value(module_node, given_param_name)
    if not param_value:
        return False
    if not case_sensitive_match:
        param_value = param_value.lower()
    return param_value in values

def fix_sloppy_boolean_param_values(module_node, param_names):
    for param_name in param_names:
        param_value = get_param_value(module_node, param_name)
        if not param_value:
            continue

        if param_value.lower() == "true":
            set_param_value(module_node, param_name, "True")
        elif param_value.lower() == "false":
            set_param_value(module_node, param_name, "False")



def convert_svu_custom_css_and_js(view_element, warnings, infos, app):
    """airlift out any customStylesheet or customJavascript params"""
    sideview_utils_module = view_element.find("./module[@name='SideviewUtils']")
    if sideview_utils_module is None:
        return

    for param in sideview_utils_module.findall("param"):
        param_name = param.get("name")
        if param_name in ["customStylesheet", "customJavascript"]:
            if not param.text:
                continue
            param_uri = param.text
            param_uri_segments = param_uri.split("/")
            if len(param_uri_segments) > 1:
                app_in_uri = param_uri_segments[0]
                if app and app != app_in_uri:
                    warnings.append("the %s param on the view tag specifies %s but Canary can only include resources from the same app." % (param_name, param_uri))
                # its only get_view_type that does this, and we really dont care.
                #elif not app:
                #    logger.warning("we see a %s param of %s and although we're not sure whether this is our app or not, we are choosing not to care " % (param_name, param_uri))
                param_uri = param_uri_segments[1]

            new_uri = [param_uri]

            new_attribute_name = "js"
            if param_name == "customStylesheet":
                new_attribute_name = "css"
                if view_element.get("css"):
                    new_uri = new_uri + [view_element.get("css")]
            infos.append("the value of the %s param on the SideviewUtils module was moved to be the value of the %s key on the view itself." % (param_name, new_attribute_name))
            view_element.set(new_attribute_name, ",".join(new_uri))


def final_inspection(view_element, module_conf):
    warnings = []
    for module_node in view_element.iter("module"):
        module_name = module_node.get("name")
        if module_name == "SearchBar":
            warnings.append("We can not migrate the legacy SearchBar module. Technically a combination of TextField, TimePicker and Search module might work, with some custom CSS")
        elif module_name == "Export":
            warnings.append("Export module - technically this can be manually replaced with a SearchControls module configured to have only the export icon")
        elif module_name == "SingleValue":
            warnings.append("SingleValue can typically be replaced by an HTML module with some effort, but this cannot be migrated automatically")
        elif module_name in ["RowNumbers", "SoftWrap"]:
            warnings.append("%s is a legacy Splunk module. It should be possible for you to manually replace this with a Checkbox module" % module_name)
        elif module_name in ["MaxLines"]:
            warnings.append("%s is a legacy Splunk module. It should be possible for you to manually replace this with a Pulldown module" % module_name)
        elif module_name == "ConditionalSwitcher":
            warnings.append("%s is a legacy Splunk module. It can be manually converted using a Switcher module and some customBehavior but this cannot be migrated automatically." % module_name)
        elif module_name != "Switcher" and module_name.endswith("Switcher"):
            first_part = module_name.replace("Switcher", "")
            if first_part in ["Tab", "Link", "Pulldown", "Button"]:
                warnings.append("%s is a legacy Splunk module. It should be possible to manually replace this with a Switcher plus a %s module but this cannot be migrated automatically." % (module_name, first_part))
        elif module_name in ["ReportType", "ReportSubType", "StatChooser", "SingleFieldChooser", "TimeRangeBinning"]:
            warnings.append(module_name + " is a legacy Splunk module and can not be migrated. It's unlikely this module still works, or that this view is used by anyone.")
        else:
            canary_module = module_conf.get(module_name, False)
            if not canary_module:
                if module_name in DEAD_SIDEVIEW_UTILS_MODULES:
                    warnings.append("We can not migrate the old Sideview %s module. This was technically never more than a prototype." % module_name)
                elif module_name in LEGACY_SPLUNK_MODULES:
                    warnings.append(module_name + " is a legacy Splunk module that we cannot migrate.")
                else:
                    warnings.append(module_name + " seems to be some unknown third-party module that we cannot migrate.")
    return warnings

def replace_bad_modules(view_element, module_conf, app=False):
    """This is basically the main migration - returns a "cleaned" version of the view"""
    warnings = []
    infos = []


    replacements = {
        "AccountBar": "TopNav",
        "AppBar": "AppNav",
        "FlashChart": "Chart",
        "FlashTimeline": "Timeline",
        "HiddenPostProcess": "PostProcess",
        "HiddenSearch": "Search",
        "JobProgressIndicator": "ProgressIndicator",
        "JobSpinner": "ProgressIndicator",
        "JSChart": "Chart",
        "NullModule": "CustomBehavior",
        "Paginator": "Pager",
        "ServerSideInclude": "HTML",
        "SimpleResultsTable": "Table"
    }

    # TODO: y no EventsViewer: Events ?

    convert_svu_custom_css_and_js(view_element, warnings, infos, app)

    for module_node in view_element.iter("module"):
        module_name = module_node.get("name")
        if module_name in replacements:
            new_module_name = replacements.get(module_name)
            module_node.set("name", new_module_name)
            infos.append("replaced %s with %s" % (module_name, new_module_name))

    for module_node in view_element.iter("module"):
        module_name = module_node.get("name")

        # :facepalm: axml was forgiving of this. we are not but we will convert it.
        if module_name.strip() != module_name:
            module_name = module_name.strip()
            module_node.set("name", module_name)


        # these are vestigial from some long gone splunk version but they have persisted in some
        # advanced xml out there.
        remove_param(module_node, "groupLabel", warnings)

        if module_name == "SearchControls":
            remove_param(module_node, ["saveMenu", "createMenu"], warnings)
            sections_param = module_node.find("./param[@name='sections']")
            if sections_param is not None:
                old_sections_value = sections_param.text
                new_sections_value = old_sections_value.replace(" saveMenu", "").replace(" createMenu", "")
                if old_sections_value != new_sections_value:
                    sections_param.text = new_sections_value
                    infos.append("we saw the 'saveMenu' and 'createMenu' param values from Sideview Utils but the Canary SearchControls module doesn't provide that so we removed them.")

        if module_name == "JobStatus":
            rename_module_to(module_node, "SearchControls")
            remove_all_params(module_node)
            warnings.append("We replaced a JobStatus module with a bare SearchControls module. This will almost certainly be a change in functionality (although it might be an improvement).")

        if module_name == "FieldPicker":
            migrate_field_picker(module_node, warnings, infos)

        if module_name == "SubmitButton":
            rename_module_to(module_node, "Button")
            remove_param(module_node, "updatePermalink", warnings, "This would need to be manually converted to a use of URLLoader")
            remove_param(module_node, "visible", warnings)
            fix_sloppy_boolean_param_values(module_node, ["allowSoftSubmit"])

        if module_name == "Button":
            fix_sloppy_boolean_param_values(module_node, ["allowSoftSubmit"])



        # checking to see if straight replacement of FlashTimeline
        # left a height or width param in there.
        if module_name == "Timeline":
            remove_param(module_node, ["height", "width"], warnings)

        # checking to see if straight replacement of FlashChart/JSChart
        # left a drilldownPrefix param in there.
        if module_name == "Chart":
            remove_param(module_node, "maxRowsForTop", warnings)
            rename_param_to(module_node, "drilldownPrefix", "name", infos)

            fix_sloppy_boolean_param_values(module_node, ["enableResize"])


            #remove_param(module_node, "width", warnings, "Chart module replaces FlashChart/JSChart but does not have a width param and width is always effectively 100%")

        # nope. nope. nope.
        # we are booting ConvertToIntention and all its params. It's way too ugly to live.
        # all of its child modules are added to its parents...
        # some of the resulting view may work. Some of it will likely not.
        if module_name == "ConvertToIntention":
            for param in module_node.findall("param"):
                module_node.remove(param)
            for child in module_node.findall("module"):
                module_node.remove(child)
                module_node.getparent().append(child)
            module_node.getparent().remove(module_node)
            warnings.append("ConvertToIntention is not supported in Canary and never will be. Rewrite this view to use Sideview's Search module instead of Splunk's HiddenSearch.")

        # checking to see if straight replacement of SimpleResultsTable
        # left various dead params in there
        if module_name == "Table":
            remove_param(module_node, ["displayRowNumbers", "entityName"], warnings)
            rename_param_to(module_node, "drilldownPrefix", "name", infos)

            if param_has_value(module_node, "drilldown", "none"):
                remove_param(module_node, "drilldown", warnings)

        # checking to see if straight replacement left Paginator's
        # weirder entityName values orphaned
        if module_name == "Pager":
            if param_has_value(module_node, "entityName", ["settings", "auto", "results"]):
                remove_param(module_node, "entityName", warnings)

        # checking to see if straight replacement left either of HiddenSearch's
        # legacy params as orphans
        if module_name == "Search":
            remove_param(module_node, ["maxCount", "maxEvents"], warnings)

        if module_name == "HiddenSavedSearch":
            rename_module_to(module_node, "SavedSearch")
            infos.append("HiddenSavedSearch module was replaced by SavedSearch.")
            rename_param_to(module_node, "savedSearch", "name")
            history_value = get_param_value(module_node, "useHistory")
            if history_value is None or history_value == "None":
                set_param_value(module_node, "useHistory", "Auto")
                warnings.append("HiddenSavedSearch module had a weird usehistory param of %s but we replaced this with \"Auto\"." % history_value)
            else:
                fix_sloppy_boolean_param_values(module_node, ["useHistory"])


        if module_name == "TimeRangePicker":
            rename_module_to(module_node, "TimePicker")
            rename_param_to(module_node, "selected", "default")

            if param_has_value(module_node, "searchWhenChanged", ["False"], False):
                warnings.append("""searchWhenChanged=False is not supported by the Canary TimePicker module
                    and was discarded. Consider using a Button module with allowSoftSubmit set to False.""")
            remove_param(module_node, "searchWhenChanged", warnings)

            # if there is no label param we have to create an explicit null one, to prevent
            # the TimePicker's default label from appearing.
            label_param = module_node.find("./param[@name='label']")
            if label_param is None:
                new_param = et.SubElement(module_node, "param")
                new_param.set("name", "label")
                module_node.append(new_param)

        # look for the group=" " workaround from advanced xml and delete it.
        if module_name == "Switcher":
            if module_node.get("group") == " ":
                del module_node.attrib["group"]
        else:
            if module_node.get("group", False):
                parent_module = module_node.find("..")
                #this is fine - group attribute is still used to set switcher labels...
                if parent_module.get("name", False) == "Switcher":
                    pass
                # yep. also fine. this is how Table Embedding works.
                elif parent_module.get("name", False) == "Table" and module_node.get("group").startswith("row.fields."):
                    pass
                else:
                    warnings.append("%s module was using a group attribute, possibly to set the old panel header in axml. This is ignored in Canary. (replace it with an explicit HTML module)" % module_name)



        if module_name == "EnablePreview":
            if param_has_value(module_node, "display", "true", False):
                warnings.append("EnablePreview module had display set to true. We removed the whole module for now but this requires manual migration if you want this functionality back. Note that the Search module has a preview param that takes $foo$ substitution, and the Checkbox module makes a working checkbox.")
            if param_has_value(module_node, "enable", "true", False):
                warnings.append("EnablePreview module had enable set to true. This requires manual migration -- Look up in the XML to the first Search that is a direct ancestor and set its preview param to true.")

        if module_name == "Pulldown":
            if param_has_value(module_node, "mode", "advanced"):
                warnings.append("Pulldown module used to have a 'mode' param you could set to 'advanced' but this is gone. Manually convert this view to use a CheckboxPulldown here instead.")
            remove_param(module_node, "mode", warnings)

        if module_name == "Count":
            convert_count_module_to_pulldown(module_node, warnings)

        if module_name == "StaticContentSample":
            rename_module_to(module_node, "HTML")
            rename_param_to(module_node, "text", "html", infos)

        if module_name == "HiddenChartFormatter":
            rename_module_to(module_node, "ValueSetter")
            remove_param(module_node, "chartTitle", warnings, "HiddenChartFormatter's chartTitle param must be manually replaced with a simple HTML module")
            for param in module_node.findall("param"):
                old_name = param.get("name", "")
                new_name = old_name
                # first add the charting. prefix IF it's not there.
                if not old_name.startswith("charting."):
                    new_name = "charting." + new_name
                #then add the arg. prefix if that's not there.
                if not new_name.startswith("arg."):
                    new_name = "arg." + new_name
                param.set("name", new_name)
                infos.append("HiddenChartFormatter was replaced by Value Setter, and a %s param was replaced with %s." % (old_name, new_name))


    for module_node in view_element.iter("module"):
        module_name = module_node.get("name")
        if module_name in ["EnablePreview", "Message", "Messaging", "SideviewUtils"]:
            module_node.getparent().remove(module_node)
            infos.append("the %s module is redundant in Canary so we removed it." % module_name)

        #migration scratch paper
        #search.timeRange.* is now shared.timeRange.* and in theory migratable.

    warnings = warnings + final_inspection(view_element, module_conf)

    return view_element, warnings, infos

def get_advanced_xml_modules_by_type(view_element, module_conf):
    """
    only to be called after replace_bad_modules has run on this view_element
    """
    splunk_modules = []
    canary_modules = []
    for module_node in view_element.iter("module"):
        module_name = module_node.get("name")
        canary_module = module_conf.get(module_name, False)
        if canary_module:
            canary_modules.append(module_name)
        else:
            splunk_modules.append(module_name)

    return canary_modules, splunk_modules

def get_static_file_path(app):
    """
    gets the absolute path to the app's appserver/static directory.
    """
    return os.path.join(bundle_paths.get_base_path(), app, "appserver", "static")

def get_pattern(app, pattern_name):
    """load the given pattern from the FS please, as an lxml node"""
    cache_key = (app, pattern_name)
    xml_str = _pattern_xml_cache.get(cache_key)
    if xml_str is None:
        pattern_file_path = os.path.join(bundle_paths.get_base_path(), app, "appserver", "patterns", pattern_name + ".xml")
        with open(pattern_file_path, "r", encoding="utf-8") as file_handle:
            xml_str = file_handle.read()
        _pattern_xml_cache[cache_key] = xml_str
    parser = et.XMLParser(remove_blank_text=True, strip_cdata=False)
    try:
        return et.XML(xml_str, parser)
    except Exception:
        logger.error("unexpected exception parsing XML for pattern %s in app %s.", pattern_name, app)
        logger.error(traceback.format_exc())
        logger.error(xml_str)
        raise


def apply_pattern_params(pattern_node, expanded_pattern_node):
    """ copy the params from the "outer" <pattern> tag into the top level node of the
        pattern definition.  Note that the param tags in the pattern definition can have
        default attributes - values set from outside will override these when present.  """
    outer_params = pattern_node.findall("param")
    outer_param_dict = {}
    for p in outer_params:
        outer_param_dict[p.attrib.get("name")] = p.text

    for pattern_param in expanded_pattern_node.findall(".//outerparam"):
        name = pattern_param.attrib.get("name", False)
        param_value = None
        if name in outer_param_dict:
            param_value = outer_param_dict[name]
        elif pattern_param.attrib.get("default"):
            param_value = pattern_param.attrib.get("default")

        if param_value:
            real_param = pattern_param.getparent()
            real_param.remove(pattern_param)
            real_param.text = param_value

def copy_nested_modules_to_insertion_point(pattern_node, expanded_pattern_node):
    insertion_point = expanded_pattern_node.findall(".//insertionPoint")
    if insertion_point:
        # explicit raise so that we can verify it in unit testing. for some reason assert()... gets nerfed?
        if len(insertion_point) > 1:
            raise AssertionError()

        insertion_point = insertion_point[0]

        # copy anything nested in the pattern_tag, into where the insertionPoint tag is
        for direct_child in pattern_node:
            if direct_child.tag in ["module", "pattern"]:
                insertion_point.addprevious(direct_child)

        insertion_point.getparent().remove(insertion_point)
    else:
        # explicit raise so that we can verify it in unit testing. for some reason assert()... gets nerfed?.
        if len(pattern_node.findall(".//module")) + len(pattern_node.findall(".//pattern")) > 0:
            raise AssertionError("View Configuration Error - This pattern tag has nested modules but the patter itself specifies no <insertionPoint/> node.")


def replace_pattern(app, pattern_node, expanded_pattern_node):
    """take the given pattern tag, and replace it with the expanded pattern definition. The tricky part is respecting insertionPoints."""

    for att_name in ["layoutPanel", "group"]:
        att_value = pattern_node.attrib.get(att_name, None)
        if att_value:
            expanded_pattern_node.attrib[att_name] = att_value

    apply_pattern_params(pattern_node, expanded_pattern_node)

    copy_nested_modules_to_insertion_point(pattern_node, expanded_pattern_node)

    replace_patterns(app, expanded_pattern_node)

    pattern_node.addnext(expanded_pattern_node)

    parent = pattern_node.getparent()
    if parent is not None:
        parent.remove(pattern_node)


def replace_patterns(app, view_element):
    """finds any patterns in this view and expands them all.
       Note that the specifics can be complicated, as patterns can nest other patterns.
       In either event the iteration will eventually replace them all and each time the
       nested contents, modules (and during the process, possibly patterns) are templated
       out and flattened.
    """
    for pattern_node in view_element.iter("pattern"):
        name = pattern_node.get("name", False)
        if not name:
            raise Exception("Pattern node has no name param")
        try:
            expanded_pattern_node = get_pattern(app, name)
        except FileNotFoundError as e:
            raise PatternNotFoundError(f"ERROR - no Sideview Pattern was found in this app named {name}")
        replace_pattern(app, pattern_node, expanded_pattern_node)
    return view_element


def get_view(request, module_conf):
    if request.action == "create" and request.view == "_new":
        return "Sideview XML", parse_view_element(BLANK_VIEW_XML, request)

    try:
        result = __get_view_result(request)
    except splunk.ResourceNotFound as e:
        # corral scope of splunk exceptions
        raise ResourceNotFound() from e
    if result.get(EAI_TYPE_KEY) == "html":
        return "HTML Dashboard", result.get(EAI_DATA_KEY)

    try:
        view = parse_view_element(result[EAI_DATA_KEY], request)
        view_type = get_view_type(view, module_conf)

    except Exception:
        logger.error("unexpected exception parsing XML for view %s in app %s.", request.view, request.app)
        logger.error(traceback.format_exc())
        logger.error(result[EAI_DATA_KEY])
        raise

    return view_type, view


def __get_view_result(request):
    """Fetch a representation of the view from backend (splunk), or from a cache.  Store splunk results in cache"""
    selector_tuple = (request.user_name, request.app, request.view)
    cached_result = view_cache.get(selector_tuple)
    if cached_result:
        return cached_result

    uri = "/servicesNS/%s/%s/data/ui/views/%s" % (request.user_name, request.app, request.view)
    result = get_single_rest_api_entry(uri, session_key=request.session_key)
    view_cache.put(selector_tuple, result)
    return result



def parse_view_element(xml_str, request=None):
    parser = et.XMLParser(remove_blank_text=True, strip_cdata=False)
    xml_str_unclean = xml_str

    ## old versions of our apps, notably cisco_cdr used to put an encoding
    ## attribute. In hindsight this was pretty dumb of us, and it makes
    ## lxml in python3 pretty unhappy. Here we strip this out if it's here.

    xml_str = re.sub(r'<\?xml version="\d\.\d"\s+encoding="[^"]+"\s?\?>', '<?xml version="1.0" ?>', xml_str_unclean)
    if xml_str_unclean != xml_str:
        extras = ""
        if request:
            extras = "app=%s view=%s" % (request.app, request.view)

        logger.debug("an encoding attribute was found and removed from the xml tag. %s", extras)

    #logger.debug(xml_str_unclean)

    return et.XML(xml_str, parser)


def make_view_dict(view_element, app, module_conf, replace_all_patterns=True):
    """get the canary dict representing the given view in the given app."""

    view_type = get_view_type(view_element, module_conf)
    if view_type in ["Advanced XML", "Sideview XML"]:
        if replace_all_patterns:
            view_element = replace_patterns(app, view_element)


        # TODO - need to pass these warnings+infos back to the UI, or somewhere.
        view_element, warnings, _infos = replace_bad_modules(view_element, module_conf, app)

        view_dict = convert_xml_to_canary_dict(view_element, module_conf)

        #quick and dirty. it's a bit useful to turn these on but doing so is manual for now.
        if SHOW_WARNINGS:
            view_dict["warnings"] = ",".join(warnings)
        else:
            view_dict["warnings"] = ""

    elif view_type in ["Canary yaml"]:
        view_dict = convert_yaml_to_canary_dict(view_element.text, {})
    else:
        raise LookupError(view_type, "This seems to be a malformed view")

    return view_dict

def add_ids_to_all_modules(view_element):
    """ walks the tree and adds a 'moduleId' attribute to all  modules.
    and adds 'patternId' attribute to all patterns.

    It does this simply by counting how many of each class it sees, such that
    the first "Search" module gets "Search_0", the second gets "Search_1" etc.
    """
    for node_type in ["module", "pattern"]:
        counter_map = {}
        for module_node in view_element.iter(node_type):
            name = module_node.get("name")
            if name not in counter_map:
                counter_map[name] = 0
            module_node.set("%sId" % node_type, "%s_%s" % (name, counter_map[name]))
            counter_map[name] += 1


def remove_ids_from_all_modules(view_element):
    for module_node in view_element.iter("module"):
        module_node.attrib.pop("moduleId")

def add_parent_ids(modules, module_conf):
    """
    By default in the Canary yaml or more generally canary lists-of-dicts,
    A given module is assumed to be "downstream" aka the "child" of the
    module before it in the list.
    This applies unless a given module has an explicit "parent" attribute
    in which case the view must also have somewhere a module with an "id"
    attribute of the same value.

    This function goes through all the modules and adds the explicit parent
    values to all modules.
    """
    valid_parent = {}
    for mod in modules:
        if mod.get("pattern"):
            continue
        module_name = mod["module"]
        if valid_parent and not "parent" in mod:
            mod["parent"] = valid_parent["moduleId"]

        if module_allows_downstream_modules(module_conf, module_name):
            valid_parent = mod

def add_default_param_values(modules, module_conf):
    """
    For many modules there are params that are not required, where if omitted
    they will assume some default value.  This function explicitly adds those
    default values to modules, (which is a list of dicts).
    """
    for mod in modules:
        if mod.get("pattern"):
            continue
        module_name = mod.get("module")
        if module_name in module_conf:
            for param in module_conf[module_name]["params"]:
                param_dict = module_conf[module_name]["params"][param]
                if param not in mod:
                    default_value = param_dict.get("default", False)
                    if default_value:
                        mod[param] = default_value


def get_module_id(mod):
    """returns the id of the given module."""
    if mod is None:
        return False
    if mod.tag == "view":
        return "top"
    return mod.attrib["moduleId"]

def get_rest_api_response(uri, session_key):
    """ simple wrapper around simpleRequest to return just the json response """
    getargs = {
        "output_mode":"json",
        "count":0
    }
    uri = quote(uri)
    _response, content = rest.simpleRequest(uri, sessionKey=session_key, method="GET",
                                            raiseAllErrors=True, getargs=getargs)
    return json.loads(content)

def get_single_rest_api_entry(uri, session_key):
    """ simplified way to just get the contents of the first stanza, parsed as json.
        95% of the time this is all we want."""

    content = get_rest_api_response(uri, session_key)
    return content["entry"][0]["content"]


def memoize_non_empty_values(func):
    cache = {}

    def memoized_func(*args):
        if args in cache:
            return cache[args]
        result = func(*args)
        if result:
            cache[args] = result
        return result

    return memoized_func



@memoize_non_empty_values
def _get_all_apps(session_key):
    return get_rest_api_response("/services/apps/local", session_key)


def get_app_labels(session_key):
    """return a dict mapping the app id's to the human-readable labels for those apps """
    content = _get_all_apps(session_key)
    return {app["name"]: app["content"].get("label", app["name"]) for app in content.get("entry", [])}



def get_config(request, app_override=None):
    """
    get the few keys that we send down with the page itself.
    """
    app = request.app
    if app_override:
        app = app_override
    conf = {}
    conf.update(get_splunk_server_config(request.session_key))
    try:
        conf.update(get_app_config(request.session_key, app))
    except ResourceNotFound:
        raise splunk.ResourceNotFound

    conf.update(get_user_config(request.session_key))

    conf["USER"] = request.user_name
    conf["APP"] = app
    conf["VIEW"] = request.view
    conf["THEME"] = request.ui_theme
    return conf



@memoize_non_empty_values
def get_splunk_server_config(session_key):
    """ returns splunk version, build number, httpport, root_endpoint, license type and instance type """
    entry = get_single_rest_api_entry("/services/server/info", session_key)

    web_settings_content = get_rest_api_response("/services/properties/web/settings", session_key)
    web = {e["name"]: e["content"] for e in web_settings_content.get("entry", [])}

    # basically if instance_type isn't there, we assume this is onprem
    # because Splunk Enterprise does not actually have this key in the response.
    return {
        "SPLUNK_VERSION": entry.get("version", "0"),
        "SPLUNK_BUILD_NUMBER": entry.get("build", "0"),
        "SPLUNKWEB_PORT_NUMBER": web.get("httpport", "8000"),
        "ROOT_ENDPOINT": web.get("root_endpoint", ""),
        "LICENSE_TYPE": entry.get("activeLicenseGroup", "unknown"),
        "INSTANCE_TYPE": entry.get("instance_type", "enterprise"),
        # uncomment if you get nervous that the memoization isn't working.  it is.
        #"RANDOM_NUMBER": round(random.random()*10)
    }

def get_current_tz_abbreviation():
    try:
        now = datetime.datetime.now()
        local_now = now.astimezone()
        return local_now.tzinfo.tzname(local_now)

    except Exception as e2:
        logger.error(e2)
        logger.error("unable to get a fallback timezone name from datetime. Users who do not have a specific TZ preference set in their prefs will experience some bugs in their time displays, timechart labels and absolute picker")
        return ""

def get_current_tz():
    """ this will get the name of the system timezone as a string.
        return values will look like "America/New York",  but in fallback cases
        they may also look like "EST"  or "EDT" etc """
    try:
        return get_localzone_name()

    except Exception as e:
        logger.error(e)
        logger.error("unable to get the proper IANA timezone name from tzlocal. Falling back to getting the TZ abbreviation from datetime.")
        return get_current_tz_abbreviation()


def get_app_config(session_key, app):
    """ returns the app.conf version and build number as a simple dict"""
    content = _get_all_apps(session_key)
    for entry in content.get("entry", []):
        if entry["name"] == app:
            c = entry["content"]
            return {
                "SUPPORTED_THEMES": c.get("supported_themes", "light"),
                "APP_VERSION": c.get("version", "0"),
                "APP_BUILD_NUMBER": c.get("build", "0")
            }
    raise ResourceNotFound()


@memoize_non_empty_values
def get_user_config(session_key):
    """ gets things from current context """
    uri = "/authentication/current-context"
    entry = get_single_rest_api_entry(uri, session_key)

    real_name = entry.get("realname", "")


    # If there is no "tz" entry it means the user's preference is set to 'system default'.
    # note - some risk that different splunk versions might be missing tz, or might set
    # it to "" so we play it a little safe here
    tz = entry.get("tz", "")
    if tz == "":
        tz = get_current_tz()

    return {
        "REAL_NAME": real_name,
        "TZ": tz
    }


def get_csrf_token(request):
    """ Eng forgot to pass the submitted csrf token from the request, but they did pass the raw
    cookie values in there, AND we can of course fish the port number on which SplunkWeb is
    listening out of the conf.  So with those 2 things we can reliably get the csrf_token  :P
    Note that the port in the cookie name is the port that splunkWeb is listening on, not
    necessarily the port to which the browser sent its request.
    """
    if not hasattr(request, "session_key"):
        return ""

    server_dict = get_splunk_server_config(request.session_key)

    # It's possible this will need to be watered down but... I think if we ever have a session_key
    # in the request but no port number in our server.conf dict, that's O_O so therefore assertion
    assert "SPLUNKWEB_PORT_NUMBER" in server_dict

    cookie_name = "splunkweb_csrf_token_%s" % server_dict.get("SPLUNKWEB_PORT_NUMBER")
    return request.get_cookie_value(cookie_name)





def replace_tokens(s, qs_dict):
    """this is a straight port from our replaceTokensFromContext() in JS.
    We use it here so that if a $foo$ token is present in the URL, we will load
    it initially with the value we see there.  Then later at runtime it may be
    replaced again, usually by URLLoader.  But this prevents the HTML from
    flashing the unreplaced "$foo$" briefly.
    And if there is no matching foo in the args this function will simply
    replace them with ""."""
    within = False
    token_name = []
    token_value = ""
    out = []
    for i, char in enumerate(s):
        if char == "$":
            within = not within
            # check for '$$' to handle all those cases correctly.
            if not within and i > 0 and s[i-1] == "$":
                out.append("$")
                continue
            # we just finished the token.
            if not within:
                token_value = qs_dict.get("".join(token_name), "")

                # only do the replacement for simple alphanumeric string values
                # or lists of simple alphanumeric string values.
                if isinstance(token_value, list):
                    if ("".join(token_value)).isalnum():
                        out.append(",".join(token_value))
                elif str(token_value).isalnum():
                    out.append(token_value)

                token_name = []
        elif within:
            token_name.append(char)
        else:
            out.append(char)
    return "".join(out)

def _(value):
    """
    It is unclear whether we're ever going to do localization, but stubbing it
    out for now.
    """
    if not value:
        return ""
    return value



def get_static_url_prefix(session_key, app, locale, root_endpoint=""):
    """ build the working URL that will be sent to the browser, for it to request
    a static asset in the given app"""
    app_config = get_app_config(session_key, app)
    if root_endpoint == "/":
        root_endpoint = ""
    if not locale:
        locale = "en-US"
    locale = "/" + locale
    prefix = "%s%s/static/@%s.%s/app/%s/" % (root_endpoint, locale, app_config["APP_VERSION"], app_config["APP_BUILD_NUMBER"], app)
    return prefix

def get_default_view_for_app(app, user_name, session_key):
    """
    Tries to find the view that's marked in the default.xml nav file as the
    default, or failing that any view called 'home'"""

    uri = "/servicesNS/%s/%s/data/ui/nav/default" % (user_name, app)
    try:
        entry = get_single_rest_api_entry(uri, session_key)
    except splunk.ResourceNotFound:
        return False

    nav_xml_str = entry[EAI_DATA_KEY]

    parser = et.XMLParser(remove_blank_text=True, strip_cdata=False)
    nav = et.XML(nav_xml_str, parser)
    default_view = nav.xpath("//view[@default='true']")

    if not default_view:
        # the lists returned by xpath method don't support concatenation somehow.
        default_view = nav.xpath("//view[@default='True']")

    if default_view:
        default_view_name = default_view[0].get("name")
    else:
        if nav.xpath("//view[@name='home']") or nav.xpath("//view[@name='home_redirect']"):
            return "home"


    if default_view_name == "home_redirect":
        return "home"
    return default_view_name



def redirect(request, view_type=None, flask_redirect=None):
    """
    the caller decided we weren't in a good place, and the caller will ALREADY have specified the
    view we're redirect to by setting the request.view property (yes this could be cleaned up)
    so our job now is to return a 301 response for them.
    CURRENTLY
        - either the request didn't specify an explicit view.
        - or the request was to the "search" view which is a contract Canary can't fulfill yet.
    """

    server_config = get_splunk_server_config(request.session_key)

    location = request.get_redirect_location(view_type, server_config.get("ROOT_ENDPOINT"))

    logger.info("redirecting user=\"%s\" locale=\"%s\" app=\"%s\" view=\"%s\" method=\"%s\" location=\"%s\"",
                request.user_name, request.locale, request.app, request.view, request.method, location)
    if flask_redirect:
        return flask_redirect(location, code=301)
    else:
        return build_response(301, "Redirecting to %s" % location, location=location)


def mako_template_exists(template_path):
    try:
        get_template(template_path)
    except exceptions.TemplateLookupException:
        return False
    return True


def get_template(template_path):
    try:
        template = MAKO_TEMPLATE_LOOKUP.get_template(template_path)
    except exceptions.TemplateLookupException:
        if template_path.find("/") != -1:
            return False
        template_path = "/view/" + template_path
        #if this one doesn't work,  just let it raise.
        return MAKO_TEMPLATE_LOOKUP.get_template(template_path)
    return template

def render_mako(template_path, template_dict):
    """
    wrapper to call render on the given mako template.
    """
    template_dict["replace_tokens"] = replace_tokens

    #TODO - please kill this and make it never come back again. kthx.
    template_dict["_"] = _

    template = get_template(template_path)
    return template.render(**template_dict)


def build_mako_response(template, template_dict):
    """ all mako templates are assumed to return HTML, and all calls to this function
    are assumed to be status-200 unless the mako template throws an exception, in which case it
    will return status=500 along with the stack trace rendered as HTML"""
    try:
        html = render_mako(template, template_dict)
        status = 200
    except Exception as e:
        logger.error("mako exception trying to load template %s", template)
        logger.error(e)
        logger.error(traceback.format_exc())
        html = exceptions.html_error_template().render()
        status = 500
    return build_response(status, html, "text/html")



def is_view_editable(request):
    if request.action == "create" and request.view == "_new":
        return True
    if request.app in ["sideview_utils", "canary"]:
        return request.view.startswith("example_") or request.view.startswith("test_") or request.view.startswith("dev_")
    else:
        return request.app not in UNEDITABLE_VIEWS or request.view not in UNEDITABLE_VIEWS[request.app]

def build_uneditable_view_response(request, flask=False):
    message = """This view has been mysteriously marked as uneditable.
    Or maybe it wasn't mysterious.  Honestly we can't tell. But you can't edit it."""
    if request.app in ["sideview_utils", "canary"] or (request.app in UNEDITABLE_VIEWS and request.view in UNEDITABLE_VIEWS[request.app]):
        message = """We cannot let you use the Editor to edit
            pieces of core Sideview apps themselves because that would be too silly.
            You may however edit any view in those apps whose name begins with the prefixes
             'example_', 'test_' or 'dev_'."""
    json_data = {"success:":False, "message": message}
    if flask:
        return json_data, 405

    payload = json.dumps(json_data)
    response = build_response(405, payload, "application/json")
    #logger.info(response)

    return response



def build_response_flask(status, payload=None, content_type=None, location=None, flask=None):
    """ core  method to return things to the client. """
    if content_type:
        #paranoia about passing content_type=None
        return flask.Response(payload, status, content_type=content_type)
    return flask.make_response(payload, status)


def build_response(status, payload=None, content_type=None, location=None):
    """ core  method to return things to the client. """
    response_dict = {}
    response_dict["status"] = status

    if payload:
        response_dict["payload"] = payload

    # pro-tip - setting a "Content-Length" header works fine on mgmt port and blows up on the
    # web port proxy somehow.
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
        #if content_type == "application/json":
        #    logger.error("json response is \n" + json.dumps(response_dict, indent=4, sort_keys=True))

    if location:
        headers["Location"] = location

    if headers:
        response_dict["headers"] = headers
    return response_dict

def build_html_response(status, payload):

    payload = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:s="http://www.splunk.com/xhtml-extensions/1.0" xml:lang="en" lang="en" class="no-js">
<head></head><body>{payload}</body></html>"""
    return build_response(status, payload)


class UnsortableList(list):
    """
    this is used here to avoid the yaml having keys in purely alphabetical
    order.  As a small improvement to readability, by convention for instance
    the "module" key is always listed first.
    Specifically, this code will always print them in the order they were
    added to the dict, and then the code itself is responsible for always
    adding them in whatever 'sensible' order was determined.
    """
    def sort(self, *args, **kwargs):
        pass

class UnsortableOrderedDict(OrderedDict):
    """
    oh hai
    """
    def items(self, *args, **kwargs):
        return UnsortableList(OrderedDict.items(self, *args, **kwargs))

def ordered_load(stream, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
    """This allows us to preserve the order of the keys on load"""
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)

def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    """ allows us to preserve the order of the keys when serialized"""
    class OrderedDumper(Dumper):
        pass
    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)

yaml.add_representer(UnsortableOrderedDict, yaml.representer.SafeRepresenter.represent_dict)

def module_children_should_be_hidden(module_conf, module_type):
    """is this a module that says all children should be hidden by default"""
    m = module_conf.get(module_type, {})
    params = m.get("params", {})
    return params.get("hideChildrenOnload", False)

def module_allows_downstream_modules(module_conf, module_type):
    """ is this a module that allows other modules to exist downstream"""
    m = module_conf.get(module_type, {})
    forbids = m.get("forbidsDownstreamModules", False)
    return not forbids

def all_prior_siblings_forbid_downstream_modules(module_conf, module_node):
    """ Picturing the final upstream-downstream hierarchy, ie the tree.
    the given module module_node may or may not have siblings, ie other
    children of module_node's parent.  This function returns true if all
    of the prior siblings have said that they forbid downstream modules.
    """
    parent_node = module_node.getparent()
    # why
    #if parent_node.tag == "view":
    #    return False

    direct_children = parent_node.findall("module")
    for i, direct_child in enumerate(direct_children):
        # we made it all the way to the given child.
        if direct_child.attrib["moduleId"] == module_node.attrib["moduleId"]:
            if i == 0:
                return False
            return True
        module_name = direct_child.attrib["name"]
        if module_allows_downstream_modules(module_conf, module_name):
            return False

    logger.error("Assertion failed - we walked through all the children of " + parent_node.attrib.get("moduleId", "(no module id)") + " without reaching its child " + module_node.attrib["moduleId"])
    raise Exception("Assertion failed - we walked through all the children of " + parent_node.attrib.get("moduleId", "(no module id)") + " without reaching its child " + module_node.attrib["moduleId"])


def get_fake_pattern_module(node):
    """ nothing to see here. """
    fake_module = {}
    fake_module["pattern"] = node.attrib["name"]
    if node.attrib.get("skipNextModule") == "True":
        fake_module["skipNextModule"] = True
    return [fake_module]



last_rendered_module = False

def flatten_module(module_node, parent_node, module_conf, hidden=False):
    """
    flattens the current module and all its downstream modules following
    the yaml format.

    TRUTHS.
    if module forbidsDownstreamModules,  then don't give it an ID
    When the view is next read, the code will assume it can't have downstream modules
    and will assign modules "after" it to the nearest ancestor that CAN have downstream modules.

    EXCEPT THAT THE NEXT module after,  specifies parent/id unnecessarily. so we need to poke a
    hole in the last_rendered_module != parent_node rule as we go, if all the direct_children so
    far through the loop, have forbidsDownstreamModules = True,
    then none of those direct_children, NOR the one after it, require parentModuleId to be set.
    the code will interpret the yaml correctly even without them.

    as soon as we hit a directChild X who allows downstream modules,  then we have to give the
    parent an ID and the NEXT module after X,  must have a parentModuleId set to the parent.
    """
    assert parent_node is not None
    assert module_node is not None

    global last_rendered_module
    module_type = module_node.attrib["name"]

    if not module_allows_downstream_modules(module_conf, module_type):
        child_modules = module_node.findall("module")
        parent = module_node.find("..")
        for m in child_modules:
            module_node.remove(m)
            parent.append(m)
            if (parent.get("layoutPanel", False) and not module_node.get("layoutPanel", False)):
                module_node.set("layoutPanel", parent.get("layoutPanel"))

    modules = []
    mod = UnsortableOrderedDict()

    # everyone gets an id, and then we take away all that aren't used in any parent=foo atts.
    mod["module"] = module_type
    mod["moduleId"] = get_module_id(module_node)
    if hidden:
        mod["visible"] = False

    if "layoutPanel" in module_node.attrib:
        mod["layoutPanel"] = module_node.attrib["layoutPanel"]

    if "group" in module_node.attrib:
        mod["group"] = module_node.attrib["group"]

    if parent_node is not None and last_rendered_module != parent_node and not all_prior_siblings_forbid_downstream_modules(module_conf, module_node):
        mod["parent"] = get_module_id(parent_node)

    last_rendered_module = module_node
    for param in module_node.findall("param"):

        if len(param.findall("param")) > 0:
            raise ValueError("%s module in this view contains a %s param that itself directly contains another param node. Most likely you forgot a \"list\" node." % (module_type, param.attrib["name"]))
        items = []
        for list_element in param.findall("list"):
            list_entry = {}
            for inner_param in list_element.findall("param"):
                list_entry[inner_param.attrib.get("name")] = inner_param.text
            items.append(list_entry)
        if items:
            param_value = items

        elif is_big_param(module_type, param.attrib["name"] and param.text):
            param_value = param.text.lstrip().rstrip()
        else:
            param_value = param.text
        mod[param.attrib["name"]] = param_value

    modules.append(mod)

    for direct_child in module_node:
        if direct_child.tag == "pattern":
            modules = modules + get_fake_pattern_module(direct_child)
        if direct_child.tag == "module":
            if module_allows_downstream_modules(module_conf, module_type):
                effective_parent = module_node
            else:
                effective_parent = parent_node

            # the second we hit this flag, all children in the rest of the
            # recursive calls are to be hidden.
            if module_children_should_be_hidden(module_conf, module_type):
                hidden = True

            modules = modules + flatten_module(direct_child, effective_parent, module_conf, hidden)
    return modules


def remove_unused_ids(modules):
    """
    for all modules, remove any "moduleId" entries where the value is
    not also present in an explicit "parent" entry.
    """
    specified_parents = {}
    for mod in modules:
        if "parent" in mod:
            specified_parents[mod["parent"]] = 1
    for mod in modules:
        if "moduleId" in mod and mod["moduleId"] not in specified_parents:
            del mod["moduleId"]

def remove_repeated_layout_panels(modules):
    """
    layoutPanels can be specified redundantly if
    1) the same value is already specified as the layoutPanel of the nearest ancestor
    2) the same value is specified by a prior sibling.
    Currently this function only implements #1.

    """
    which_panel = {}
    parent_hash = {}
    for mod in modules:
        if "moduleId" not in mod:
            continue
        module_id = mod.get("moduleId")
        if "layoutPanel" in mod:
            which_panel[module_id] = mod["layoutPanel"]
        parent_hash[module_id] = mod

    for mod in modules:
        explicit_layout_panel = mod.get("layoutPanel", False)
        if explicit_layout_panel:

            # ----- could be pulled up
            relevant_module_node = mod
            relevant_ancestor_layout_panel = False
            while True:
                ancestor_id = relevant_module_node.get("parent", False)
                if not ancestor_id or ancestor_id == "top":
                    break
                if ancestor_id in which_panel:
                    relevant_ancestor_layout_panel = which_panel.get(ancestor_id)
                    break
                relevant_module_node = parent_hash[ancestor_id]
            # ----- end

            if relevant_ancestor_layout_panel:
                if explicit_layout_panel == relevant_ancestor_layout_panel:
                    #print("%s getting its layoutPanel deleted cause its the same as the next ancestor" % mod.get("moduleId"))
                    del mod["layoutPanel"]
                continue


def remove_redundant_parent_attributes(modules, module_conf):
    """ a bit odd - in almost all cases this will remove the parent="top"
    attribute from only the first module"""

    for mod in modules:
        #since we start from the top, all parent="top" are dumb.
        if "parent" in mod and mod["parent"] == "top":
            del mod["parent"]

        if mod.get("pattern"):
            continue
        module_type = mod["module"]
        #however the MOMENT we hit a module that DOESNT forbid downstream modules, then
        # any further parent="top" attributes are actually meaningful.
        if module_allows_downstream_modules(module_conf, module_type):
            return




def fill_in_inherited_layout_panels(modules):
    """
    a sort of inverse of remove_repeated_layout_panels, this will give every
    module an explicit value for layoutPanel.
    """


    # there's a convention allowing them to be omitted .
    # If you read the yaml top to bottom, each module will pick up the last
    # one seen in the file.
    # and if a top level module has none specified we assume 'viewHeader'

    last_layout_panel = DEFAULT_LAYOUT_PANEL
    # however whenever there's a 'parent' attribute, we have to set
    # last_layout_panel to the last_layout_panel that was in effect AT THE PARENT
    # MODULE, so this is how we remember which modules had which.
    which_panel = {}
    panels_used = {}

    for mod in modules:
        if mod.get("pattern"):
            continue
        parent_id = mod.get("parent", False)
        explicit_panel = mod.get("layoutPanel", False)
        module_id = mod.get("moduleId")


        if explicit_panel:
            panel_to_use = explicit_panel
            #logger.error("%s has explicit panel of %s ", module_id, explicit_panel)
            which_panel[module_id] = explicit_panel

        elif parent_id and parent_id == "top":
            panel_to_use = DEFAULT_LAYOUT_PANEL
        elif parent_id and parent_id != "top":
            panel_to_use = which_panel.get(parent_id, DEFAULT_LAYOUT_PANEL)
            #logger.error("%s had no explicit layoutPanel but did have a parent attribute of %s which had last known layoutPanel of %s ", module_id, parent_id, last_layout_panel)
        elif last_layout_panel:
            panel_to_use = last_layout_panel


        #logger.error("assigning %s a layout panel of %s", module_id, last_layout_panel)
        mod["layoutPanel"] = panel_to_use
        which_panel[module_id] = panel_to_use
        panels_used[panel_to_use] = 1


    # The list of the panels that actually had modules in them.
    return list(panels_used.keys())



def add_dynamic_params(view_dict, app):
    """
    get the params that actually require information beyond the view
    config and module config
    NOTE - currently it's ONLY the "src" param on the HTML module.
    """
    for mod in view_dict["modules"]:
        if mod.get("module", None) == "HTML":
            src = mod.get("src", None)
            if src:
                src_segments = re.split(ALL_SLASHES_RE, src)
                full_path = os.path.join(get_static_file_path(app), *src_segments)
                try:
                    with open(full_path, "r+", encoding="utf-8") as file_handle:
                        content = "".join(file_handle.readlines())
                        mod["html"] = content
                except FileNotFoundError as e:
                    raise IncludeFileNotFoundError(f"ERROR - no include file was found in this app matching the relative path {src}")


def get_list_param(list_nodes):
    param_list = []
    for list_node in list_nodes:
        param_dict = {}
        for nested_param in list_node.findall("param"):
            param_dict[nested_param.get("name")] = nested_param.text
        param_list.append(param_dict)
    return param_list

def get_module_nodes_params_as_dict(module):
    params = {}
    for param in module.findall("param"):
        name = param.attrib.get("name")
        list_nodes = param.findall("list")
        if len(list_nodes) > 0:
            params[name] = get_list_param(list_nodes)
        else:
            text = param.text or ""
            params[name] = text.strip()
    return params

def get_module_attribute(module, name):
    """ The convention for xml attributes in these documents, is a little unusual.
        sementically, all attribute values besides name are inherited by child nodes.
        So this method basically looks up the chain.
    """
    if module is None:
        #logger.error(view_element.toprettyxml())
        raise KeyError("no module passed to get_module_attribute")
    value = module.attrib.get(name, None)
    inherited_value = None

    module_copy = module
    while module_copy.getparent().getparent() and module_copy.getparent().attrib and not inherited_value:
        module_copy = module_copy.getparent()
        inherited_value = module_copy.attrib.get(name, None)
    if not inherited_value:
        inherited_value = ""
    if not value:
        value = inherited_value
    return value, inherited_value


def get_module_params(module_conf, module_name):
    """DRY"""
    return module_conf.get(module_name, {}).get("params", {})

def get_hierarchy_errors(modules, module_conf):
    """return a list of places where modules have gotten to somewhere they're
       not supposed to be."""
    fails = []

    modules_that_are_parents = []
    for mod in modules:
        parent = mod.get("parent", False)
        if parent and parent != "top":
            modules_that_are_parents.append(parent)

    for mod in modules:
        if mod.get("pattern"):
            continue

        module_name = mod["module"]
        # This function is forgiving of modules that are totally undefined.
        # (That's someone else's problem)
        module_params = get_module_params(module_conf, module_name)

        # Step 1 - check for required params
        #TODO - this could be optimized but first check how much time its actually taking.
        for param_name, param_value in module_params.items():

            if not param_value:
                continue

            if param_name == "forbidsDownstreamModules" and module_name in modules_that_are_parents:
                fails.append("%s does not allow downstream modules yet it has one in this view" % module_name)
            if param_name == "forbidsUpstreamModules" and mod.get("parent", "top") != "top":
                fails.append("%s does not allow upstrea modules yet it has one in this view" % module_name)
            if param_name == "requiresDownstreamModules" and not module_name in modules_that_are_parents:
                fails.append("%s requires at least one downstream module to be valid, but it does not have one in this view" % module_name)
            if param_name == "requiresUpstreamModules" and mod.get("parent", "top") == "top":
                fails.append("%s requires at least one upstream module to be valid, but it does not have one in this view" % module_name)
    return fails

def get_missing_param_errors(modules, module_conf):
    """ return a list of error messages about params that are missing"""
    fails = []

    for mod in modules:
        if mod.get("pattern"):
            continue
        module_name = mod["module"]
        # This function is forgiving of modules that are totally undefined.
        # (That's someone else's problem)
        module_params = get_module_params(module_conf, module_name)

        required_params = []
        for param_name, param_dict in module_params.items():
            if param_dict.get("required", "False") == "True":
                required_params.append(param_name)
        for required_param in required_params:
            if required_param not in mod:
                fails.append("error - %s module is missing a value for the required param '%s'."
                             % (module_name, required_param))
    return fails

def get_validation_errors(view_dict, module_conf, layout_panels_used=[]):
    """get an overall list of all validation errors about the given view """
    modules = view_dict["modules"]
    fails = get_hierarchy_errors(modules, module_conf)
    fails += get_missing_param_errors(modules, module_conf)

    for mod in modules:
        if mod.get("module") == "Link" and mod.get("hideUntilPushReceived") == "False":
            label = mod.get("label", "")
            if "$" in label:
                fails.append("Link module has hideUntilPushReceived=False but its label '%s' contains a token. "
                              "A dynamic label requires a push to resolve, which contradicts hideUntilPushReceived=False." % label)

    for mod in modules:
        if mod.get("pattern"):
            continue
        module_name = mod.get("module")

        # Step 1 - check for modules that are... just bad or unmigratable.
        if module_name not in module_conf:
            if module_name in DEAD_SIDEVIEW_UTILS_MODULES:
                fails.append("%s is a old Sideview module that never saw the light of day" % module_name)
            elif module_name in LEGACY_SPLUNK_MODULES:
                fails.append("%s is a legacy splunk module" % module_name)
            else:
                fails.append("No %s module found in Canary (perhaps upgrade the Canary app to latest).  " % module_name)
            continue

        module_params = get_module_params(module_conf, module_name)

        wildcard_params = []
        for param_name in module_params:
            if param_name.endswith("*"):
                wildcard_params.append(param_name[:-1])

        for param_name in mod:
            if param_name in ["layoutPanel", "moduleId", "module", "parent", "group"]:
                continue

            # Step 2 - check for params that are just invalid.
            if param_name not in module_params:
                is_wildcard = False
                for wildcard_param in wildcard_params:
                    if param_name.startswith(wildcard_param):
                        is_wildcard = True
                if not is_wildcard and param_name != "visible":
                    fails.append("%s module does not have a param called '%s'." % (module_name, param_name))

            # step 3 - ok the param is valid but check the values
            else:
                values = module_params[param_name].get("values")
                param_value = mod[param_name]
                if values:
                    if param_value.startswith("$") and param_value.endswith("$"):
                        pass
                    elif param_value not in values:
                        fails.append("%s module does not allow '%s' as a value for the '%s' param."
                                     % (module_name, param_value, param_name))
    #logger.error(layout_panels_used)
    fails += validate_layout_panels(layout_panels_used)

    return fails


def get_view_type(view_element, module_conf):
    """Inspects the content of the given XML to determine what kind of view this is"""

    tag = view_element.tag

    # Fast path: Simple XML types
    if tag == "dashboard":
        return "Simple XML (dashboard)"
    elif tag == "form":
        return "Simple XML (form)"
    elif tag != "view":
        return "Unable to determine view type"

    # View element analysis
    type_attribute = view_element.get("type", "")
    if type_attribute == "redirect":
        return "Splunk redirect view"

    module_tags = view_element.findall("module")

    # No modules: template-based view
    if not module_tags:
        template_attribute = view_element.get("template", "")
        if template_attribute.endswith(".html"):
            if template_attribute.startswith(("licensing", "pages/")):
                return "Internal splunk view"
            elif ":" in template_attribute:
                return "App-specific template"
            else:
                return "Unknown"

        # Check for Canary YAML (no modules, no template)
        if view_element.text:
            try:
                yaml.safe_load(view_element.text)
                return "Canary yaml"
            except (yaml.YAMLError, AttributeError):
                pass
        return False

    # Has modules: Advanced/Sideview XML
    canary_modules, splunk_modules = get_advanced_xml_modules_by_type(view_element, module_conf)

    if splunk_modules and not canary_modules:
        return "Advanced XML"

    if canary_modules:
        return "Sideview XML"

    # Note this path is only rarely hit, if we had some splunk modules AND some canary modules.
    cloned_view = copy.deepcopy(view_element)
    modified_clone, _warnings, _infos = replace_bad_modules(
        cloned_view, module_conf
    )
    # after cleaning we check again.
    canary_modules, splunk_modules = get_advanced_xml_modules_by_type(modified_clone, module_conf)

    if canary_modules:
        return "Sideview XML"

    return "Unable to determine view type"



def get_spacetree_json(request, module_conf):

    st_json = {}
    st_json["id"] = request.view
    st_json["name"] = request.view
    st_json["data"] = {"type": "view"}

    _view_type, view_element = get_view(request, module_conf)

    view_element, _warnings, _infos = replace_bad_modules(view_element, module_conf, request.app)

    add_ids_to_all_modules(view_element)
    convert_to_spacetree_json(st_json, view_element)
    return json.dumps(st_json)

def convert_to_spacetree_json(json_node, xml_node):
    """ converts an elementTree representation of a Canary view into
    the json structure used by the spacetree visualization library """
    json_node["children"] = []

    for child in xml_node:
        if child.tag == "pattern":
            json_child = {
                "id": child.attrib.get("patternId"),
                "name": child.attrib.get("name"),
                "data": {"type": "pattern"}
            }
        elif child.tag == "module":

            json_child = {
                "id": child.attrib.get("moduleId"),
                "name": child.attrib.get("name"),
                "data": {}
            }
            for param in child:
                if param.tag != "param":
                    continue
                param_name = param.attrib.get("name")
                json_child["data"][param_name] = param.text
        else:
            continue
        json_node["children"].append(json_child)
        convert_to_spacetree_json(json_child, child)



def get_elastic_errors(elastic_resp):
    """ definitely a work in progress.   We are not at all sure that this is currently
    capturing the full range of errors that can come out of elastic
    """
    root_causes = elastic_resp.get("error").get("root_cause", [])

    messages = []
    for root_cause in root_causes:
        messages.append({
            "type": "error",
            "text": root_cause.get("reason")
        })
    return messages

def convert_elastic_to_splunk_json_cols(elastic):
    """ converts the elasticsearch output format into the
        splunk "json_cols" output format   """


    out = {
        "preview": False,
        "init_offset": 0,
        "messages": [],
        "fields": [],
    }

    if "id" in elastic:
        out["id"] = elastic["id"]
    if "is_running" in elastic:
        out["is_running"] = elastic["is_running"]

    if "error" in elastic:
        out["messages"] = get_elastic_errors(elastic)

    # nick still doesn't like list comprehensions.
    elastic_columns = elastic.get("columns",[])
    for column in elastic_columns:
        out["fields"].append(column["name"])

    # and he's not crazy about this either.
    # All this does is transpose the 2d array.
    elastic_values = elastic.get("values",[])
    columns = list(map(list, zip(*elastic_values)))

    out["columns"] = columns

    return out

def convert_elastic_to_splunk_json(elastic):
    """  converts the elastic search output into the splunk
    json outputtype.
    NOTE: there was formerly a second implementation by josh
    that looked at things like "hits" and "shards".   """


    out = {
        "preview":False,
        "init_offset":0,
        "messages":[],
        "fields": [],
        "results": [],
        "highlighted": {},
    }

    if "id" in elastic:
        out["id"] = elastic["id"]
    if "is_running" in elastic:
        out["is_running"] = elastic["is_running"]

    #logger.error("raw elastic response is ")
    #logger.error(elastic)
    if "error" in elastic:
        out["messages"] = get_elastic_errors(elastic)

    fields = []
    for col in elastic.get("columns", []):
        field_name = col.get("name","")
        fields.append(field_name)
        out["fields"].append({
            "name": field_name,
            "type": "str"
        })

    for i, row in enumerate(elastic.get("values", [])):
        result = {}

        for j, field_name in enumerate(fields):
            result[field_name] = row[j]

        out["results"].append(result)

    return out


def convert_yaml_to_canary_dict(yaml_str, patterns):
    """ more or less just defers to load, except it has to do some magic
        with patterns """
    canary_dict = UnsortableOrderedDict()
    canary_dict = yaml.safe_load(yaml_str)
    modules = canary_dict["modules"]

    found_one = False
    for i, mod in enumerate(modules):
        pattern_name = mod.get("pattern", False)
        if not pattern_name:
            continue
        if pattern_name and not pattern_name in patterns:
            raise KeyError("pattern %s not found in currently loaded patterns" % pattern_name)
        found_one = True
        p_modules = patterns[pattern_name]["pattern"]
        #print(yaml.dump(p_modules, default_flow_style=False))
        modules[i:i+1] = p_modules

    if found_one:
        canary_dict["modules"] = modules

    return canary_dict

def convert_canary_dict_to_yaml(view_dict):
    """ dump out the view object as yaml"""

    #for thing in view_dict["modules"]:
    #    if thing["module"].get("pattern", False):
    #       thing["pattern"] = thing["module"].replace("pattern:", "")
    #        del thing["module"]


    return yaml.dump(view_dict, default_flow_style=False)

def convert_xml_to_canary_dict(view_element, module_conf):
    """
    Given an Elementtree node representing a Sideview XML view,
    return a minimal flat representation in the "canary" format.
    eg: instead of parent-child relationships being encoded by element
    nesting, they are usually inferred, with each module N in
    the by default assumed to be the "child" of module N-1
    """
    add_ids_to_all_modules(view_element)

    modules = []
    for child in view_element:

        if child.tag == "module":
            modules = modules + flatten_module(child, view_element, module_conf)
        elif child.tag == "pattern":
            modules = modules + get_fake_pattern_module(child)
    #logger.error(json.dumps(modules, indent=4))

    remove_repeated_layout_panels(modules)

    remove_redundant_parent_attributes(modules, module_conf)

    canary_dict = UnsortableOrderedDict()
    label_element = view_element.find("./label")
    if label_element is not None and label_element.text:
        canary_dict["viewLabel"] = label_element.text
    else:
        canary_dict["viewLabel"] = "(no label defined)"

    legacy_stylesheet = view_element.attrib.get("stylesheet")
    css = view_element.attrib.get("css", legacy_stylesheet)
    if css:
        canary_dict["css"] = css

    # it's not very likely anyone ever created this, as it was omitted from the Editor
    # and was thus fairly hard to discover.
    legacy_custom_js = view_element.attrib.get("customJS")
    js = view_element.attrib.get("js", legacy_custom_js)
    if js:
        canary_dict["js"] = js

    canary_dict["modules"] = modules

    #yaml_output = yaml.dump(canary_dict, default_flow_style=False)
    #logger.error("yaml_output is \n%s", yaml_output)

    return canary_dict



def to_app_path(file_path):
    """
    given a base file path like:
    p = "C:\\Program Files\\Splunk\\etc\\apps\\canary\\appserver\\modules\\HTML\\HTML.html
    it returns a weird relative path like
    "/modules/SomeModule/SomeModule.html"

    IT SEEMS LIKE THIS IS ONLY USED FOR HTML FILES.
    """

    if file_path.find(BASE_DIR) == 0:
        file_path = file_path.replace(BASE_DIR + os.path.sep, "")
        segments = file_path.split(os.path.sep)

        return "/" + "/".join(segments[4:])

    # I'm really not sure what this is, or if it's ever hit
    return "=" + file_path


def get_application_js(app):
    """ get the webserver path to the application.js file for this app if it exists"""
    if os.path.exists(os.path.join(get_static_file_path(app), "application.js")):
        return ["/static/app/%s/application.js" % app]
    return []


def is_theme_supported(ui_theme, splunk_config):
    supported_themes = splunk_config.get("SUPPORTED_THEMES", "light").split(",")
    for i, t in enumerate(supported_themes):
        supported_themes[i] = t.strip()
    return splunk_config.get("THEME","light") in supported_themes


def get_application_css(app, theme="light"):
    """ get the webserver path to the application.css file for this app if it exists"""
    filename = "application.css"
    if theme=="dark":
        filename = "application_dark.css"
    if os.path.exists(os.path.join(get_static_file_path(app), filename)):
        return [filename]
    return []

def get_custom_js_for_view(view_dict):
    """ get any custom css file for this app if it exists"""
    attribute_value = view_dict.get("js", view_dict.get("customJS", ""))
    if attribute_value == "":
        return []
    return attribute_value.split(",")


def get_custom_css_for_view(view_dict, app, theme="light"):
    """ get any custom css file for this app if it exists"""
    attribute_value = view_dict.get("css", view_dict.get("customCSS", ""))
    if attribute_value == "":
        return []
    file_names = attribute_value.split(",")
    if theme == "dark":
        for i, name in enumerate(file_names):
            name = name.replace(".css", "")
            if os.path.exists(os.path.join(get_static_file_path(app), file_names[i].replace(".css", "_dark.css"))):
                file_names[i] = name + "_dark.css"
            else:
                logger.debug("app %s ships a %s.css file but no %s_dark.css file", app, name, name)
    return file_names

def get_files_for_view(modules, module_conf, theme):
    """
    This gets lists of html, css and js files needed to render this particular view.
    It also returns the list of class names as a convenience.
    """
    module_html = {}
    module_css = []
    module_js = []
    class_names = []

    for mod in modules:
        if mod.get("pattern"):
            continue
        module_name = mod.get("module")


        files = module_conf.get(module_name, {})

        if "html" in files:
            module_html[module_name] = to_app_path(files["html"])
        if "css" in files and not files["css"] in module_css:
            module_css.append(files["css"])
        if "js" in files and not files["js"] in module_js:
            module_js.append(files["js"])
            class_names.append(module_name)
    return module_html, module_css, module_js, class_names



def validate_layout_panels(panels_used):
    """
    validates.
    """
    fails = []

    for panel_name in panels_used:
        if panel_name not in LEGAL_LAYOUT_PANELS:
            if panel_name.startswith("panel_row"):
                if panel_name.find("_grp") == -1:
                    continue
                #else:
                #    fails.append(INVALID_PANEL_MESSAGE % (panel_name,"Sorry the \"*_grp\" panels are not supported in Canary. Let us know you're seeing this though; we do respond to nagging."))
            else:
                fails.append(INVALID_PANEL_MESSAGE % (panel_name, ""))
    return fails



def commit_changes_to_view(request, view_element):
    app = request.app
    view = request.view
    user_name = request.user_name
    session_key = request.session_key

    remove_ids_from_all_modules(view_element)

    pretty_xml = et.tostring(view_element, pretty_print=True)

    pretty_xml = patch_xml_for_readability(pretty_xml)

    view_entity = en.getEntity('data/ui/views', view, namespace=app, owner=user_name, sessionKey=session_key)

    #garbagePropertiesReturnedBySplunk6Beta = ["isDashboard","isVisible","label"]
    #for p in garbagePropertiesReturnedBySplunk6Beta:
    #    if (view_entity.properties.get(p)):
    #        logger.warn("Sideview Editor - garbage property detected in the getEntity response (" + p + "). We are deleting it here or else it will correctly trigger an error from splunkd when we try to post the modified entity back via setEntity")
    #        del(view_entity.properties[p])

    # in the create new cases, view will be "_new"
    if request.action == "create" and request.view == "_new":
        view_entity.properties["name"] = request.post_dict["name"]

    view_entity[en.EAI_DATA_KEY] = pretty_xml

    try:
        en.setEntity(view_entity, sessionKey=session_key)
        ## remnants of some 4.X logging insanity where I never got a handle on root cause.
        #logger.info("view updated by Canary Editor. view=%s user=%s %s", view, user_name, updateMetaData)

    except Exception as e:
        logger.error("exception trying to update view.  view=%s user=%s message=%s", view, user_name, str(e))
        #logger.error(traceback.print_exc())
        raise

    # invalidate cache of views with this name in all apps for all users.
    # In splunk, these are likely to be copies (or partial copies) of the same view data.

    view_cache.invalidate(lambda tup: tup[2] == view)


def get_legal_values_for_module(module_class_name, module_conf):
    """ Vote for Pedro"""
    module_class = module_conf[module_class_name]
    values = {}
    params = module_class["params"]
    for param_name, param in params.items():
        new_entry = {}

        new_entry["required"] = param["required"]
        if "values" in param:
            new_entry["values"] = param["values"]
        values[param_name] = new_entry

    values["layoutPanel"] = {
        "required": False,
        "values": list(LEGAL_LAYOUT_PANELS)
    }
    return values

def static_file_exists(app, alleged_file_name):
    """ is there a file by the given name in /appserver/static of the given app. """
    possible_mixed_slashes = os.path.join(ETC_APPS_DIR, app, "appserver/static/")
    root_static_dir = os.path.abspath(possible_mixed_slashes)

    for name in os.listdir(root_static_dir):
        if name == alleged_file_name:
            return True
    return False

def get_view_attribute_error(attribute_name, legal_values, submitted_value, is_required):

    message = "ERROR - %s is not allowed as a value for %s. Set one of the allowed values - (%s)"
    if is_required:
        message += "."
    else:
        message += " or leave it blank."
    return message % (submitted_value, attribute_name, ", ".join(legal_values))


def set_params_for_module(module_element, module_params):

    for param in module_element.findall("param"):
        module_element.remove(param)

    module_class_name = module_element.get("name")

    for param_name in module_params:
        param_node = et.SubElement(module_element, "param")

        param_node.set("name", param_name)
        param_value = module_params.get(param_name)
        if is_list_param(module_class_name, param_name):
            set_list_param(param_node, param_value)

        elif is_big_param(module_class_name, param_name):
            param_node.text = et.CDATA(param_value)
        else:
            param_node.text = param_value




def is_big_param(module, param):
    """
    some module params, notably "html" in the HTML module and "search" in the
    Search module, are assumed to be generally very large, such that it is
    desirable to by default wrap the value in CDATA by default, even when this is
    not necessary.
    """
    for pair in BIG_PARAMS:
        if pair["module"] == module and pair["param"] == param:
            return True
    return False

def is_list_param(module_name, param):
    """
    Is the given param of the kind where it is a list of dictionaries and not
    a simple string value.
    """
    for param_dict in LIST_PARAMS:
        if param_dict["module"] == module_name and param_dict["param"] == param:
            return True
    return False

def set_list_param(param_node, json_str_value):
    json_value = json.loads(json_str_value)
    for item_dict in json_value:
        list_node = et.SubElement(param_node, "list")
        #enforce consistent order
        legal_names_in_order = ["name", "value", "label", "selected"]
        for name in item_dict:
            if name not in legal_names_in_order:
                raise ValueError("%s seems to be an illegal nested param for a %s param" % ( name, param_node.get("name")))

        for name in legal_names_in_order:
            if name not in item_dict:
                continue
            value = item_dict[name]
            inner_param_node = et.SubElement(list_node, "param")
            inner_param_node.set("name", name)
            inner_param_node.text = value
            list_node.append(inner_param_node)
        param_node.append(list_node)



VIEW_ATTRIBUTES = {
    #    "displayView": "(optional) If this attribute is set, and searches and reports are saved in this view,  when those searches and reports are run later they will be loaded within the given view rather than this view.",
    #    "refresh": "(optional) When set to an integer N, the view will automatically refresh every N seconds.",
    #    "onunloadCancelJobs": "(optional) When set to True, the page will try to cancel any outstanding ad-hoc jobs that are running at the time. Note that jobs loaded from permalinks, jobs from scheduled saved searches, and jobs that the user might have redirected into new windows, are never cancelled by this functionality. ",
    #    "autoCancelInterval": "(optional) If unset, defaults to 120.  value is given in seconds.  If a job is dispatched in this view and then the given number of seconds goes by with no requests to key endpoints such as /events, /results, /summary, /timeline or /touch,  the running job will be cancelled.",
    "template": "(optional) If unset, defaults to 'search.html'.  This determines the mako template for the page.  Be careful that the legal space of layoutPanel attributes is different for each template. For instance changing the template from dashboard.html to search.html will invalidate the view if there are any layoutPanels with the panel_rowN_colM syntax still in the view.",
    #    "isSticky": "(optional) If set to True, then a small number of modules will attempt to remember the value set for each user and restore that value when the view is loaded.  Note that if you leave this set to True for a while and then you change it to False,  whatever value was last set at that time for each user will continue to prepopulate for that user.  To truly wipe the memory of this system you'll have to hunt down and delete many many viewstate stanzas. ",
    #"isPersistable": "(optional) If set to True, then when a search or report is saved, Splunk's legacy viewstate system will try to 'snapshot' certain context keys that are present at the point where the search is being saved.   If True those snapshotted keys will be preserved in a viewstate entity that is linked to the savedsearch entity",
    "isVisible": "(optional) defaults to True.  This determines whether the view is visible in the navigation. Note that if the user has correct permissions to view this view,  then they will always be able to go to it by typing the URL into their browser directly, regardless of the setting here. ",
    "css": "(optional) When set to a value like 'foo.css', the system will look for a CSS stylesheet by that name within /etc/apps/<appName>/appserver/static.  If the stylesheet is found, it will be included in the page.  Note that if the app also has an 'application.css' file in that same directory, BOTH CSS files will be included..",
    "js": "(optional) Much the same as 'css' but with js files",
}

UNEDITABLE_VIEWS = {
    "sideview_utils":["controls", "description", "home", "editor_intro", "licensing"],
    "cisco_cdr":["home", "browse", "call_detail", "devices", "extensions", "gateways", "sites", "911_calls", "general_report", "gateway_utilization", "busy_hour_calculator", "extension_detail", "device_detail", "gateway_detail", "site_detail", "update_license", "setup_data_inputs", "setup_clusters", "setup_sites", "setup_groups", "setup_clusters", "setup_groups"]
}

DEAD_SIDEVIEW_UTILS_MODULES = ["SankeyChart", "TreeMap", "NavBar"]

LEGACY_SPLUNK_MODULES = [
    "AccountBar",
    "AddTotals",
    "AdvancedModeToggle",
    "AjaxInclude",
    "AppBar",
    "AsciiTimeline",
    "AxisScaleFormatter",
    "BaseChartFormatter",
    "BaseReportBuilderField",
    "BreadCrumb",
    "ButtonSwitcher",
    "CakeBrushFormatter",
    "ChartTitleFormatter",
    "ChartTypeFormatter",
    "ConditionalSwitcher",
    "ConvertToDrilldownSearch",
    "ConvertToIntention",
    "ConvertToRedirect",
    "Count",
    "DashboardTitleBar",
    "DataOverlay",
    "DisableRequiredFieldsButton",
    "DispatchingModule",
    "DistributedSearchServerChooser",
    "EnablePreview",
    "EntityLinkLister",
    "EntityRadioLister",
    "EntitySelectLister",
    "EventsViewer",
    "Export",
    "ExtendedFieldSearch",
    "FancyChartTypeFormatter",
    "FieldPicker",
    "FieldSearch",
    "FieldViewer",
    "FlashChart",
    "FlashTimeline",
    "FlashWrapper",
    "GenericHeader",
    "Gimp",
    "HiddenChartFormatter",
    "HiddenFieldPicker",
    "HiddenIntention",
    "HiddenPostProcess",
    "HiddenSavedSearch",
    "HiddenSearch",
    "HiddenSoftWrap",
    "IFrameInclude",
    "IndexSizes",
    "JSChart",
    "JobManager",
    "JobProgressIndicator",
    "JobStatus",
    "LegendFormatter",
    "LineMarkerFormatter",
    "LinkList",
    "LinkSwitcher",
    "LiteBar",
    "ManagerBar",
    "MaxLines",
    "Message",
    "MultiFieldViewer",
    "MultiplexSparkline",
    "NotReporting",
    "NullModule",
    "NullValueFormatter",
    "Paginator",
    "PostProcessBar",
    "PostProcessFilter",
    "PulldownSwitcher",
    "RadioButtonSearch",
    "ReportBuilderSearchField",
    "ReportSubType",
    "ReportType",
    "ResultsActionButtons",
    "ResultsHeader",
    "RowNumbers",
    "SavedSearches",
    "SearchBar",
    "SearchLinkLister",
    "SearchMode",
    "SearchRadioLister",
    "SearchSelectLister",
    "SearchTextSetting",
    "Segmentation",
    "Selector",
    "ServerSideInclude",
    "ShowHideHeader",
    "ShowSource",
    "SimpleDrilldown",
    "SimpleEventsViewer",
    "SimpleResultsHeader",
    "SimpleResultsTable",
    "SingleFieldChooser",
    "SingleValue",
    "SoftWrap",
    "Sorter",
    "SplitByChooser",
    "SplitModeFormatter",
    "StackModeFormatter",
    "StatChooser",
    "StaticContentSample",
    "StaticRadio",
    "StaticSelect",
    "SubmitButton",
    "SuggestedFieldViewer",
    "TabSwitcher",
    "TextSetting",
    "TimeRangeBinning",
    "TimeRangePicker",
    "TitleBar",
    "ViewRedirector",
    "ViewRedirectorLink",
    "ViewstateAdapter",
    "XAxisTitleFormatter",
    "YAxisRangeMaximumFormatter",
    "YAxisRangeMinimumFormatter",
    "YAxisTitleFormatter"
]

BIG_PARAMS = [{
    "module": "HTML",
    "param":"html"
}, {
    "module": "Search",
    "param":"search"
}, {
    "module": "PostProcess",
    "param":"search"
}
             ]

LIST_PARAMS = [{
    "module": "Pulldown",
    "param": "staticOptions",
    "keys": ["value", "label", "selected"]
}, {
    "module": "Pulldown",
    "param": "staticFieldsToDisplay",
    "keys": ["value", "label", "selected"]
}, {
    "module": "CheckboxPulldown",
    "param": "staticOptions",
    "keys": ["value", "label", "selected"]
}, {
    "module": "Pulldown",
    "param": "searchFieldsToDisplay",
    "keys": ["value", "label"]
}, {
    "module": "Tabs",
    "param": "staticTabs",
    "keys": ["value", "label", "selected"]
}, {
    "module": "Radio",
    "param": "staticRadios",
    "keys": ["value", "label", "selected"]
}, {
    "module": "Checkboxes",
    "param": "staticCheckboxes",
    "keys": ["value", "label", "selected"]
}, {
    "module": "StaticRadio",
    "param": "staticFieldsToDisplay",
    "keys": ["value", "label", "checked"]
}]

def build_splunkd_mgmt_url(url, rest_uri=None, rest_handler_params=None):
    """ Accepts a url such as /services/....
        returns a url such as https://localhost:8089:/services/...

        rest_uri -> 'https://127.0.0.1:8089'
        rest_handler_params -> { ..., 'server': { 'rest_uri' : 'https://127.0.0.1:8089', ... }, ...}
        The latter is the format of the junk that SplunkPersistentRestHandlers are fed
  """
    if url.startswith('http'):
        return url
    if not rest_uri and not rest_handler_params:
        raise Exception("Must provide a rest_uri or rest_handler_params")
    if not rest_uri:
        rest_uri = rest_handler_params['server']['rest_uri']
    if not url.startswith('/'):
        url = '/' + url
    return rest_uri + url
