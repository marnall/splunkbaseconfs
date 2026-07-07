Hi Splunkers
this addon was created by Baha' Mahmoud & Mohammad Shahin to automate loki scanner on servers using Splunk Agent and deployment server.

########### Prerequisites:
1) install the add-on and unarchive it to add the below dependencies before deploying it

2) install Loki scanner from github, we prefer to use version 0.33 (most stable) "https://github.com/Neo23x0/Loki/releases/tag/0.33.0"
	2.1) copy {config, docs,plugins, tools, license, loki.exe} to the addon TA_loki/bin

3) install Loki master scanner from the github "https://github.com/Neo23x0/Loki"
	2.1) copy {loki-upgrader.py} to TA_loki/bin
	2.2) copy files inside {lib} to TA_loki/bin/lib

4) Splunk Agent on windows need to be running with admin privilage as loki scanners require that.

########### How to use:

1) After doing the above prerequisites archive the TA_Loki add-on and push it to the Splunk Deployment Server --> $SPLUNK_HOME/etc/deployment-apps 

2) copy 2 lib from TA_loki/bin/lib to $SPLUNK_HOME/lib/python3.7/site-packages/
	2.1) cp -R TA_loki/bin/lib/colorama $SPLUNK_HOME/lib/python3.7/site-packages/
	2.2) cp -R TA_loki/bin/lib/colorama-0.4.4.dist-info/ $SPLUNK_HOME/lib/python3.7/site-packages/

3) Run signature upgrade for loki, use same user running Splunk service (in my case Splunk user). the signature updater better to run before scanning devices interval
***if using $SPLUNK_HOME different than /opt/splunk change it in TA_loki/bin/update-signature.sh
	3.1) run:
		$SPLUNK_HOME/bin/splunk cmd $SPLUNK_HOME/etc/deployment-apps/TA_loki/bin/update-signature.sh
		or you can schedule it using crontab feature in Linux
		

4) set the interval of running inside inputs.conf 
	mkdir TA_loki/local
		[script://$SPLUNK_HOME\etc\apps\TA_Loki\bin\loki.bat]
		disabled = false
		index = <Index>
		sourcetype = loki_exec
		interval = 0 23 25-31 * <set your preference for scanning schedule>
	

########### Customization 

1) logs are written by default in %SPLUNKPATH%\var\log\TA_Loki, you can change it from TA_Loki/bin/loki.bat

2) scan runs on C: driver only, you can change it from TA_Loki/bin/loki.bat 