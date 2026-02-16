"""
Offer validation and management service.
Handles offer creation, updates, and seller verification checks.
"""
from typing import Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from apps.marketplace.models import Offer, GameMarket, Server, ItemType
from apps.verification.models import SellerVerification
from apps.accounts.models import User


class OfferService:
    """
    Service for managing marketplace offers.
    Security-first with verification checks.
    """
    
    @staticmethod
    def can_create_offer(user: User, game_market: GameMarket) -> tuple[bool, Optional[str]]:
        """
        Check if user can create offer in this market.
        
        Returns:
            (can_create: bool, reason: str or None)
        """
        # Check if market type requires verification
        if game_market.market_type.requires_verification:
            try:
                verification = SellerVerification.objects.get(user=user)
                if verification.status != SellerVerification.APPROVED:
                    return False, "Seller verification required for this market type"
            except SellerVerification.DoesNotExist:
                return False, "Seller verification required for this market type"
        
        return True, None
    
    @staticmethod
    @transaction.atomic
    def create_offer(
        seller: User,
        game_market_id: str,
        title: str,
        description: str,
        price_per_unit: Decimal,
        available_stock: int,
        delivery_method: str,
        delivery_speed: str,
        min_purchase: int = 1,
        server_id: Optional[str] = None,
        item_type_id: Optional[str] = None,
        custom_fields: Optional[dict] = None
    ) -> Offer:
        """
        Create a new offer with validation.
        
        Security:
        - Verifies seller permissions
        - Validates all inputs
        - Prevents restricted market access
        """
        # Get game market
        try:
            game_market = GameMarket.objects.select_related(
                'game', 'market_type'
            ).get(id=game_market_id, is_active=True)
        except GameMarket.DoesNotExist:
            raise ValidationError("Invalid game market")
        
        # Check seller permissions
        can_create, reason = OfferService.can_create_offer(seller, game_market)
        if not can_create:
            raise PermissionDenied(reason)
        
        # Validate server (if provided)
        server = None
        if server_id:
            try:
                server = Server.objects.get(
                    id=server_id,
                    game=game_market.game,
                    is_active=True
                )
            except Server.DoesNotExist:
                raise ValidationError("Invalid server for this game")
        
        # Validate item type (if provided)
        item_type = None
        if item_type_id:
            try:
                item_type = ItemType.objects.get(
                    id=item_type_id,
                    game_market=game_market,
                    is_active=True
                )
            except ItemType.DoesNotExist:
                raise ValidationError("Invalid item type for this market")
        
        # Create offer
        offer = Offer.objects.create(
            seller=seller,
            game_market=game_market,
            server=server,
            item_type=item_type,
            title=title[:128],  # Enforce max length
            description=description[:5000],  # Enforce max length
            price_per_unit=price_per_unit,
            available_stock=available_stock,
            min_purchase=min_purchase,
            delivery_method=delivery_method,
            delivery_speed=delivery_speed,
            custom_fields=custom_fields or{},
            status=Offer.ACTIVE
        )
        
        # Update market offer count (cached)
        GameMarket.objects.filter(id=game_market.id).update(
            offer_count=models.F('offer_count') + 1
        )
        
        return offer
    
    @staticmethod
    @transaction.atomic
    def update_offer(
        offer: Offer,
        user: User,
        **update_fields
    ) -> Offer:
        """
        Update an existing offer.
        
        Security:
        - Ownership validation
        - Field validation
        """
        # Verify ownership
        if offer.seller != user:
            raise PermissionDenied("You can only update your own offers")
        
        # Update allowed fields
        allowed_fields = [
            'title', 'description', 'price_per_unit', 'available_stock',
            'min_purchase', 'delivery_speed', 'status', 'custom_fields'
        ]
        
        for field, value in update_fields.items():
            if field in allowed_fields:
                if field == 'title':
                    value = value[:128]
                elif field == 'description':
                    value = value[:5000]
                setattr(offer, field, value)
        
        offer.save()
        return offer
    
    @staticmethod
    @transaction.atomic
    def delete_offer(offer: Offer, user: User) -> None:
        """
        Soft delete an offer.
        
        Security:
        - Ownership validation
        """
        # Verify ownership  
        if offer.seller != user:
            raise PermissionDenied("You can only delete your own offers")
        
        # Soft delete
        offer.status = Offer.DELETED
        offer.save()
        
        # Update market offer count
        if offer.game_market:
            GameMarket.objects.filter(id=offer.game_market.id).update(
                offer_count=models.F('offer_count') - 1
            )
    
    @staticmethod
    def decrement_stock(offer: Offer, quantity: int) -> None:
        """
        Decrement offer stock after purchase.
        Uses F() expression to prevent race conditions.
        """
        with transaction.atomic():
            updated = Offer.objects.filter(
                id=offer.id,
                available_stock__gte=quantity
            ).update(
                available_stock=models.F('available_stock') - quantity,
                sales_count=models.F('sales_count') + 1
            )
            
            if not updated:
                raise ValidationError("Insufficient stock available")
            
            # Refresh from database
            offer.refresh_from_db()
            
            # Mark as sold out if stock is 0
            if offer.available_stock == 0:
                offer.status = Offer.SOLD_OUT
                offer.save()
    
    @staticmethod
    def increment_views(offer: Offer) -> None:
        """Increment view count."""
        Offer.objects.filter(id=offer.id).update(
            views_count=models.F('views_count') + 1
        )


# Import models at the end to avoid circular imports
from django.db.models import F as models_F
models.F = models_F
