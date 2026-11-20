(function(window, document, $) {
    'use strict';

    if (!$) {
        return;
    }

    var portal = window.PetanquePortal = window.PetanquePortal || {};

    var RESPONSIVE_QUERIES = {
        mobile: '(max-width: 767.98px)',
        tablet: '(min-width: 768px) and (max-width: 1400px)',
        compact: '(max-width: 1400px)'
    };
    var RESPONSIVE_PAGE_SIZES = {
        defaultValue: 50,
        tablet: 30,
        mobile: 25
    };
    var TOOLTIP_SELECTOR = '[data-bs-toggle="tooltip"], [data-toggle="tooltip"]';
    var TOOLTIP_DATA_OFFSET = '0,2';
    var TOOLTIP_OFFSET = [0, 2];
    var TOUCH_TOOLTIP_QUERY = window.matchMedia
        ? window.matchMedia('(hover: none), (pointer: coarse)')
        : null;
    var activeTooltipTrigger = null;

    function mediaMatches(queryName) {
        if (!window.matchMedia || !RESPONSIVE_QUERIES[queryName]) {
            return false;
        }

        return window.matchMedia(RESPONSIVE_QUERIES[queryName]).matches;
    }

    function responsivePageSize() {
        if (mediaMatches('mobile')) {
            return RESPONSIVE_PAGE_SIZES.mobile;
        }

        if (mediaMatches('compact')) {
            return RESPONSIVE_PAGE_SIZES.tablet;
        }

        return RESPONSIVE_PAGE_SIZES.defaultValue;
    }

    function responsiveLayout() {
        if (mediaMatches('mobile')) {
            return 'mobile';
        }

        if (mediaMatches('tablet')) {
            return 'tablet';
        }

        return 'desktop';
    }

    function findWithSelf(root, selector) {
        var $root = root && root.jquery ? root : $(root || document);

        return $root.filter(selector).add($root.find(selector));
    }

    function bootstrapTooltipApi() {
        return window.bootstrap && window.bootstrap.Tooltip;
    }

    function getBootstrapTooltip(element) {
        var Tooltip = bootstrapTooltipApi();

        if (!Tooltip || !Tooltip.getInstance) {
            return null;
        }

        return Tooltip.getInstance(element);
    }

    function createBootstrapTooltip(element) {
        var Tooltip = bootstrapTooltipApi();

        if (!Tooltip) {
            return null;
        }

        if (Tooltip.getOrCreateInstance) {
            return Tooltip.getOrCreateInstance(element, {
                container: 'body',
                offset: TOOLTIP_OFFSET
            });
        }

        return Tooltip.getInstance(element) || new Tooltip(element, {
            container: 'body',
            offset: TOOLTIP_OFFSET
        });
    }

    function disposeJqueryTooltip($element) {
        if (!$.fn.tooltip || !$element.data('bs.tooltip')) {
            return;
        }

        try {
            $element.tooltip('dispose');
        } catch (error) {
            $element.tooltip('destroy');
        }
    }

    function disposeTooltip(element) {
        var tooltip = getBootstrapTooltip(element);

        if (tooltip && tooltip.dispose) {
            tooltip.dispose();
            return;
        }

        disposeJqueryTooltip($(element));
    }

    function prepareTooltip(element) {
        $(element).attr('data-bs-offset', TOOLTIP_DATA_OFFSET);
    }

    function initTooltip(element, showImmediately) {
        var tooltip;
        var $element = $(element);

        prepareTooltip(element);

        if (bootstrapTooltipApi()) {
            tooltip = createBootstrapTooltip(element);
            if (showImmediately && tooltip && tooltip.show) {
                tooltip.show();
            }
            return;
        }

        if ($.fn.tooltip) {
            if (!$element.data('bs.tooltip')) {
                $element.tooltip({
                    container: 'body',
                    offset: TOOLTIP_OFFSET
                });
            }

            if (showImmediately) {
                $element.tooltip('show');
            }
        }
    }

    function refreshTooltips(root) {
        findWithSelf(root, TOOLTIP_SELECTOR).each(function() {
            initTooltip(this, false);
        });
    }

    function disableTooltips(root) {
        findWithSelf(root, TOOLTIP_SELECTOR).each(function() {
            disposeTooltip(this);
            $(this)
                .removeAttr('data-bs-toggle data-toggle data-bs-placement data-placement')
                .removeAttr('data-bs-container data-container data-bs-offset')
                .removeAttr('data-bs-original-title data-original-title')
                .removeAttr('aria-describedby title');
        });
    }

    function isTouchTooltipDevice() {
        return TOUCH_TOOLTIP_QUERY ? TOUCH_TOOLTIP_QUERY.matches : false;
    }

    function isTouchTooltipEvent(event) {
        var originalEvent = event.originalEvent || event;

        return isTouchTooltipDevice() ||
            originalEvent.pointerType === 'touch' ||
            originalEvent.type === 'touchstart';
    }

    function isTooltipVisible(element) {
        var tooltipId = element.getAttribute('aria-describedby');

        return Boolean(tooltipId && document.getElementById(tooltipId));
    }

    function hideTooltip(element) {
        var tooltip = getBootstrapTooltip(element);
        var $element = $(element);

        if (tooltip && tooltip.hide) {
            tooltip.hide();
        } else if ($.fn.tooltip && $element.data('bs.tooltip')) {
            $element.tooltip('hide');
        }

        $element.trigger('blur');
    }

    function hideAllTooltips(exceptElement) {
        $(TOOLTIP_SELECTOR).each(function() {
            if (this !== exceptElement) {
                hideTooltip(this);
            }
        });
    }

    function handleTouchTooltipTap(event) {
        var trigger;

        if (!isTouchTooltipEvent(event)) {
            return;
        }

        if ($(event.target).closest('.tooltip').length) {
            return;
        }

        trigger = $(event.target).closest(TOOLTIP_SELECTOR)[0];

        if (!trigger) {
            hideAllTooltips();
            activeTooltipTrigger = null;
            return;
        }

        if ($(trigger).is('a[href]')) {
            hideAllTooltips(trigger);
            activeTooltipTrigger = trigger;
            return;
        }

        if (isTooltipVisible(trigger)) {
            event.preventDefault();
            event.stopImmediatePropagation();
            hideTooltip(trigger);
            activeTooltipTrigger = null;
            return;
        }

        hideAllTooltips(trigger);
        activeTooltipTrigger = trigger;
    }

    function initRowClicks() {
        $(document).on('click', '#players tbody tr.players-row, #clubs tbody tr.clubs-row, .player-tournament-row', function(event) {
            var href;

            if ($(event.target).closest('a, button, input, select').length) {
                return;
            }

            href = $(this).data('href');
            if (href) {
                window.location.href = href;
            }
        });
    }

    function initTournamentNotesCards() {
        $('[data-tournament-notes-card]').each(function() {
            var $card = $(this);
            var $editButton = $card.find('[data-tournament-notes-edit]');
            var $display = $card.find('[data-tournament-notes-display]');
            var $form = $card.find('[data-tournament-notes-form]');
            var $textarea = $form.find('textarea');

            if ($card.data('notesInitialized') || !$editButton.length || !$display.length || !$form.length || !$textarea.length) {
                return;
            }

            $card.data('notesInitialized', true);
            $editButton.on('click', function() {
                var isEditing = !$form.prop('hidden');
                var textarea = $textarea[0];

                $form.prop('hidden', isEditing);
                $display.prop('hidden', !isEditing);
                $editButton.attr('aria-expanded', isEditing ? 'false' : 'true');

                if (!isEditing) {
                    textarea.focus();
                    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
                }
            });
        });
    }

    function initPortalUi() {
        refreshTooltips(document);
        initRowClicks();
        initTournamentNotesCards();

        $(document).on('click', '.players-column-help', function(event) {
            event.preventDefault();
            event.stopPropagation();
        });

        $(document).on('click', '.force-follow-link', function(event) {
            event.preventDefault();
            window.location.href = $(this).attr('href');
        });
    }

    $(document)
        .on(window.PointerEvent ? 'pointerdown' : 'touchstart', handleTouchTooltipTap)
        .on('show.bs.tooltip', function(event) {
            if (!isTouchTooltipDevice()) {
                return;
            }

            hideAllTooltips(event.target);
            activeTooltipTrigger = event.target;
        })
        .on('hidden.bs.tooltip', function(event) {
            if (activeTooltipTrigger === event.target) {
                activeTooltipTrigger = null;
            }
        })
        .on('pointerover', TOOLTIP_SELECTOR, function() {
            initTooltip(this, true);
        })
        .on('focusin', TOOLTIP_SELECTOR, function() {
            initTooltip(this, true);
        });

    portal.responsive = {
        pageSize: responsivePageSize,
        layout: responsiveLayout
    };

    portal.tooltips = {
        disable: disableTooltips,
        hideAll: hideAllTooltips,
        refresh: refreshTooltips
    };

    $(initPortalUi);
})(window, document, window.jQuery);
