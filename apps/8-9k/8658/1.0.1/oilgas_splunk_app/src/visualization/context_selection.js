"use strict";

var GLOBAL_CONTEXT_CONTROLLER_KEY = "__aiChatContextController";
var PANEL_SELECTOR = ".dashboard-panel";
var DASHBOARD_TITLE_SELECTORS = [
  ".dashboard-header .dashboard-title",
  ".dashboard-header h1",
  ".dashboard-title",
  ".header h1",
  ".dashboard-header h2",
  ".dashboard-header-title"
];

function trimToString(value) {
  if (value === undefined || value === null) {
    return "";
  }
  return String(value).trim();
}

function setSafeText(element, value) {
  if (!element) {
    return;
  }
  element.textContent = value === undefined || value === null ? "" : String(value);
}

function scheduleBrowserFrame(callback) {
  if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
    window.requestAnimationFrame(callback);
    return;
  }
  setTimeout(callback, 16);
}

function getEmptySelection() {
  return {
    dashboardSelected: true,
    dashboardLabel: "Dashboard",
    selectedPanels: []
  };
}

function getDashboardTitleElement() {
  for (var i = 0; i < DASHBOARD_TITLE_SELECTORS.length; i += 1) {
    var element = document.querySelector(DASHBOARD_TITLE_SELECTORS[i]);
    if (element) {
      return element;
    }
  }
  return null;
}

function getDashboardLabel() {
  var titleElement = getDashboardTitleElement();
  var label = trimToString(titleElement ? titleElement.textContent : "");
  if (label) {
    return label;
  }

  var pageTitle = trimToString(document.title || "");
  return pageTitle || "Dashboard";
}

function getPanelLabelFromElement(panelEl, position) {
  if (!panelEl) {
    return "Panel " + String(position + 1);
  }

  var titleEl =
    panelEl.querySelector(".panel-title") ||
    panelEl.querySelector(".dashboard-panel-title") ||
    panelEl.querySelector("h2") ||
    panelEl.querySelector("h3");
  var title = trimToString(titleEl ? titleEl.textContent : "");
  if (title) {
    return title;
  }

  return "Panel " + String(position + 1);
}

function getStablePanelKey(panelEl, position) {
  if (!panelEl) {
    return "panel-auto:" + String(position + 1);
  }

  var candidates = [];
  var hostCell = panelEl.closest(".dashboard-cell, .dashboard-layout-panel");
  if (hostCell) {
    candidates.push(hostCell.id);
    candidates.push(hostCell.getAttribute("data-cid"));
  }

  candidates.push(panelEl.id);
  candidates.push(panelEl.getAttribute("data-cid"));

  var firstElement = panelEl.querySelector(".dashboard-element[id]");
  if (firstElement) {
    candidates.push(firstElement.id);
  }

  for (var i = 0; i < candidates.length; i += 1) {
    var candidate = trimToString(candidates[i]);
    if (!candidate) {
      continue;
    }
    return "panel-stable:" + candidate;
  }

  return "panel-auto:" + String(position + 1);
}

function sortSelectionItems(items) {
  return items.sort(function (left, right) {
    var leftLabel = trimToString(left && left.label).toLowerCase();
    var rightLabel = trimToString(right && right.label).toLowerCase();

    if (leftLabel < rightLabel) {
      return -1;
    }
    if (leftLabel > rightLabel) {
      return 1;
    }

    var leftKey = trimToString(left && left.key);
    var rightKey = trimToString(right && right.key);

    if (leftKey < rightKey) {
      return -1;
    }
    if (leftKey > rightKey) {
      return 1;
    }

    return 0;
  });
}

function getPanelButtonLabel(isSelected) {
  return isSelected ? "Attached" : "Attach";
}

function getDashboardButtonLabel(isSelected) {
  return isSelected ? "Dashboard attached" : "Attach dashboard";
}

function createContextController() {
  return {
    panelEntries: {},
    selectedPanelKeys: {},
    dashboardSelected: true,
    subscribers: {},
    observer: null,
    scanTimerId: null,
    scanScheduled: false,
    lastSnapshotJson: "",
    globalPointerHandler: null,
    globalClickHandler: null,
    globalKeyHandler: null,
    suppressClickUntil: 0,

    register: function (instanceId, callback) {
      this.subscribers[instanceId] = callback;
      this.ensureStarted();

      if (typeof callback === "function") {
        callback(this.getSelectionSnapshot());
      }
    },

    unregister: function (instanceId) {
      delete this.subscribers[instanceId];
    },

    ensureStarted: function () {
      if (this.scanTimerId) {
        return;
      }

      var self = this;
      this.scheduleScan();

      function resolveActionTarget(target) {
        if (target && target.nodeType === 3) {
          target = target.parentElement;
        }

        if (!target || typeof target.closest !== "function") {
          return null;
        }

        var panelButton = target.closest(".ai-chat-panel-attach-btn");
        if (panelButton) {
          return {
            kind: "panel",
            element: panelButton
          };
        }

        var dashboardButton = target.closest(".ai-chat-dashboard-attach-btn");
        if (dashboardButton) {
          return {
            kind: "dashboard",
            element: dashboardButton
          };
        }

        return null;
      }

      function shouldIgnoreMouseButton(event) {
        if (!event || event.type !== "pointerdown") {
          return false;
        }

        if (event.button === undefined || event.button === 0) {
          return false;
        }

        return true;
      }

      function toggleFromAction(action) {
        if (!action) {
          return;
        }

        if (action.kind === "panel") {
          var panelButton = action.element;
          var panelKey = trimToString(panelButton.getAttribute("data-ai-chat-panel-key"));
          if (!panelKey) {
            var panelRoot = panelButton.closest(PANEL_SELECTOR);
            panelKey = getStablePanelKey(panelRoot, 0);
            if (panelKey) {
              panelButton.setAttribute("data-ai-chat-panel-key", panelKey);
            }
          }

          if (panelKey) {
            self.togglePanel(panelKey);
          }
          return;
        }

        if (action.kind === "dashboard") {
          self.toggleDashboard();
        }
      }

      if (!this.globalPointerHandler) {
        this.globalPointerHandler = function (event) {
          if (shouldIgnoreMouseButton(event)) {
            return;
          }

          var action = resolveActionTarget(event.target);
          if (!action) {
            return;
          }

          event.preventDefault();
          event.stopPropagation();
          if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
          }

          self.suppressClickUntil = Date.now() + 350;
          toggleFromAction(action);
        };

        document.addEventListener("pointerdown", this.globalPointerHandler, true);
      }

      if (!this.globalClickHandler) {
        this.globalClickHandler = function (event) {
          var action = resolveActionTarget(event.target);
          if (!action) {
            return;
          }

          if (Date.now() < self.suppressClickUntil) {
            event.preventDefault();
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === "function") {
              event.stopImmediatePropagation();
            }
            return;
          }

          event.preventDefault();
          event.stopPropagation();
          if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
          }

          toggleFromAction(action);
        };

        document.addEventListener("click", this.globalClickHandler, true);
      }

      if (!this.globalKeyHandler) {
        this.globalKeyHandler = function (event) {
          if (event.key !== "Enter" && event.key !== " ") {
            return;
          }

          var action = resolveActionTarget(event.target);
          if (!action) {
            return;
          }

          event.preventDefault();
          event.stopPropagation();
          if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
          }

          toggleFromAction(action);
        };

        document.addEventListener("keydown", this.globalKeyHandler, true);
      }

      if (typeof MutationObserver === "function" && document.body) {
        this.observer = new MutationObserver(function () {
          self.scheduleScan();
        });
        this.observer.observe(document.body, {
          childList: true,
          subtree: true
        });
      }

      this.scanTimerId = window.setInterval(function () {
        self.scanNow();
      }, 1200);
    },

    scheduleScan: function () {
      if (this.scanScheduled) {
        return;
      }

      this.scanScheduled = true;
      var self = this;
      scheduleBrowserFrame(function () {
        self.scanScheduled = false;
        self.scanNow();
      });
    },

    scanNow: function () {
      var panelNodes = document.querySelectorAll(PANEL_SELECTOR);
      var seen = {};

      for (var i = 0; i < panelNodes.length; i += 1) {
        var panelEl = panelNodes[i];
        if (!panelEl || !panelEl.isConnected) {
          continue;
        }

        var key = panelEl.getAttribute("data-ai-chat-panel-key");
        var stableKey = getStablePanelKey(panelEl, i);
        if (!key || key.indexOf("panel-auto:") === 0) {
          key = stableKey;
          panelEl.setAttribute("data-ai-chat-panel-key", key);
        }

        var entry = this.panelEntries[key] || {};
        entry.key = key;
        entry.element = panelEl;
        entry.label = getPanelLabelFromElement(panelEl, i);
        this.panelEntries[key] = entry;
        seen[key] = true;

        this.ensurePanelButton(entry);
      }

      for (var storedKey in this.panelEntries) {
        if (!Object.prototype.hasOwnProperty.call(this.panelEntries, storedKey)) {
          continue;
        }
        if (seen[storedKey]) {
          continue;
        }
        delete this.panelEntries[storedKey];
      }

      this.ensureDashboardButton();
      this.refreshButtons();
      this.notify();
    },

    ensurePanelButton: function (entry) {
      if (!entry || !entry.element) {
        return;
      }

      var panelEl = entry.element;
      var actionsEl =
        panelEl.querySelector(".dashboard-element-footer .menus") ||
        panelEl.querySelector(".element-footer .menus") ||
        panelEl.querySelector(".panel-head .panel-actions") ||
        panelEl.querySelector(".panel-actions");
      if (!actionsEl) {
        return;
      }

      var button = actionsEl.querySelector(".ai-chat-panel-attach-btn");
      if (!button) {
        button = document.createElement("button");
        button.type = "button";
        button.className = "btn-pill ai-chat-panel-attach-btn";
        button.setAttribute("aria-label", "Attach panel to context");
        actionsEl.appendChild(button);
      }

      button.setAttribute("data-ai-chat-panel-key", entry.key);
      button.title = "Attach panel results to chat context";
    },

    ensureDashboardButton: function () {
      var titleEl = getDashboardTitleElement();
      if (!titleEl || !titleEl.parentNode) {
        return;
      }

      var hostEl = titleEl.parentNode;
      var button = hostEl.querySelector(".ai-chat-dashboard-attach-btn");
      if (!button) {
        button = document.createElement("button");
        button.type = "button";
        button.className = "btn-pill ai-chat-dashboard-attach-btn";
        button.setAttribute("aria-label", "Attach dashboard to context");
        button.title = "Attach all dashboard panel results to chat context";

        if (titleEl.nextSibling) {
          hostEl.insertBefore(button, titleEl.nextSibling);
        } else {
          hostEl.appendChild(button);
        }
      }
    },

    refreshButtons: function () {
      var panelButtons = document.querySelectorAll(".ai-chat-panel-attach-btn");
      for (var i = 0; i < panelButtons.length; i += 1) {
        var panelButton = panelButtons[i];
        var panelKey = trimToString(panelButton.getAttribute("data-ai-chat-panel-key"));
        var isSelected = Boolean(panelKey && this.selectedPanelKeys[panelKey]);
        panelButton.classList.toggle("is-selected", isSelected);
        panelButton.setAttribute("aria-pressed", isSelected ? "true" : "false");
        panelButton.setAttribute(
          "aria-label",
          isSelected ? "Panel attached to context" : "Attach panel to context"
        );
        panelButton.title = isSelected
          ? "Panel results are attached to chat context"
          : "Attach panel results to chat context";
        setSafeText(panelButton, getPanelButtonLabel(isSelected));
      }

      var dashboardButton = document.querySelector(".ai-chat-dashboard-attach-btn");
      if (dashboardButton) {
        dashboardButton.classList.toggle("is-selected", this.dashboardSelected);
        dashboardButton.setAttribute("aria-pressed", this.dashboardSelected ? "true" : "false");
        dashboardButton.setAttribute(
          "aria-label",
          this.dashboardSelected ? "Dashboard attached to context" : "Attach dashboard to context"
        );
        dashboardButton.title = this.dashboardSelected
          ? "All dashboard panel results are attached to chat context"
          : "Attach all dashboard panel results to chat context";
        setSafeText(dashboardButton, getDashboardButtonLabel(this.dashboardSelected));
      }
    },

    togglePanel: function (panelKey) {
      if (!panelKey) {
        return;
      }

      if (this.selectedPanelKeys[panelKey]) {
        delete this.selectedPanelKeys[panelKey];
      } else {
        this.selectedPanelKeys[panelKey] = true;
      }

      this.refreshButtons();
      this.notify();
    },

    setPanelSelected: function (panelKey, isSelected) {
      if (!panelKey) {
        return;
      }

      if (isSelected) {
        this.selectedPanelKeys[panelKey] = true;
      } else {
        delete this.selectedPanelKeys[panelKey];
      }

      this.refreshButtons();
      this.notify();
    },

    toggleDashboard: function () {
      this.dashboardSelected = !this.dashboardSelected;
      this.refreshButtons();
      this.notify();
    },

    setDashboardSelected: function (isSelected) {
      this.dashboardSelected = Boolean(isSelected);
      this.refreshButtons();
      this.notify();
    },

    getSelectionSnapshot: function () {
      var selectedPanels = [];

      for (var key in this.selectedPanelKeys) {
        if (!Object.prototype.hasOwnProperty.call(this.selectedPanelKeys, key)) {
          continue;
        }
        if (!this.selectedPanelKeys[key]) {
          continue;
        }

        var entry = this.panelEntries[key];
        selectedPanels.push({
          key: key,
          label: entry && entry.label ? entry.label : key
        });
      }

      return {
        dashboardSelected: this.dashboardSelected,
        dashboardLabel: getDashboardLabel(),
        selectedPanels: sortSelectionItems(selectedPanels)
      };
    },

    getPanelEntriesForContext: function () {
      var entriesByKey = {};

      if (this.dashboardSelected) {
        for (var key in this.panelEntries) {
          if (!Object.prototype.hasOwnProperty.call(this.panelEntries, key)) {
            continue;
          }
          entriesByKey[key] = this.panelEntries[key];
        }
      }

      for (var selectedKey in this.selectedPanelKeys) {
        if (!Object.prototype.hasOwnProperty.call(this.selectedPanelKeys, selectedKey)) {
          continue;
        }
        if (!this.selectedPanelKeys[selectedKey]) {
          continue;
        }
        if (this.panelEntries[selectedKey]) {
          entriesByKey[selectedKey] = this.panelEntries[selectedKey];
        }
      }

      var output = [];
      for (var outputKey in entriesByKey) {
        if (!Object.prototype.hasOwnProperty.call(entriesByKey, outputKey)) {
          continue;
        }

        var entry = entriesByKey[outputKey];
        if (!entry || !entry.element || !entry.element.isConnected) {
          continue;
        }

        output.push({
          key: entry.key,
          label: entry.label,
          element: entry.element
        });
      }

      return sortSelectionItems(output);
    },

    hasExplicitSelection: function () {
      if (this.dashboardSelected) {
        return true;
      }

      for (var key in this.selectedPanelKeys) {
        if (!Object.prototype.hasOwnProperty.call(this.selectedPanelKeys, key)) {
          continue;
        }
        if (this.selectedPanelKeys[key]) {
          return true;
        }
      }

      return false;
    },

    notify: function () {
      var snapshot = this.getSelectionSnapshot();
      var snapshotJson = JSON.stringify(snapshot);
      if (snapshotJson === this.lastSnapshotJson) {
        return;
      }

      this.lastSnapshotJson = snapshotJson;

      for (var instanceId in this.subscribers) {
        if (!Object.prototype.hasOwnProperty.call(this.subscribers, instanceId)) {
          continue;
        }

        var callback = this.subscribers[instanceId];
        if (typeof callback === "function") {
          callback(snapshot);
        }
      }
    }
  };
}

var localController = null;

function getGlobalContextController() {
  if (typeof window === "undefined") {
    if (!localController) {
      localController = createContextController();
    }
    return localController;
  }

  if (!window[GLOBAL_CONTEXT_CONTROLLER_KEY]) {
    window[GLOBAL_CONTEXT_CONTROLLER_KEY] = createContextController();
  }

  return window[GLOBAL_CONTEXT_CONTROLLER_KEY];
}

module.exports = {
  getEmptySelection: getEmptySelection,
  getGlobalContextController: getGlobalContextController
};
