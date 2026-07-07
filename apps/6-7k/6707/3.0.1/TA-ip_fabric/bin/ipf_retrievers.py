from typing import Optional

from ipfabric import IPFClient


def fetch_table(
    client: IPFClient,
    table_path: str,
    filters: Optional[dict] = None,
    reports: bool = False,
) -> list[dict]:
    """Fetch every row of an IP Fabric table via the URL-based endpoint.

    `table_path` is whatever the input stanza configures — anything from
    `/tables/security/acl/interfaces` to `technology/routing/bgp/neighbors`.
    The IPFClient handles leading-slash normalization internally.

    Pass `reports=True` to merge intent-check results into each row.
    Pass `filters={"and": [...]}` (parsed JSON) to scope the query.
    """
    return client.fetch_all(table_path, filters=filters, reports=reports)