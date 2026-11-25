(() => {
    const page = document.querySelector('[data-documents]');
    const search = page?.querySelector('#documentsSearch');
    if (!search) return;

    const pageSize = 12;
    const viewKey = 'petanque.documents.view';
    const list = page.querySelector('#documentList');
    const sort = page.querySelector('#documentsSort');
    const categorySelect = page.querySelector('#documentsCategory');
    const yearFilters = page.querySelector('#documentsYearFilters');
    const categoryButtons = [...page.querySelectorAll('button[data-category]')];
    const viewButtons = [...page.querySelectorAll('[data-documents-view]')];
    const empty = page.querySelector('#documentsEmptyState');
    const showMore = page.querySelector('#documentsShowMore');

    let category = 'all';
    let year = 'all';
    let query = '';
    let limit = pageSize;
    let searchTimer;

    const now = Date.now();
    const week = 7 * 24 * 60 * 60 * 1000;
    const cards = [...list.querySelectorAll('.document-card')].map(element => {
        const { category, date } = element.dataset;
        const title = element.querySelector('.document-card-title').textContent.toLowerCase();
        const notes = element.querySelector('.document-card-notes')?.textContent.toLowerCase() ?? '';
        const badge = element.querySelector('[data-document-new]');
        const age = now - Date.parse(date);
        if (badge) badge.hidden = !(age >= 0 && age < week);
        return { element, category, date, year: date.slice(0, 4), title, notes };
    });

    const years = [...new Set(cards.map(card => card.year).filter(Boolean))].sort().reverse();
    for (const value of years) {
        const button = yearFilters.firstElementChild.cloneNode();
        button.dataset.year = value;
        button.textContent = value;
        yearFilters.append(button);
    }
    const yearButtons = [...yearFilters.querySelectorAll('button')];

    function setPressed(buttons, key, value) {
        buttons.forEach(button => button.setAttribute('aria-pressed', button.dataset[key] === value));
    }

    function setView(view) {
        list.dataset.view = view;
        setPressed(viewButtons, 'documentsView', view);
    }

    function sortCards() {
        const direction = sort.value === 'oldest' ? 1 : -1;
        cards.sort((first, second) => {
            if (!first.date || !second.date) {
                return Number(!first.date) - Number(!second.date);
            }
            return direction * first.date.localeCompare(second.date);
        });
        const fragment = document.createDocumentFragment();
        cards.forEach(({ element }) => fragment.append(element));
        list.append(fragment);
    }

    function showMatches() {
        let matches = 0;
        for (const card of cards) {
            const match = (category === 'all' || category === card.category)
                && (year === 'all' || year === card.year)
                && (card.title.includes(query) || card.notes.includes(query));
            if (match) matches += 1;
            card.element.hidden = !match || matches > limit;
        }
        list.hidden = matches === 0;
        empty.hidden = matches !== 0;
        showMore.hidden = matches <= limit;
    }

    function applyFilters() {
        clearTimeout(searchTimer);
        query = search.value.trim().toLowerCase();
        limit = pageSize;
        list.classList.toggle('document-list--filtered-category', category !== 'all');
        setPressed(categoryButtons, 'category', category);
        categorySelect.value = category;
        setPressed(yearButtons, 'year', year);
        showMatches();
    }

    categoryButtons.forEach(button => button.addEventListener('click', () => {
        category = button.dataset.category;
        applyFilters();
    }));

    categorySelect.addEventListener('change', () => {
        category = categorySelect.value;
        applyFilters();
    });

    yearButtons.forEach(button => button.addEventListener('click', () => {
        year = button.dataset.year;
        applyFilters();
    }));

    search.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(applyFilters, 300);
    });
    sort.addEventListener('change', () => {
        sortCards();
        showMatches();
    });
    viewButtons.forEach(button => button.addEventListener('click', () => {
        const view = button.dataset.documentsView;
        setView(view);
        try {
            localStorage.setItem(viewKey, view);
        } catch {
            // The current view is still usable when storage is disabled.
        }
    }));

    showMore.querySelector('button').addEventListener('click', () => {
        const previousLimit = limit;
        limit += pageSize;
        showMatches();
        if (showMore.hidden) {
            list.querySelectorAll('.document-card:not([hidden])')[previousLimit]
                ?.querySelector('.document-download').focus();
        }
    });

    page.querySelector('.documents-view-all').addEventListener('click', event => {
        event.preventDefault();
        category = year = 'all';
        search.value = '';
        applyFilters();
        list.focus();
    });

    try {
        setView(localStorage.getItem(viewKey) === 'line' ? 'line' : 'card');
    } catch {
        setView('card');
    }
    sortCards();
    applyFilters();
    page.querySelectorAll('[data-documents-controls]').forEach(element => {
        element.hidden = false;
    });
})();
