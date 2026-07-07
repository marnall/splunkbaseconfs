# README #
The infobutton app adds a JavaScript file and a CSS file to Splunk which enable the user to create dropdowns in panels on dashboards.

## Contents ##
Example dashboard: infobutton_example.xml
Infobutton JavaScript: infobutton.js
Infobutton CSS: infobutton.css

## Example usage ##
Add the following to the XML of the dashboard:

<dashboard script="ita_infobutton:infobutton.js" stylesheet="ita_infobutton:infobutton.css">
...
<row>
  <panel>
    <html>
      <div class="infobutton" parent="panel_id">
        [Content go here]
      </div>
    </html>
  </panel>
</row>
<row>
  <panel id="panel_id">
  ...