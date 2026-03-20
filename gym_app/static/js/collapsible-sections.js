document.addEventListener("DOMContentLoaded", function () {
    var triggers = document.querySelectorAll(".collapsible-trigger[aria-controls]");

    triggers.forEach(function (trigger) {
        var panelId = trigger.getAttribute("aria-controls");
        var panel = document.getElementById(panelId);

        if (!panel) {
            return;
        }

        function setExpanded(isExpanded) {
            trigger.setAttribute("aria-expanded", isExpanded ? "true" : "false");
            panel.hidden = !isExpanded;
        }

        setExpanded(trigger.getAttribute("aria-expanded") !== "false");

        trigger.addEventListener("click", function () {
            setExpanded(trigger.getAttribute("aria-expanded") !== "true");
        });
    });
});
