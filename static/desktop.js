(function() {
    function prefersReducedMotion() {
        return window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function findHashTarget(hash) {
        if (!hash || hash.length < 2) {
            return null;
        }
        try {
            return document.querySelector(hash);
        } catch (error) {
            return null;
        }
    }

    function pulseTarget(target) {
        target.classList.remove("is-focus-glow");
        window.requestAnimationFrame(function() {
            target.classList.add("is-focus-glow");
            window.setTimeout(function() {
                target.classList.remove("is-focus-glow");
            }, 1000);
        });
    }

    function focusTarget(target) {
        if (typeof target.focus === "function") {
            target.focus({ preventScroll: true });
        }
        pulseTarget(target);
    }

    function slideToTarget(target) {
        var reduced = prefersReducedMotion();
        target.scrollIntoView({
            behavior: reduced ? "auto" : "smooth",
            block: "center"
        });
        window.setTimeout(function() {
            focusTarget(target);
        }, reduced ? 0 : 280);
    }

    function initStepActions() {
        document.querySelectorAll('.setup-step-action[href^="#"]').forEach(function(link) {
            link.addEventListener("click", function(event) {
                var target = findHashTarget(link.getAttribute("href"));
                if (!target) {
                    return;
                }
                event.preventDefault();
                if (history.pushState) {
                    history.pushState(null, "", link.getAttribute("href"));
                }
                slideToTarget(target);
            });
        });
    }

    function initHashLanding() {
        var target = findHashTarget(window.location.hash);
        if (!target) {
            return;
        }
        window.requestAnimationFrame(function() {
            slideToTarget(target);
        });
    }

    function initInstantFeedback() {
        document.addEventListener("pointerdown", function(event) {
            var target = event.target;
            if (!(target instanceof HTMLElement)) {
                return;
            }
            var control = target.closest("button, .settings-secondary-action, .setup-step-action");
            if (!(control instanceof HTMLElement)) {
                return;
            }
            control.classList.add("is-pressing");
            window.setTimeout(function() {
                control.classList.remove("is-pressing");
            }, 180);
        });
    }

    document.addEventListener("DOMContentLoaded", function() {
        document.body.classList.add("settings-motion-ready");
        initStepActions();
        initHashLanding();
        initInstantFeedback();
    });
}());
