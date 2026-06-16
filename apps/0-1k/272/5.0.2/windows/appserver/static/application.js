// Augment the help link
if( $('#WindowsMonitoringAppBar_0_0_0').size() > 0 ){
   // retrieve help link
   var helpLink = $('.WindowsMonitoringAppBar a.help').attr("href");
   
   // sample location string
   // location=%5BWindows%3A2.2.0%5D
   
   // replace "[Windows:" as "[WindowsApp:"
   helpLink = helpLink.replace('%5Bwindows%3A', '%5BWindowsApp%3A');
   
   // replace ":major.minor.revision]" as ":major.minor]"
   var appVersion = helpLink.match(/%3A(\d+\.\d+).*%5D/);
   
   if (appVersion != null) {
      helpLink = helpLink.replace(appVersion[0], '%3A'.concat(appVersion[1],'%5D'));
   }
   
   // update help link
   $('.WindowsMonitoringAppBar a.help').attr("href", helpLink);
}