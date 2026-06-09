(function(window, document) {
    window.PetanquePortal = window.PetanquePortal || {};

    var tooltipSelector = '[data-bs-toggle="tooltip"], [data-toggle="tooltip"]';
    var touchQuery = window.matchMedia
        ? window.matchMedia('(hover: none), (pointer: coarse)')
        : null;
    var activeTooltipTrigger = null;

    function isTouchTooltipDevice() {
        return touchQuery ? touchQuery.matches : false;
    }

    function isTouchTooltipEvent(event) {
        return isTouchTooltipDevice() || event.pointerType === 'touch' || event.type === 'touchstart';
    }

    function getBootstrapTooltip(element) {
        var Tooltip = window.bootstrap && window.bootstrap.Tooltip;

        if (!Tooltip || !Tooltip.getInstance) {
            return null;
        }

        return Tooltip.getInstance(element);
    }

    function isTooltipVisible(element) {
        var tooltipId = element.getAttribute('aria-describedby');

        return Boolean(tooltipId && document.getElementById(tooltipId));
    }

    function hideTooltip(element) {
        var tooltip = getBootstrapTooltip(element);

        if (tooltip && tooltip.hide) {
            tooltip.hide();
        }

        if (element.blur) {
            element.blur();
        }
    }

    function hideAllTooltips(exceptElement) {
        document.querySelectorAll(tooltipSelector).forEach(function(element) {
            if (element !== exceptElement) {
                hideTooltip(element);
            }
        });
    }

    function closestTooltipTrigger(target) {
        if (!target.closest) {
            return null;
        }

        return target.closest(tooltipSelector);
    }

    function handleTouchTooltipTap(event) {
        var trigger;

        if (!isTouchTooltipEvent(event)) {
            return;
        }

        if (event.target.closest && event.target.closest('.tooltip')) {
            return;
        }

        trigger = closestTooltipTrigger(event.target);

        if (!trigger) {
            hideAllTooltips();
            activeTooltipTrigger = null;
            return;
        }

        if (trigger.matches && trigger.matches('a[href]')) {
            hideAllTooltips(trigger);
            activeTooltipTrigger = trigger;
            return;
        }

        if (isTooltipVisible(trigger)) {
            event.preventDefault();

            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }

            hideTooltip(trigger);
            activeTooltipTrigger = null;
            return;
        }

        hideAllTooltips(trigger);
        activeTooltipTrigger = trigger;
    }

    document.addEventListener('show.bs.tooltip', function(event) {
        if (!isTouchTooltipDevice()) {
            return;
        }

        hideAllTooltips(event.target);
        activeTooltipTrigger = event.target;
    }, true);

    document.addEventListener('hidden.bs.tooltip', function(event) {
        if (activeTooltipTrigger === event.target) {
            activeTooltipTrigger = null;
        }
    }, true);

    document.addEventListener(
        window.PointerEvent ? 'pointerdown' : 'touchstart',
        handleTouchTooltipTap,
        true
    );

    window.PetanquePortal.tooltips = {
        hideAll: hideAllTooltips
    };
})(window, document);
