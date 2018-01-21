# Rating Settings
RATING_TOURNAMENT_POINTS_TABLE = [{
  'max_teams':8,
  'points': 3,
},{
  'max_teams':16,
  'points': 4,
},{
  'max_teams':32,
  'points': 5,
},{
  'max_teams':64,
  'points': 6,
},{
  'max_teams':128,
  'points': 7,
},{
  'max_teams':256,
  'points': 8,
},{
  'max_teams':99999999,
  'points': 9,
}]

# Tournament power = sum(top N team powers) / N
RATING_TOURNAMENT_POWER_TEAMS_COUNT = 16
RATING_TOURNAMENT_MINIMUM_POWER = 1

# Player power = sum(top N tournament points during last M month)
# Team power = sum(player powers) / players count
RATING_PLAYER_POWER_TOURNAMENTS_COUNT = 10
RATING_PLAYER_POWER_PAST_MONTHES = 12
