from django_countries import countries


EU_COUNTRIES = [
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
    'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
    'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE',
]

EXCLUDED_COUNTRIES = ['RU', 'BY', 'IR']


def get_ordered_country_choices():
    all_countries = [
        (code, str(name)) for code, name in countries
        if code not in EXCLUDED_COUNTRIES
    ]

    ukraine = [('UA', 'Україна')]
    eu = sorted(
        [(code, name) for code, name in all_countries if code in EU_COUNTRIES],
        key=lambda item: item[1],
    )
    rest = sorted(
        [(code, name) for code, name in all_countries if code not in EU_COUNTRIES and code != 'UA'],
        key=lambda item: item[1],
    )

    return [
        ('', 'Оберіть країну'),
        ('Україна', ukraine),
        ('Країни ЄС', eu),
        ('Інші країни', rest),
    ]
