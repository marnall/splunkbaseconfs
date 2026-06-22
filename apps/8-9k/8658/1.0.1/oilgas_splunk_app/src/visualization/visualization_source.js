"use strict";

var React = require("react");
var ReactDomClient = require("react-dom/client");
var MarkdownIt = require("markdown-it");
var DOMPurifyModule = require("dompurify");

var ChatLogic = require("./chat_logic");
var ContextSelection = require("./context_selection");
var ReactView = require("./react_view");

var createRoot = ReactDomClient.createRoot;
var ChatApp = ReactView.ChatApp;
var DOMPurify = DOMPurifyModule && DOMPurifyModule.default ? DOMPurifyModule.default : DOMPurifyModule;

var WELCOME_MESSAGE = {
  sender: "agent",
  text: "Hi! How can I help you today?"
};
var DEFAULT_APP_ID = "oilgas_splunk_app";
var DEFAULT_BUTTON_LABEL = "Ask AI";
var DEFAULT_WINDOW_TITLE = "AI Chat";
var DEFAULT_PLACEHOLDER_TEXT = "Ask about this dashboard...";
var DEFAULT_MAX_HISTORY_MESSAGES = 12;
var DEFAULT_CLIENT_TIMEOUT_MS = 90000;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function detectAppId() {
  if (typeof window !== "undefined" && window.$C && window.$C.APP) {
    return String(window.$C.APP);
  }

  if (typeof window !== "undefined") {
    var match = String(window.location.pathname || "").match(/\/app\/([^/]+)/);
    if (match && match[1]) {
      try {
        return decodeURIComponent(match[1]);
      } catch {
        return match[1];
      }
    }
  }

  return DEFAULT_APP_ID;
}

function getPathPrefix() {
  if (typeof window !== "undefined" && window.$C && typeof window.$C.PATH_PREFIX === "string") {
    return String(window.$C.PATH_PREFIX);
  }

  if (typeof window !== "undefined") {
    var match = String(window.location.pathname || "").match(/^\/[^/]+/);
    return match && match[0] ? match[0] : "";
  }

  return "";
}

function getFormKey() {
  if (typeof window !== "undefined" && window.$C) {
    if (window.$C.MRSPARKLE_FORM_KEY) {
      return String(window.$C.MRSPARKLE_FORM_KEY);
    }
    if (window.$C.FORM_KEY) {
      return String(window.$C.FORM_KEY);
    }
  }

  if (typeof document === "undefined") {
    return "";
  }

  var cookiePairs = String(document.cookie || "").split(";");
  for (var i = 0; i < cookiePairs.length; i += 1) {
    var pair = ChatLogic.trimToString(cookiePairs[i]);
    if (!pair) {
      continue;
    }

    var separatorIndex = pair.indexOf("=");
    if (separatorIndex <= 0) {
      continue;
    }

    var cookieName = ChatLogic.trimToString(pair.slice(0, separatorIndex));
    if (cookieName.indexOf("splunkweb_csrf_token_") !== 0) {
      continue;
    }

    return ChatLogic.trimToString(pair.slice(separatorIndex + 1)).replace(/^"|"$/g, "");
  }

  return "";
}

function buildSplunkdRawUrl(path, query) {
  var url = getPathPrefix() + "/splunkd/__raw" + path;
  var parts = [];

  if (query && typeof query === "object") {
    Object.keys(query).forEach(function (key) {
      var value = query[key];
      if (value === undefined || value === null || value === "") {
        return;
      }
      parts.push(encodeURIComponent(key) + "=" + encodeURIComponent(String(value)));
    });
  }

  if (!parts.length) {
    return url;
  }

  return url + "?" + parts.join("&");
}

function buildSplunkRequestHeaders(extraHeaders) {
  var headers = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest"
  };
  var formKey = getFormKey();
  if (formKey) {
    headers["X-Splunk-Form-Key"] = formKey;
  }

  if (extraHeaders && typeof extraHeaders === "object") {
    Object.keys(extraHeaders).forEach(function (key) {
      headers[key] = extraHeaders[key];
    });
  }

  return headers;
}

function parseXmlErrorText(bodyText) {
  var xmlText = ChatLogic.trimToString(bodyText);
  if (!xmlText || xmlText.indexOf("<") !== 0) {
    return "";
  }

  var match = xmlText.match(/<msg[^>]*>([\s\S]*?)<\/msg>/i);
  if (!match || !match[1]) {
    return "";
  }

  return ChatLogic.trimToString(match[1].replace(/\s+/g, " "));
}

function readBackendResponseOrThrow(response) {
  return response.text().then(function (bodyText) {
    var parsedBody = null;

    if (bodyText) {
      try {
        parsedBody = JSON.parse(bodyText);
      } catch {
        parsedBody = null;
      }
    }

    if (!response.ok) {
      var errorMessage =
        ChatLogic.trimToString(parsedBody && (parsedBody.error || parsedBody.message)) ||
        parseXmlErrorText(bodyText) ||
        ChatLogic.trimToString(bodyText) ||
        response.statusText ||
        ("HTTP " + response.status);

      throw new Error(errorMessage);
    }

    if (parsedBody !== null) {
      return parsedBody;
    }

    return {
      message: ChatLogic.trimToString(bodyText)
    };
  });
}

function createVisualizationFactory(dependencies) {
  var SplunkVisualizationBase = dependencies.SplunkVisualizationBase;

  return SplunkVisualizationBase.extend({
    formatter: {
      contextSearchIds: {
        title: "Context Search IDs",
        description: "List of search manager IDs to use as context for the backend chat request.",
        type: "array",
        default: [],
        items: {
          type: "string"
        }
      },
      height: {
        title: "Chat Height",
        description: "Initial chat window height in pixels.",
        type: "number",
        default: 400
      },
      buttonLabel: {
        title: "Launcher Label",
        description: "Text shown on the floating chat launcher button.",
        type: "string",
        default: DEFAULT_BUTTON_LABEL
      },
      windowTitle: {
        title: "Window Title",
        description: "Title shown in the chat modal header.",
        type: "string",
        default: DEFAULT_WINDOW_TITLE
      },
      placeholderText: {
        title: "Input Placeholder",
        description: "Placeholder shown in the chat input box.",
        type: "string",
        default: DEFAULT_PLACEHOLDER_TEXT
      },
      systemPrompt: {
        title: "System Prompt",
        description: "Instruction appended to each backend request.",
        type: "string",
        default: ChatLogic.DEFAULT_SYSTEM_PROMPT
      },
      maxHistoryMessages: {
        title: "Max History Messages",
        description: "Maximum number of local chat turns sent back to the backend.",
        type: "number",
        default: DEFAULT_MAX_HISTORY_MESSAGES
      }
    },

    initialize: function () {
      SplunkVisualizationBase.prototype.initialize.apply(this, arguments);

      this.messages = [WELCOME_MESSAGE];
      this.chatHistory = [];
      this.latestData = {
        fields: [],
        rows: []
      };
      this.contextSearchIds = [];
      this.inputValue = "";
      this.isOpen = false;
      this.isLoading = false;
      this.error = null;
      this.height = 400;
      this.buttonLabel = DEFAULT_BUTTON_LABEL;
      this.windowTitle = DEFAULT_WINDOW_TITLE;
      this.placeholderText = DEFAULT_PLACEHOLDER_TEXT;
      this.systemPrompt = ChatLogic.DEFAULT_SYSTEM_PROMPT;
      this.maxHistoryMessages = DEFAULT_MAX_HISTORY_MESSAGES;
      this.appId = detectAppId();
      this.panelInstanceId =
        "ai-chat-panel-" + Date.now() + "-" + Math.floor(Math.random() * 100000);
      this.contextController = ContextSelection.getGlobalContextController();
      this.contextSelection = ContextSelection.getEmptySelection();
      this._splunkMvcPromise = null;
      this._root = createRoot(this.el);
      this.markdownRenderer = new MarkdownIt({
        html: false,
        linkify: true,
        breaks: true
      });
      this.domPurify = DOMPurify;

      if (this.contextController && typeof this.contextController.register === "function") {
        this.contextController.register(
          this.panelInstanceId,
          this._onContextSelectionChanged.bind(this)
        );
      }

      this._render();
    },

    getInitialDataParams: function () {
      return {
        outputMode: SplunkVisualizationBase.ROW_MAJOR_OUTPUT_MODE,
        count: 10000
      };
    },

    formatData: function (data) {
      if (data && Array.isArray(data.rows)) {
        this.latestData = {
          fields: Array.isArray(data.fields) ? data.fields : [],
          rows: data.rows
        };
      }

      return data;
    },

    updateView: function (data, config) {
      if (data) {
        this.latestData = {
          fields: Array.isArray(data.fields) ? data.fields : [],
          rows: Array.isArray(data.rows) ? data.rows : []
        };
      }

      var rawContextIds =
        this._readConfig(config || {}, "contextSearchIds", this.contextSearchIds) || [];
      this.contextSearchIds = ChatLogic.normalizeContextSearchIds(rawContextIds);
      this.height = clamp(
        parseInt(this._readConfig(config || {}, "height", this.height), 10) || 400,
        320,
        900
      );
      this.buttonLabel = ChatLogic.trimToString(
        this._readConfig(config || {}, "buttonLabel", this.buttonLabel)
      ) || DEFAULT_BUTTON_LABEL;
      this.windowTitle = ChatLogic.trimToString(
        this._readConfig(config || {}, "windowTitle", this.windowTitle)
      ) || DEFAULT_WINDOW_TITLE;
      this.placeholderText = ChatLogic.trimToString(
        this._readConfig(config || {}, "placeholderText", this.placeholderText)
      ) || DEFAULT_PLACEHOLDER_TEXT;
      this.systemPrompt = ChatLogic.trimToString(
        this._readConfig(config || {}, "systemPrompt", this.systemPrompt)
      ) || ChatLogic.DEFAULT_SYSTEM_PROMPT;
      this.maxHistoryMessages = clamp(
        parseInt(
          this._readConfig(config || {}, "maxHistoryMessages", this.maxHistoryMessages),
          10
        ) || DEFAULT_MAX_HISTORY_MESSAGES,
        1,
        50
      );
      this._render();
    },

    remove: function () {
      if (this.contextController && typeof this.contextController.unregister === "function") {
        this.contextController.unregister(this.panelInstanceId);
      }
      if (this._root) {
        this._root.unmount();
        this._root = null;
      }
      return SplunkVisualizationBase.prototype.remove.apply(this, arguments);
    },

    reflow: function () {
      this._render();
    },

    _readConfig: function (config, key, fallback) {
      var namespace = "";

      try {
        var namespaceInfo = this.getPropertyNamespaceInfo && this.getPropertyNamespaceInfo();
        namespace = namespaceInfo && namespaceInfo.propertyNamespace ? namespaceInfo.propertyNamespace : "";
      } catch {
        namespace = "";
      }

      if (namespace && config[namespace + key] !== undefined && config[namespace + key] !== "") {
        return config[namespace + key];
      }

      if (config[key] !== undefined && config[key] !== "") {
        return config[key];
      }

      return fallback;
    },

    _render: function () {
      if (!this._root) {
        return;
      }

      this._root.render(
        React.createElement(ChatApp, {
          buttonLabel: this.buttonLabel,
          contextSelection: this.contextSelection,
          domPurify: this.domPurify,
          error: this.error,
          height: this.height,
          inputValue: this.inputValue,
          isLoading: this.isLoading,
          isOpen: this.isOpen,
          markdownRenderer: this.markdownRenderer,
          messages: this.messages,
          onClearHistory: this.clearChatHistory.bind(this),
          onClose: this._closeChat.bind(this),
          onInputChange: this._setInputValue.bind(this),
          onOpen: this._openChat.bind(this),
          onRemoveContextItem: this._onRemoveContextItem.bind(this),
          onSend: this._sendCurrentMessage.bind(this),
          placeholderText: this.placeholderText,
          windowTitle: this.windowTitle
        })
      );
    },

    _openChat: function () {
      this.isOpen = true;
      this._render();
    },

    _closeChat: function () {
      this.isOpen = false;
      this._render();
    },

    _setInputValue: function (value) {
      this.inputValue = ChatLogic.trimToString(value);
      this._render();
    },

    _onContextSelectionChanged: function (selection) {
      this.contextSelection = selection || ContextSelection.getEmptySelection();
      this._render();
    },

    _onRemoveContextItem: function (item) {
      if (!this.contextController || !item) {
        return;
      }

      var type = ChatLogic.trimToString(item.type);
      var key = ChatLogic.trimToString(item.key);

      if (type === "dashboard" && typeof this.contextController.setDashboardSelected === "function") {
        this.contextController.setDashboardSelected(false);
        return;
      }

      if (type === "panel" && key && typeof this.contextController.setPanelSelected === "function") {
        this.contextController.setPanelSelected(key, false);
      }
    },

    addMessage: function (sender, text) {
      this.messages = this.messages.concat([
        {
          sender: sender,
          text: ChatLogic.trimToString(text)
        }
      ]);

      if (sender === "user") {
        this.chatHistory.push({
          role: "user",
          content: ChatLogic.trimToString(text)
        });
      } else if (sender === "agent") {
        this.chatHistory.push({
          role: "assistant",
          content: ChatLogic.trimToString(text)
        });
      }

      this._render();
    },

    clearChatHistory: function () {
      this.messages = [WELCOME_MESSAGE];
      this.chatHistory = [];
      this.error = null;
      this._render();
    },

    setLoading: function (value) {
      this.isLoading = Boolean(value);
      this._render();
    },

    setError: function (value) {
      this.error = ChatLogic.trimToString(value);
      this._render();
    },

    getContextString: function () {
      return ChatLogic.buildContextString(this.latestData);
    },

    _sendCurrentMessage: function () {
      var message = ChatLogic.trimToString(this.inputValue);
      if (!message || this.isLoading) {
        return;
      }

      var historyBeforeMessage = this.chatHistory.slice();
      this.addMessage("user", message);
      this.inputValue = "";
      this.setLoading(true);
      this.setError(null);
      this.sendMessageToAgent(message, historyBeforeMessage);
    },

    sendMessageToAgent: function (message, historyBeforeMessage) {
      var self = this;

      this.fetchContextForRequest()
        .then(function (contextString) {
          var resolvedContext = ChatLogic.trimToString(contextString) || self.getContextString() || "";

          if (resolvedContext) {
            self._sendMessageToAI(
              ChatLogic.buildBackendRequest(
                message,
                resolvedContext,
                historyBeforeMessage,
                self.systemPrompt,
                self.maxHistoryMessages
              )
            );
            return;
          }

          self._sendMessageToAI(
            ChatLogic.buildBackendRequest(
              message,
              null,
              historyBeforeMessage,
              self.systemPrompt,
              self.maxHistoryMessages
            )
          );
        })
        .catch(function () {
          self._sendMessageToAI(
            ChatLogic.buildBackendRequest(
              message,
              null,
              historyBeforeMessage,
              self.systemPrompt,
              self.maxHistoryMessages
            )
          );
        });
    },

    fetchContextForRequest: function () {
      var self = this;

      return this.fetchSelectedContextFromPanels().then(function (selectedContext) {
        var resolvedSelectedContext = ChatLogic.trimToString(selectedContext);
        if (resolvedSelectedContext) {
          return resolvedSelectedContext;
        }
        return self.fetchContextFromSearchManagers();
      });
    },

    fetchSelectedContextFromPanels: function () {
      if (
        !this.contextController ||
        typeof this.contextController.hasExplicitSelection !== "function" ||
        !this.contextController.hasExplicitSelection()
      ) {
        return Promise.resolve(null);
      }

      var selection =
        typeof this.contextController.getSelectionSnapshot === "function"
          ? this.contextController.getSelectionSnapshot()
          : this.contextSelection;
      var panelEntries =
        typeof this.contextController.getPanelEntriesForContext === "function"
          ? this.contextController.getPanelEntriesForContext()
          : [];

      if (!panelEntries.length) {
        return Promise.resolve(ChatLogic.buildSelectedContextString([], selection));
      }

      var self = this;

      return this._loadSplunkMvc()
        .then(function (mvc) {
          if (!mvc || !mvc.Components) {
            return ChatLogic.buildSelectedContextString([], selection);
          }

          var tasks = panelEntries.map(function (entry) {
            return self._buildSourceContextsFromPanel(entry, mvc);
          });

          return Promise.all(tasks).then(function (sourceGroups) {
            var sources = [];
            sourceGroups.forEach(function (group) {
              if (Array.isArray(group)) {
                sources.push.apply(sources, group);
                return;
              }
              if (group) {
                sources.push(group);
              }
            });
            return ChatLogic.buildSelectedContextString(sources, selection);
          });
        })
        .catch(function () {
          return ChatLogic.buildSelectedContextString([], selection);
        });
    },

    fetchContextFromSearchManagers: function () {
      var self = this;
      var amdRequire =
        typeof window !== "undefined" && typeof window.require === "function"
          ? window.require
          : null;

      if (!amdRequire) {
        return Promise.resolve(this.getContextString() || "");
      }

      return new Promise(function (resolve) {
        var normalizedIds = ChatLogic.normalizeContextSearchIds(self.contextSearchIds);

        if (!normalizedIds.length) {
          amdRequire(
            ["splunkjs/mvc", "splunkjs/mvc/searchmanager"],
            function (mvc, SearchManagerCtor) {
              var components =
                mvc &&
                mvc.Components &&
                typeof mvc.Components.getInstances === "function"
                  ? mvc.Components.getInstances()
                  : null;

              if (!components || typeof components !== "object") {
                resolve(self.getContextString() || "");
                return;
              }

              var discoveredIds = [];
              Object.keys(components).forEach(function (key) {
                var component = components[key];
                if (component instanceof SearchManagerCtor) {
                  discoveredIds.push(component.id);
                }
              });

              self.contextSearchIds = discoveredIds;
              if (!self.contextSearchIds.length) {
                resolve(self.getContextString() || "");
                return;
              }

              self.fetchContextFromSearchManagers().then(resolve);
            },
            function () {
              resolve(self.getContextString() || "");
            }
          );
          return;
        }

        amdRequire(
          ["splunkjs/mvc"],
          function (mvc) {
            if (!mvc || !mvc.Components || typeof mvc.Components.get !== "function") {
              resolve(self.getContextString() || "");
              return;
            }

            var contextChunks = [];
            var completed = 0;

            function finish() {
              completed += 1;
              if (completed === normalizedIds.length) {
                resolve(contextChunks.join("\n\n"));
              }
            }

            normalizedIds.forEach(function (searchId) {
              var manager = mvc.Components.get(searchId);
              var label = manager && manager.label ? manager.label : searchId;

              if (!manager || typeof manager.data !== "function") {
                finish();
                return;
              }

              var results = manager.data("results");
              if (!results || typeof results.data !== "function") {
                finish();
                return;
              }

              function handleData() {
                var normalizedPayload = self._normalizeResultsPayload(results.data());
                var lines = ["[Panel: " + label + " | ID: " + searchId + "]"];

                if (normalizedPayload.fields.length) {
                  lines.push(normalizedPayload.fields.join(" | "));
                }

                normalizedPayload.rows.forEach(function (row) {
                  if (Array.isArray(row)) {
                    lines.push(row.join(" | "));
                  }
                });

                contextChunks.push(lines.join("\n"));
                if (typeof results.off === "function") {
                  results.off("data", handleData);
                }
                finish();
              }

              if (typeof results.on === "function") {
                results.on("data", handleData);
              }

              try {
                if (typeof results.hasData === "function" && results.hasData()) {
                  handleData();
                  return;
                }

                if (typeof results.fetch === "function") {
                  results.fetch({
                    count: 0
                  });
                  return;
                }
              } catch {}

              finish();
            });
          },
          function () {
            resolve(self.getContextString() || "");
          }
        );
      });
    },

    _loadSplunkMvc: function () {
      if (this._splunkMvcPromise) {
        return this._splunkMvcPromise;
      }

      var amdRequire =
        typeof window !== "undefined" && typeof window.require === "function"
          ? window.require
          : null;

      if (!amdRequire) {
        this._splunkMvcPromise = Promise.resolve(null);
        return this._splunkMvcPromise;
      }

      this._splunkMvcPromise = new Promise(function (resolve) {
        amdRequire(
          ["splunkjs/mvc"],
          function (mvc) {
            resolve(mvc || null);
          },
          function () {
            resolve(null);
          }
        );
      });

      return this._splunkMvcPromise;
    },

    _buildSourceContextsFromPanel: function (panelEntry, mvc) {
      var panelLabel = ChatLogic.trimToString(panelEntry && panelEntry.label);
      var panelKey = ChatLogic.trimToString(panelEntry && panelEntry.key);
      var managerIds = this._resolvePanelManagerIds(panelEntry ? panelEntry.element : null, mvc);

      if (!managerIds.length) {
        return Promise.resolve([
          {
            panel_key: panelKey,
            panel_label: panelLabel || panelKey || "Panel",
            manager_id: "",
            fields: [],
            rows: []
          }
        ]);
      }

      var self = this;
      var tasks = managerIds.map(function (managerId) {
        var manager =
          mvc && mvc.Components && typeof mvc.Components.get === "function"
            ? mvc.Components.get(managerId)
            : null;
        var sourceLabel =
          ChatLogic.trimToString(manager && manager.label) || panelLabel || panelKey || managerId;

        return self._fetchSearchManagerContext(mvc, managerId)
          .then(function (results) {
            return {
              panel_key: panelKey,
              panel_label: sourceLabel,
              manager_id: managerId,
              fields: results.fields,
              rows: results.rows
            };
          })
          .catch(function () {
            return {
              panel_key: panelKey,
              panel_label: sourceLabel,
              manager_id: managerId,
              fields: [],
              rows: []
            };
          });
      });

      return Promise.all(tasks);
    },

    _resolvePanelManagerIds: function (panelEl, mvc) {
      if (!panelEl || !mvc || !mvc.Components || typeof mvc.Components.get !== "function") {
        return [];
      }

      var managerIds = [];
      var seen = {};

      function addManagerId(value) {
        var managerId = ChatLogic.trimToString(value);
        if (!managerId || seen[managerId]) {
          return;
        }
        seen[managerId] = true;
        managerIds.push(managerId);
      }

      var ids = panelEl.querySelectorAll("[id]");
      for (var i = 0; i < ids.length; i += 1) {
        var nodeId = ChatLogic.trimToString(ids[i].id);
        if (!nodeId) {
          continue;
        }

        var directComponent = mvc.Components.get(nodeId);
        addManagerId(this._extractManagerIdFromComponent(directComponent));

        // JS dashboards may mount bare SearchManagers directly to placeholder ids.
        if (directComponent && typeof directComponent.data === "function") {
          addManagerId(directComponent.id || nodeId);
        }
      }

      if (typeof mvc.Components.getInstances !== "function") {
        return managerIds;
      }

      var instances = mvc.Components.getInstances();
      if (!instances || typeof instances !== "object") {
        return managerIds;
      }

      for (var key in instances) {
        if (!Object.prototype.hasOwnProperty.call(instances, key)) {
          continue;
        }

        var instance = instances[key];
        if (!instance) {
          continue;
        }

        var instanceEl = instance.el;
        if (!instanceEl && instance.settings && typeof instance.settings.get === "function") {
          instanceEl = instance.settings.get("el");
        }
        if (typeof instanceEl === "string") {
          instanceEl = document.querySelector(instanceEl);
        }
        if (!instanceEl || typeof instanceEl.contains !== "function") {
          continue;
        }
        if (!panelEl.contains(instanceEl)) {
          continue;
        }

        addManagerId(this._extractManagerIdFromComponent(instance));
        if (typeof instance.data === "function") {
          addManagerId(instance.id);
        }
      }

      return managerIds;
    },

    _extractManagerIdFromComponent: function (component) {
      if (!component) {
        return "";
      }

      var candidates = [component.managerid, component.managerId];

      if (component.options) {
        candidates.push(component.options.managerid);
        candidates.push(component.options.managerId);
      }

      if (component.manager && component.manager.id) {
        candidates.push(component.manager.id);
      }

      if (component.settings && typeof component.settings.get === "function") {
        candidates.push(component.settings.get("managerid"));
        candidates.push(component.settings.get("managerId"));
        candidates.push(component.settings.get("searchManager"));
      }

      for (var i = 0; i < candidates.length; i += 1) {
        var candidate = candidates[i];
        if (candidate && typeof candidate === "object" && candidate.id) {
          candidate = candidate.id;
        }

        var managerId = ChatLogic.trimToString(candidate);
        if (managerId) {
          return managerId;
        }
      }

      return "";
    },

    _fetchSearchManagerContext: function (mvc, managerId) {
      if (!mvc || !mvc.Components || typeof mvc.Components.get !== "function") {
        return Promise.resolve({
          fields: [],
          rows: []
        });
      }

      var searchManager = mvc.Components.get(managerId);
      if (!searchManager || typeof searchManager.data !== "function") {
        return Promise.resolve({
          fields: [],
          rows: []
        });
      }

      var resultsModel = null;
      try {
        resultsModel = searchManager.data("results", {
          count: 0,
          output_mode: "json_rows"
        });
      } catch {
        resultsModel = searchManager.data("results");
      }

      if (!resultsModel || typeof resultsModel.data !== "function") {
        return Promise.resolve({
          fields: [],
          rows: []
        });
      }

      var self = this;
      return new Promise(function (resolve) {
        var settled = false;
        var timeoutId = null;

        function cleanup() {
          if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
          }

          if (typeof resultsModel.off === "function") {
            resultsModel.off("data", onData);
            resultsModel.off("error", onError);
          }
        }

        function complete(payload) {
          if (settled) {
            return;
          }

          settled = true;
          cleanup();
          resolve(payload);
        }

        function readCurrent() {
          try {
            complete(self._normalizeResultsPayload(resultsModel.data()));
          } catch {
            complete({
              fields: [],
              rows: []
            });
          }
        }

        function onData() {
          readCurrent();
        }

        function onError() {
          complete({
            fields: [],
            rows: []
          });
        }

        if (typeof resultsModel.on === "function") {
          resultsModel.on("data", onData);
          resultsModel.on("error", onError);
        }

        try {
          if (typeof resultsModel.hasData === "function" && resultsModel.hasData()) {
            readCurrent();
            return;
          }

          if (typeof resultsModel.fetch === "function") {
            resultsModel.fetch({
              count: 0
            });
          } else {
            readCurrent();
            return;
          }
        } catch {
          complete({
            fields: [],
            rows: []
          });
          return;
        }

        timeoutId = window.setTimeout(function () {
          readCurrent();
        }, 7000);
      });
    },

    _normalizeResultsPayload: function (dataObj) {
      var fields = [];
      if (dataObj && Array.isArray(dataObj.fields)) {
        for (var fieldIndex = 0; fieldIndex < dataObj.fields.length; fieldIndex += 1) {
          var field = dataObj.fields[fieldIndex];
          fields.push(String(field && field.name ? field.name : field));
        }
      }

      var sourceRows = dataObj && Array.isArray(dataObj.rows) ? dataObj.rows : [];
      if (
        !fields.length &&
        sourceRows.length > 0 &&
        sourceRows[0] &&
        typeof sourceRows[0] === "object" &&
        !Array.isArray(sourceRows[0])
      ) {
        for (var key in sourceRows[0]) {
          if (!Object.prototype.hasOwnProperty.call(sourceRows[0], key)) {
            continue;
          }
          fields.push(String(key));
        }
      }

      var rows = [];
      for (var rowIndex = 0; rowIndex < sourceRows.length; rowIndex += 1) {
        var row = sourceRows[rowIndex];
        if (Array.isArray(row)) {
          rows.push(row);
          continue;
        }

        if (row && typeof row === "object" && fields.length) {
          var normalizedRow = [];
          for (var fieldPos = 0; fieldPos < fields.length; fieldPos += 1) {
            normalizedRow.push(row[fields[fieldPos]]);
          }
          rows.push(normalizedRow);
        }
      }

      return {
        fields: fields,
        rows: rows
      };
    },

    _sendMessageToAI: function (requestPayload) {
      var self = this;

      this._executeBackendRequest(requestPayload)
        .then(function (responsePayload) {
          var normalizedResponse = ChatLogic.extractBackendResponse(responsePayload);
          self.addMessage("agent", normalizedResponse.message || "No response from AI.");
          self.setLoading(false);
        })
        .catch(function (error) {
          var message =
            ChatLogic.trimToString(error && error.message) || "Backend AI request failed";
          self.setError(message);
          self.addMessage("agent", "Sorry, I encountered an error: " + message);
          self.setLoading(false);
        });
    },

    _executeBackendRequest: function (requestPayload) {
      var backendPath =
        "/servicesNS/nobody/" +
        encodeURIComponent(this.appId) +
        "/ai_chat_backend/chat";
      var endpointUrl = buildSplunkdRawUrl(backendPath);

      return new Promise(function (resolve, reject) {
        var controller = null;
        var timeoutId = null;

        if (typeof AbortController !== "undefined") {
          controller = new AbortController();
        }

        timeoutId = window.setTimeout(function () {
          if (controller) {
            controller.abort();
            return;
          }

          reject(new Error("AI backend request timed out."));
        }, DEFAULT_CLIENT_TIMEOUT_MS);

        fetch(endpointUrl, {
          body: JSON.stringify(requestPayload || {}),
          credentials: "same-origin",
          headers: buildSplunkRequestHeaders(),
          method: "POST",
          signal: controller ? controller.signal : undefined
        })
          .then(readBackendResponseOrThrow)
          .then(function (payload) {
            resolve(payload || {});
          })
          .catch(function (error) {
            if (error && error.name === "AbortError") {
              reject(new Error("AI backend request timed out."));
              return;
            }
            reject(error);
          })
          .finally(function () {
            if (timeoutId) {
              clearTimeout(timeoutId);
            }
          });
      });
    }
  });
}

module.exports = createVisualizationFactory;
