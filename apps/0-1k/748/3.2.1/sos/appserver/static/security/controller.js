function hitEndpoint(endpoint)
{
    var url = Splunk.util.make_url("custom", Splunk.util.getCurrentApp(), "health_controller", endpoint);
    raw_response = $.getJSON(url);
    raw_response.responseText;



}


var url = Splunk.util.make_url("custom", Splunk.util.getCurrentApp(), "health_controller", "check_ssl");


//$.getJSON(
  //        url,
    //      function(data){
//
  //            alert(data.msg);

    //          });


  //$.getJSON(url);
