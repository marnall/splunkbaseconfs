
README for the Splunk Synthetic Monitoring and Web Optimization Add-on.
<h1>Overview</h1>
        <div>
        <p>Splunk Synthetic Monitoring and Splunk Web Optimization are services Splunk offers to customers with an online console for managing these performance analyses. These services help customers measure key performance metrics and solutions across their web based platforms in a couple of ways:</p>
        </div>
        <div style="padding-left: 50px;">
        <p>- Splunk Synthetic Monitoring measures your web site performance details using synthetic transactions from locations around the world.</p>
        <p>- Splunk Web Optimization deeply analyzes your web property to show performance of different components and direct specific improvements to your web code and implementation.</p>
        </div>
        <div>
        <p>This supporting add-on brings this data into the Splunk platform for use in regular SPL queries as well as ITSI searches that populate KPIs. This add-on creates a new command in your Splunk Search Processing Language (SPL) called <code>synthetics</code> that will bring your synthetic data into Splunk directly from these environments. This new <code>synthetics</code> command has a set of subcommands documented below that allow you to retrieve the right data. The results can be further processed using your SPL skills, or written to a local index using the collect SPL command. And using this new data, you can create a correlated view alongside whatever other data you have in Splunk, including your Log and Observability data. If you use the ITSI premium solution from Splunk, then use this new command to easily create KPIs and Services.
        </p>
        </div>
<h1>Learn More</h1>
        <p>Learn more about Splunk Synthetic Monitoring here: <a href="https://www.splunk.com/en_us/devops/synthetic-monitoring-use-case.html">https://www.splunk.com/synthetic-monitoring-use-case</a>
        </p>
        <p>Start your own free trial of Splunk Synthetic Monitoring here: <a href="https://www.splunk.com/en_us/form/splunk-synthetic-monitoring-free-trial.html">https://www.splunk.com/splunk-synthetic-monitoring-free-trial</a>
        </p>
        <p>Learn more about Splunk Web Optimization here: <a href="https://help.rigor.com/hc/en-us/articles/115006250447-Where-Should-I-Start-With-Splunk-Web-Optimization-">https://help.rigor.com/Where-Should-I-Start-With-Splunk-Web-Optimization</a>
        </p>
Command Description
        <div>The <code>synthetics</code> command in your SPL begins the connection to your Splunk Synthetic Monitoring environment. This command must begin with a "pipe", or "|" and followed by subcommands to access synthetic data.</div>

<h1>Command Syntax</h1>
        <div style="font-size: 15px;">
          <b>synthetics</b>
        </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics <i>(arguments)</i> | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Use this Generating Command in your Splunk Search Processing Language, and data is returned allowing you to process that data with further SPL.<br/>
          Usage:
          <code>| synthetics <i>(insert argument here)</i>
          </code>
        </div>
<h1>Command Arguments to get Web Optimization data</h1>
        <p>
          <div style="font-size: 15px;">
            <b>tests</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics tests | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get specific data about a test executed within your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics tests | spath</code>
            <br/>
        </div>
        </p>
        <p>
          <div style="font-size: 15px;">
            <b>test</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics tests test_id=&lt;int&gt; | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get specific data about a test executed within your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics test id=104505 | spath</code>
            <br/>
        </div>
        </p>
        <p>
          <div style="font-size: 15px;">
            <b>snapshots</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics snapshots test_id=&lt;int&gt; | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get specific data about all snapshots executed within your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics snapshots test_id=104505 | spath</code>
            <br/>
        </div>
        </p>
        <p>
          <div style="font-size: 15px;">
            <b>snapshot</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics snapshot test_id=&lt;int&gt; snapshot_id=&lt;int&gt; | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get specific data about a test and snapshot executed within your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics snapshot test_id=175384 snapshot_id=8204006066 | spath</code>
            <br/>
        </div>
        </p>
        <p>
          <div style="font-size: 15px;">
            <b>policies</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics policies | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get the list of policies within your Splunk Web Optimization environment.<br/>
          Usage: 
          <code>| synthetics policies | spath</code>
            <br/>
        </div>
        </p>
        <p>
          <div style="font-size: 15px;">
            <b>policy_checks</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics policy_checks defect_check_policy_id=&lt;int&gt; | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get specific data about what policies are present in your Splunk Web Optimization environment.<br/>
          Usage: 
          <code>| synthetics policy_checks defect_check_policy_id=4040 | spath</code>
            <br/>
        </div>
        </p>
        <p>
          <div style="font-size: 15px;">
            <b>defects</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics defects test_id=&lt;int&gt; snapshot_id=&lt;int&gt; | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get specific data about what defects were found on your website inluding fixes to improve your code.<br/>
          Usage: 
          <code>| synthetics defects test_id=175384 snapshot_id=8204006066 | spath</code>
            <br/>
        </div>
        </p>
<h1>Command Arguments to get Synthetic Monitoring data</h1>
        <div style="font-size: 15px;">
          <b>checks</b>
        </div>
        <p>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics checks | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get each of your configured "checks" from your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics checks | spath | table id, name, type, frequency, status.last_response_time, links.last_run</code>
            <br/>
        </div>
        </p>
        <p>
        <div style="font-size: 15px;">
          <b>kpi</b>
        </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics kpi id=&lt;int&gt; metric=&lt;string&gt; | <i>(further SPL)</i> </code>
            <br/>
          Description: Get a report on a specific KPI from your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics kpi id=175384 metric=dom_interactive_time_ms | timechart by browsers</code>
            <br/>
        </div>
        </p>
        <p>
        <div style="font-size: 15px;">
          <b>runs</b>
        </div>
        <div style="padding-left: 50px;">
          Syntax:
            <code> | synthetics runs id=&lt;int&gt; | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get data about what runs have been executed for a given check ID from your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics runs id=175384 | spath | table runs{}.id, runs{}.timestamp, runs{}.region_code, runs{}.share_link</code>
            <br/>
        </div>
        </p>
        <p>
          <div style="font-size: 15px;">
            <b>run</b>
          </div>
        <div style="padding-left: 50px;">
          Syntax: <code> | synthetics run id=&lt;int&gt; check_id=&lt;int&gt; | <i>(further SPL)</i>
            </code>
            <br/>
          Description: Get specific data about a run executed within your Splunk Synthetic Monitoring environment.<br/>
          Usage: 
          <code>| synthetics run id=175384 check_id=8204006066 | spath</code>
            <br/>
        </div>
        </p>
<h1>Getting Started</h1>
        <h3>Installation</h3>
        <p><div style="padding-left: 50px;">
          <p>1. Open the console for your Splunk instance.</p>
          <p>2. Install this add-on using the Apps menu or from Splunkbase.</p>
          <p>3. Open the App in your console for Splunk.</p>
          <p>4. Use the Configuration tab to provide API keys for your environment.</p>
          <p>5. Open the App to view these Dashboards:</p>
        </div></p>
        <div>
          <h3>Dashboards</h3>
          <p>
          <div style="padding-left: 50px;">
            <h3>Welcome</h3>
          </div>
          <div style="padding-left: 50px;">
          This screen shows the basic elements on using the new command, including
          examples to get you started.</div>
          </p>
          <p>
          <div style="padding-left: 50px;">
            <h3>Configuration</h3>
          </div>
          <div style="padding-left: 50px;">
          This screen has input boxes for specifying your API Keys that connect to both your Splunk Synthetic Monitoring environment and your Splunk Web Optimization environment. This is obtained by accessing the user interface for those services and navigating to your settings page and copying the API Keys.
          </div>
          </p>
          <p>
            <div style="padding-left: 50px;">
            <h3>Search</h3>
            </div>
            <div style="padding-left: 50px;">
          This screen merely displays the Search bar that all Splunk users have to access and manipulate machine data. This is provided for you to easily get to the Search bar to start using the <code> | synthetics</code> command within Splunk.
            </div>
          </p>
          <p>
            <div style="padding-left: 50px;">
            <h3>Splunk Synthetic Monitoring</h3>
            </div>
            <div style="padding-left: 50px;">
            This tab will take you to a set of Dashboards created to expose Splunk Synthetic Monitoring data using add-on. You can use these Dashboards as-is, or modify to include other data you want to see alongside other data. These Dashboards are titled:
            </div>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Synthetic Real Browser Checks</i>:</h4> Use the details about the Real Browser checks within your environment in several charts. Real Browser Checks include navigating to your web property with an actual browser and gathering metrics.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Synthetic API Checks</i>:</h4> Use details about the API checks within your environment and present metrics about the check performed on your API.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Synthetic HTTP Checks</i>:</h4> Use details about the HTTP (or uptime) checks within your environment and present metrics about the quick check performed on your endpoint's uptime.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Synthetic Benchmark Checks</i>:</h4> This Dashboard shows details about the Benchmark rankings you ahve created within your environment and presents rankings of how your web property compares to competitors you have created.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Synthetics KPI Browser</i>:</h4> Browse a list of the many different metrics possible using this tool. The dashboard has details of the KPI subcommands showing you the data within your environment.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Synthetics KPI Comparison</i>:</h4> This Dashboard shows how to compare the KPIs of different Runs within your environment and presents comparison timecharts of the KPI data about those different Checks.</div>
            </p>
          </p>
          <p>
            <div style="padding-left: 50px;">
            <h3>Splunk Web Optimization</h3>
            </div>
            <div style="padding-left: 50px;">
          This tab will take you to a set of Dashboards created to expose Splunk Web Optimization data using this add-on. You can use these Dashboards as-is, or modify to include other data you want to see alongside other data. These Dashboards are titled:
            </div>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Web Optimization Scores</i>:</h4> Use the performance details for your Web Optimization tests, such as scores, latencies, defects and sources in your Splunk instance.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Web Optimization Page Timings</i>:</h4> This dashboard shows the page timings such as First Paint, Dom Interactive, Blocking time and many others.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Web Optimization Improvements</i>:</h4> Use an automated detailed analysis of your page including very specific details about what improvements can be made to your web site such as using improved code or more effective implementation to improve performance.</div>
            </p>
          <p>
              <div style="padding-left: 100px;">
                <h4>
                <i>Web Optimization Policy Configurations</i>:</h4> View the Web Optimization Policies across your environment, including a direct link to modify defects and threshold settings.</div>
            </p>
          </p>
        </div>
        <h1>Use of this Splunk Synthetic Monitoring Add-on in ITSI</h1>
        <div class="pad_left">
          You can use this new supporting addon within ITSI to create KPI base searches and Services today. More information is available in the documentation for using the Content Pack here: https://docs.splunk.com/Documentation/ITSICP/current/Config/AboutSM<br/>
        </div>
