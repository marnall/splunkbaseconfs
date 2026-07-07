# Introduction

This application is an add-on that gathers data from your JBoss servers. It uses JMX interface and it has customizable list of attributes to retrieve. It was written as a complement of **[App for JBoss]**(http://apps.splunk.com/app/1804/). Please visit its site for more informations and use cases.

# Add-on features
*  Flexible and simple configuration
*  Works with JBoss AS 5,6 and 7 versions!
*  Built-in script for autodetection of your JMX interface

# Requirements
Add-on works with the following versions:
*  JBoss Application Server 5
*  JBoss Application Server 6
*  JBoss 7 (community edition)

## Platform
Currently this plugin runs on Linux, but can gather data from JBoss servers running on other platforms - see installation intructions below.

## Java
It requires **java** command to be included in **PATH**. It can be any java implementation with version **6** or higher.

## JBoss configuration
In order to retrieve values properly you need enable access to JMX interface. If your security policy doesn't allow you to pass traffic from external hosts you can use splunk forwarder and use traffic on loopback interface (via localhost).
 
For JBoss 6 and 7 you need to add the folowing stanza to your configuration file (e.g. *standalone.xml*) to be able to retrieve all configured data fields:

    <system-properties>
        <property name="org.apache.tomcat.util.ENABLE_MODELER" value="true"/>
    </system-properties>


It can be added just after the `extensions` closing tag (</extensions>). Alternatively only `<property name=...` can be put into `<system-properties>` tag if it already exists.

For JBoss 5 you need to define additional java options. Please add the following options to JBoss startup options (run.conf):

    JAVA_OPTS="$JAVA_OPTS -Dcom.sun.management.jmxremote.port=9999"
    JAVA_OPTS="$JAVA_OPTS -Dcom.sun.management.jmxremote.ssl=false"
    JAVA_OPTS="$JAVA_OPTS -Dcom.sun.management.jmxremote.authenticate=false"
    JAVA_OPTS="$JAVA_OPTS -Djboss.platform.mbeanserver"
    JAVA_OPTS="$JAVA_OPTS -Djavax.management.builder.initial=org.jboss.system.server.jmx.MBeanServerBuilderImpl"


**WARNING!**

Please note that above settings will disable authentication and are only useful when using Splunk Forwarder on your JBoss server (data transfer over loopback interface)!
If you want to enable authentication please set **-Dcom.sun.management.jmxremote.authenticate=true** and configure java security credentials in your JVM. More details can be found in [official java documentation](http://docs.oracle.com/javase/6/docs/technotes/guides/management/agent.html).


# Installation
* First you need to install **Add-on for JBoss** on your Splunk Forwarder. It can be either or the same machine as JBoss or the other provided that it can connect to JBoss JMX interface (see below).
* After you install the add-on you need to define JMX connection to JBoss. 

You can use a script included in the app. It's in **bin/** directory of the application:

    $SPLUNK_HOME/etc/apps/ta-jboss/bin/jmx-config.sh

When invoked without any options it will try to autodetect JMX interface on **localhost** interface. If you want to change default options (include user, password and ip address) then please take a look at options described in built-in help:

    $SPLUNK_HOME/etc/apps/ta-jboss/bin/jmx-config.sh -h

After you find your JMX interface you can use `-w` option to write it to the configuration file **$SPLUNK_HOME/etc/apps/local/inputs.conf**. 

    $SPLUNK_HOME/etc/apps/ta-jboss/bin/jmx-config.sh -h

Example config file may look like this:

    [script://./bin/jmxstats service:jmx:rmi://localhost/jndi/rmi://localhost:9999/jmxrmi]
    disabled = false
    index = jboss
    interval = 30
    source = jmxstats_localhost
    sourcetype = jmxstats

You can adjust it to your needs and add other inputs attributes.

Finally you can check on your Splunk Indexer or Search Head if there's any data in the **jboss** index.

# Contact
Add-On for JBoss development team:
*  Radosław Żak-Brodalko 
*  Grzegorz Hałajko 
*  Dariusz Kwaśny 
*  Tomasz Cholewa 

If you have any questions, please contact us at **splunk@linuxpolska.com**. Your feedback is welcome and will be much appreciated!


