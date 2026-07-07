"""
How the navigation system works is described in detail in the following documentation
https://dev.splunk.com/enterprise/docs/developapps/createapps/addnavsplunkapp/

In short the navigation xml looks like the following.

<nav color={hexadecimal} search_view={view}>
    <view /> (0..n)
    <saved /> (0..n)
    <collection label={label}>
        <view /> (0..n)
        <saved /> (0..n)
        <a /> (0..n)
    </collection> (0..n)
    <a href={URL} target={target}>{text}</a> (0..n)
</nav>

The app has a pre-defined navigation in
TA-recordedfuture/default/data/ui/nav/default.xml
"""

from lxml import etree  # pylint: disable=import-error
from recordedfuture.api.splunk_api import SplunkClient
from recordedfuture.core.logging import setup_logging
from recordedfuture.core.utils import remove_query_params


""" App sub-pages """
HELP_APP_PAGES = [
    ("1_1_overview", "Overview"),
    ("releasenotes", "Latest Release"),
    ("1_4_install", "Install"),
    ("changelog", "Change log"),
    ("about", "About"),
]

""" Feature Setup sub-pages """
HELP_FEATURE_SETUP_PAGES = [
    ("3_alert_centre", "Alert Center"),
    ("4_1_rf_alerts_setup", "Recorded Future Alerts"),
    ("5_1_1_correlation_def_setup", "Default Correlations"),
    ("5_2_1_correlation_data_setup", "Data Model Correlations"),
    ("dashboards_enrichment", "Enrichment"),
    ("threat_hunt_dashboard", "Threat Hunt Dashboard"),
    ("21_sigma_rules", "Sigma Rules"),
    ("autonomous_threat_operations", "Autonomous Threat Operations"),
]

""" Splunk ES Integration sub-pages """
HELP_ENTERPRISE_SECURITY_PAGES = [
    ("2_0_es_overview", "Overview"),
    ("2_1_es_install", "Install"),
    ("2_4_adm", "Accelerated Data Model Correlations"),
    ("2_3_rba", "Setup Risk Based Alerting"),
    ("desc_conf_es", "Setup Security Feeds"),
    ("classic_and_pb_alerts_notable", "Setup Notables for Ingested Alerts"),
    ("2_5_sigma", "Setup Notables for Sigma Detections"),
    ("2_6_threat_hunt", "Setup Findings (Notables) for Threat Hunts"),
]

""" Help main pages """
HELP_MAIN_PAGES = [
    (HELP_APP_PAGES, "App"),
    (HELP_FEATURE_SETUP_PAGES, "Feature Setup"),
    (HELP_ENTERPRISE_SECURITY_PAGES, "Splunk ES Integration"),
    ("24_troubleshooting", "Troubleshoot"),
]

ALERT_CENTER = "Alert Center"

logger = setup_logging()


def get_current_menu(app_env=None, update=False):
    def _current_menu():
        if not app_env:
            return None

        splunk = SplunkClient(app_env)
        blob = splunk.ui.default_nav()
        current_nav = blob["entry"][0]["content"]["eai:data"]
        current_nav = etree.fromstring(
            current_nav, etree.XMLParser(remove_blank_text=True)
        )
        return current_nav

    if update:
        get_current_menu.menu = _current_menu()
        return get_current_menu.menu

    cached_menu = getattr(get_current_menu, "menu", None)
    if hasattr(cached_menu, "items"):
        return get_current_menu.menu

    menu = _current_menu()
    if not hasattr(menu, "items"):
        raise ValueError("There is no current menu, and no app_env provided")
    get_current_menu.menu = menu
    return menu


class BaseMenu(object):
    """Base menu object."""

    def _calculate_position(self, position):
        tree = get_current_menu()
        total_elements = len(tree.findall("./"))
        if position == -1:
            position = total_elements
        elif position < 0:
            position = total_elements + position + 1
        return position

    def _add_nav_item(self, tag, data, collection=None, text=None, position=0):
        """Add a new item to the nav tree."""
        tree = get_current_menu()
        new_element = tree.makeelement(tag, **data)

        position = self._calculate_position(position)

        if text:
            new_element.text = text
        if not collection:
            tree.insert(position, new_element)
            get_current_menu.menu = tree
        else:
            for element in tree.findall(".//collection"):
                if element.get("label") == collection:
                    element.insert(position, new_element)
                    get_current_menu.menu = tree
                    break
            else:
                raise ValueError("Collection %s does not exist" % collection)

    def _add_collection(self, name, position, collection=None):
        """Create a new collection in the nav tree."""
        tree = get_current_menu()
        new_element = tree.makeelement("collection", **{"label": name})

        position = self._calculate_position(position)

        if not collection:
            tree.insert(position, new_element)
            get_current_menu.menu = tree
        else:
            for element in tree.findall(".//collection"):
                logger.debug("Found collection: %s" % etree.tostring(element))
                if element.get("label") == collection:
                    element.insert(position, new_element)
                    get_current_menu.menu = tree
                    break
            else:
                raise ValueError("Collection %s does not exist." % collection)


class Link(BaseMenu):
    """Creates a `A` tag and inserts that into the navigation"""

    def __init__(self, text, collection=None, position=-1, **kwargs):
        self._add_nav_item(
            "a", data=kwargs, position=position, text=text, collection=collection
        )


class Collection(BaseMenu):
    """Creates a `Collection` tag and inserts that into the navigation"""

    def __init__(self, name, position=-1, collection=None):
        self._add_collection(name=name, position=position, collection=collection)


class View(BaseMenu):
    """Creates a `View` tag and inserts that into the navigation"""

    def __init__(self, collection=None, position=-1, **kwargs):
        self._add_nav_item(
            "view", data=kwargs, position=position, collection=collection
        )


class Menu(BaseMenu):
    """Menu object."""

    def __init__(self, app_env):
        self.app_env = app_env
        self.splunk = SplunkClient(app_env)
        self.config_entries = ["enrichment", "search", "custom"]
        self.correlation_view_id = "rfes_correlation_cached"
        get_current_menu(app_env)

    def delete_collection(self, name):
        """Remove a collection from a nav tree."""
        tree = get_current_menu(self.app_env)
        for element in tree.findall("collection"):
            if element.get("label") == name:
                tree.remove(element)
        get_current_menu.menu = tree

    def delete_view(self, name):
        """Delete view"""
        tree = get_current_menu(self.app_env)
        for element in tree.findall("view"):
            if element.get("name") == name:
                tree.remove(element)
        get_current_menu.menu = tree

    def delete_link(self, link):
        """Delete link"""
        tree = get_current_menu(self.app_env)
        for element in tree.findall("a"):
            if remove_query_params(element.get("href") or "") == link:
                tree.remove(element)
        get_current_menu.menu = tree

    def get_config_labels(self):
        """Get all configuration labels"""
        menu_labels = []

        for config in self.config_entries:
            config_data = self.app_env.get_stanzas(config)
            config_items = config_data.values()
            labels = set([e["menu_label"] for e in config_items])
            menu_labels.extend(labels)
        return menu_labels

    def reset_menu(self):
        """Reset the menu"""
        # Nav from v1.1
        old_labels = ["Enrich", "Correlate", "SOC", "Other", "Help", "Configuration"]

        old_labels.extend(self.get_config_labels())
        for label in old_labels:
            self.delete_collection(label)

        # Nav from v1.1
        self.delete_view("configuration")
        self.delete_view("rfes_alerts_list")
        self.delete_link("https://app.recordedfuture.com/live")

        # Nav from v2.1
        # Changed naming to rfes_alerts_list_v2, and moved it into package
        self.delete_view("rfes_alerts_list")
        # Nav from 2.1, ensuring duplicates won't appear.
        self.delete_view("rfes_alerts_list_v2")
        # From v2.1, needs to be deleted in case it's there since we always add it
        self.delete_view("sigma_detection")
        # From v2.1, needs to be deleted in case there are no correlation rules set up
        self.delete_view("alert_center")
        # From v2.1, needs to be deleted in case there are no correlation rules set up
        self.delete_view(self.correlation_view_id)
        # From v2.3, needs to be deleted in case it's there since we always add it
        self.delete_view("rfes_threathunt_dashboard")

        # From v2.6, needs to be deleted in case it's there since we always add it.
        self.delete_view("threathunt_dashboard")

        # From 2.8 we need to delete the overview dashboard since we always add  it
        self.delete_view("rfes_landing_page")

        # Nav from 2.0 and older, correlations used to have one view per rule stored in collection
        self.delete_collection("Correlations")

        # These are removed, but needs to be cleared as the system is upgraded:
        self.delete_collection("Help")
        self.delete_collection("Other")
        self.delete_collection("Alerting Rules")
        self.delete_collection("Alerts")
        # From 2.1 menu rework
        self.delete_collection("Search")
        self.delete_collection(ALERT_CENTER)
        self.delete_collection("Attack Surface Intelligence")
        self.delete_collection("Data")
        self.delete_collection("Docs")

    def create_docs_menu_section(self, name, menu_items, parent, base_path):
        """Create a submenu section of the Docs menu."""
        Collection(name, collection=parent)
        for page, text in menu_items:
            Link(
                href="{}{}".format(base_path, page),
                text=text,
                collection=name,
            )

    def create_docs_menu(self):
        """Create the help menu."""
        base_path = "/app/TA-recordedfuture/help?topic="
        self.delete_collection("Help")
        Collection("Docs", position=5)

        for key, value in HELP_MAIN_PAGES:
            if isinstance(key, list):
                self.create_docs_menu_section(value, key, "Docs", base_path)
            else:
                Link(href="{}{}".format(base_path, key), text=value, collection="Docs")

    def create_config_menus(self):
        """Create menus based settings

        Parses the recorded future settings and looks for the stanzas in
        self.config_entries. The stanza needs to contain 'view_id' and 'menu_label'
        for the function to generate the menu. Where the "menu_label" is the
        top level name.
        """
        for config_label in self.config_entries:
            self.app_env.logger.debug("config menus: %s", config_label)
            config_data = self.app_env.get_stanzas(config_label)
            config_items = sorted(
                config_data.values(),
                key=lambda x: int(x.get("menu_sort_order", "1")),
                reverse=False,
            )
            for num, value_dict in enumerate(config_items):
                if num == 0:
                    self.delete_collection(value_dict["menu_label"])
                    Collection(value_dict["menu_label"], position=4)
                View(name=value_dict["view_id"], collection=value_dict["menu_label"])

    def create_correlaton_menu(self):
        """Create the menu item used for the cached correlations view"""
        if self.app_env.correlations:
            View(name=self.correlation_view_id, collection=ALERT_CENTER, position=2)

    def create_ti_framework_menus(self):
        """Create the TI Framework config menu."""
        if self.app_env.es:
            View(name="ti_framework_list", collection="Configuration", position=3)

    def create_data_menu(self):
        """Create the other menu."""
        other_pages = ["dashboards", "data_models", "reports"]
        self.delete_collection("Other")
        self.delete_collection("SOC")
        self.delete_collection("Data")
        Collection("Data", position=3)
        for page in other_pages:
            View(name=page, collection="Data")

    def create_search_menu(self):
        """Create Search menu
        Search is generated in BFI, so try add and on failure recover by creating.
        """
        try:
            View(name="search", collection="Search", position=4)
        except ValueError:
            Collection(name="Search", position=2)
            self.create_search_menu()

    def create_base_menu(self):
        """Menu items for the base menu."""

        # NOTE: when adding more items above for other pages make sure landing
        # is positioned alphabetically.
        View(name="rfes_landing_page", position=0, default="true")

        Collection(name=ALERT_CENTER, position=1)
        View(name="alert_center", collection=ALERT_CENTER, position=0)
        View(name="rfes_alerts_list_v2", collection=ALERT_CENTER, position=1)
        View(name="sigma_detection", collection=ALERT_CENTER, position=3)
        View(name="playbook_alerts", collection=ALERT_CENTER, position=4)
        View(name="threathunt_runs", collection=ALERT_CENTER, position=5)

        Collection("Configuration", position=5)
        View(name="settings", collection="Configuration")
        View(name="alerts_configuration", collection="Configuration")
        View(name="correlations_list", collection="Configuration")
        View(name="sigma_configuration", collection="Configuration")

        View(name="threathunt_dashboard", position=3)

        Collection("Attack Surface Intelligence", position=4)
        View(name="asi_activity", collection="Attack Surface Intelligence")
        View(name="asi_risks", collection="Attack Surface Intelligence")
        View(name="asi_inventory", collection="Attack Surface Intelligence")
        View(name="asi_asset_investigator", collection="Attack Surface Intelligence")

        Link(
            href="https://app.recordedfuture.com/live?utm_source=splunk_3_2_1",
            target="_blank",
            text="Recorded Future Portal",
        )

    def _fetch_menu(self):
        """Convenience method for tests / debugging"""
        menu = get_current_menu(self.app_env)
        return etree.tostring(menu, pretty_print=True).decode("utf8").strip()

    def setup(self):
        """Set up the default menu
        The menu bar is essentially an array, positions index as 0 from the left
        Collections, i.e. dropdowns, also index from 0 starting from top.
        """
        self.app_env.refresh_config()
        self.app_env.logger.info("Self config: %s" % self.app_env.my_config)

        CURRENT_MENU = get_current_menu(self.app_env, update=True)

        self.reset_menu()
        self.create_config_menus()
        self.create_search_menu()
        self.create_data_menu()
        self.create_docs_menu()
        self.create_base_menu()
        # Correlation and TI are children of base_menu, so they must be after
        self.create_correlaton_menu()
        self.create_ti_framework_menus()
        self.splunk.ui.post_default_nav(CURRENT_MENU)
        self.splunk.config.reload()
