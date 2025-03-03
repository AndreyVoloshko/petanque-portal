from django.core.management.base import BaseCommand
from django.utils.timezone import now
from federation.models.player import Player

class Command(BaseCommand):
  help = "Recalculate ratings for all licensed players. This command is intended to be run periodically."

  def handle(self, *args, **kwargs):
    self.stdout.write(f"Recalculating started: {now()}")
    
    players = Player.get_actual_players_list()
    for player in players:
      self.stdout.write(f"Recalculating player: {player}")
      try:
        player.recalculate_ratings()
        self.stdout.write(f"Player recalculated: {player}")
      except Exception as e:
        self.stdout.write(f"Error during player recalculation: {player}, {e}")
    
    self.stdout.write(self.style.SUCCESS(f"Recalculating finished: {now()}"))
