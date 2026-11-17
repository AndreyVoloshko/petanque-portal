from urllib.parse import urlencode


def pagination_links(page_obj, path, active_filters):
    def page_url(number):
        params = dict(active_filters)
        if number != 1:
            params['page'] = number
        query = urlencode(params)
        return f'{path}?{query}' if query else path

    last = page_obj.paginator.num_pages
    first_neighbor = max(1, page_obj.number - 1)
    last_neighbor = min(last, page_obj.number + 1)
    numbers = sorted({1, last, *range(first_neighbor, last_neighbor + 1)})
    pages = []
    for number in numbers:
        if pages and number > pages[-1] + 1:
            pages.append('ellipsis')
        pages.append(number)

    return {
        'pagination_pages': pages,
        'pagination_urls': {
            'first': page_url(1),
            'previous': page_url(page_obj.previous_page_number()) if page_obj.has_previous() else '',
            'next': page_url(page_obj.next_page_number()) if page_obj.has_next() else '',
            'last': page_url(last),
            'pages': {number: page_url(number) for number in numbers},
        },
    }
