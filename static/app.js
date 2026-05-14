var EXPORT_OPTION_STORAGE_KEY = "copy-format-export-options";
var WORKSPACE_DRAFT_STORAGE_KEY = "englishlearning-workspace-draft-v1";
var workspaceDraftTimer = 0;
var sidebarManualActiveUntil = 0;

function escapeHtml(value) {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function loadExportOptions() {
    try {
        var raw = window.localStorage.getItem(EXPORT_OPTION_STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch (error) {
        return {};
    }
}

function saveExportOptions(container) {
    try {
        var payload = {
            trim: !!container.querySelector('[data-export-option="trim"]:checked'),
            dedupeFront: !!container.querySelector('[data-export-option="dedupe-front"]:checked')
        };
        window.localStorage.setItem(EXPORT_OPTION_STORAGE_KEY, JSON.stringify(payload));
    } catch (error) {
        return;
    }
}

function restoreExportOptions(container) {
    var options = loadExportOptions();
    var trimInput = container.querySelector('[data-export-option="trim"]');
    var dedupeInput = container.querySelector('[data-export-option="dedupe-front"]');
    if (trimInput instanceof HTMLInputElement && typeof options.trim === "boolean") {
        trimInput.checked = options.trim;
    }
    if (dedupeInput instanceof HTMLInputElement && typeof options.dedupeFront === "boolean") {
        dedupeInput.checked = options.dedupeFront;
    }
}

function buildExportPayload(container) {
    var shouldTrim = !!container.querySelector('[data-export-option="trim"]:checked');
    var shouldDedupeFront = !!container.querySelector('[data-export-option="dedupe-front"]:checked');
    var cards = document.querySelectorAll(".grouped-result-card");
    var grouped = [];
    var orderedFrontKeys = [];
    var chosenEntriesByFront = new Map();

    cards.forEach(function(card) {
        if (!(card instanceof HTMLElement)) {
            return;
        }
        var inputWord = card.getAttribute("data-input-word") || "";
        var phraseBoxes = card.querySelectorAll(".phrase-box");
        var phrases = [];
        phraseBoxes.forEach(function(box) {
            if (!(box instanceof HTMLElement)) {
                return;
            }
            var checkbox = box.querySelector(".phrase-select-input");
            var lockInput = box.querySelector(".phrase-lock-input");
            var frontField = box.querySelector(".phrase-front-input");
            var backField = box.querySelector(".phrase-back-input");
            if (!(checkbox instanceof HTMLInputElement) || !(lockInput instanceof HTMLInputElement) || !(frontField instanceof HTMLTextAreaElement) || !(backField instanceof HTMLTextAreaElement) || !checkbox.checked) {
                return;
            }
            var front = shouldTrim ? frontField.value.trim() : frontField.value;
            var back = shouldTrim ? backField.value.trim() : backField.value;
            if (!front.trim() || !back.trim()) {
                return;
            }
            if (!shouldDedupeFront) {
                phrases.push({ front: front, back: back });
                return;
            }
            var frontKey = front.toLocaleLowerCase();
            var nextEntry = {
                inputWord: inputWord,
                phrase: { front: front, back: back },
                locked: lockInput.checked
            };
            if (!chosenEntriesByFront.has(frontKey)) {
                orderedFrontKeys.push(frontKey);
                chosenEntriesByFront.set(frontKey, nextEntry);
                return;
            }
            var existingEntry = chosenEntriesByFront.get(frontKey);
            if (nextEntry.locked && existingEntry && !existingEntry.locked) {
                chosenEntriesByFront.set(frontKey, nextEntry);
            }
        });
        if (phrases.length) {
            grouped.push({ inputWord: inputWord, phrases: phrases });
        }
    });

    if (shouldDedupeFront) {
        grouped = [];
        orderedFrontKeys.forEach(function(frontKey) {
            var chosenEntry = chosenEntriesByFront.get(frontKey);
            if (!chosenEntry) {
                return;
            }
            var lastGroup = grouped[grouped.length - 1];
            if (lastGroup && lastGroup.inputWord === chosenEntry.inputWord) {
                lastGroup.phrases.push(chosenEntry.phrase);
                return;
            }
            grouped.push({
                inputWord: chosenEntry.inputWord,
                phrases: [chosenEntry.phrase]
            });
        });
    }

    return grouped;
}

function buildPlainText(grouped) {
    return grouped.map(function(group) {
        var lines = ["[" + group.inputWord + "]"];
        group.phrases.forEach(function(item) {
            lines.push(item.front + " - " + item.back);
        });
        return lines.join("\n");
    }).join("\n\n");
}

function buildMarkdown(grouped) {
    return grouped.map(function(group) {
        var lines = ["## " + group.inputWord];
        group.phrases.forEach(function(item) {
            lines.push("- " + item.front + ": " + item.back);
        });
        return lines.join("\n");
    }).join("\n\n");
}

function buildAnkiText(grouped) {
    var lines = [];
    grouped.forEach(function(group) {
        group.phrases.forEach(function(item) {
            lines.push(item.front + "\t" + item.back);
        });
    });
    return lines.join("\n");
}

function readWorkspaceInputValues() {
    return Array.prototype.map.call(document.querySelectorAll(".input-word-field"), function(field) {
        return field instanceof HTMLTextAreaElement ? field.value : "";
    });
}

function hasWorkspaceInputValue() {
    return readWorkspaceInputValues().some(function(value) {
        return value.trim().length > 0;
    });
}

function saveWorkspaceDraftNow() {
    try {
        var inputs = readWorkspaceInputValues();
        if (!inputs.length) {
            return;
        }
        window.localStorage.setItem(WORKSPACE_DRAFT_STORAGE_KEY, JSON.stringify({
            inputs: inputs,
            savedAt: Date.now()
        }));
    } catch (error) {
        return;
    }
}

function scheduleWorkspaceDraftSave() {
    window.clearTimeout(workspaceDraftTimer);
    workspaceDraftTimer = window.setTimeout(saveWorkspaceDraftNow, 180);
}

function restoreWorkspaceDraft() {
    try {
        if (hasWorkspaceInputValue()) {
            return;
        }
        var raw = window.localStorage.getItem(WORKSPACE_DRAFT_STORAGE_KEY);
        if (!raw) {
            return;
        }
        var payload = JSON.parse(raw);
        if (!payload || !Array.isArray(payload.inputs)) {
            return;
        }
        var fields = document.querySelectorAll(".input-word-field");
        payload.inputs.forEach(function(value, index) {
            var field = fields[index];
            if (field instanceof HTMLTextAreaElement && typeof value === "string") {
                field.value = value;
            }
        });
    } catch (error) {
        return;
    }
}

function setPanelValue(panel, value) {
    panel.value = value;
    panel.textContent = value;
    panel.setAttribute("rows", String(Math.max(value.split("\n").length, 1)));
}

function buildSubmissionPreviewCards(grouped) {
    return grouped.map(function(group) {
        var cards = group.phrases.map(function(item) {
            return [
                '<article class="submission-preview-card">',
                '<p class="submission-preview-card-front">' + escapeHtml(item.front) + '</p>',
                '<p class="submission-preview-card-back">' + escapeHtml(item.back) + '</p>',
                '</article>'
            ].join("");
        }).join("");
        return [
            '<section class="submission-preview-group">',
            '<h4 class="submission-preview-group-title">' + escapeHtml(group.inputWord) + '</h4>',
            '<div class="submission-preview-card-list">' + cards + '</div>',
            '</section>'
        ].join("");
    }).join("");
}

function refreshCopyExportArea() {
    var container = document.querySelector(".copy-export-area");
    if (!(container instanceof HTMLElement)) {
        return;
    }
    var grouped = buildExportPayload(container);
    var values = {
        plain: buildPlainText(grouped),
        markdown: buildMarkdown(grouped),
        anki: buildAnkiText(grouped)
    };
    ["plain", "markdown", "anki"].forEach(function(format) {
        var panel = document.getElementById("copy-export-text-" + format);
        if (panel instanceof HTMLTextAreaElement) {
            setPanelValue(panel, values[format]);
        }
    });
    var help = container.querySelector(".copy-export-help");
    if (help instanceof HTMLElement) {
        help.textContent = grouped.length ? "仅汇总当前勾选的词组，默认会清理首尾空白并按英文词组去重。" : "当前没有可导出的已勾选词组。";
    }
    var submissionPreview = document.getElementById("submission-preview-cards");
    if (submissionPreview instanceof HTMLElement) {
        submissionPreview.innerHTML = buildSubmissionPreviewCards(grouped);
    }
    var feedback = container.querySelector("[data-copy-feedback]");
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "";
    }
}

function filterDeckOptions(searchInput, select, feedback) {
    var query = searchInput.value.trim().toLocaleLowerCase();
    var currentValue = select.value;
    var originalOptions = select.__originalDeckOptions || [];
    var matchingCount = 0;
    select.innerHTML = "";

    originalOptions.forEach(function(optionData) {
        var matches = !query || optionData.label.toLocaleLowerCase().indexOf(query) !== -1;
        var shouldKeep = matches || optionData.value === currentValue;
        if (!shouldKeep) {
            return;
        }
        if (matches) {
            matchingCount += 1;
        }
        var option = document.createElement("option");
        option.value = optionData.value;
        option.textContent = optionData.label;
        if (optionData.value === currentValue) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    if (!select.options.length && originalOptions.length) {
        originalOptions.forEach(function(optionData) {
            var option = document.createElement("option");
            option.value = optionData.value;
            option.textContent = optionData.label;
            select.appendChild(option);
        });
        select.value = currentValue;
    }

    if (!(feedback instanceof HTMLElement)) {
        return;
    }
    if (!query) {
        feedback.textContent = "";
    } else if (matchingCount > 0) {
        feedback.textContent = "已筛出 " + matchingCount + " 个 deck";
    } else if (currentValue) {
        feedback.textContent = "没有匹配的 deck，已保留当前选中项。";
    } else {
        feedback.textContent = "没有匹配的 deck";
    }
}

function initDeckSearch() {
    var searchInput = document.querySelector("[data-deck-search]");
    var select = document.querySelector("[data-deck-selection]");
    var feedback = document.querySelector("[data-deck-feedback]");
    if (!(searchInput instanceof HTMLInputElement) || !(select instanceof HTMLSelectElement)) {
        return;
    }
    if (select.getAttribute("data-deck-search-initialized") === "true") {
        return;
    }
    select.setAttribute("data-deck-search-initialized", "true");
    select.__originalDeckOptions = Array.prototype.map.call(select.options, function(option) {
        return { value: option.value, label: option.textContent || option.value };
    });
    searchInput.addEventListener("input", function() {
        filterDeckOptions(searchInput, select, feedback);
    });
    select.addEventListener("change", function() {
        filterDeckOptions(searchInput, select, feedback);
    });
    filterDeckOptions(searchInput, select, feedback);
}

function initGenerationPendingState() {
    var form = document.querySelector("form");
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    form.addEventListener("submit", function(event) {
        var submitEvent = event;
        var submitter = submitEvent.submitter;
        if (!(submitter instanceof HTMLButtonElement) || submitter.value !== "generate") {
            return;
        }
        var banner = form.querySelector("[data-generation-pending-banner]");
        if (banner instanceof HTMLElement) {
            banner.classList.add("is-visible");
        }
        form.querySelectorAll('button[name="action"][value="generate"]').forEach(function(button) {
            if (button instanceof HTMLButtonElement) {
                button.classList.add("is-pending");
                button.setAttribute("aria-disabled", "true");
                button.textContent = "生成中...";
            }
        });
    });
}

function initSubmissionPendingState() {
    var form = document.querySelector("form");
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    form.addEventListener("submit", function(event) {
        var submitEvent = event;
        var submitter = submitEvent.submitter;
        if (!(submitter instanceof HTMLButtonElement) || submitter.value !== "submit") {
            return;
        }
        var banner = form.querySelector("[data-submission-pending-banner]");
        if (banner instanceof HTMLElement) {
            banner.classList.add("is-visible");
        }
        form.querySelectorAll('button[name="action"][value="submit"]').forEach(function(button) {
            if (button instanceof HTMLButtonElement) {
                button.classList.add("is-pending");
                button.setAttribute("aria-disabled", "true");
                button.textContent = "提交中...";
            }
        });
    });
}

function initTxtDropImport() {
    var panel = document.querySelector("[data-txt-import-panel]");
    if (!(panel instanceof HTMLElement)) {
        return;
    }
    if (panel.getAttribute("data-txt-import-initialized") === "true") {
        return;
    }
    panel.setAttribute("data-txt-import-initialized", "true");
    var form = document.querySelector("form");
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    var fileInput = document.getElementById("txt-import-file");
    if (!(fileInput instanceof HTMLInputElement)) {
        return;
    }

    var submitImport = function() {
        if (!fileInput.files || !fileInput.files.length) {
            return;
        }
        var actionInput = form.querySelector('input[name="action"][data-auto-import-action]');
        if (!(actionInput instanceof HTMLInputElement)) {
            actionInput = document.createElement("input");
            actionInput.type = "hidden";
            actionInput.name = "action";
            actionInput.value = "import-txt";
            actionInput.setAttribute("data-auto-import-action", "true");
            form.appendChild(actionInput);
        }
        form.requestSubmit();
    };

    var toggleDragging = function(isDragging) {
        panel.classList.toggle("is-dragging", isDragging);
    };

    ["dragenter", "dragover"].forEach(function(eventName) {
        panel.addEventListener(eventName, function(event) {
            event.preventDefault();
            toggleDragging(true);
        });
    });
    ["dragleave", "dragend", "drop"].forEach(function(eventName) {
        panel.addEventListener(eventName, function(event) {
            event.preventDefault();
            toggleDragging(false);
        });
    });
    panel.addEventListener("drop", function(event) {
        var droppedFiles = event.dataTransfer ? event.dataTransfer.files : null;
        if (!droppedFiles || !droppedFiles.length) {
            return;
        }
        fileInput.files = droppedFiles;
        submitImport();
    });
    fileInput.addEventListener("change", submitImport);
}

function getWorkspaceAction(form, submitter) {
    if (submitter instanceof HTMLButtonElement && submitter.name === "action") {
        return submitter.value;
    }
    var autoAction = form.querySelector('input[name="action"][data-auto-import-action]');
    if (autoAction instanceof HTMLInputElement) {
        return autoAction.value;
    }
    return "";
}

function shouldHandleWorkspaceAction(action) {
    return ["add-input", "add-50-inputs", "generate", "submit", "import-txt"].indexOf(action) !== -1;
}

function clearTransientActionInputs(form) {
    form.querySelectorAll('input[name="action"][data-auto-import-action], input[name="action"][data-ajax-fallback-action]').forEach(function(input) {
        input.remove();
    });
}

function ensureFallbackActionInput(form, action) {
    clearTransientActionInputs(form);
    if (!action) {
        return;
    }
    var actionInput = document.createElement("input");
    actionInput.type = "hidden";
    actionInput.name = "action";
    actionInput.value = action;
    actionInput.setAttribute("data-ajax-fallback-action", "true");
    form.appendChild(actionInput);
}

function collectWorkspaceFormData(form, submitter, action) {
    var formData = new FormData(form);
    if (submitter instanceof HTMLButtonElement && submitter.name) {
        formData.set(submitter.name, submitter.value);
    } else if (action) {
        formData.set("action", action);
    }
    return formData;
}

function markWorkspaceUpdating(isUpdating) {
    document.body.classList.toggle("is-workspace-updating", isUpdating);
    [".top-workbench", ".review-workspace", ".action-bar"].forEach(function(selector) {
        var element = document.querySelector(selector);
        if (element instanceof HTMLElement) {
            element.classList.toggle("is-updating", isUpdating);
        }
    });
}

function replaceElementFromDocument(sourceDocument, selector, freshClassName) {
    var current = document.querySelector(selector);
    var next = sourceDocument.querySelector(selector);
    if (!(current instanceof HTMLElement) || !(next instanceof HTMLElement)) {
        return false;
    }
    var replacement = document.importNode(next, true);
    if (replacement instanceof HTMLElement && freshClassName) {
        replacement.classList.add(freshClassName);
    }
    current.replaceWith(replacement);
    if (replacement instanceof HTMLElement && freshClassName) {
        window.setTimeout(function() {
            replacement.classList.remove(freshClassName);
        }, 320);
    }
    return true;
}

function replaceWorkspaceFromDocument(sourceDocument) {
    var replaced = false;
    [
        [".desktop-status-strip", ""],
        ["[data-generation-pending-banner]", ""],
        ["[data-submission-pending-banner]", ""],
        [".top-workbench", ""],
        [".review-workspace", "is-fresh"],
        [".action-bar", ""]
    ].forEach(function(item) {
        replaced = replaceElementFromDocument(sourceDocument, item[0], item[1]) || replaced;
    });
    return replaced;
}

function refreshWorkspaceBehaviorsAfterAjax(form, action) {
    clearTransientActionInputs(form);
    var exportContainer = document.querySelector(".copy-export-area");
    if (exportContainer instanceof HTMLElement) {
        restoreExportOptions(exportContainer);
    }
    initDeckSearch();
    initTxtDropImport();
    refreshCopyExportArea();
    if (action !== "submit") {
        saveWorkspaceDraftNow();
    }
}

function submitWorkspaceFormTraditional(form, action) {
    ensureFallbackActionInput(form, action);
    form.submit();
}

function submitWorkspaceFormAjax(form, submitter, action) {
    var formData = collectWorkspaceFormData(form, submitter, action);
    var requestCompleted = false;
    markWorkspaceUpdating(true);
    fetch(form.getAttribute("action") || window.location.href, {
        method: "POST",
        body: formData,
        headers: {
            "X-Requested-With": "XMLHttpRequest"
        }
    }).then(function(response) {
        requestCompleted = true;
        if (!response.ok) {
            throw new Error(String(response.status));
        }
        return response.text();
    }).then(function(responseHtml) {
        var responseDocument = new DOMParser().parseFromString(responseHtml, "text/html");
        var replaced = replaceWorkspaceFromDocument(responseDocument);
        markWorkspaceUpdating(false);
        if (replaced) {
            refreshWorkspaceBehaviorsAfterAjax(form, action);
        }
    }).catch(function() {
        markWorkspaceUpdating(false);
        if (!requestCompleted) {
            submitWorkspaceFormTraditional(form, action);
        }
    });
}

function initAjaxWorkspaceSubmission() {
    var form = document.querySelector(".desktop-main form");
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    if (form.getAttribute("data-ajax-workspace-initialized") === "true") {
        return;
    }
    form.setAttribute("data-ajax-workspace-initialized", "true");
    form.addEventListener("submit", function(event) {
        if (!window.fetch || !window.DOMParser) {
            return;
        }
        var submitEvent = event;
        var submitter = submitEvent.submitter;
        var action = getWorkspaceAction(form, submitter);
        if (!shouldHandleWorkspaceAction(action)) {
            return;
        }
        event.preventDefault();
        saveWorkspaceDraftNow();
        submitWorkspaceFormAjax(form, submitter, action);
    });
}

function setSidebarActiveLink(activeLink) {
    document.querySelectorAll(".sidebar-nav-link").forEach(function(link) {
        if (link instanceof HTMLElement) {
            link.classList.toggle("is-active", link === activeLink);
        }
    });
}

function initSidebarNavigation() {
    var links = Array.prototype.filter.call(document.querySelectorAll('.sidebar-nav-link[href^="#"]'), function(link) {
        if (!(link instanceof HTMLAnchorElement)) {
            return false;
        }
        return !!document.querySelector(link.getAttribute("href") || "");
    });
    if (!links.length) {
        return;
    }

    links.forEach(function(link) {
        link.addEventListener("click", function(event) {
            var hash = link.getAttribute("href") || "";
            var target = document.querySelector(hash);
            if (!(target instanceof HTMLElement)) {
                return;
            }
            event.preventDefault();
            sidebarManualActiveUntil = Date.now() + 900;
            setSidebarActiveLink(link);
            target.scrollIntoView({
                behavior: window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
                block: "start"
            });
            if (history.replaceState) {
                history.replaceState(null, "", hash);
            }
        });
    });

    if (!("IntersectionObserver" in window)) {
        return;
    }
    var linksByHash = new Map();
    links.forEach(function(link) {
        linksByHash.set(link.getAttribute("href"), link);
    });
    var observer = new IntersectionObserver(function(entries) {
        if (Date.now() < sidebarManualActiveUntil) {
            return;
        }
        var visibleEntries = entries.filter(function(entry) {
            return entry.isIntersecting;
        }).sort(function(left, right) {
            return right.intersectionRatio - left.intersectionRatio;
        });
        if (!visibleEntries.length) {
            return;
        }
        var nextLink = linksByHash.get("#" + visibleEntries[0].target.id);
        if (nextLink instanceof HTMLElement) {
            setSidebarActiveLink(nextLink);
        }
    }, {
        rootMargin: "-18% 0px -58% 0px",
        threshold: [0.12, 0.32, 0.6]
    });
    linksByHash.forEach(function(_link, hash) {
        var target = document.querySelector(hash);
        if (target instanceof HTMLElement) {
            observer.observe(target);
        }
    });
}

function initInstantFeedback() {
    document.addEventListener("pointerdown", function(event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        var control = target.closest("button, .sidebar-nav-link, .copy-export-format-button");
        if (!(control instanceof HTMLElement)) {
            return;
        }
        control.classList.add("is-pressing");
        window.setTimeout(function() {
            control.classList.remove("is-pressing");
        }, 180);
    });
}

function activateExportFormat(button) {
    var format = button.getAttribute("data-export-format");
    if (!format) {
        return;
    }
    var container = button.closest(".copy-export-area");
    if (!(container instanceof HTMLElement)) {
        return;
    }
    var buttons = container.querySelectorAll(".copy-export-format-button");
    buttons.forEach(function(item) {
        if (item instanceof HTMLElement) {
            item.classList.toggle("is-active", item === button);
        }
    });
    var panels = container.querySelectorAll(".copy-export-text");
    panels.forEach(function(panel) {
        if (!(panel instanceof HTMLElement)) {
            return;
        }
        var isActive = panel.getAttribute("data-export-panel") === format;
        panel.classList.toggle("is-active", isActive);
        panel.hidden = !isActive;
    });
    var copyButton = container.querySelector("[data-copy-target]");
    if (copyButton instanceof HTMLElement) {
        copyButton.setAttribute("data-copy-target", "copy-export-text-" + format);
    }
    var feedback = container.querySelector("[data-copy-feedback]");
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "";
    }
}

document.addEventListener("input", function(event) {
    var target = event.target;
    if (!(target instanceof HTMLElement)) {
        return;
    }
    if (target.matches(".phrase-front-input, .phrase-back-input")) {
        refreshCopyExportArea();
    }
    if (target.matches(".input-word-field")) {
        scheduleWorkspaceDraftSave();
    }
});

document.addEventListener("change", function(event) {
    var target = event.target;
    if (!(target instanceof HTMLElement)) {
        return;
    }
    if (target.matches(".phrase-select-input, .phrase-lock-input, .copy-export-option-input")) {
        var exportContainer = document.querySelector(".copy-export-area");
        if (exportContainer instanceof HTMLElement) {
            saveExportOptions(exportContainer);
        }
        refreshCopyExportArea();
    }
});

document.addEventListener("click", function(event) {
    var target = event.target;
    if (!(target instanceof HTMLElement)) {
        return;
    }
    if (target.matches(".copy-export-format-button")) {
        activateExportFormat(target);
        return;
    }
    if (!target.matches("[data-copy-target]")) {
        return;
    }
    var textAreaId = target.getAttribute("data-copy-target");
    if (!textAreaId) {
        return;
    }
    var textArea = document.getElementById(textAreaId);
    if (!(textArea instanceof HTMLTextAreaElement)) {
        return;
    }
    textArea.select();
    textArea.setSelectionRange(0, textArea.value.length);
    var container = target.closest(".copy-export-area");
    var feedback = container ? container.querySelector("[data-copy-feedback]") : null;
    var onSuccess = function(message) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = message;
        }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textArea.value).then(
            function() { onSuccess("已复制到剪贴板"); },
            function() {
                document.execCommand("copy");
                onSuccess("已复制到剪贴板");
            }
        );
        return;
    }
    document.execCommand("copy");
    onSuccess("已复制到剪贴板");
});

var initialExportContainer = document.querySelector(".copy-export-area");
if (initialExportContainer instanceof HTMLElement) {
    restoreExportOptions(initialExportContainer);
}
restoreWorkspaceDraft();
initDeckSearch();
initGenerationPendingState();
initSubmissionPendingState();
initTxtDropImport();
initAjaxWorkspaceSubmission();
initSidebarNavigation();
initInstantFeedback();
refreshCopyExportArea();
