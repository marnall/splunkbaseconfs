(window["webpackJsonp"] = window["webpackJsonp"] || []).push([[0],{

/***/ 40:
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(0);
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _splunk_react_ui_WaitSpinner__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(19);
/* harmony import */ var _splunk_react_ui_WaitSpinner__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_WaitSpinner__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(5);
/* harmony import */ var _splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(31);
/* harmony import */ var _splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(7);
/* harmony import */ var _splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_4___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_4__);
/* harmony import */ var _splunk_react_ui_Heading__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(12);
/* harmony import */ var _splunk_react_ui_Heading__WEBPACK_IMPORTED_MODULE_5___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Heading__WEBPACK_IMPORTED_MODULE_5__);
/* harmony import */ var _splunk_react_ui_Link__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(24);
/* harmony import */ var _splunk_react_ui_Link__WEBPACK_IMPORTED_MODULE_6___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Link__WEBPACK_IMPORTED_MODULE_6__);
/* harmony import */ var _HeadLinesUtils__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(20);
/* harmony import */ var _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(11);
/* harmony import */ var _HeadLinesConsts__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(21);
/* harmony import */ var _splunk_react_ui_SlidingPanels__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(33);
/* harmony import */ var _splunk_react_ui_SlidingPanels__WEBPACK_IMPORTED_MODULE_10___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_SlidingPanels__WEBPACK_IMPORTED_MODULE_10__);
/* harmony import */ var _splunk_react_ui_Paragraph__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(34);
/* harmony import */ var _splunk_react_ui_Paragraph__WEBPACK_IMPORTED_MODULE_11___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Paragraph__WEBPACK_IMPORTED_MODULE_11__);
/* harmony import */ var _splunk_react_ui_Text__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(35);
/* harmony import */ var _splunk_react_ui_Text__WEBPACK_IMPORTED_MODULE_12___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Text__WEBPACK_IMPORTED_MODULE_12__);
/* harmony import */ var _splunk_react_ui_Select__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(9);
/* harmony import */ var _splunk_react_ui_Select__WEBPACK_IMPORTED_MODULE_13___default = /*#__PURE__*/__webpack_require__.n(_splunk_react_ui_Select__WEBPACK_IMPORTED_MODULE_13__);
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }
















var HeadlinesModal = /*#__PURE__*/function (_Component) {
  _inherits(HeadlinesModal, _Component);

  var _super = _createSuper(HeadlinesModal);

  function HeadlinesModal(props) {
    var _this;

    _classCallCheck(this, HeadlinesModal);

    _this = _super.call(this, props);

    _defineProperty(_assertThisInitialized(_this), "manageHeadLines", function () {
      Object(_HeadLinesUtils__WEBPACK_IMPORTED_MODULE_7__[/* sendGetRequest */ "a"])(_HeadLinesConsts__WEBPACK_IMPORTED_MODULE_9__[/* manageHeadlineURI */ "d"], {}).then(function (response) {
        _this.setState({
          isLoading: false,
          data: response.data.headlines
        });
      });
    });

    _defineProperty(_assertThisInitialized(_this), "handleSort", function (e, _ref) {
      var sortKey = _ref.sortKey;

      _this.setState(function (state) {
        var prevSortKey = state.sortKey;
        var prevSortDir = prevSortKey === sortKey ? state.sortDir : 'none';
        var nextSortDir = prevSortDir === "asc" ? "desc" : "asc";
        return {
          sortKey: sortKey,
          sortDir: nextSortDir
        };
      });
    });

    _defineProperty(_assertThisInitialized(_this), "handleChange", function (e, _ref2) {
      var name = _ref2.name,
          value = _ref2.value;

      _this.setState(_defineProperty({}, name, value));
    });

    _defineProperty(_assertThisInitialized(_this), "handleRequestOpen", function () {
      _this.setState({
        open: true
      });
    });

    _defineProperty(_assertThisInitialized(_this), "resetSelection", function () {
      _this.setState({
        label: "",
        name: "",
        description: "",
        message: "",
        data: [],
        sortKey: "label",
        sortDir: "asc",
        errors: []
      });
    });

    _defineProperty(_assertThisInitialized(_this), "handleRequestClose", function (e) {
      if (e.reason !== "clickAway") {
        _this.setState({
          open: false,
          isLoading: true,
          activePanelId: "manage",
          activePanelAction: "Create New Headline",
          label: "",
          name: "",
          alert_name: "",
          description: "",
          message: "",
          panelKey: "",
          panelTitle: "",
          data: [],
          alerts: [],
          errors: []
        });

        _this.props.handleClose();
      }
    });

    _defineProperty(_assertThisInitialized(_this), "handleActionClick", function (e, _ref3) {
      var value = _ref3.value;

      if (value == "manage") {
        Object(_HeadLinesUtils__WEBPACK_IMPORTED_MODULE_7__[/* sendGetRequest */ "a"])(_HeadLinesConsts__WEBPACK_IMPORTED_MODULE_9__[/* newHeadlineURI */ "e"], {}).then(function (response) {
          _this.setState({
            alert_name: response.data.alerts[0].name,
            alerts: response.data.alerts
          });
        });

        _this.setState({
          activePanelId: "create"
        });

        _this.setState({
          activePanelAction: "Create New Headline"
        });

        _this.setState({
          panelKey: "create"
        });

        _this.setState({
          panelTitle: "Create Headline"
        });
      } else if (value == "create") {
        _this.setState({
          name: "_new"
        }, function () {
          return _this.saveHeadline();
        });
      } else if (value == "edit") {
        _this.saveHeadline();
      } else if (value == "success") {
        _this.setState({
          isLoading: true
        });

        _this.manageHeadLines();

        _this.setState({
          activePanelId: "manage"
        });

        _this.setState({
          activePanelAction: "Create New Headline"
        });
      }
    });

    _defineProperty(_assertThisInitialized(_this), "deleteHeadline", function (name, label) {
      var cnfrm = confirm("Delete headline '" + JSON.stringify(label) + "'?");

      if (cnfrm === true) {
        Object(_HeadLinesUtils__WEBPACK_IMPORTED_MODULE_7__[/* sendPostRequest */ "b"])(_HeadLinesConsts__WEBPACK_IMPORTED_MODULE_9__[/* deleteHeadlineURI */ "a"], {
          'name': name
        }, false).then(function (response) {
          if (response.data.success === "true") {
            _this.setState({
              isLoading: true,
              sortKey: "label",
              sortDir: "asc"
            }, function () {
              return _this.manageHeadLines();
            });
          } else console.log(response.data.error);
        })["catch"](function (error) {
          console.error('error deleting headline: ' + label);
        });
      }
    });

    _defineProperty(_assertThisInitialized(_this), "validateParams", function (params, requiredParams) {
      var inValidValueParams = [];
      requiredParams.map(function (param) {
        if (params[param] == "") {
          inValidValueParams.push(param);
        }
      });

      if (inValidValueParams.length > 0) {
        var errorMessage = "The following required arguments are missing: ".concat(inValidValueParams.join(", "), ".");

        _this.setState({
          errors: [errorMessage]
        });

        return false;
      } else {
        return params;
      }
    });

    _defineProperty(_assertThisInitialized(_this), "saveHeadline", function () {
      var description = _this.state.description === "" ? "None" : _this.state.description;
      var params = {
        'name': _this.state.name.trim(),
        'label': _this.state.label.trim(),
        'alert_name': _this.state.alert_name.trim(),
        'description': description.trim(),
        'message': _this.state.message.trim()
      };

      var validatedParams = _this.validateParams(params, ['label', 'message']);

      if (validatedParams) {
        Object(_HeadLinesUtils__WEBPACK_IMPORTED_MODULE_7__[/* sendPostRequest */ "b"])(_HeadLinesConsts__WEBPACK_IMPORTED_MODULE_9__[/* saveHeadlineURI */ "f"], params, false).then(function (response) {
          _this.resetSelection();

          if ('success' in response.data) {
            _this.setState({
              activePanelId: "success"
            });

            _this.setState({
              activePanelAction: "OK"
            });
          } else if (response.data.headline.length > 0 && 'errors' in response.data.headline[0]) _this.setState({
            errors: response.data.headline[0].errors
          });
        });
      }
    });

    _defineProperty(_assertThisInitialized(_this), "editHeadline", function (name, label) {
      _this.setState({
        activePanelId: "edit"
      });

      _this.setState({
        activePanelAction: "Update Headline"
      });

      _this.setState({
        panelKey: "edit"
      });

      _this.setState({
        panelTitle: "Edit Headline"
      });

      Object(_HeadLinesUtils__WEBPACK_IMPORTED_MODULE_7__[/* sendGetRequest */ "a"])(_HeadLinesConsts__WEBPACK_IMPORTED_MODULE_9__[/* getHeadlineURI */ "b"] + '/' + name, {}).then(function (response) {
        if (response.data.success === "false") console.log(response.data.error);else {
          var description = response.data.headline[0].description === "None" ? "" : response.data.headline[0].description;

          _this.setState({
            alerts: response.data.alerts,
            errors: response.data.headline[0].errors,
            alert_name: response.data.headline[0].alert_name,
            label: response.data.headline[0].label,
            name: response.data.headline[0].name,
            description: description,
            message: response.data.headline[0].message
          });
        }
      });
    });

    _this.state = {
      open: false,
      isLoading: true,
      activePanelId: "manage",
      activePanelAction: "Create New Headline",
      sortKey: "label",
      sortDir: "asc",
      label: "",
      name: "",
      alert_name: "",
      description: "",
      message: "",
      panelKey: "",
      panelTitle: "",
      data: [],
      alerts: [],
      errors: []
    };
    return _this;
  }

  _createClass(HeadlinesModal, [{
    key: "componentWillReceiveProps",
    value: function componentWillReceiveProps(nextProps) {
      this.setState(nextProps);
    }
  }, {
    key: "componentDidUpdate",
    value: function componentDidUpdate(prevProps) {
      if (prevProps.open !== this.props.open && this.props.open) this.manageHeadLines();
    }
  }, {
    key: "render",
    value: function render() {
      var _this2 = this;

      var _this$state = this.state,
          sortKey = _this$state.sortKey,
          sortDir = _this$state.sortDir;
      return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3___default.a, {
        onRequestClose: this.handleRequestClose,
        open: this.state.open,
        style: {
          width: '800px'
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3___default.a.Header, {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* backgroundStyle */ "a"],
        onRequestClose: this.handleRequestClose
      }), this.state.isLoading ? /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3___default.a.Body, {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* backgroundStyle */ "a"]
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("div", {
        style: {
          textAlign: "center",
          margin: "15%"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_WaitSpinner__WEBPACK_IMPORTED_MODULE_1___default.a, {
        style: {
          textAlign: "center"
        }
      }), " ")) : /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(react__WEBPACK_IMPORTED_MODULE_0___default.a.Fragment, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3___default.a.Body, {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* backgroundStyle */ "a"]
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_SlidingPanels__WEBPACK_IMPORTED_MODULE_10___default.a, {
        activePanelId: this.state.activePanelId
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_SlidingPanels__WEBPACK_IMPORTED_MODULE_10___default.a.Panel, {
        key: "manage",
        panelId: "manage"
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Heading__WEBPACK_IMPORTED_MODULE_5___default.a, {
        level: 1,
        style: {
          marginLeft: "15px",
          marginBottom: "20px",
          marginTop: 0
        }
      }, "Manage Headlines"), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("div", {
        style: {
          margin: "0 15px"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("hr", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* hrStyle */ "f"]
      }), this.state.data.length > 0 ? /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("div", {
        style: {
          marginBottom: "30px"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a, {
        stripeRows: true
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Head, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.HeadCell, {
        key: "label",
        onSort: this.handleSort,
        sortKey: "label",
        sortDir: "label" === sortKey ? sortDir : "none"
      }, "Headline"), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.HeadCell, {
        key: "alert_name",
        onSort: this.handleSort,
        sortKey: "alert_name",
        sortDir: "alert_name" === sortKey ? sortDir : "none"
      }, "Alert"), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.HeadCell, null, "Action")), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Body, null, this.state.data.sort(function (rowA, rowB) {
        if (sortDir === "asc") {
          return rowA[sortKey] > rowB[sortKey] ? 1 : -1;
        }

        if (sortDir === "desc") {
          return rowB[sortKey] > rowA[sortKey] ? 1 : -1;
        }

        return 0;
      }).map(function (headline) {
        return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Row, {
          key: headline.name
        }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Link__WEBPACK_IMPORTED_MODULE_6___default.a, {
          onClick: function onClick() {
            return _this2.editHeadline(headline.name, headline.label);
          }
        }, headline.label)), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, null, headline.alert_name), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Link__WEBPACK_IMPORTED_MODULE_6___default.a, {
          onClick: function onClick() {
            return _this2.deleteHeadline(headline.name, headline.label);
          }
        }, "Delete")));
      })))) : /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("div", null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* contentStyle */ "b"]
      }, "No Headlines Configured...")))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_SlidingPanels__WEBPACK_IMPORTED_MODULE_10___default.a.Panel, {
        key: this.state.panelKey,
        panelId: this.state.panelKey
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Heading__WEBPACK_IMPORTED_MODULE_5___default.a, {
        level: 1,
        style: {
          marginLeft: "15px",
          marginBottom: "20px",
          marginTop: 0
        }
      }, this.state.panelTitle), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("div", {
        style: {
          margin: "0 15px"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("hr", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* hrStyle */ "f"]
      }), this.state.errors.length > 0 ? /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Paragraph__WEBPACK_IMPORTED_MODULE_11___default.a, {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* errorStyle */ "c"]
      }, this.state.errors[0]) : null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Head, {
        style: {
          display: "none"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.HeadCell, null), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.HeadCell, null)), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Body, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Row, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, {
        align: "right",
        style: {
          width: "20%"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* formInputStyle */ "e"]
      }, "Label: ", /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("span", {
        style: {
          color: "red"
        }
      }, "*"))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, {
        style: {
          width: "65%"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Text__WEBPACK_IMPORTED_MODULE_12___default.a, {
        style: {
          width: "80%"
        },
        onChange: this.handleChange,
        name: "label",
        value: this.state.label
      }))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Row, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, {
        align: "right"
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* formInputStyle */ "e"]
      }, "Link To Alert: ", /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("span", {
        style: {
          color: "red"
        }
      }, "*"))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, null, this.state.alerts.length > 0 ? /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Select__WEBPACK_IMPORTED_MODULE_13___default.a, {
        name: "alert_name",
        value: this.state.alert_name,
        onChange: this.handleChange,
        style: {
          width: "80%"
        }
      }, this.state.alerts.map(function (alert) {
        return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Select__WEBPACK_IMPORTED_MODULE_13___default.a.Option, {
          label: alert.name,
          value: alert.name
        });
      })) : /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Paragraph__WEBPACK_IMPORTED_MODULE_11___default.a, null, "No alerts configured..."))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Row, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, {
        align: "right"
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* formInputStyle */ "e"]
      }, "Description:")), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Text__WEBPACK_IMPORTED_MODULE_12___default.a, {
        multiline: true,
        style: {
          width: "80%"
        },
        onChange: this.handleChange,
        name: "description",
        value: this.state.description
      }))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Row, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, {
        align: "right"
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* formInputStyle */ "e"]
      }, "Displayed Message: ", /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("span", {
        style: {
          color: "red"
        }
      }, "*"))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Table__WEBPACK_IMPORTED_MODULE_2___default.a.Cell, null, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Text__WEBPACK_IMPORTED_MODULE_12___default.a, {
        style: {
          width: "80%"
        },
        onChange: this.handleChange,
        name: "message",
        value: this.state.message
      }))))))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_SlidingPanels__WEBPACK_IMPORTED_MODULE_10___default.a.Panel, {
        key: "success",
        panelId: "success"
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Heading__WEBPACK_IMPORTED_MODULE_5___default.a, {
        level: 1,
        style: {
          marginLeft: "15px",
          marginBottom: "20px",
          marginTop: 0
        }
      }, "Success!"), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("div", {
        style: {
          margin: "0 15px"
        }
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("hr", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* hrStyle */ "f"]
      }), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement("p", {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* pStyle */ "g"]
      }, "Your headline has been saved.  Click \"OK\" to return to the headlines manager."))))), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Modal__WEBPACK_IMPORTED_MODULE_3___default.a.Footer, {
        style: _HeadLineStyles__WEBPACK_IMPORTED_MODULE_8__[/* backgroundStyle */ "a"]
      }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_4___default.a, {
        appearance: "secondary",
        onClick: this.handleRequestClose,
        label: "Cancel"
      }), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default.a.createElement(_splunk_react_ui_Button__WEBPACK_IMPORTED_MODULE_4___default.a, {
        appearance: "primary",
        onClick: this.handleActionClick,
        label: this.state.activePanelAction,
        value: this.state.activePanelId
      }))));
    }
  }]);

  return HeadlinesModal;
}(react__WEBPACK_IMPORTED_MODULE_0__["Component"]);

/* harmony default export */ __webpack_exports__["default"] = (HeadlinesModal);

/***/ })

}]);