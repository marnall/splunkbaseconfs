/**
* vim: tabstop=4 shiftwidth=4 softtabstop=4
*/
var focusedParams, customParams, soleraPopup, fieldReady,
	whichField, logger, currentEvent, lastEvent, IPv6Regex,
	IPv4Regex, IPValidChars;

focusedParams = {};
customParams = {};

/**
* Contains the popup that you get when you click on
* the magnifying class icon in each event.
*
* @param object
*/
soleraPopup = undefined;

/**
* Used to work around the ajaxComplete weirdness that
* occurs when I'm trying to hook the end of the field
* menu to rewrite the "Analyze with" and "Pcap" URLs
*
* @param bool
*/
fieldReady = false;

whichField = undefined;

logger = Splunk.Logger.getLogger("application.js");

currentEvent = undefined;
lastEvent = undefined;

/**
* @see http://forums.dartware.com/viewtopic.php?t=452
*/
IPv6Regex = /^((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))$/;
IPv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
IPValidChars = /[^0-9A-F:.]/gi;

/**
* jQuery Spin 1.1.1
*
* Fixes added by Tim to handle weirdness that happens
* with $(this) and variable scope.
*
* @author Naohiko Mori
* @author Tim Rupp <caphrim007@gmail.com>
* @copyright 2009
* @license MIT
* @license GPL
*/
(function($){
	var calcFloat = {
		get: function(num){
			var num, nn, po, st, sign;

			num = num.toString();
			if(num.indexOf('.') == -1) {
				return[0, eval(num)];
			}
			nn = num.split('.');
			po = nn[1].length;
			st = nn.join('');
			sign = '';
			if(st.charAt(0)=='-'){
				st = st.substr(1);
				sign = '-';
			}
			for(var i = 0; i < st.length; ++i) {
				if(st.charAt(0) == '0') {
					st = st.substr(1, st.length);
				}
			}
			st = sign + st;
			return [po, eval(st)];
		},

		getInt: function(num, figure) {
			var d, n, v1, v2;

			d = Math.pow(10, figure);
			n = this.get(num);
			v1 = eval('num * d');
			v2 = eval('n[1] * d');

			if(this.get(v1)[1]==v2) {
				return v1;
			}

			return (n[0]==0 ? v1 : eval(v2 + '/Math.pow(10, n[0])'));
		},

		sum: function(v1, v2) {
			var n1, n2, figure;

			n1 = this.get(v1);
			n2 = this.get(v2);
			figure = (n1[0] > n2[0] ? n1[0] : n2[0]);
			v1 = this.getInt(v1, figure);
			v2 = this.getInt(v2, figure);
			return eval('v1 + v2')/Math.pow(10, figure);
		}
	};

	$.extend({
		spin: {
			imageBasePath: Splunk.util.make_url('/static/app/SoleraDeepSeeApp/spin/') + '/',
			spinBtnImage: 'spin_button.gif',
			spinUpImage: 'spin_up.gif',
			spinDownImage: 'spin_down.gif',
			interval: 1,
			max: null,
			min: null,
			timeInterval: 500,
			timeBlink: 200,
			btnClass: null,
			btnCss: {cursor: 'pointer', padding: 0, margin: 0, verticalAlign: 'middle'},
			txtCss: {marginRight: 0, paddingRight: 0},
			lock: false,
			decimal: null,
			beforeChange: null,
			changed: null,
			buttonUp: null,
			buttonDown: null,
			padZero: false,
			padSpaces: 2
		}
	});

	$.fn.extend({
		spin: function(o){
			return this.each(function() {
				var opt, txt, spinBtnImage, btnSpin, spinUpImage,
				    btnSpinUp, spinDownImage, btnSpinDown, btn;

				o = o || {};
				opt = {};
				$.each($.spin, function(k,v){
					opt[k] = (typeof o[k]!='undefined' ? o[k] : v);
				});

				txt = $(this);
				spinBtnImage = opt.imageBasePath + opt.spinBtnImage;
				btnSpin = new Image();
				btnSpin.src = spinBtnImage;
				spinUpImage = opt.imageBasePath + opt.spinUpImage;
				btnSpinUp = new Image();
				btnSpinUp.src = spinUpImage;
				spinDownImage = opt.imageBasePath + opt.spinDownImage;
				btnSpinDown = new Image();
				btnSpinDown.src = spinDownImage;

				btn = $(document.createElement('img'));
				btn.attr('src', spinBtnImage);

				if(opt.btnClass) {
					btn.addClass(opt.btnClass);
				}

				if(opt.btnCss) {
					btn.css(opt.btnCss);
				}

				if(opt.txtCss) {
					txt.css(opt.txtCss);
				}

				txt.after(btn);

				if(opt.lock) {
					txt.focus(function(){txt.blur();});
				}

				function spin(vector) {
					var val, org_val, ret, diffLen, padStr, padValStr;

					val = txt.val();
					org_val = val;
					if(opt.decimal) {
						val = val.replace(opt.decimal, '.');
					}

					if(!isNaN(val)) {
						val = calcFloat.sum(val, vector * opt.interval);
						if(opt.min !== null && val < opt.min) {
							val = opt.max;
						}

						if(opt.max !== null && val > opt.max) {
							val = opt.min;
						}

						if(val != txt.val()){
							if(opt.decimal) {
								val = val.toString().replace('.', opt.decimal);
							}

							ret = ($.isFunction(opt.beforeChange) ? opt.beforeChange.apply(txt, [val, org_val]) : true);
							if(ret !== false){
								if (opt.padZero == true) {
									diffLen = opt.padSpaces - val.toString().length;
									padStr = "";
									for (var k = 0; k < diffLen; k++) {
										padStr += "0";
									}

									padValStr = padStr + val.toString();
									$('#' + txt.attr('id')).val(padValStr);
									txt.val(padValStr);
								} else {
									$('#' + txt.attr('id')).val(val);
									txt.val(val);
								}

								if($.isFunction(opt.changed)) {
									opt.changed.apply(txt, [val]);
								}

								txt.change();
								src = (vector > 0 ? spinUpImage : spinDownImage);
								btn.attr('src', src);

								if(opt.timeBlink < opt.timeInterval) {
									setTimeout(function () {
										btn.attr('src', spinBtnImage);
									}, opt.timeBlink);
								}
							}
						}
					}

					if(vector > 0) {
						if($.isFunction(opt.buttonUp)) {
							opt.buttonUp.apply(txt, [val]);
						}
					} else {
						if($.isFunction(opt.buttonDown)) {
							opt.buttonDown.apply(txt, [val]);
						}
					}
				}

				btn.mousedown(function(e) {
					var pos, vector, mBtn;

					pos = e.pageY - $(this).offset().top;
					vector = ($(this).height()/2 > pos ? 1 : -1);
					mBtn = $(this);

					(function () {
						var tk;
						spin(vector);
						tk = setTimeout(arguments.callee, opt.timeInterval);
						$(document).one('mouseup', function () {
							clearTimeout(tk); mBtn.attr('src', spinBtnImage);
						});
					})();

					return false;
				});
			});
		}
	});
})(jQuery);

function isIPv6(address) {
	return (IPv6Regex.test(address));
}

function isIPv4(address) {
	return (IPv4Regex.test(address));
}

/**
* Checks for empty addresses and removes non-IP characters
* from an address
*
* @param string address IP address to clean up
* @return string
*/
function cleanAddress(address) {
	if (empty(address)) {
		return '';
	} else {
		return trim(address.replace(IPValidChars, ''));
	}
}

function initCapPopup() {
	var start, stop;

	customParams = getCustomParams();
	start = focusedParams.start.split('.');
	stop = focusedParams.end.split('.');

	$("#start_year").val(start[0]);
	$("#start_month").val(start[1]);
	$("#start_day").val(start[2]);
	$("#start_hour").val(start[3]);
	$("#start_minute").val(start[4]);
	$("#start_second").val(start[5]);

	$("#stop_year").val(stop[0]);
	$("#stop_month").val(stop[1]);
	$("#stop_day").val(stop[2]);
	$("#stop_hour").val(stop[3]);
	$("#stop_minute").val(stop[4]);
	$("#stop_second").val(stop[5]);

	if (currentEvent === lastEvent) {
		if (empty(customParams['src_ip']) && !empty(focusedParams['src_ip'])) {
			setCustomParam('SoleraSourceAddress', focusedParams['src_ip']);
		}
		if (empty(customParams['src_port']) && !empty(focusedParams['src_port'])) {
			setCustomParam('SoleraSourcePort', focusedParams['src_port']);
		}
		if (empty(customParams['dest_ip']) && !empty(focusedParams['dest_ip'])) {
			setCustomParam('SoleraDestinationAddress', focusedParams['dest_ip']);
		}
		if (empty(customParams['dest_port']) && !empty(focusedParams['dest_port'])) {
			setCustomParam('SoleraDestinationPort', focusedParams['dest_port']);
		}
	} else {
		if (!empty(focusedParams['src_ip'])) {
			setCustomParam('SoleraSourceAddress', focusedParams['src_ip']);
		}
		if (!empty(focusedParams['src_port'])) {
			setCustomParam('SoleraSourcePort', focusedParams['src_port']);
		}
		if (!empty(focusedParams['dest_ip'])) {
			setCustomParam('SoleraDestinationAddress', focusedParams['dest_ip']);
		}
		if (!empty(focusedParams['dest_port'])) {
			setCustomParam('SoleraDestinationPort', focusedParams['dest_port']);
		}
	}
}

/**
* This is the grandmaster event for the event renderer as
* shown in the example custom event renderer in the splunk
* docs.
*/
function SoleraEventRendererHandler(event, options) {
	var type, target, field, value;

	type = options.nativeEvent.type;
	target = options.nativeEvent.target;

	/**
	* This method handles all clicks the happen on the
	* event row.
	*
	* There are two click events that I am interested
	* in for this function because I don't "know" how
	* they are handled otherwise.
	*
	* Those clicks are
	*
	*	1. On the drop arrow for fields
	*	2. On the drop arrow to the left of each event
	*/
	if (type == 'click') {
		/**
		* When _any_ click happens on the event row, I want
		* to capture it and update the current event details
		* like the timestamp for the event and the fields
		* shown for the event so that later if Solera specific
		* stuff is requested, those values are relevant only
		* that the event being operated on.
		*/
		focusedParams = {};

		lastEvent = currentEvent;
		currentEvent = $(options.nativeEvent.target).parents('.splEvent-SoleraEventRenderer').find('.pos').html();

		logger.info('Last event "' + lastEvent + '"');
		logger.info('Current event "' + currentEvent + '"');

		EventParams = $(options.nativeEvent.target).parents('.splEvent-SoleraEventRenderer').find('div.SoleraEventParams');
		focusedParams = {
			start : EventParams.find('input[name=SoleraTimespanStart]').val(),
			end : EventParams.find('input[name=SoleraTimespanEnd]').val(),
			src_ip : EventParams.find('input[name=SoleraEventSrcIp]').val(),
			src_port : EventParams.find('input[name=SoleraEventSrcPort]').val(),
			dest_ip : EventParams.find('input[name=SoleraEventDestIp]').val(),
			dest_port : EventParams.find('input[name=SoleraEventDestPort]').val(),
			protocol : EventParams.find('input[name=SoleraEventTrans]').val()
		};
		focusedParams['src_ip'] = cleanAddress(focusedParams['src_ip']);
		focusedParams['dest_ip'] = cleanAddress(focusedParams['dest_ip']);

		if ($(target).hasClass('actions')) {
			logger.info('Clicked the event actions menu');
			fieldReady = false;
			whichField = "actions";
		} else if ($(target).hasClass('fm')) {
			logger.info('Clicked the field actions menu');
			fieldReady = false;
			whichField = "fields";
		}
	}
}

/**
* Rewrites the Solera URI that is available in either the event
* actions or field actions menus.
*
* Event actions are items in the menu that is displayed when you
* click on the drop down menu to the left of the actual event data
*
* Fields are located below the event data. There are usually many
* fields such as "host", "sourcetype" and "source". The Field
* actions are items in the menu that is displayed when you click
* on the drop down menu to the right of the field value.
*
* This function will edit the URL in place.
*/
function rewriteSoleraUri() {
	DeepSeeUrl = $(".innerMenuWrapper a[target='_blank']");

	$(DeepSeeUrl).each(function(item){
		var linkTxt = $(this).html();
		if (linkTxt.indexOf('olera') < 0) {
			return;
		}

		if (whichField == 'actions') {
			logger.info('Rewriting URL for event actions menu');
			params = {
				'start': focusedParams.start,
				'end': focusedParams.end
			};
		} else {
			logger.info('Rewriting URL for event fields menu');
			params = focusedParams;
		}

		url = getDeepSeeUrl(params);

		logger.info('Generated URL ' + url);

		$(this).attr('href', url);
	});
}

/**
* Creates the "stuff" for the DeepSee or Merge Path URLs that
* is inbetween the suffix and prefix of the respective formats.
*
* For instance, all the common ipv4_address, tcp_port, etc
* parameters that the URLs can use.
*
* @param array params Javascript dict of params to stitch together
* @return string
*/
function makeUrlBody(params) {
	var url;

	url = '';

	if (!empty(params.protocol)) {
		if (!empty(params.src_port) && !empty(params.dest_port)) {
			url += params.protocol + '_port/';
			url += '/' + params.src_port + '_and_' + params.dest_port + '/';
		} else if (!empty(params.src_port)) {
			url += params.protocol + '_port/';
			url += '/' + params.src_port + '/';
		} else if (!empty(params.dest_port)) {
			url += params.protocol + '_port/';
			url += '/' + params.dest_port + '/';
		}
	}

	if (!empty(params.src_ip) && !empty(params.dest_ip)) {
		if (isIPv4(params.src_ip) && isIPv4(params.dest_ip)) {
			logger.info("Source and Dest IP were V4");
			url += '/ipv4_address/' + params.src_ip + '_and_' + params.dest_ip + '/';
		} else if (isIPv6(params.src_ip) && isIPv6(params.dest_ip)) {
			logger.info("Source and Dest IP were V6");
			url += '/ipv6_address/' + params.src_ip + '_and_' + params.dest_ip + '/';
		} else {
			logger.info("Source and Dest IP were unknown");
		}
	} else if (!empty(params.src_ip)) {
		if (isIPv4(params.src_ip)) {
			logger.info("Source IP was V4");
			url += '/ipv4_address/' + params.src_ip + '/';
		} else if (isIPv6(params.src_ip)) {
			logger.info("Source IP was V6");
			url += '/ipv6_address/' + params.src_ip + '/';
		} else {
			logger.info("Source IP was unknown");
		}
	} else if (!empty(params.dest_ip)) {
		if (isIPv4(params.dest_ip)) {
			logger.info("Dest IP was V4");
			url += '/ipv4_address/' + params.dest_ip + '/';
		} else if (isIPv6(params.dest_ip)) {
			logger.info("Dest IP was V6");
			url += '/ipv6_address/' + params.dest_ip + '/';
		} else {
			logger.info("Dest IP was unknown");
		}
	}

	return url;
}

/**
* URL format is
*
*	https://$host:$port/deepsee_reports?user=$usr&password=$pwd
*	#pathString=/timespan/$start-$stop/$ipproto_port/$srcport_and_$dstport/
*	ipv4_address/$srcip_and_$dstip/;reportIndex=0
*
* @param array params Javascript dict of params to stitch together
* @return string
*/
function getDeepSeeUrl(params) {
	var url, config;

	config = getSoleraConfig();
	if (config.port == 'none') {
		url = config.hostname;
	} else {
		url = config.hostname + ':' + config.port;
	}

	url += '/deepsee_reports?'
	+ 'username=' + config.username
	+ '&password=' + config.password
	+ '#pathString=/timespan/' + params.start + '.' + params.end + '/';

	url += makeUrlBody(params);

	url += ';reportIndex=0';
	url = 'https://' + url.replace(/[\/]+/g, '/');

	return url;
}

/**
* URL format is
*
*	https://$host:$port/ws/pcap?method=deepsee&
*	path=/timespan/$start-$stop/$ipproto_port/$srcport_and_$dstport/
*	ipv4_address/$srcip_and_$dstip/data.pcap&user=$usr&password=$pwd
*
* @param array
* @return string
*/
function getPcapUrl(params) {
	var url, config;

	config = getSoleraConfig();
	if (config.port == 'none') {
		url = config.hostname;
	} else {
		url = config.hostname + ':' + config.port;
	}

	url += '/ws/pcap?method=deepsee&path='
	+ '/timespan/' + params.start + '.' + params.end + '/';

	url += makeUrlBody(params);

	url += 'data.pcap&username=' + config.username
	+ '&password=' + config.password;

	url = 'https://' + url.replace(/[\/]+/g, '/');

	return url;
}

/**
* Retrieves the SoleraConfig values as defined in the solera.conf file
*
* These values are the ones parsed from the local ini file in the
* default/ and local/ directories. These values are parsed from the
* ini file by the event_renderer Python script.
*
* @return array
*/
function getSoleraConfig() {
	var result, SoleraConfig;

	result = {};

	// There appears to be no way to get the applications
	// config from inside javascript, so I have to resort
	// to pulling it from the HTML inside of the event
	// renderer. :((
	SoleraConfig = $($('.SoleraConfig')[0]);

	result = {
		username : SoleraConfig.find('input[name=SoleraUsername]').val(),
		password : SoleraConfig.find('input[name=SoleraPassword]').val(),
		hostname : SoleraConfig.find('input[name=SoleraHostname]').val(),
		port : SoleraConfig.find('input[name=SoleraPort]').val()
	};

	return result;
}

/**
* Reads the values from the popup window's "Custom" button
* and returns them.
*
* @return array
*/
function getCustomParams() {
	var result;

	result = {};

	timespanStart = $("#start_year").val()
	  + '.' + $("#start_month").val()
	  + '.' + $("#start_day").val()
	  + '.' + $("#start_hour").val()
	  + '.' + $("#start_minute").val()
	  + '.' + $("#start_second").val();

	timespanEnd = $("#stop_year").val()
	  + '.' + $("#stop_month").val()
	  + '.' + $("#stop_day").val()
	  + '.' + $("#stop_hour").val()
	  + '.' + $("#stop_minute").val()
	  + '.' + $("#stop_second").val();

	result = {
		action : $('#customDeepSee select[name="SoleraAction"]').val(),
		protocol : $('#customDeepSee select[name="SoleraProtocol"]').val(),
		src_ip : $('#customDeepSee input[name="SoleraSourceAddress"]').val(),
		src_port : $('#customDeepSee input[name="SoleraSourcePort"]').val(),
		dest_ip : $('#customDeepSee input[name="SoleraDestinationAddress"]').val(),
		dest_port : $('#customDeepSee input[name="SoleraDestinationPort"]').val(),
		start : timespanStart,
		end : timespanEnd
	};
	result['src_ip'] = cleanAddress(result['src_ip']);
	result['dest_ip'] = cleanAddress(result['dest_ip']);

	return result;
}

/**
* Sets a parameter in the "Custom" fields of the popup window
*
* @param string param Custom parameter to set in the popup window
* @param mixed value Value to set the custom parameter to
*/
function setCustomParam(param, value) {
	logger.info('Setting custom param "' + param + '" to value "' + value + '"');
	$('#customDeepSee input[name="' + param + '"]').val(value);
}

/**
* php.js array_merge
*
* @author Brett Zamir <http://brett-zamir.me>
* @author Nate
* @author josh
* @copyright 2010
* @license MIT
* @license GPL
*/
function array_merge () {
	var args = Array.prototype.slice.call(arguments), retObj = {}, k, j = 0, i = 0, retArr = true;
    
	for (i=0; i < args.length; i++) {
		if (!(args[i] instanceof Array)) {
			retArr=false;
			break;
		}
	}
    
	if (retArr) {
		retArr = [];
		for (i=0; i < args.length; i++) {
			retArr = retArr.concat(args[i]);
		}
		return retArr;
	}

	var ct = 0;
    
	for (i=0, ct=0; i < args.length; i++) {
		if (args[i] instanceof Array) {
			for (j=0; j < args[i].length; j++) {
				retObj[ct++] = args[i][j];
			}
		} else {
			for (k in args[i]) {
				if (args[i].hasOwnProperty(k)) {
					if (parseInt(k, 10)+'' === k) {
						retObj[ct++] = args[i][k];
					} else {
						retObj[k] = args[i][k];
					}
				}
			}
		}
	}

	return retObj;
}

/**
* php.js empty
*
* @author Philippe Baumann
* @author Onno Marsman
* @author Kevin van Zonneveld <http://kevin.vanzonneveld.net>
* @author LH
* @author Francesco
* @author Marc Jansen
* @author Stoyan Kyosev <http://www.svest.org/>
* @copyright 2010
* @license MIT
* @license GPL
*/
function empty (mixed_var) {
	var key;
    
	if (mixed_var === "" ||
		mixed_var === 0 ||
		mixed_var === "0" ||
		mixed_var === null ||
		mixed_var === false ||
		mixed_var === "none" ||
		mixed_var === "None" ||
		typeof mixed_var === 'undefined'
	){
		return true;
	}

	if (typeof mixed_var == 'object') {
		for (key in mixed_var) {
			return false;
		}
		return true;
	}

	return false;
}

/**
* php.js empty
*
* @author Kevin van Zonneveld <http://kevin.vanzonneveld.net>
* @author mdsjack <http://www.mdsjack.bo.it>
* @author Alexander Ermolaev <http://snippets.dzone.com/user/AlexanderErmolaev>
* @author Erkekjetter
* @author DxGx
* @author Steven Levithan <http://blog.stevenlevithan.com>
* @author Jack
* @author Onno Marsman
* @copyright 2010
* @license MIT
* @license GPL
*/
function trim (str, charlist) {
	var whitespace, l = 0, i = 0;
	str += '';
    
	if (!charlist) {
		// default list
		whitespace = " \n\r\t\f\x0b\xa0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u3000";
	} else {
		// preg_quote custom list
		charlist += '';
		whitespace = charlist.replace(/([\[\]\(\)\.\?\/\*\{\}\+\$\^\:])/g, '$1');
	}
    
	l = str.length;
	for (i = 0; i < l; i++) {
		if (whitespace.indexOf(str.charAt(i)) === -1) {
			str = str.substring(i);
			break;
		}
	}
    
	l = str.length;
	for (i = l - 1; i >= 0; i--) {
		if (whitespace.indexOf(str.charAt(i)) === -1) {
			str = str.substring(0, i + 1);
			break;
		}
	}
    
	return whitespace.indexOf(str.charAt(0)) === -1 ? str : '';
}

$(document).ready(function(){
	var uri;

	$("#start_month").spin({min:1,max:12,padZero:true});
	$("#start_day").spin({min:1,max:31,padZero:true});
	$("#start_year").spin({min:1970,max:2050});
	$("#start_hour").spin({min:0,max:23,padZero:true});
	$("#start_minute").spin({min:0,max:59,padZero:true});
	$("#start_second").spin({min:0,max:59,padZero:true});

	$("#stop_month").spin({min:1,max:12,padZero:true});
	$("#stop_day").spin({min:1,max:31,padZero:true});
	$("#stop_year").spin({min:1970,max:2050});
	$("#stop_hour").spin({min:0,max:23,padZero:true});
	$("#stop_minute").spin({min:0,max:59,padZero:true});
	$("#stop_second").spin({min:0,max:59,padZero:true});

	uri = Splunk.util.make_url('/static/app/', Splunk.util.getCurrentApp(), '/include.html');

	$.ajax({
		url: uri,
		dataType: 'html',
		success: function(resp, status) {
			$('body').append(resp);
		}
	});

});
$(document).bind("splEvent-SoleraEventRenderer", SoleraEventRendererHandler);

/**
* This is a rather poor way to hook into the field actions
* popup, but until one figures out what is being hooked
* by splunk to fire that trigger that updates the field
* actions, this is a "good enough" way to get what we want;
* the ability to manipulate the field actions after they
* have been created.
*/
$('*').ajaxComplete(function(e, xhr, settings) {
	if (fieldReady === true) {
		return;
	}

	if (settings.url.search("api/field/actions/") > -1) {
		fieldReady = true;
		rewriteSoleraUri();
	}
});

/**
* The inspect element is the magnifying class in each event
*/
$('.inspect').live('click', function(){
	var popup;

	initCapPopup();
	popup = new Splunk.Popup($('#inspectPopup'), {
		title : "Solera DeepSee",
		width: 360,
		pclass : "soleraPopupClass",
		buttons : [
			{
				label: 'Cancel',
				type : 'secondary',
				callback: function(){
					$(soleraPopup.getPopup()).find('.popupFooter .splButton-primary').hide();
					return true;
				}.bind(this)
			},
			{
				label: 'Submit',
				type : 'primary',
				callback: function(){
					var url;

					params = focusedParams;
					custom = getCustomParams();

					params = array_merge(params, custom);

					if (custom.action == 'deepsee') {
						url = getDeepSeeUrl(params);
					} else {
						url = getPcapUrl(params);
					}

					logger.info(url);
					$(soleraPopup.getPopup()).find('.popupFooter .splButton-primary').hide();
					window.open(url, "_blank");
					return true;
				}.bind(this)
			}
		]
	});

	/**
	* Splunk appears to erase the id attribute of my
	* HTML popup content when you init the Popup above.
	* So it's easiest to just store the created popup
	* object in a variable so that it can be referenced
	* later.
	*/
	soleraPopup = popup;
	$(popup.getPopup()).find('.popupFooter .splButton-primary').hide();
});

/**
* Handles clicking of the "DeepSee" button in the popup
* window. The Window orders the buttons as shown below.
* The button I'm referring to is pointed out below
*
*	 -----------    --------    ----------
*	|  DeepSee  |  |  PCAP  |  |  Custom  |
*    -----------    --------    ----------
*
*         ^
*     This one
*/
$('#DeepSeeBtn').live('click', function(){
	var url;

	logger.info('Clicked on DeepSee button');
	params = focusedParams;

	url = getDeepSeeUrl(params);
	logger.info(url);
	soleraPopup.destroyPopup();
	window.open(url, "_blank");
});

/**
* Handles clicking of the "PCAP" button in the popup
* window. The Window orders the buttons as shown below.
* The button I'm referring to is pointed out below
*
*	 -----------    --------    ----------
*	|  DeepSee  |  |  PCAP  |  |  Custom  |
*    -----------    --------    ----------
*
*                      ^
*                   This one
*/
$('#PcapBtn').live('click', function() {
	var url;

	logger.info('Clicked on PCAP button');
	params = focusedParams;

	url = getPcapUrl(params);
	logger.info(url);
	soleraPopup.destroyPopup();
	window.open(url, "_blank");
});

/**
* Handles clicking of the "Custom" button in the popup
* window. The Window orders the buttons as shown below.
* The button I'm referring to is pointed out below
*
*	 -----------    --------    ----------
*	|  DeepSee  |  |  PCAP  |  |  Custom  |
*    -----------    --------    ----------
*
*                                   ^
*                                This one
*/
$('#customDeepSeeBtn').live('click', function() {
	logger.info('Clicked on Custom button');

	if ($(this).hasClass('splButton-primary')) {
		$(soleraPopup.getPopup()).find('.popupFooter .splButton-primary').hide();
		$(this).removeClass('splButton-primary');
		$(this).addClass('splButton-secondary');
	} else {
		$(soleraPopup.getPopup()).find('.popupFooter .splButton-primary').show();
		$(this).removeClass('splButton-secondary');
		$(this).addClass('splButton-primary');
	}
	$('#customDeepSee').toggle();
});

