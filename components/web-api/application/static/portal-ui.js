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
    var DATA_TABLE_LARGE_PAGE_SIZE = 100;
    var DATA_TABLE_ALL_PAGE_SIZE = -1;
    var DATA_TABLE_LENGTH_VALUES = [
        RESPONSIVE_PAGE_SIZES.mobile,
        RESPONSIVE_PAGE_SIZES.defaultValue,
        DATA_TABLE_LARGE_PAGE_SIZE,
        DATA_TABLE_ALL_PAGE_SIZE
    ];
    var PAGE_SIZE_PARAM = 'per_page';
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

    function enforceResponsivePageSize() {
        var url;
        var targetSize;

        if (!window.URL || !window.URLSearchParams) {
            return false;
        }

        url = new URL(window.location.href);
        if (url.searchParams.has(PAGE_SIZE_PARAM)) {
            return false;
        }

        targetSize = responsivePageSize();
        if (targetSize === RESPONSIVE_PAGE_SIZES.defaultValue) {
            return false;
        }

        url.searchParams.set(PAGE_SIZE_PARAM, String(targetSize));
        url.searchParams.delete('page');
        window.location.replace(url.toString());
        return true;
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

    function addResponsiveLayoutListener(callback) {
        $.each(['mobile', 'tablet'], function(index, queryName) {
            var media = window.matchMedia ? window.matchMedia(RESPONSIVE_QUERIES[queryName]) : null;

            if (!media) {
                return;
            }

            if (media.addEventListener) {
                media.addEventListener('change', callback);
            } else if (media.addListener) {
                media.addListener(callback);
            }
        });
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

    function fuzzyNum(value) {
        return String(value || '').replace(/[^\d.\-]/g, '');
    }

    function registerDataTableOrdering() {
        if (!$.fn.dataTable || !$.fn.dataTable.ext) {
            return;
        }

        $.fn.dataTable.ext.order['numbercase-asc'] = function(x, y) {
            return fuzzyNum(x) - fuzzyNum(y);
        };

        $.fn.dataTable.ext.order['numbercase-desc'] = function(x, y) {
            return fuzzyNum(y) - fuzzyNum(x);
        };
    }

    function dataTableFooterOptions(options) {
        var config = options || {};
        var lengthLabel = config.lengthLabel || '';
        var allLabel = config.allLabel || 'All';

        return {
            dom: 't<"d-none portal-datatable-generated-controls"lpi>',
            pageLength: config.pageLength || responsivePageSize(),
            pagingType: 'full_numbers',
            lengthMenu: [
                DATA_TABLE_LENGTH_VALUES,
                [
                    RESPONSIVE_PAGE_SIZES.mobile,
                    RESPONSIVE_PAGE_SIZES.defaultValue,
                    DATA_TABLE_LENGTH_VALUES[2],
                    allLabel
                ]
            ],
            language: {
                lengthMenu: '<span>' + lengthLabel + '</span> _MENU_',
                paginate: {
                    first: '<i class="bi bi-chevron-double-left" aria-hidden="true"></i>',
                    previous: '<i class="bi bi-chevron-left" aria-hidden="true"></i>',
                    next: '<i class="bi bi-chevron-right" aria-hidden="true"></i>',
                    last: '<i class="bi bi-chevron-double-right" aria-hidden="true"></i>'
                }
            }
        };
    }

    function mountDataTableFooter(tableElement, footerElement) {
        var table = $(tableElement);
        var footer = $(footerElement);
        var wrapper = table.closest('.dataTables_wrapper');
        var length = wrapper.find('.dataTables_length');
        var info = wrapper.find('.dataTables_info');
        var paginate = wrapper.find('.dataTables_paginate');
        var infoMount = footer.find('.js-datatable-info-mount');
        var paginationMount = footer.find('.js-datatable-pagination-mount');
        var lengthMount = footer.find('.js-datatable-length-mount');

        if (info.length && infoMount.length && info.parent()[0] !== infoMount[0]) {
            infoMount.empty().append(info);
        }

        if (paginate.length && paginationMount.length && paginate.parent()[0] !== paginationMount[0]) {
            paginationMount.empty().append(paginate);
        }

        if (length.length && lengthMount.length) {
            length.addClass('players-page-size-form');
            if (length.parent()[0] !== lengthMount[0]) {
                lengthMount.empty().append(length);
            }
        }
    }

    function initResponsiveTemplateMount(mountElement) {
        var $mount = $(mountElement);
        var tabletTemplateId = $mount.data('tabletTemplate');
        var mobileTemplateId = $mount.data('mobileTemplate');
        var layoutClass = $mount.data('layoutClass');
        var disableMobileTooltips = $mount.data('disableMobileTooltips') === true ||
            $mount.data('disableMobileTooltips') === 'true';

        function render() {
            var layout = responsiveLayout();
            var template;

            if (layoutClass) {
                $(document.documentElement).addClass(layoutClass);
            }

            if ($mount.data('portalLayout') === layout) {
                return;
            }

            $mount.empty().data('portalLayout', layout);

            if (layout === 'desktop') {
                return;
            }

            template = document.getElementById(layout === 'mobile' ? mobileTemplateId : tabletTemplateId);
            if (!template) {
                return;
            }

            if (template.content) {
                mountElement.appendChild(template.content.cloneNode(true));
            } else {
                $mount.html($(template).html());
            }

            if (layout === 'mobile' && disableMobileTooltips) {
                disableTooltips($mount);
            } else {
                refreshTooltips($mount);
            }
        }

        render();
        addResponsiveLayoutListener(render);
    }

    function initResponsiveTemplateMounts() {
        $('[data-responsive-template-mount]').each(function() {
            initResponsiveTemplateMount(this);
        });
    }

    function submitClosestForm() {
        $(this).closest('form').trigger('submit');
    }

    function initAutoSubmitControls() {
        $(document).on(
            'change',
            '.tournament-filter-form select, .players-filter-form select, .players-page-size-form select[name="' + PAGE_SIZE_PARAM + '"]',
            submitClosestForm
        );
        $(document).on('change', '.tournament-toggle-form input[type="checkbox"]', submitClosestForm);
    }

    function initRowClicks() {
        $(document).on('click', '.tournament-row-clickable, #players tbody tr.players-row', function(event) {
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

    function initScrollMemory(linkSelector, targetSelector, storageKey) {
        $(document).on('click', linkSelector, function() {
            if (!$(this).hasClass('is-disabled') && $(this).attr('href') !== '#') {
                window.sessionStorage.setItem(storageKey, '1');
            }
        });

        if (window.sessionStorage.getItem(storageKey) === '1') {
            window.sessionStorage.removeItem(storageKey);
            $(targetSelector).each(function() {
                this.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                return false;
            });
        }
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
        if ($('[data-responsive-page-size]').length && enforceResponsivePageSize()) {
            return;
        }

        registerDataTableOrdering();
        initResponsiveTemplateMounts();
        refreshTooltips(document);
        initAutoSubmitControls();
        initRowClicks();
        initTournamentNotesCards();
        initScrollMemory('.tournaments-page-link', '.tournaments-results-surface', 'tournaments-table-scroll');
        initScrollMemory('.players-page-link', '.players-results-surface', 'players-table-scroll');

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
        enforcePageSize: enforceResponsivePageSize,
        layout: responsiveLayout
    };

    portal.tooltips = {
        disable: disableTooltips,
        hideAll: hideAllTooltips,
        refresh: refreshTooltips
    };

    portal.dataTableFooter = {
        defaultPageLength: responsivePageSize,
        init: function(tableElement, tableOptions, footerElement, afterDraw) {
            var table = $(tableElement);
            var options = $.extend(true, {}, tableOptions || {});
            var portalFooter = options.portalFooter || {};
            var dataTable;

            delete options.portalFooter;
            dataTable = table.DataTable($.extend(true, {}, dataTableFooterOptions(portalFooter), options));

            mountDataTableFooter(table, footerElement);
            dataTable.on('draw.dt', function() {
                mountDataTableFooter(table, footerElement);
                if (typeof afterDraw === 'function') {
                    afterDraw(dataTable);
                }
            });

            return dataTable;
        },
        mount: mountDataTableFooter
    };

    $(initPortalUi);
})(window, document, window.jQuery);
