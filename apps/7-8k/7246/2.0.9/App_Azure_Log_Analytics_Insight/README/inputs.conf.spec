[mde://<name>]
azure_account = Account that created only for capturing logs from MDE with Reader permission (AdvancedHunting.Read.All).
table_name = The name of the table from MDE Advanced Hunting where logs get stored.
query = Query should be in Azure Kusto Query Language (KQL) and Make sure it is optimized.
sourcetypes = azure:kql:defender:<Type of log>

[azure_kql://<name>]
azure_account = Account that created only for capturing logs with Application Insights Component Contributor or Reader permission.
azure_service = Please choose 'Log Analytics' if you are capturing logs from a log analytics service. Similarly, opt for 'Application Insights' if you are capturing logs from application insights.
workspace_app_id = Please enter 'Workspace ID' if you are capturing logs from a log analytics service. Similarly, Enter the 'Application ID' if you are capturing logs from application insights.
table_name = The name of the table in Azure service (Log Analytics or Application Insight) where logs get stored.
query = Query should be in Azure Kusto Query Language (KQL) and Make sure it is optimized.
sourcetypes = Tip: Web - azure:kql:web,  Change - azure:kql:change,  Authentication - azure:kql:auth,  Application Change - azure:kql:appchange, Inter-processing - azure:kql:Interprocessing.