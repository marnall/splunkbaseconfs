(window["webpackJsonp"] = window["webpackJsonp"] || []).push([[3],{

/***/ 39:
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(0);
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(31);
/* harmony import */ var _splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(7);
/* harmony import */ var _splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(1);
/* harmony import */ var _splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _splunk_react_ui_Message__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(32);
/* harmony import */ var _splunk_react_ui_Message__WEBPACK_IMPORTED_MODULE_4___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Message__WEBPACK_IMPORTED_MODULE_4__);
/* harmony import */ var _splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(2);
/* harmony import */ var _splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5___default = /*#__PURE__*/__webpack_require__.n(_splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5__);
/* harmony import */ var _Utils_RequestUtils__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(23);
/* harmony import */ var _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(4);








var srcHome = Object(_splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5__["createStaticURL"])("app/".concat(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__["app"], "/images/Home-Demo.png"));
var srcAlerts = Object(_splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5__["createStaticURL"])("app/".concat(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__["app"], "/images/Alerts-Demo.png"));
var srcHosts = Object(_splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5__["createStaticURL"])("app/".concat(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__["app"], "/images/Hosts-Demo.png"));
var srcMetrics = Object(_splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5__["createStaticURL"])("app/".concat(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__["app"], "/images/Metrics-Demo.png"));
var header = "Welcome to the Splunk app for Unix";
var adminMessage = 'You need to configure this app before it will work!';
var nonAdminMessage = 'Ask your Splunk admin to configure this app before it will work!';
var redirectLink = 'settings';
var docsName = 'UnixApp';
var setupURI = "custom/".concat(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__["app"], "/unixsetup/").concat(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__["app"], "/check_setup");

var WelcomeModal = function WelcomeModal(props) {
  var handleConfigure = function handleConfigure(e) {
    props.modalCloser(e);
    window.open(redirectLink, "_self");
  };

  var handleCancel = function handleCancel(e) {
    props.modalCloser(e);
    Object(_Utils_RequestUtils__WEBPACK_IMPORTED_MODULE_6__[/* sendGetRequest */ "a"])(setupURI, {
      set_ignore: true
    });
  };

  var handleHelp = function handleHelp() {
    var docURL = Object(_splunk_splunk_utils_url__WEBPACK_IMPORTED_MODULE_5__["createAppDocsURL"])("app.".concat(_splunk_splunk_utils_config__WEBPACK_IMPORTED_MODULE_3__["app"], ".ftr"), {
      appName: docsName,
      appVersion: props.appVersion
    });
    window.open(docURL, "_blank");
  };

  var open = props.open;
  var isAdmin = props.isAdmin;
  var message_element;
  var configButton = /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(react__WEBPACK_IMPORTED_MODULE_0___default.a.Fragment, null);

  if (isAdmin) {
    configButton = /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_2___default.a, {
      appearance: "primary",
      label: "Configure",
      onClick: handleConfigure
    });
    message_element = /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Message__WEBPACK_IMPORTED_MODULE_4___default.a, {
      type: "warning"
    }, adminMessage);
  } else {
    message_element = /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Message__WEBPACK_IMPORTED_MODULE_4___default.a, {
      type: "warning"
    }, nonAdminMessage);
  }

  return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_1___default.a, {
    open: open,
    onRequestClose: props.modalCloser,
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalStyle */ "l"]
  }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_1___default.a.Header, {
    title: header,
    onRequestClose: props.modalCloser
  }), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_1___default.a.Body, {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalBodyStyle */ "i"]
  }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("table", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* imageTable */ "g"]
  }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("tbody", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("tr", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("td", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", null, "Real Time Monitoring ", /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("span", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalSpanStyle */ "k"]
  }, "- Home")), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("img", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalImage */ "j"],
    src: srcHome
  })), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("td", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", null, "System Topology ", /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("span", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalSpanStyle */ "k"]
  }, "- Hosts")), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("img", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalImage */ "j"],
    src: srcHosts
  }))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("tr", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("td", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", null, "Historical Analysis ", /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("span", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalSpanStyle */ "k"]
  }, "- Metrics")), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("img", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalImage */ "j"],
    src: srcMetrics
  })), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("td", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", null, "Alert Analysis ", /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("span", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalSpanStyle */ "k"]
  }, "- Alerts")), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("img", {
    style: _UnixSpiderGraphStyles__WEBPACK_IMPORTED_MODULE_7__[/* modalImage */ "j"],
    src: srcAlerts
  })))))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_1___default.a.Footer, null, message_element, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_2___default.a, {
    appearance: "secondary",
    label: "Cancel",
    style: {
      "float": 'Left'
    },
    onClick: handleCancel
  }), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_2___default.a, {
    appearance: "secondary",
    label: "Help",
    style: {
      "float": 'Left'
    },
    onClick: handleHelp
  }), configButton));
};

/* harmony default export */ __webpack_exports__["default"] = (WelcomeModal);

/***/ })

}]);