"use strict";

var DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant - oil and gas upstream expert.";

function trimToString(value) {
  if (value === undefined || value === null) {
    return "";
  }
  return String(value).trim();
}

function normalizeContextSearchIds(value) {
  if (Array.isArray(value)) {
    return value.map(trimToString).filter(Boolean);
  }

  if (typeof value === "string") {
    return value
      .split(/[;,|\s]+/)
      .map(trimToString)
      .filter(Boolean);
  }

  return [];
}

function normalizeRows(rows) {
  if (!Array.isArray(rows)) {
    return [];
  }

  return rows.filter(function (row) {
    return Array.isArray(row);
  });
}

function valueToCellString(value) {
  if (value === undefined || value === null) {
    return "";
  }

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  try {
    return JSON.stringify(value);
  } catch {
    return "";
  }
}

function buildContextString(contextData) {
  if (!contextData || !Array.isArray(contextData.rows) || !contextData.rows.length) {
    return null;
  }

  var lines = [];
  var fields = Array.isArray(contextData.fields)
    ? contextData.fields.map(normalizeFieldName).filter(Boolean)
    : [];
  if (fields.length) {
    lines.push(fields.join(" | "));
  }

  normalizeRows(contextData.rows).forEach(function (row) {
    lines.push(
      row.map(function (cell) {
        return valueToCellString(cell);
      }).join(" | ")
    );
  });

  var contextString = lines.join("\n").trim();
  return contextString || null;
}

function buildSelectedContextString(sources, selection) {
  var normalizedSources = Array.isArray(sources) ? sources.slice() : [];
  var lines = [];
  var selectionMeta = selection || {};
  var selectedPanels = Array.isArray(selectionMeta.selectedPanels) ? selectionMeta.selectedPanels : [];
  var seenPanelKeys = {};

  if (selectionMeta.dashboardSelected) {
    lines.push("[Dashboard: " + (trimToString(selectionMeta.dashboardLabel) || "Dashboard") + "]");
  }

  normalizedSources.forEach(function (source) {
    var sourceKey = trimToString(source && (source.panel_key || source.key));
    if (sourceKey) {
      seenPanelKeys[sourceKey] = true;
    }
  });

  selectedPanels.forEach(function (panel) {
    var panelKey = trimToString(panel && panel.key);
    if (panelKey && seenPanelKeys[panelKey]) {
      return;
    }

    normalizedSources.push({
      panel_key: panelKey,
      panel_label: trimToString(panel && panel.label) || panelKey || "Panel",
      manager_id: "",
      fields: [],
      rows: []
    });
  });

  normalizedSources.forEach(function (source) {
    var panelLabel = trimToString(source && (source.panel_label || source.label || source.key));
    var managerId = trimToString(source && source.manager_id);
    var fields = Array.isArray(source && source.fields)
      ? source.fields.map(normalizeFieldName).filter(Boolean)
      : [];
    var rows = normalizeRows(source && source.rows);

    if (lines.length) {
      lines.push("");
    }

    lines.push("[Panel: " + (panelLabel || "Panel") + (managerId ? " | ID: " + managerId : "") + "]");

    if (fields.length) {
      lines.push(fields.join(" | "));
    }

    if (rows.length) {
      rows.forEach(function (row) {
        lines.push(
          row.map(function (cell) {
            return valueToCellString(cell);
          }).join(" | ")
        );
      });
      return;
    }

    if (!fields.length) {
      lines.push("No search results available for this selection.");
    }
  });

  if (!normalizedSources.length && lines.length) {
    lines.push("No search results available for this selection.");
  }

  var output = lines.join("\n").trim();
  return output || null;
}

function buildPromptWithHistory(currentMessage, contextStr, chatHistory, systemPrompt) {
  var prompt = "";
  var history = Array.isArray(chatHistory) ? chatHistory : [];
  var normalizedContext = trimToString(contextStr);
  var normalizedSystemPrompt = trimToString(systemPrompt) || DEFAULT_SYSTEM_PROMPT;

  if (history.length === 0) {
    if (normalizedContext) {
      prompt +=
        "system: " +
        normalizedSystemPrompt +
        " Use the following context data to inform your responses when relevant:\n\n" +
        normalizedContext +
        "\n\n";
    } else {
      prompt += "system: " + normalizedSystemPrompt + "\n\n";
    }
  } else if (normalizedContext) {
    prompt += "context:\n" + normalizedContext + "\n\n";
  }

  if (history.length > 0) {
    history.slice(-10).forEach(function (turn) {
      var role = trimToString(turn && turn.role);
      var content = trimToString(turn && turn.content);
      if (!role || !content) {
        return;
      }
      prompt += role + ": " + content + "\n\n";
    });
  }

  prompt += "user: " + trimToString(currentMessage) + "\n\nassistant:";
  return prompt;
}

function escapePromptForSearch(prompt) {
  return trimToString(prompt).replace(/\n/g, " \\n ").replace(/"/g, '\\"');
}

function buildAiSearch(prompt) {
  return '| makeresults | ai prompt="' + escapePromptForSearch(prompt) + '"';
}

function normalizeFieldName(field) {
  if (field && typeof field === "object" && field.name) {
    return String(field.name);
  }
  return trimToString(field);
}

function extractAiResponse(resultsData) {
  var data = resultsData || {};
  var rows = Array.isArray(data.rows) ? data.rows : [];
  if (!rows.length) {
    return "";
  }

  var fields = Array.isArray(data.fields) ? data.fields.map(normalizeFieldName) : [];
  var aiFieldIndex = fields.indexOf("ai_result_1");

  if (aiFieldIndex >= 0 && Array.isArray(rows[0])) {
    return trimToString(rows[0][aiFieldIndex]);
  }

  if (Array.isArray(rows[0])) {
    return trimToString(rows[0][1]);
  }

  if (rows[0] && typeof rows[0] === "object") {
    if (rows[0].ai_result_1 !== undefined) {
      return trimToString(rows[0].ai_result_1);
    }

    var rowKeys = Object.keys(rows[0]);
    if (rowKeys.length > 1) {
      return trimToString(rows[0][rowKeys[1]]);
    }
  }

  return "";
}

function normalizeChatHistory(history, maxItems) {
  var normalizedHistory = Array.isArray(history) ? history : [];
  var normalizedLimit = parseInt(maxItems, 10);
  if (!normalizedLimit || normalizedLimit < 1) {
    normalizedLimit = 12;
  }

  var filtered = normalizedHistory
    .map(function (item) {
      var role = trimToString(item && item.role).toLowerCase();
      var content = trimToString(item && item.content);
      if ((role !== "user" && role !== "assistant") || !content) {
        return null;
      }
      return {
        role: role,
        content: content
      };
    })
    .filter(Boolean);

  if (filtered.length <= normalizedLimit) {
    return filtered;
  }

  return filtered.slice(filtered.length - normalizedLimit);
}

function buildEffectiveSystemPrompt(systemPrompt, contextStr) {
  var parts = [];
  var normalizedSystemPrompt = trimToString(systemPrompt);
  var normalizedContext = trimToString(contextStr);

  if (normalizedSystemPrompt) {
    parts.push(normalizedSystemPrompt);
  }

  if (normalizedContext) {
    parts.push(
      "Use the following Splunk dashboard context when it is relevant to the user's request:\n\n" +
        normalizedContext
    );
  }

  return parts.join("\n\n").trim();
}

function buildBackendRequest(message, contextStr, chatHistory, systemPrompt, maxHistoryMessages) {
  var payload = {
    message: trimToString(message),
    history: normalizeChatHistory(chatHistory, maxHistoryMessages)
  };

  var normalizedSystemPrompt = trimToString(systemPrompt);
  if (normalizedSystemPrompt) {
    payload.system_prompt = normalizedSystemPrompt;
  }

  var normalizedContext = trimToString(contextStr);
  if (normalizedContext) {
    payload.context = normalizedContext;
  }

  return payload;
}

function extractTextLikeContent(value) {
  if (typeof value === "string") {
    return value.trim();
  }

  if (Array.isArray(value)) {
    return value
      .map(extractTextLikeContent)
      .filter(Boolean)
      .join("\n")
      .trim();
  }

  if (value && typeof value === "object") {
    if (typeof value.text === "string") {
      return trimToString(value.text);
    }
    if (typeof value.content === "string") {
      return trimToString(value.content);
    }
    if (Array.isArray(value.parts)) {
      return extractTextLikeContent(value.parts);
    }
    if (Array.isArray(value.content)) {
      return extractTextLikeContent(value.content);
    }
    if (value.message) {
      return extractTextLikeContent(value.message);
    }
  }

  return "";
}

function extractBackendResponse(responseBody) {
  if (typeof responseBody === "string") {
    return {
      message: trimToString(responseBody)
    };
  }

  var payload = responseBody && typeof responseBody === "object" ? responseBody : {};
  var message = trimToString(payload.message || payload.markdown || payload.answer || payload.text);

  if (!message) {
    message = extractTextLikeContent(payload.output_text || payload.response || payload.content);
  }

  if (!message && Array.isArray(payload.choices) && payload.choices.length) {
    message = extractTextLikeContent(payload.choices[0]);
  }

  if (!message && Array.isArray(payload.candidates) && payload.candidates.length) {
    message = extractTextLikeContent(payload.candidates[0]);
  }

  return {
    message: message || "Assistant returned no message."
  };
}

module.exports = {
  DEFAULT_SYSTEM_PROMPT: DEFAULT_SYSTEM_PROMPT,
  buildBackendRequest: buildBackendRequest,
  buildEffectiveSystemPrompt: buildEffectiveSystemPrompt,
  buildAiSearch: buildAiSearch,
  buildContextString: buildContextString,
  buildPromptWithHistory: buildPromptWithHistory,
  buildSelectedContextString: buildSelectedContextString,
  escapePromptForSearch: escapePromptForSearch,
  extractBackendResponse: extractBackendResponse,
  extractAiResponse: extractAiResponse,
  normalizeChatHistory: normalizeChatHistory,
  normalizeContextSearchIds: normalizeContextSearchIds,
  trimToString: trimToString
};
