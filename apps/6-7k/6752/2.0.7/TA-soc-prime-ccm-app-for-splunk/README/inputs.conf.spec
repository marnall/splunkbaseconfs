[socprime_tdm_api_input://<name>]
ccm_api_url = The API URL for integration with the SOC Prime Platform.
client_secret_id = Copy it from https://tdm.socprime.com/api-access/
job_names_list = Specify the names of Jobs configured in CCM. Format: ["<job1>", "<job2>", ... ].
splunk_default_host_port_list = May be necessary for remote content installation. Format: ["<splunk_host>:<port>"]. Default: ["localhost:8089"].
splunk_default_restapi_user = May be necessary for remote content installation.
splunk_default_restapi_password = May be necessary for remote content installation.
rule_exception_list = Optionally, specify rules to exclude from deployment. Format: ["<rule_name1>", "<rule_name2>", ... ].
force_updating_rules = Optionally, force synchronization of all savedsearches and parameters from CCM. Format: true/false. By default: true.
splunk_default_rules_owner = Optionally, assign owner to uploaded rules.