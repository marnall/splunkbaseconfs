require([
  "domReady",
  "jquery", 
  "jquery.ui.core",
  "jquery.bgiframe",
  "lowpro",
  "splunk.menu_builder",
  "bootstrap.transition",
  "bootstrap.affix",
  "bootstrap.alert",
  "bootstrap.modal",
  "bootstrap.dropdown",
  "bootstrap.scrollspy",
  "bootstrap.tab",
  "bootstrap.tooltip",
  "bootstrap.popover",
  "bootstrap.button",
  "bootstrap.collapse",
  "bootstrap.carousel",
  "bootstrap.typeahead",
  "shBrushXML", 
  "shBrushJS", 
  "shBrushPY", 
  "shCore"
  ],
  function(domReady) {
      var $side_nav = $(".sidebar-nav"),
          $top_nav = $(".top-nav"),
          $top_nav_pills = $(".nav-spy");

      domReady(function() {
        // enable syntax highlighter
        SyntaxHighlighter.defaults.toolbar = false;
        SyntaxHighlighter.highlight();
      });

      // affix the nav
      //$side_nav.affix();
      //$top_nav.affix();
     
      // scroll spy
      //$top_nav_pills.scrollspy();

      // binding for resize
      $(window).resize(function() {
          var win_width = $(this).width();
          if ($side_nav.hasClass('affix') === true) {
              $side_nav.width(Math.max(win_width/6.59, 199));
          } else {
              if ($side_nav.width() > 199) { 
                  $side_nav.width('100%');
              } else {
                  $side_nav.width(Math.max(win_width/6.59, 199));
              }
          }
      });
       
      // binding for scroll to trigger resize
      $(window).scroll(function() {
          $(this).trigger('resize'); 
      });
  }
);
