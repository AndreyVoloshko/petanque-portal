PLAYER_CHANGE_MESSAGE_CHANGED_KEY = 'changed'
PLAYER_CHANGE_MESSAGE_FIELDS_KEY = 'fields'
AUDIT_CHANGE_MESSAGE_VALUES_KEY = 'values'
AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY = 'old'
AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY = 'new'
AUDIT_CHANGE_MESSAGE_REVERTED_KEY = 'reverted'
AUDIT_CHANGE_MESSAGE_SOURCE_LOG_ENTRY_ID_KEY = 'source_log_entry_id'

PLAYER_CHANGE_FIELD_AVATAR = 'avatar'
PLAYER_CHANGE_FIELD_CURRENT_CLUB = 'current_club'
PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE = 'insurance_expiration_date'
PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE = 'is_licence_active'
PLAYER_CHANGE_FIELD_LICENCE_NUMBER = 'licence_number'
PLAYER_CHANGE_FIELD_PASSWORD = 'password'
PLAYER_CHANGE_FIELD_SPORT_TITLE = 'sport_title'

PLAYER_CHANGE_FILTER_CLUB = 'club'
TOURNAMENT_CHANGE_FIELD_TEAM_PLACES = 'team_places'
SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME = 'system.tournament.results'
SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME = 'system.petanque.draw'

PLAYER_CHANGE_IGNORED_FIELDS = frozenset((
    'current_rating',
    'current_rating_b',
    'current_rating_inclusive',
    'current_rating_liga',
    'current_rating_tournaments',
    'current_rating_b_tournaments',
    'current_rating_inclusive_tournaments',
    'current_power',
    'current_power_b',
    'current_power_inclusive',
))

AUDIT_NON_REVERTABLE_FIELDS = frozenset((
    PLAYER_CHANGE_FIELD_PASSWORD,
    'user',
))

PLAYER_CHANGE_FIELDS = (
    'user',
    PLAYER_CHANGE_FIELD_CURRENT_CLUB,
    PLAYER_CHANGE_FIELD_AVATAR,
    'name',
    'surname',
    'second_name',
    'birth_date',
    'email',
    PLAYER_CHANGE_FIELD_PASSWORD,
    'country',
    'gender',
    PLAYER_CHANGE_FIELD_LICENCE_NUMBER,
    PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE,
    'is_inclusive',
    'prefred_position',
    'facebook',
    'twitter',
    'instagram',
    'website',
    'arbiter_level',
    'coach_level',
    PLAYER_CHANGE_FIELD_SPORT_TITLE,
    PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE,
)

PLAYER_CHANGE_FILTER_ALIASES = {
    PLAYER_CHANGE_FIELD_CURRENT_CLUB: PLAYER_CHANGE_FILTER_CLUB,
}
