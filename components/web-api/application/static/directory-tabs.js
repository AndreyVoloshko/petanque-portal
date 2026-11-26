(() => {
    const select = document.querySelector('.title-registry-select');
    const Tab = window.bootstrap?.Tab;
    if (!select || !Tab) return;

    const tabList = select.nextElementSibling;
    select.value = tabList.querySelector('[aria-selected="true"]').id;
    select.addEventListener('change', () => {
        const tab = document.getElementById(select.value);
        Tab.getOrCreateInstance(tab).show();
    });
    tabList.addEventListener('shown.bs.tab', event => {
        select.value = event.target.id;
    });
    select.hidden = false;
})();
