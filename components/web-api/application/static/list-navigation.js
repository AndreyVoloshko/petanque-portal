(() => {
    const region = document.querySelector('[data-list-region]');
    if (!region) return;

    const announcements = document.createElement('div');
    announcements.className = 'visually-hidden';
    announcements.setAttribute('role', 'status');
    region.after(announcements);

    const scrollPositions = new Map();
    let nextEntry = 0;
    let entry = String(performance.timeOrigin);
    let pending;
    history.replaceState({...history.state, portalListEntry: entry}, '');
    history.scrollRestoration = 'manual';

    function saveScroll() {
        scrollPositions.set(entry, window.scrollY);
    }

    function sameRoute(url) {
        return url.origin === location.origin && url.pathname === location.pathname;
    }

    function focusKey(element) {
        if (element.matches('.portal-list-size-menu button, .portal-list-size-options summary')) {
            return 'page-size';
        }
        return [
            element.tagName, element.name, element.value,
            element.getAttribute('aria-label') || element.textContent.trim(),
        ].join('|');
    }

    async function update(url, historyEntry = null) {
        const fromHistory = historyEntry !== null;
        pending?.abort();
        const request = new AbortController();
        pending = request;
        region.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(url, {signal: request.signal});
            if (!response.ok || response.redirected) throw new Error('The list could not be loaded.');
            const nextPage = new DOMParser().parseFromString(await response.text(), 'text/html');
            const nextRegion = nextPage.querySelector('[data-list-region]');
            if (!nextRegion) throw new Error('The response has no list.');
            if (request.signal.aborted) return;

            const active = document.activeElement;
            const preserveFocus = region.contains(active);
            const key = preserveFocus ? focusKey(active) : null;
            const oldScroll = window.scrollY;
            const footerWasActive = preserveFocus && active.closest('.portal-list-footer');
            const results = region.querySelector('.portal-results') || region;
            const resultsTop = results.getBoundingClientRect().top + oldScroll;

            if (fromHistory) {
                entry = historyEntry;
            } else if (url.href !== location.href) {
                saveScroll();
                entry = `${performance.timeOrigin}:${++nextEntry}`;
                history.pushState({portalListEntry: entry}, '', url);
            }

            window.PetanquePortal?.tooltips.disable(region);
            region.replaceChildren(...nextRegion.childNodes);
            window.PetanquePortal?.tooltips.refresh(region);

            const footer = region.querySelector('.portal-list-footer');
            const target = preserveFocus && [...region.querySelectorAll('a, button, input, select, summary')]
                .find(element => focusKey(element) === key);
            if (target) {
                target.focus({preventScroll: true});
            } else if (preserveFocus) {
                const nextResults = region.querySelector('.portal-results') || region;
                nextResults.tabIndex = -1;
                nextResults.focus({preventScroll: true});
            }

            const footerBottom = footer?.getBoundingClientRect().bottom + window.scrollY;
            const scrollTop = fromHistory
                ? scrollPositions.get(entry) ?? oldScroll
                : footerWasActive && (!footer || footerBottom < oldScroll) ? resultsTop : oldScroll;
            window.scrollTo({top: scrollTop, behavior: 'instant'});

            announcements.textContent = footer?.querySelector('p')?.textContent.trim()
                || (region.querySelector('.portal-results, .player-tournaments-empty') || region).innerText.trim();
        } catch (error) {
            if (!request.signal.aborted) {
                if (fromHistory) location.reload();
                else location.assign(url);
            }
        } finally {
            if (pending === request) {
                pending = null;
                region.removeAttribute('aria-busy');
            }
        }
    }

    region.addEventListener('change', event => {
        const select = event.target;
        if (select instanceof HTMLSelectElement && select.form?.matches('.portal-filter-bar[data-list-form]')) {
            select.form.requestSubmit();
        }
    });

    region.addEventListener('submit', event => {
        const form = event.target.closest('form[data-list-form]');
        if (!form || event.defaultPrevented) return;
        const url = new URL(form.action);
        if (!sameRoute(url)) return;
        url.search = new URLSearchParams(new FormData(form, event.submitter)).toString();
        event.preventDefault();
        update(url);
    });

    region.addEventListener('click', event => {
        const link = event.target.closest('a[data-list-link]');
        if (!link || event.defaultPrevented || event.button !== 0
            || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey
            || (link.target && link.target !== '_self') || link.hasAttribute('download')) return;
        const url = new URL(link.href);
        if (!sameRoute(url)) return;
        event.preventDefault();
        update(url);
    });

    window.addEventListener('popstate', event => {
        if (event.state?.portalListEntry == null) return;
        saveScroll();
        update(new URL(location.href), event.state.portalListEntry);
    });
})();
