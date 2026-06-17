Splunk.Module.SearchPerfTable = $.klass(Splunk.Module.DispatchingModule, {
	initialize: function($super, container) {
		$super(container);
		$(this.container).attr("style",this.getParam("style"));
	},
	onContextChange: function(context) {
                var t = document.getElementById("perf"), // This has to be the ID of your table, not the tag
                 d = t.getElementsByTagName("tr");
                 for (i in d) {
                    if (isNaN(i)){
                      console.log(i);
                    }else{
                      var clearrows=$(t.getElementsByTagName("td")[i]);
                      clearrows.html("");
                    }
                 }

	},
	onJobProgress: function(e) {
		this.renderSearchPerf("Job in progress");
	},
	onJobDone: function(e) {
		//Render the main plot...
		this.renderSearchPerf("Job done");
	},
	renderSearchPerf: function(msg) {
    var Parent = document.getElementById("perfbody");
    while(Parent.hasChildNodes())
    {
    Parent.removeChild(Parent.firstChild);
   
    }

		var context = this.getContext();
		var search  = context.get("search");
		var job = search.job;
		var data = job._performance;
                console.log("freds=",job);
                providers = job._searchProviders;
                scancount  = job._scanCount;
		sid = job._sid;
		diskUsage = job._diskUsage;
		runDuration = job._runDuration;
		eventSearch = job._eventSearch;
                eventCount = job._eventCount;
                EPS = Number(scancount/runDuration).toFixed(2);
                if(job._reportSearch == null) {
                  reportSearch = "Report search not used";
                  resultCount = "Results not reported due to no Report search.";
                }else{
                  reportSearch = job._reportSearch;
                  resultCount = job._resultCount;
                }
		search = job._search;
		$(".sptmsg",this.container).html(String(msg));
                var arr = {};
                var perfs={}; 
                var totalarr=[];
 
                function displayResult()
                {  
                var table=document.getElementById("perfbody");
                var row=table.insertRow(0);
                var cell1=row.insertCell(0);
                var cell2=row.insertCell(1);
                var cell3=row.insertCell(2);
                var cell4=row.insertCell(3);
                var cell5=row.insertCell(4);
                cell1.innerHTML=totalarr[i]['duration'];
                cell2.innerHTML=totalarr[i]['name'];
                cell3.innerHTML=totalarr[i]['invocations'];
                cell4.innerHTML=totalarr[i]['input'];
                cell5.innerHTML=totalarr[i]['output'];

                }
                
                for(i in data){
                    var changed=String(i.replace(/\./g, "\\."));
                    if(data[i]) {
                       perfs.name=String(i);
                      if(data[i]['invocations']){
                         perfs.invocations=String(data[i]['invocations']) ;
                      }else{
                         perfs.invocations="-";
                     }
                      if(data[i]['duration_secs']){
                         perfs.duration=Number(data[i]['duration_secs']).toFixed(2);
                      }else{
                         perfs.duration="-";
                      }
                      if(data[i]['input_count']){
                         perfs.input=Number(data[i]['input_count']);
                      }else{
                         perfs.input="-";
                      }
                      if(data[i]['output_count']){
                         perfs.output=Number(data[i]['output_count']);
                      }else{
                         perfs.output="-";
                      }
                      var item=String(i);
                      perfs.name=item;
                      totalarr.push(perfs);
                      perfs={}
                      arr={}
                    }

                    

               }
                $(".sid",this.container).html(String(sid));
                $(".diskUsage",this.container).html(String(diskUsage));
                $(".runDuration",this.container).html(String(runDuration));
                $(".eventSearch",this.container).html(String(eventSearch));
                $(".reportSearch",this.container).html(String(reportSearch));
                $(".search",this.container).html(String(search));
                $(".resultCount",this.container).html(String(resultCount));
                $(".providers",this.container).html(String(providers));
                $(".scancount",this.container).html(String(scancount));
                $(".eventCount",this.container).html(String(eventCount));
                $(".EPS",this.container).html(String(EPS));
                var len=totalarr.length;
                totalarr.sort(function(a, b){
                var nameA=a.name.toLowerCase(), nameB=b.name.toLowerCase()
                if (nameA > nameB) //sort string ascending
                   return -1
                if (nameA < nameB)
                   return 1
                return 0 //default return value (no sorting)
                })
                for (var i=0; i<len; ++i) {
                     if (i in totalarr) {
                         displayResult()
                     }
                }
	},
	resetUI: function() {}
});
