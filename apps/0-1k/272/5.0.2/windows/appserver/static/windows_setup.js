//http://www.mail-archive.com/discuss@jquery.com/msg04261.html
jQuery.fn.reverse = [].reverse;
var WINDOWS_SETUP_NAMESPACES = ['winevtlog', 'winperfmon'];
var WINDOWS_SETUP_LIMITS = {};
WINDOWS_SETUP_LIMITS[WINDOWS_SETUP_NAMESPACES[0]] = 63;

// sorts a jQuery list obj with sortDescending a bool
function sortList(list, sortDescending) {
    var listitems = list.children('li:visible').get();
    listitems.sort(function(a, b) {
       var compA = $(a).text().toUpperCase();
       var compB = $(b).text().toUpperCase();
       if (sortDescending) {
          return (compA < compB) ? 1 : (compA > compB) ? -1 : 0;
       } else {
          return (compA < compB) ? -1 : (compA > compB) ? 1 : 0;
       }
    });
    $.each(listitems, function(idx, itm){ 
        list.append(itm); 
    });
}

// adds a specific attr set to an input object 
// and appends it to the provided helper
function addInput(helper, attrObj, value) {
    if (!( $(helper).children('input').size() > 0 )) {
        $('<input>')
            .attr(attrObj)
            .val(value)
            .appendTo(helper);
    }
}

function filterText(search_text, input, target) {
    var regex = new RegExp(search_text.replace('*', '.*'), 'i');
    $(target).children().each( function () {
        if ($(this).html().search(regex) == -1) {
            $(this).css('display', 'none');
        } else {
            $(this).css('display', '');
        }
    });
}

function toggleSort(list, target, desc) {
    desc = !desc;
    sortList(list, desc);
    if (desc === false) {
        $(target).text('Sort (desc)');
    } else {
        $(target).text('Sort (asc)');
    }
    return desc;
}

function isVisible(text, filter_text) {
    if (!(filter_text) || filter_text == null || filter_text == '') {
        return true;
    }
    var regex = new RegExp(filter_text.replace('*', '.*'), 'i');
    if (text.search(regex) == -1){
        return false;  
    } else {
        return true;
    } 
}

function bindLists(ns) {
    $('#' + ns + '_enabled li').unbind('click').click((function(ns) {
        return function (event){
            enabledToDisabled(event.target, ns);
            event.preventDefault();
        };
    }(ns))).disableSelection();
    $('#' + ns + '_disabled li').unbind('click').click((function(ns) {
        return function (event){
            disabledToEnabled(event.target, ns);
            event.preventDefault();
        };
    }(ns))).disableSelection();
}

function enabledToDisabled(target, ns) {
    var id = '#' + $(target).attr('id');
    $(target).parent().remove(id)
    $(target).children().remove();
    $(target).unbind('click').click((function(ns) {
        return function(event) {
            disabledToEnabled(event.target, ns);
        };
    }(ns)));
    if (!(isVisible($(target).html(), $('#' + ns + '_disable_filter').val()))) {
        $(target).css('display', 'none');
    }
    $('#' + ns + '_disabled').prepend(target);
}

function disabledToEnabled(target, ns) {
    var id = '#' + $(target).attr('id');
    $(target).parent().remove(id)
    addInput(target, {'type':'hidden','name': ns + 's'}, $(target).attr('id'));
    $(target).unbind('click').click((function(ns) {
        return function(event) {
            enabledToDisabled(event.target, ns);
        };
    }(ns)));
    if (!(isVisible($(target).html(), $('#' + ns + '_enable_filter').val()))) {
        $(target).css('display', 'none');
    }
    $('#' + ns + '_enabled').prepend(target);
}

$(document).ready(function (){
    // disable buttons on form submit and change text
    $('#windows_form').submit(function (event) {
        var bail = false;
        for (var i = 0; i < WINDOWS_SETUP_NAMESPACES.length; i++) {
            var ns = WINDOWS_SETUP_NAMESPACES[i];
            var limit = WINDOWS_SETUP_LIMITS[ns];
            if ((typeof limit !== 'undefined') && ($('#' + ns + '_enabled li').size() > limit)) {
                bail = true;
            }
        }
        if (bail) {
            $('<p>').attr('class', 'errorText')
                .text('Error: cannot monitor more than 63 event logs on one machine.')
                .appendTo($('.WindowsError')[0]); 
            event.preventDefault();
        } else {
            $('#windows_submit').attr('disabled', 'disabled').val('Please wait...')
                .next().attr('disabled', 'disabled');
        }
    });

    for (var i = 0; i < WINDOWS_SETUP_NAMESPACES.length; i++) {
        var ns = WINDOWS_SETUP_NAMESPACES[i];
        (function() {
            var enable_desc = false,
                disable_desc = false,
                search_text = {'enabled' : null, 'disabled': null},
                snapshot = {'enabled': null, 'disabled': null, 'radio': null};
            snapshot.enabled = $('#' + ns + '_enabled').html();
            snapshot.disabled = $('#' + ns + '_disabled').html();
            snapshot.radio = $('input[type=radio]:checked');
            
            // need to override reset behavior to handle evtlogs and not
            // break the filter inputs functionality (reset will nuke them)
            $('#windows_reset').click((function(ns) {
                return function (event){
                    $('.errorText').hide().html('');
                    $('#' + ns + '_enabled').html(snapshot.enabled);
                    $('#' + ns + '_disabled').html(snapshot.disabled);
                    $.each(snapshot.radio, function(){
                        $(this).attr('checked', 'checked'); 
                    });
                    $('#' + ns + '_enable_filter').val('');
                    $('#' + ns + '_disable_filter').val('');
                    bindLists(ns);
                    event.preventDefault();
                };
            }(ns)));
            // binding for clicks in the enabled or disabled lists
            bindLists(ns);
            // hook up the filters 
            // use type watch to avoid firing tons of events
            $('#' + ns + '_enable_filter').typeWatch({
                callback: (function(ns) {
                                return function() { 
                                  search_text.enabled = $('#' + ns + '_enable_filter').val(); 
                                  filterText(search_text.enabled, '#' + ns + '_enable_filter', '#' + ns + '_enabled'); 
                                  $('#' + ns + '_enabled').scrollTop(0);
                                };
                          }(ns)),
                wait: 600,
                captureLength: -1,
                highlight: false 
            });
            $('#' + ns + '_disable_filter').typeWatch({
                callback: (function(ns) {
                                return function() { 
                                  search_text.disabled = $('#' + ns + '_disable_filter').val(); 
                                  filterText(search_text.disabled, '#' + ns + '_disable_filter', '#' + ns + '_disabled'); 
                                  $('#' + ns + '_disabled').scrollTop(0);
                                };
                          }(ns)),
                wait: 600,
                captureLength: -1,
                highlight: false 

            });
            // hook up clicks on the filter clears
            $('#' + ns + '_enable_filter_clear').click((function(ns) {
                return function (event) {
                    if (!($('#' + ns + '_enable_filter').val() == '')) {    
                        $('#' + ns + '_enable_filter').val('');
                        $('#' + ns + '_enabled li').css('display', '');
                        enable_desc = toggleSort($('#' + ns + '_enabled'), 
                            '#' + ns + '_enable_sort', !enable_desc);
                    }
                    event.preventDefault();
                };
            }(ns)));
            $('#' + ns + '_disable_filter_clear').click((function(ns) {
                return function (event) {
                    if (!($('#' + ns + '_disable_filter').val() == '')) {    
                        $('#' + ns + '_disable_filter').val('');
                        $('#' + ns + '_disabled li').css('display', '');
                        disable_desc = toggleSort($('#' + ns + '_disabled'), 
                            '#' + ns + '_disable_sort', !disable_desc);
                    }
                    event.preventDefault();
                };
            }(ns)));
            // hook up sorting
            $('#' + ns + '_enable_sort').click((function(ns) {
                return function (event) {
                    enable_desc = toggleSort($('#' + ns + '_enabled'), 
                        event.target, enable_desc);
                    event.preventDefault();
                };
            }(ns)));
            $('#' + ns + '_disable_sort').click((function(ns) {
                return function (event) {
                    disable_desc = toggleSort($('#' + ns + '_disabled'), 
                        event.target, disable_desc);
                    event.preventDefault();
                };
            }(ns)));
            // hook up enable/disable all
            $('#' + ns + '_enable_move').click((function(ns) {
                return function (event) {
                    $('#' + ns + '_enabled li:visible').each(function () {
                        enabledToDisabled(this, ns); 
                    });
                    event.preventDefault();
                };
            }(ns)));
            $('#' + ns + '_disable_move').click((function(ns) {
                return function (event) {
                    $('#' + ns + '_disabled li:visible').each(function () {
                        disabledToEnabled(this, ns); 
                    });
                    event.preventDefault();
                };
            }(ns)));
        }());
    }
});
