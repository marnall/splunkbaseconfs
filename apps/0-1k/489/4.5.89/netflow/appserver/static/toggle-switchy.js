require([
    'underscore',
    'jquery',
    'splunkjs/mvc',
    'splunkjs/mvc/simplexml/ready!',
    'splunkjs/ready!'
], function(_, $, mvc) {

        var defaultTokenModel = mvc.Components.get("default");
        var submittedTokenModel = mvc.Components.get("submitted");

        $(document).on("change", "#show_1line_btn", function() {
          var z = document.getElementById("show_1line_btn");
          if( $(z).prop('checked')){
            defaultTokenModel.set("show_1line","| dedup nfo_hostname device_ip"); 
            submittedTokenModel.set("show_1line","| dedup nfo_hostname device_ip"); 
          }
          else {
            defaultTokenModel.set("show_1line",""); 
            submittedTokenModel.set("show_1line",""); 
          }
        });

        $(document).on("change", "#show_inactive_interfaces_btn", function() {
          var z = document.getElementById("show_inactive_interfaces_btn");
          if( $(z).prop('checked')){
            defaultTokenModel.set("show_inactive_interfaces",""); 
            submittedTokenModel.set("show_inactive_interfaces",""); 
          }
          else {
            defaultTokenModel.set("show_inactive_interfaces","| search ifPktsChange>0"); 
            submittedTokenModel.set("show_inactive_interfaces","| search ifPktsChange>0"); 
          }
        });
        $(document).on("change", "#show_non_critical_interfaces_btn", function() {
          var z = document.getElementById("show_non_critical_interfaces_btn");
          if( $(z).prop('checked')){
            defaultTokenModel.set("show_non_critical_interfaces",""); 
            submittedTokenModel.set("show_non_critical_interfaces",""); 
          }
          else {
            defaultTokenModel.set("show_non_critical_interfaces","| lookup critical_interfaces_lookup nfo_hostname management_ip as mgmt_ip snmp_index as ifIndex OUTPUT comment | fillnull comment value=&quot;nullcomment&quot; | search comment!=&quot;nullcomment&quot;");
            submittedTokenModel.set("show_non_critical_interfaces","| lookup critical_interfaces_lookup nfo_hostname management_ip as mgmt_ip snmp_index as ifIndex OUTPUT comment | fillnull comment value=&quot;nullcomment&quot; | search comment!=&quot;nullcomment&quot;");
          }
        });
});
