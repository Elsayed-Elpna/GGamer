"""
Game and market management service.
"""
from typing import List, Optional
from django.db.models import Count, Q
from apps.marketplace.models import Game, GameMarket, MarketType, Server


class GameService:
    """Service for game and market operations."""
    
    @staticmethod
    def get_active_games() -> List[Game]:
        """Get all active games with market counts."""
        return Game.objects.filter(
            is_active=True
        ).prefetch_related(
            'markets__market_type'
        ).annotate(
            market_count=Count('markets', filter=Q(markets__is_active=True))
        ).order_by('name')
    
    @staticmethod
    def get_game_by_slug(slug: str) -> Optional[Game]:
        """Get game by slug."""
        try:
            return Game.objects.get(slug=slug, is_active=True)
        except Game.DoesNotExist:
            return None
    
    @staticmethod
    def get_game_markets(game: Game) -> List[GameMarket]:
        """Get all active markets for a game."""
        return GameMarket.objects.filter(
            game=game,
            is_active=True
        ).select_related('market_type').order_by('market_type__name')
    
    @staticmethod
    def get_game_servers(game: Game) -> List[Server]:
        """Get all active servers for a game."""
        return Server.objects.filter(
            game=game,
            is_active=True
        ).order_by('name')
