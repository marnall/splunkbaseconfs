"use strict";

var React = require("react");

function renderMarkdown(markdownRenderer, domPurify, text) {
  var value = text === undefined || text === null ? "" : String(text);
  if (!markdownRenderer || !domPurify || typeof domPurify.sanitize !== "function") {
    return value;
  }

  return domPurify.sanitize(markdownRenderer.render(value));
}

function MessageBubble(props) {
  var message = props.message || {};
  var markdownRenderer = props.markdownRenderer;
  var domPurify = props.domPurify;

  return React.createElement(
    "div",
    {
      className: "ai-chat-msg ai-chat-msg-" + (message.sender || "agent")
    },
    React.createElement("div", {
      className: "ai-chat-msg-body",
      dangerouslySetInnerHTML: {
        __html: renderMarkdown(markdownRenderer, domPurify, message.text)
      }
    })
  );
}

function AttachmentChip(props) {
  var item = props.item || {};

  return React.createElement(
    "span",
    {
      className: "ai-chat-attachment-chip"
    },
    React.createElement(
      "span",
      {
        className: "ai-chat-attachment-chip-label"
      },
      item.kind === "dashboard" ? "Dashboard: " + item.label : "Panel: " + item.label
    ),
    React.createElement(
      "button",
      {
        type: "button",
        className: "ai-chat-attachment-chip-remove",
        "aria-label": "Remove attachment",
        title: "Remove attachment",
        onClick: function () {
          if (props.onRemove) {
            props.onRemove({
              type: item.kind,
              key: item.key
            });
          }
        }
      },
      "x"
    )
  );
}

function AttachmentBar(props) {
  var selection = props.selection || {};
  var selectedPanels = Array.isArray(selection.selectedPanels) ? selection.selectedPanels : [];
  var items = [];

  if (selection.dashboardSelected) {
    items.push({
      kind: "dashboard",
      key: "__dashboard__",
      label: selection.dashboardLabel || "Dashboard"
    });
  }

  selectedPanels.forEach(function (panel) {
    items.push({
      kind: "panel",
      key: panel && panel.key ? panel.key : "",
      label: panel && panel.label ? panel.label : panel && panel.key ? panel.key : "Panel"
    });
  });

  return React.createElement(
    "div",
    {
      className: "ai-chat-attachment-bar"
    },
    React.createElement(
      "div",
      {
        className: "ai-chat-attachment-title"
      },
      "Attached context"
    ),
    items.length
      ? React.createElement(
          "div",
          {
            className: "ai-chat-attachment-list"
          },
          items.map(function (item) {
            return React.createElement(AttachmentChip, {
              key: item.kind + ":" + item.key,
              item: item,
              onRemove: props.onRemove
            });
          })
        )
      : React.createElement(
          "div",
          {
            className: "ai-chat-attachment-empty"
          },
          "No attachments selected. Use the dashboard or panel Attach buttons."
        )
  );
}

function ChatApp(props) {
  var messagesRef = React.useRef(null);
  var inputRef = React.useRef(null);
  var launcherLabel = props.buttonLabel || "Ask AI";
  var windowTitle = props.windowTitle || "AI Chat";
  var placeholderText = props.placeholderText || "Type your message...";

  React.useEffect(function () {
    if (!messagesRef.current) {
      return;
    }
    messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [props.messages, props.isLoading, props.error]);

  React.useEffect(function () {
    if (props.isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [props.isOpen]);

  return React.createElement(
    React.Fragment,
    null,
    !props.isOpen
      ? React.createElement(
          "button",
          {
            type: "button",
            className: "ai-chat-fab",
            title: "Open chat",
            onClick: props.onOpen
          },
          launcherLabel
        )
      : null,
    props.isOpen
      ? React.createElement(
          "div",
          {
            className: "ai-chat-modal-overlay",
            onClick: function (event) {
              if (event.target === event.currentTarget) {
                props.onClose();
              }
            }
          },
          React.createElement(
            "div",
            {
              className: "ai-chat-modal",
              style: {
                height: props.height + "px"
              }
            },
            React.createElement(
              "div",
              {
                className: "ai-chat-title"
              },
              React.createElement("span", null, windowTitle),
              React.createElement(
                "div",
                {
                  className: "ai-chat-title-actions"
                },
                React.createElement(
                  "button",
                  {
                    type: "button",
                    className: "ai-chat-clear-btn",
                    onClick: props.onClearHistory
                  },
                  "Clear History"
                ),
                React.createElement(
                  "button",
                  {
                    type: "button",
                    className: "ai-chat-close-btn",
                    onClick: props.onClose
                  },
                  "Close"
                )
              )
            ),
            React.createElement(
              AttachmentBar,
              {
                selection: props.contextSelection,
                onRemove: props.onRemoveContextItem
              }
            ),
            React.createElement(
              "div",
              {
                className: "ai-chat-messages",
                ref: messagesRef
              },
              props.messages.map(function (message, index) {
                return React.createElement(MessageBubble, {
                  key: message.sender + "-" + index,
                  message: message,
                  markdownRenderer: props.markdownRenderer,
                  domPurify: props.domPurify
                });
              }),
              props.isLoading
                ? React.createElement(
                    "div",
                    {
                      className: "ai-chat-loading"
                    },
                    "Loading..."
                  )
                : null,
              props.error
                ? React.createElement(
                    "div",
                    {
                      className: "ai-chat-error"
                    },
                    props.error
                  )
                : null
            ),
            React.createElement(
              "div",
              {
                className: "ai-chat-input-row"
              },
              React.createElement("input", {
                ref: inputRef,
                type: "text",
                className: "ai-chat-input",
                placeholder: placeholderText,
                value: props.inputValue,
                disabled: props.isLoading,
                onChange: function (event) {
                  props.onInputChange(event.target.value);
                },
                onKeyDown: function (event) {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    props.onSend();
                  }
                }
              }),
              React.createElement(
                "button",
                {
                  type: "button",
                  className: "ai-chat-send-btn",
                  disabled: props.isLoading,
                  onClick: props.onSend
                },
                props.isLoading ? "Sending..." : "Send"
              )
            )
          )
        )
      : null
  );
}

module.exports = {
  ChatApp: ChatApp
};
