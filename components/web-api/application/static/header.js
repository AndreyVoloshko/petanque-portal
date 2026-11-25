function initHeaderSearch(search) {
    const form = search.querySelector('form');
    const input = form.querySelector('input');
    const panel = form.querySelector('.portal-search-panel');
    const status = panel.querySelector('[role="status"]');
    const results = panel.querySelector('[role="listbox"]');
    const toggle = search.querySelector('.portal-search-toggle');
    const navigation = document.getElementById('portal-navigation');
    const menuButton = document.querySelector('.portal-header-toggle');
    const mobile = window.matchMedia('(max-width: 1199.98px)');
    const icons = { player: 'bi-person', club: 'bi-buildings', tournament: 'bi-trophy' };
    const cache = new Map();
    let timer;
    let controller;
    let matches = [];
    let options = [];
    let activeIndex = -1;

    function cancelLookup() {
        window.clearTimeout(timer);
        controller?.abort();
        controller = undefined;
    }

    function selectOption(index) {
        if (activeIndex >= 0) options[activeIndex].setAttribute('aria-selected', 'false');
        activeIndex = index;
        if (index < 0) {
            input.removeAttribute('aria-activedescendant');
            return;
        }
        const option = options[index];
        option.setAttribute('aria-selected', 'true');
        input.setAttribute('aria-activedescendant', option.id);
        option.scrollIntoView({ block: 'nearest' });
    }

    function showStatus(message) {
        selectOption(-1);
        options = [];
        matches = [];
        results.replaceChildren();
        status.textContent = message;
        status.hidden = !message;
        panel.hidden = false;
        input.setAttribute('aria-expanded', 'true');
    }

    function dismissResults() {
        cancelLookup();
        selectOption(-1);
        panel.hidden = true;
        input.setAttribute('aria-expanded', 'false');
    }

    function closeSearch(restoreFocus = false) {
        dismissResults();
        if (search.hasAttribute('data-open')) {
            search.removeAttribute('data-open');
            toggle.setAttribute('aria-expanded', 'false');
            if (restoreFocus) toggle.focus();
        }
    }

    function render(items) {
        showStatus(items.length ? '' : form.dataset.empty);
        for (const [kind, iconClass] of Object.entries(icons)) {
            const groupItems = items.filter(item => item.kind === kind);
            if (!groupItems.length) continue;

            const group = document.createElement('div');
            const heading = document.createElement('div');
            heading.id = `portal-search-group-${kind}`;
            heading.className = 'portal-search-group';
            heading.textContent = form.dataset[kind];
            group.setAttribute('role', 'group');
            group.setAttribute('aria-labelledby', heading.id);
            group.append(heading);

            for (const item of groupItems) {
                const link = document.createElement('a');
                const icon = document.createElement('i');
                const label = document.createElement('span');
                link.id = `portal-search-option-${options.length}`;
                link.className = 'portal-search-option';
                link.href = item.href;
                link.tabIndex = -1;
                link.setAttribute('role', 'option');
                link.setAttribute('aria-selected', 'false');
                icon.className = `bi ${iconClass}`;
                icon.setAttribute('aria-hidden', 'true');
                label.textContent = item.value;
                link.append(icon, label);
                group.append(link);
                options.push(link);
                matches.push(item);
            }
            results.append(group);
        }
    }

    async function lookup(query) {
        const request = new AbortController();
        controller = request;
        const url = new URL(form.dataset.url, window.location.origin);
        url.searchParams.set('typedText', query);
        url.searchParams.set('limit_per_type', '4');
        try {
            const response = await fetch(url, { signal: request.signal, headers: { Accept: 'application/json' } });
            if (!response.ok) throw new Error('Search request failed');
            const items = await response.json();
            if (controller !== request) return;
            if (cache.size >= 24) cache.delete(cache.keys().next().value);
            cache.set(query, items);
            render(items);
        } catch {
            if (controller === request && !request.signal.aborted) showStatus(form.dataset.error);
        } finally {
            if (controller === request) controller = undefined;
        }
    }

    function updateSearch(delay = 160) {
        cancelLookup();
        const query = input.value.trim();
        if (query.length < 2) {
            showStatus(form.dataset.minimum);
            return;
        }
        if (cache.has(query)) {
            render(cache.get(query));
            return;
        }
        showStatus(form.dataset.loading);
        if (delay) timer = window.setTimeout(() => lookup(query), delay);
        else lookup(query);
    }

    function closeNavigation() {
        const collapse = window.bootstrap?.Collapse.getInstance(navigation);
        if (navigation.classList.contains('collapsing') && menuButton.getAttribute('aria-expanded') === 'true') {
            navigation.addEventListener('shown.bs.collapse', () => collapse?.hide(), { once: true });
        } else {
            collapse?.hide();
        }
    }

    toggle.addEventListener('click', () => {
        if (search.hasAttribute('data-open')) {
            closeSearch(true);
            return;
        }
        closeNavigation();
        search.setAttribute('data-open', '');
        toggle.setAttribute('aria-expanded', 'true');
        input.focus();
    });
    form.querySelector('.portal-search-close').addEventListener('click', () => closeSearch(true));
    navigation.addEventListener('show.bs.collapse', () => closeSearch());
    mobile.addEventListener('change', () => closeSearch());
    input.addEventListener('focus', () => updateSearch());
    input.addEventListener('click', () => {
        if (panel.hidden) updateSearch();
    });
    input.addEventListener('input', event => {
        if (!event.isComposing) updateSearch();
    });
    input.addEventListener('compositionend', () => updateSearch());
    form.addEventListener('submit', event => {
        event.preventDefault();
        const match = !panel.hidden && matches[activeIndex < 0 ? 0 : activeIndex];
        if (match) window.location.assign(match.href);
        else if (!controller) updateSearch(0);
    });
    input.addEventListener('keydown', event => {
        if (event.isComposing) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            closeSearch(true);
        } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            if (panel.hidden) updateSearch(0);
            if (!options.length) return;
            event.preventDefault();
            const next = event.key === 'ArrowDown' ? activeIndex + 1
                : (activeIndex < 0 ? options.length : activeIndex) - 1;
            selectOption((next + options.length) % options.length);
        }
    });
    search.addEventListener('focusout', event => {
        if (event.relatedTarget && !search.contains(event.relatedTarget)) closeSearch();
    });
    document.addEventListener('pointerdown', event => {
        if (!search.contains(event.target)) closeSearch();
        if (!navigation.contains(event.target) && !menuButton.contains(event.target)) {
            closeNavigation();
        }
    });
    search.hidden = false;
}

const headerSearch = document.querySelector('[data-header-search]');
if (headerSearch) initHeaderSearch(headerSearch);

const consent = document.getElementById('gdpr_warning');
if (consent) {
    consent.querySelector('#gdpr-yes').addEventListener('click', () => {
        const expires = new Date();
        expires.setFullYear(expires.getFullYear() + 10);
        document.cookie = `gdpr_agree=1; path=/; expires=${expires.toUTCString()}; SameSite=Lax`;
        consent.remove();
    });
    consent.querySelector('#gdpr-no').addEventListener('click', () => {
        window.location.assign('https://www.google.com');
    });
}
