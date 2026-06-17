var debug=false

function log(message) {
	if (debug) { console.log(message); }
}

function escapeHTML(inp) {
    return inp.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function replacekeys(input,tokenActionArray) {
	  var output = input;
	  for (var r=0; r<tokenActionArray.length;r++) {
	    var pat = tokenActionArray[r][0];
	    var action = tokenActionArray[r][1];
	    var regexp = new RegExp(pat,"g");
 		log("Looking for " + pat + " in " + output + ".");
        if( output.match( regexp ) ) {
 		  log("Found " + pat + " in " + output + ".");
	      if( jQuery.isFunction( action ) ) {
			var result = regexp.exec(output);
			action = (action)(result[1]);
			log("Function for " + pat + " returned " + action + " from " + result[1] + ".");
          }
          log("Replacing "+pat+" in "+output+" with "+action);
          output = output.replace(regexp , ""+action);
        }
	  }
	  return output;
}

	strpTimeToRegex = new Array();
	strpTimeToRegex.push( ["%a" , '[A-Za-z]+'] );
	strpTimeToRegex.push( ["%A" , '[A-Za-z]+'] );
	strpTimeToRegex.push( ["%b" , '[A-Za-z]+'] );
	strpTimeToRegex.push( ["%B" , '[A-Za-z]+'] );
	strpTimeToRegex.push( ["%d" , '\\d{1,2}'] );
	strpTimeToRegex.push( ["%H" , '\\d{1,2}'] );
	strpTimeToRegex.push( ["%k" , '\\d{1,2}'] );
	strpTimeToRegex.push( ["%m" , '\\d{1,2}'] );
	strpTimeToRegex.push( ["%M" , '\\d{1,2}'] );
	strpTimeToRegex.push( ["%3N" , '\\d{1,3}'] );
	strpTimeToRegex.push( ["%6N" , '\\d{1,6}'] );
	strpTimeToRegex.push( ["%S" , '\\d{1,2}'] );
	strpTimeToRegex.push( ["%T" , '\\d{1,2}:\\d{2}:\\d{2}'] );
	strpTimeToRegex.push( ["%y" , '\\d{2}'] );
	strpTimeToRegex.push( ["%Y" , '\\d{4}'] );
	strpTimeToRegex.push( ["%z" , '[\\-\\=]?[\\d:]+'] );
	strpTimeToRegex.push( ["%:*z" , '[\\-\\=]?[\\d:]+'] );
	strpTimeToRegex.push( ["%Z" , '[A-Za-z]{3}'] );

	strpTimeToExample = new Array();
	strpTimeToExample.push( ["%a" , 'Thu'] );
	strpTimeToExample.push( ["%A" , 'Thu'] );
	strpTimeToExample.push( ["%b" , 'Oct'] );
	strpTimeToExample.push( ["%B" , 'Oct'] );
	strpTimeToExample.push( ["%c" , 'Thu Oct 13 13:55:36 2011'] );
	strpTimeToExample.push( ["%C" , "20"] );
	strpTimeToExample.push( ["%d" , '13'] );
	strpTimeToExample.push( ["%D" , "10/13/11"] );
	strpTimeToExample.push( ["%e" , "13"] );
	strpTimeToExample.push( ["%h" , "Oct"] );
	strpTimeToExample.push( ["%H" , "13"] );
	strpTimeToExample.push( ["%I" , " 1"] );
	strpTimeToExample.push( ["%j" , "286"] );
	strpTimeToExample.push( ["%m" , '10'] );
	strpTimeToExample.push( ["%M" , "55"] );
	strpTimeToExample.push( ["%n" , " "] );
	strpTimeToExample.push( ["%3N" , "132"] );
	strpTimeToExample.push( ["%6N" , "132658"] );
	strpTimeToExample.push( ["%p" , "PM"] );
	strpTimeToExample.push( ["%r" , "01:55:36 PM"] );
	strpTimeToExample.push( ["%R" , "13:55"] );
	strpTimeToExample.push( ["%S" , '36'] );
	strpTimeToExample.push( ["%t" , " "] );
	strpTimeToExample.push( ["%T" , "13:55:36"] );
	strpTimeToExample.push( ["%U" , "41"] );
	strpTimeToExample.push( ["%w" , "5"] );
	strpTimeToExample.push( ["%W" , "41"] );
	strpTimeToExample.push( ["%x" , "10/13/2011"] );
	strpTimeToExample.push( ["%X" , "13:55:36"] );
	strpTimeToExample.push( ["%y" , "11"] );
	strpTimeToExample.push( ["%Y" , '2011'] );
	strpTimeToExample.push( ["%z" , '-0700'] );
	strpTimeToExample.push( ["%:z" , '-07:00'] );
	strpTimeToExample.push( ["%::z" , '-07:00:00'] );
	strpTimeToExample.push( ["%Z" , 'MST'] );
	strpTimeToExample.push( ["%%" , '%'] );

	function unquote(format){
	  format = jQuery.trim(format).replace(/^"(.*)"$/,"$1");
	  format = format.replace(/\\"/g,"\"");
	  return format;
	//  return format.split(/\s+/);
	}
	
	
	function buildRegexFromDateFormat(format) {
	  return replacekeys(format.replace(/\./g,"\\."),strpTimeToRegex).replace(/\s+/g,"\\s+");
	}

    function buildDateExampleFromDateFormat(format)	{
      return replacekeys(format,strpTimeToExample);
    }
