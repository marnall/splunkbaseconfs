[<input_name>]
connection = connection name in opseclea_connection.conf
data = Data to fetch, which can be non_audit(Non-Audit), audit(Firewall audits), fw(Firewall Audit), smartdefense(SmartDefense) and vpn(VPN)
index = Index of the fetched data
interval = Input interval in seconds
mode = Input mode which can be offline or online
host = Host(Optional)
starttime = Start time for fetching data(Optional)
noresolve = Parameter of resolve or no-resolve mode(Optional)
fields = fields to fetch back from OPSEC (Optional, default is empty and will fetch all fields back)
filter = only entries which match the filter rules will be fetched. (Optional, default is empty and will fetch all events back)
field_black_list = fields shown in the excluded fields side
field_white_list = fields shown in the included fields side