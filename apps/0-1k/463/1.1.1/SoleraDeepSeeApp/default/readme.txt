===== Installation as Standalone App =====

To install this splunk app as a standalone app, do the following.

1. Install splunk

2. Copy the SoleraDeepSeeApp.tar.gz file to /opt/splunk/etc/apps/

	cp SoleraDeepSeeApp.tar.gz /opt/splunk/etc/apps/

3. Change into the apps directory and extract the tarball

	cd /opt/splunk/etc/apps/
	tar zxvf SoleraDeepSeeApp.tar.gz

4. Restart splunk

5. Navigate to Splunk's "Launcher" and find the "Solera Networks DeepSee™ App for Splunk" app

6. Click the "Enable" link to enable the app.

7. Restart splunk

8. Navigate to Splunk's "Launcher" and find the "Solera Networks DeepSee™ App for Splunk" app

9. Click the app to be taken to the setup screen.

10. Change the Solera appliance settings to match your environment.

11. Save the changes.

12. Proceed to use the app as you would the normal Splunk Search app.


===== Installation as Splunk Search Override =====

These instructions should be followed only if you intend to override the
existing Splunk Search app.

One reason you may want to do this is because you do not want to have two
different search apps in Splunk. The Solera Networks DeepSee™ App for Splunk
app looks and behaves the same manner as the default Splunk Search app with
the exception that it has event renderer customizations that allow search
results to hook into DeepSee.

1. Install splunk

2. In your home directory, extract the SoleraDeepSeeApp.tar.gz tarball

	cd ~
	tar zxvf SoleraDeepSeeApp.tar.gz

3. Copy the following items into the default Splunk search app, overwriting
   the existing

	appserver/static/application.js
	appserver/static/application.css
	appserver/static/include.html
	appserver/static/inspect.png
	appserver/static/spin/

	bin/SoleraConfig.py

	default/eventtypes.conf
	default/restmap.conf
	default/setup.xml
	default/solera.conf
	default/workflow_actions.conf

4. Append the contents of the following files to their equivalents in the
   default Splunk search app.

	default/event_renderers.conf

5. Restart splunk

6. Follow steps 5 to 12 of the "Installation as Standalone App" instructions


===== Integration points =====

The Solera Networks app integrates Solera DeepSee at the following points

  - Event actions link to DeepSee for the timestamp (with a 5 minute buffer
    on each side) of the event

  - Field actions for the fields 'src_ip' and 'dest_ip' link to DeepSee for
    the timestamp (with a 5 minute buffer on each side) of the event and
    also includes the discovered source or destination IP address; a field
    recommended for use in the Splunk Common Information Model

  - Inspect functionality for each event.

    If the event has any of the fields src_ip, src_port, dest_ip, dest_port,
    they will be used to link to DeepSee for the timestamp (with a 5 minute
    buffer on each side) of the event.

  - Custom inspect functionality.

    Using the same inspect button mentioned in the previous bullet, a custom
    DeepSee path can be constructed and used to link to DeepSee.
