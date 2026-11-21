document.querySelectorAll('[data-landing-carousel]').forEach(carousel => {
    const track = carousel.querySelector('[data-carousel-track]');
    const previous = carousel.querySelector('[data-carousel-prev]');
    const next = carousel.querySelector('[data-carousel-next]');
    const dots = carousel.querySelector('[data-carousel-dots]');
    const items = [...track.children];
    let columns = 1;
    let current = 0;

    function pageOffsets() {
        const first = items[0].offsetLeft;
        const max = track.scrollWidth - track.clientWidth;
        return items.filter((_, index) => index % columns === 0)
            .map(item => Math.min(item.offsetLeft - first, max));
    }

    function updateState() {
        const offsets = pageOffsets();
        current = offsets.reduce((nearest, offset, index) =>
            Math.abs(offset - track.scrollLeft) < Math.abs(offsets[nearest] - track.scrollLeft) ? index : nearest, 0);
        previous.disabled = track.scrollLeft <= 1;
        next.disabled = track.scrollLeft >= offsets[offsets.length - 1] - 1;
        [...dots.children].forEach((dot, index) => {
            dot.classList.toggle('is-active', index === current);
            dot.setAttribute('aria-current', String(index === current));
        });
    }

    function showPage(page) {
        const offset = pageOffsets()[page];
        if (offset !== undefined) track.scrollTo({left: offset});
    }

    previous.addEventListener('click', () => showPage(current - 1));
    next.addEventListener('click', () => showPage(current + 1));
    track.addEventListener('scroll', updateState, {passive: true});

    function resize() {
        columns = Number(getComputedStyle(carousel).getPropertyValue('--carousel-columns'));
        const pages = Math.ceil(items.length / columns);
        carousel.toggleAttribute('data-carousel-ready', pages > 1);
        if (dots.childElementCount !== pages) {
            const buttons = Array.from({length: pages}, (_, index) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'landing-carousel-dot';
                button.setAttribute('aria-label', `${carousel.dataset.slideLabel} ${index + 1}`);
                button.addEventListener('click', () => showPage(index));
                return button;
            });
            dots.replaceChildren(...buttons);
        }
        updateState();
    }

    new ResizeObserver(resize).observe(track);
    resize();
});
