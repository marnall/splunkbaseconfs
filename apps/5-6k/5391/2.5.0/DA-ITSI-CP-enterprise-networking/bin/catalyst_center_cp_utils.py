"""
Utility methods for catalyst center service import
"""
from typing import List, Dict, Set

from catalyst_center_cp_constants import COMPOSITE_ID_LENGTH


def get_composite_title(site_name: str, site_id: str) -> str:
    """
    Returns a composite title of the form "siteName (abcdef)" where
    'abcdef' is the first N characters of the site ID.

    Args:
        site_name (str): The site name.
        site_id (str): The unique site ID.

    Returns:
        str: The formatted composite title.
    """
    site_name = site_name or "Unknown"
    return f"{site_name} ({site_id[:COMPOSITE_ID_LENGTH]})"


def build_catalyst_import(
        sites: List[dict],
        cisco_dnac_host: str,
        template: str,
        levels_to_import: int = 1,
        selected_sites: List[str] = None,
) -> List[List[str]]:
    """
    Build a list of rows to import catalyst sites as ITSI services
    :param sites: list of site to build import from
    :param cisco_dnac_host: the catalyst controller
    :param template: the service template name
    :param levels_to_import: number of site levels to import
    :param selected_sites: list of site IDs to import. If None, import all with
                           siteType == 'building'.
    :return: 2D list representing CSV rows
    """
    header = ["title", "dependencies", "cisco_catalyst_host", "siteHierarchy", "template"]
    rows = [header]

    # Build a map from title to service for quick lookup
    site_map = {svc.get("tags", {}).get("siteId", ""): svc for svc in sites}

    # Determine which services to process
    if selected_sites is None or len(selected_sites) == 0:
        selected_sites = [svc.get("tags", {}).get("siteId", "") for svc in sites if
                          svc.get("tags", {}).get("siteType") == "building"]

    composite_site_names: Dict[str, str] = {}
    top_level_site: Set[str] = set()
    for site_id in selected_sites:
        site = site_map.get(site_id)
        if not site:
            continue

        # add row for current site
        site_title = get_composite_title(site["title"], site_id)
        composite_site_names[site_id] = site_title
        site_hierarchy = site.get("tags", {}).get("siteHierarchy", "")
        row = [site_title, "", cisco_dnac_host, site_hierarchy, template]
        rows.append(row)

        # walk up the tree to add parents
        last_site_id = site_id
        site_id = site.get("tags", {}).get("parentSiteId", "")
        child_title = site_title
        level = 1
        while level < levels_to_import and site_id in site_map:
            site = site_map[site_id]

            # stop if we reach the Global service
            if site.get("tags", {}).get("siteType") == "global":
                break

            if site_id in composite_site_names:
                site_title = composite_site_names[site_id]
            else:
                site_title = get_composite_title(site["title"], site_id)
                composite_site_names[site_id] = site_title

            # add row for the parent
            site_hierarchy = site.get("tags", {}).get("siteHierarchy", "")
            row = [site_title, child_title, cisco_dnac_host, site_hierarchy, template]
            rows.append(row)

            # setup next iteration
            level += 1
            last_site_id = site_id
            site_id = site.get("tags", {}).get("parentSiteId", "")
            child_title = site_title

        # add the last service we imported to top_level_sites
        top_level_site.add(last_site_id)

    # add rows linking the root service (cisco_dnac_host) to top-level services
    root_service_name = f"Catalyst Center Host ({cisco_dnac_host})"
    for site_id in top_level_site:
        site = site_map.get(site_id)
        if not site:
            continue

        if site_id in composite_site_names:
            site_title = composite_site_names[site_id]
        else:
            site_title = get_composite_title(site["title"], site_id)
            composite_site_names[site_id] = site_title

        # root service has no template or entity filter rules
        row = [root_service_name, site_title, "", "", ""]
        rows.append(row)

    return rows
