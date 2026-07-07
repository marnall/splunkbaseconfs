[insightvm_asset_import://<name>]
insightvm_connection = 
asset_filter = Asset filter to limit assets within scope (eg. "sites IN ['site-name']")
import_vulnerabilities = Select to enable the import of Asset Vulnerability Findings
vulnerability_filter = Vulnerability filter to limit vulnerabilities within scope (eg.  "cvss_v2_score > 6")
include_same_vulnerabilities = Select to enable the import of vulnerabilities that are not new or remediated since the last import
full_import_schedule = Number of days (up to 90) after which a full import will be forced. 0 always performs a full import

[insightvm_vulnerability_definition_import://<name>]
insightvm_connection = 
vulnerability_filter =