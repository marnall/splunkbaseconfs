/*
Report Capture - Screenshot JS
Version 0.4

IMPORTANT:
Due to an issue with PhantomJS, PDF output is locked to A4.
Attempting to change this will result in weird scaling issues!

*/

/* Enable strict checking */
"use strict";

/* Logging Settings */
var CASPER_LOGLEVEL = 'debug';
var CASPER_VERBOSE  = true;
/* Required Options (defaults are used for the remainder) */
var REQ_OPTS = ['file', 'password', 'screen_height', 'screen_width', 'url', 'username', 'wait'];
/* Page HiDPI Setting */
var SCREEN_HIDPI = true;
/* Page Zoom Factor (default to zero) */
var SCREEN_ZOOMFACTOR = 1;

/* Global Variables - Non-Static */
var casper = null;
var opts   = {};


function checkOptions() {
    /* Check the required options are present and valid */
    casper.log('Checking required options are present and valid', 'debug');
    /* Check for the required options */
    for (var i = 0; i < REQ_OPTS.length; i += 1) {
        if (!(String(REQ_OPTS[i]) in opts)) {
            die('Missing option: ' + String(REQ_OPTS[i]));
        }
    }
    /* Timeout */
    if ((parseInt(opts.wait, 10) < 10) || (parseInt(opts.wait, 10) > 180)) {
        die('Specified wait setting is not valid');
    }
    /* HiDPI */
    if (typeof(opts.screen_hidpi) !== 'boolean') {
        die('Specified screen_hidpi setting is not a valid boolean');
    }
    /* Zoom Factor */
    if ((parseFloat(opts.screen_zoom) < 0) ||
        (parseFloat(opts.screen_zoom) > 4)) {
        die('Specified screen_zoom setting is not in range');
    }
}

function die(msg) {
    /* Handle a failure */
    if (casper) {
        casper.log('ERROR: ' + String(msg), 'error');
        casper.exit();
    }
    throw 'ERROR: ' + msg;
}

function getDocumentHeight(page) {
    /* Determine the height of the document from multiple sources
       as not all of them are accurate */
    var body = document.body;
    var html = document.documentElement;
    casper.log('Body Height (Scroll): ' + String(body.scrollHeight), 'debug');
    casper.log('Body Height (Offset): ' + String(body.offsetHeight), 'debug');
    casper.log('HTML Height (Client): ' + String(html.clientHeight), 'debug');
    casper.log('HTML Height (Scroll): ' + String(html.scrollHeight), 'debug');
    casper.log('HTML Height (Offset): ' + String(html.offsetHeight), 'debug');
    var footer_top = page.evaluate(getFooterTop);
    casper.log('Footer Bounding Top:  ' + String(footer_top), 'debug');
    var height = Math.max(body.scrollHeight, body.offsetHeight,
                          html.clientHeight, html.scrollHeight,
                          html.offsetHeight, footer_top);
    casper.log('Using height: ' + String(height), 'debug');
    return height;
}

function getDashboardPanelClip(page, pname) {
    /* Determine the boundary of the specified dashboard panel */
    var panel_stats = page.evaluate(function(s) {
        var panel = document.getElementById(String(s));
        if (!panel) {
            return [-1, -1, -1, -1];
        }
        var panelTop    = panel.getBoundingClientRect().top;
        var panelHeight = panel.getBoundingClientRect().height;
        var panelLeft   = panel.getBoundingClientRect().left;
        var panelWidth  = panel.getBoundingClientRect().width;
        return [panelTop, panelHeight, panelLeft, panelWidth];
    }, String(pname));
    if (!(panel_stats)) {
        casper.log('No panel stats returned');
        throw 'Panel not found';
    }
    if (panel_stats[0] == -1) {
        casper.log('Panel not found: ' + panel_stats.toString());
        throw 'Panel not found';
    }
    return panel_stats;
}

function mainExec() {
    /* Main execution */
    /* Create the initial casper object for arg-processing/logging */
    casper = require('casper').create({
        verbose:  CASPER_VERBOSE,
        logLevel: CASPER_LOGLEVEL
    });

    /* Configure the default config options (can be overriden via CLI) */
    casper.log('Setting default options', 'debug');
    opts.screen_hidpi = SCREEN_HIDPI;
    opts.screen_zoom  = SCREEN_ZOOMFACTOR;

    /* Parse the CLI args */
    casper.log('Parsing CLI arguments', 'debug');
    parseArgs();

    /* Check the passed options */
    checkOptions();

    /* Log the settings */
    casper.log('Settings Begin', 'debug');
    var keys = []
    for (var key in opts) {
        keys.push(key);
    }
    keys = keys.sort();
    for (var i = 0; i < keys.length ; i += 1) {
        if (keys[i] !== 'password') {
            casper.log('- ' + String(keys[i]) + ': ' + String(opts[keys[i]]), 'debug');
        } else {
            casper.log('- password: ********');
        }
    }
    casper.log('Settings End', 'debug');

    /* Create the real Casper object */
    casper.log('Creating Casper object', 'debug');
    try {
        casper = require('casper').create({
            verbose:  CASPER_VERBOSE,
            logLevel: CASPER_LOGLEVEL,
            viewportSize: {
                'height': parseInt(opts.screen_height, 10),
                'width':  parseInt(opts.screen_width, 10)
            },
            waitTimeout: parseInt(parseInt(opts.wait * 1000, 10), 10),
            zoomFactor:  parseFloat(opts.screen_zoom)
        });
    } catch (err) {
        die('Failed to create Casper object: ' + String(err));
    }

    /* Perform the initial login */
    casper.log('Performing Splunk authentication', 'debug');
    try {
        performLogin();
    } catch (err) {
        die('Failed to authenticate to Splunk: ' + String(err));
    }

    /* Enable retina mode (for high-quality images/charts etc) */
    // Note: This may not be active yet in the code version
    if (opts.screen_hidpi) {
        casper.log('Configuring pixel-ratio (HiDPI)', 'debug');
        try {
            casper.page.devicePixelRatio = 2;
        } catch (err) {
            casper.log('Failed to configure pixel-ratio, your CasperJS/PhantomJS version is too old', 'warning');
        }
    }

    /* Configure the capture */
    casper.log('Preparing capture job', 'debug');
    try {
        performCapture();
    } catch (err) {
        die('Failed to prepare capture job: ' + String(err));
    }

    /* Begin the job */
    casper.log('Beginning capture job', 'debug');
    try {
        casper.run();
    } catch (err) {
        die('Failed to execute job: ' + String(err));
    }
}

function parseArgs() {
    /* Parse any CLI args */
    var argc = 0;
    var argopt = null;
    while (casper.cli.has(argc)) {
        if (!argopt) {
            /* Store the new option-name */
            argopt = String(casper.cli.get(argc));
            if (argopt.charAt(0) === '-') {
                argopt = String(argopt.substr(1));
            }
        } else {
            /* Store the option and reset the arg-opt value */
            if ((String(casper.cli.get(argc)).toLowerCase() === 'true') ||
                (String(casper.cli.get(argc)).toLowerCase() === 'false')) {
                /* Boolean */
                opts[argopt] = (String(casper.cli.get(argc)).toLowerCase() === 'true');
            } else if (!(isNaN(casper.cli.get(argc)))) {
                /* Number */
                if (String(casper.cli.get(argc)).indexOf('.') != -1) {
                    /* Float */
                    opts[argopt] = parseFloat(casper.cli.get(argc));
                } else {
                    /* Integer */
                    opts[argopt] = parseInt(casper.cli.get(argc), 10);
                }
            } else {
                /* Other */
                opts[argopt] = String(casper.cli.get(argc));
            }
            argopt = null;
        }
        /* Increment the counter */
        argc += 1;
    }
}

function performCapture() {
    /* Wait for the page to load, then begin the capture */
    casper.then(function () {
        this.wait((opts.wait * 1000), function () {
            /* Clipping data (set later) */
            var clipRect = {};
            try {
                /* Remove the header from the page */
                this.page.evaluate(removeHeader);
                /* Remove the field-sets from the page */
                this.page.evaluate(removeFieldSet);
                /* Remove the background colour */
                this.page.evaluate(removeBGColour);
                /* Remove any opacity on the page */
                this.page.evaluate(removeOpacity);
                /* Remove any page-select controls */
                this.page.evaluate(removePaginator);
                /* Override the page dimensions (only if enabled) */
            } catch (err) {
                casper.log('Failed to manipulate page elements: ' + String(err), 'warning');
            }
            /* Determine the size of the capture */
            try {
                if (opts.panel) {
                    /* Panel specified, find it and size it */
                    casper.log('Panel ID: ' + String(opts.panel), 'debug');
                    /* Get the dimensions of the panel and update the clipping */
                    var panel = getDashboardPanelClip(this.page, opts.panel)
                    clipRect = {
                        'top':    parseInt(panel[0], 10),
                        'height': parseInt(panel[1], 10),
                        'left':   parseInt(panel[2], 10),
                        'width':  parseInt(panel[3], 10)
                    }
                } else {
                    /* No panel specified */
                    casper.log('No Panel specified, capturing full page', 'debug');
                    clipRect = {
                        'top':    0,
                        'height': parseInt(getDocumentHeight(this.page), 10),
                        'left':   0,
                        'width':  parseInt(opts.screen_width)
                    }
                }
            } catch (err) {
                die('Failed to determine clipping values: ' + String(err));
            }
            casper.log('Clip Top:    ' + String(clipRect.top), 'debug');
            casper.log('Clip Height: ' + String(clipRect.height), 'debug');
            casper.log('Clip Left:   ' + String(clipRect.left), 'debug');
            casper.log('Clip Width:  ' + String(clipRect.width), 'debug');
            /* Remove the footer (must be done after calculating the page height) */
            this.page.evaluate(removeFooter);
            casper.log('Creating image', 'debug');
            this.capture(String(opts.file), clipRect, {
                format: 'png',
                quality: 100
            });
            casper.log('Image created', 'debug');
        });
    });
}

function performLogin() {
    /* Perform the initial login to Splunk */
    casper.start(opts.url, function () {
        casper.waitForSelector('form.loginForm', function () {
            this.fill('form', {
                    username: String(opts.username),
                    password: String(opts.password)
                },
                true);
        });
    });
}

/*
   Functions for the rendered page:
   This code is ran in the context of the target page,
   NOT the current casper session.
*/

function getFooterTop() {
    /* Get the pixel value for the top of the splunk footer (used for cropping) */
    if ($('.splunk-footer').length) {
        /* Dashboard */
        return $('.splunk-footer').offset().top;
    } else if ($('footer').length) {
        /* Report */
        return $('footer').offset().top;
    } else {
        /* Unknown */
        return 0;
    }
}

function removeBGColour() {
    /* Remove the background colour */
    $('.dashboard-body').css('background-color','transparent');
    $('body').css('background', 'transparent');
}

function removeFieldSet() {
    /* Remove the Splunk Field-Settings/Actionbar/Time-Picker */
    if ($('.fieldset').length) {
        /* Dashboard */
        $('.fieldset').remove();
    }
    if ($('.report-actionbar').length) {
        /* Report */
        $('.report-actionbar').remove();
    }
    if ($('.job-bar').length) {
        $('.job-bar').remove();
    }
    if ($('.shared-timerangepicker').length) {
        /* Dashboard / Report */
        $('.shared-timerangepicker').remove();
    }
}

function removeFooter() {
    /* Remove the Splunk Footer */
    if ($('.splunk-footer').length) {
        /* Dashboard */
        $('.splunk-footer').remove();
    }
    if ($('footer').length) {
        /* Report */
        $('footer').remove();
    }
}

function removeHeader() {
    /* Remove the Splunk header */
    if ($('.dashboard-menu').length) {
        $('.dashboard-menu').remove();
    }
    if ($('.splunk-header').length) {
        $('.splunk-header').remove();
    }
    if ($('.report-message').length) {
        $('.report-message').remove();
    }
    if ($('header').length) {
        $('header').remove();
    }
}

function removePaginator() {
    /* Remove any page-dialogs */
    $('.splunk-paginator').each(function(i, obj) {
        obj.remove();
    });
    $('.report-tablecontrols').each(function(i, obj) {
        obj.remove();
    });
}

function removeOpacity() {
    /* Remove opacity on all elements */
    var nodes = document.querySelectorAll('*[stroke-opacity]');
    var elem = null, strokeOpacity = null;
    for (i = 0; i < nodes.length; i += 1) {
        elem = nodes[i];
        strokeOpacity = elem.getAttribute('stroke-opacity');
        elem.removeAttribute('stroke-opacity');
        elem.setAttribute('opacity', strokeOpacity);
    }
}


// Launch
mainExec();

