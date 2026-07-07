equire([
     'jquery',
     'underscore',
     'splunkjs/mvc',
     'splunkjs/mvc/simplexml/ready!'
 ], function ($, _, mvc) {
     defaultTokenModel = mvc.Components.get("default");
     // All anchor tags close the Modal Pop Up
     $(document).on("click","#modalTableDrilldown a", function () {
         defaultTokenModel.set("tokHideShow", "hide fade");
     });
     // On click of table cell get Table Width and adjust Modal PopUp size
     $(document).on("click","#tableWithModalPopUp table tbody tr td", function(e){
         // viewWidth stores Table Width
         var viewWidth=e.view.innerWidth;
         // Show modal pop-up a bit below the current cell.
         var top = e.pageY+10;
         var left = e.pageX;
         //Adjust position when clicking extreme left side of the table. Modal window has width 400.
         if(left<400){
             left=left+400;
         }
         //Adjust position when clicking extreme right side of the table. Modal window has width 400.
         if(left+200>viewWidth){
             left=viewWidth-200;
         }
         $("#modalTableDrilldown").css({
             top: top,
             left: left
         });
     });
 });
