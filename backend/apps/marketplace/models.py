"""
Marketplace models - Games, Markets, Offers.
Production-ready with security, validation, and audit trails.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from apps.accounts.models import User


class Game(models.Model):
    """
    Represents a game in the marketplace (e.g., Path of Exile, Diablo).
    Games contain multiple market types.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(max_length=250, unique=True, db_index=True)
    icon = models.ImageField(upload_to='games/icons/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        indexes = [
            models.Index(fields=['is_active', 'name']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MarketType(models.Model):
    """
    Market types: ITEMS, CURRENCY, ACCOUNTS, BOOSTING.
    Some market types require seller verification.
    """
    ITEMS = 'ITEMS'
    CURRENCY = 'CURRENCY'
    ACCOUNTS = 'ACCOUNTS'
    BOOSTING = 'BOOSTING'
    
    MARKET_TYPE_CHOICES = [
        (ITEMS, 'Items'),
        (CURRENCY, 'Game Currency'),
        (ACCOUNTS, 'Accounts'),
        (BOOSTING, 'Boosting'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50, 
        choices=MARKET_TYPE_CHOICES, 
        unique=True,
        db_index=True
    )
    display_name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)  # Icon class or emoji
    requires_verification = models.BooleanField(
        default=False,
        help_text="Whether seller must be verified to list in this market"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Market Type'
        verbose_name_plural = 'Market Types'
    
    def __str__(self):
        return self.display_name


class GameMarket(models.Model):
    """
    Connects a game to a market type.
    E.g., "Path of Exile" + "Currency" = "POE Currency Market"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(
        Game, 
        on_delete=models.CASCADE, 
        related_name='markets'
    )
    market_type = models.ForeignKey(
        MarketType, 
        on_delete=models.CASCADE,
        related_name='game_markets'
    )
    offer_count = models.IntegerField(
        default=0,
        help_text="Cached count of active offers"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['game__name', 'market_type__name']
        verbose_name = 'Game Market'
        verbose_name_plural = 'Game Markets'
        unique_together = [['game', 'market_type']]
        indexes = [
            models.Index(fields=['game', 'is_active']),
            models.Index(fields=['market_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.game.name} - {self.market_type.display_name}"


class Server(models.Model):
    """
    Game servers/regions (e.g., EU, NA, Asia).
    Used for offers that are server-specific.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(
        Game, 
        on_delete=models.CASCADE, 
        related_name='servers'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['game__name', 'name']
        verbose_name = 'Server'
        verbose_name_plural = 'Servers'
        unique_together = [['game', 'slug']]
        indexes = [
            models.Index(fields=['game', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.game.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ItemType(models.Model):
    """
    Specific items within a game market.
    E.g., "Divine Orb", "Chaos Orb" for POE Currency.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game_market = models.ForeignKey(
        GameMarket,
        on_delete=models.CASCADE,
        related_name='item_types'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['game_market', 'name']
        verbose_name = 'Item Type'
        verbose_name_plural = 'Item Types'
        unique_together = [['game_market', 'name']]
        indexes = [
            models.Index(fields=['game_market', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.game_market} - {self.name}"


class Offer(models.Model):
    """
    Seller listing/offer.
    Core marketplace entity.
    """
    # Delivery methods
    FACE_TO_FACE = 'FACE_TO_FACE'
    MAIL = 'MAIL'
    
    DELIVERY_METHOD_CHOICES = [
        (FACE_TO_FACE, 'Face to Face'),
        (MAIL, 'In-Game Mail'),
    ]
    
    # Offer status
    ACTIVE = 'ACTIVE'
    PAUSED = 'PAUSED'
    SOLD_OUT = 'SOLD_OUT'
    DELETED = 'DELETED'
    
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (PAUSED, 'Paused'),
        (SOLD_OUT, 'Sold Out'),
        (DELETED, 'Deleted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relations
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='offers'
    )
    game_market = models.ForeignKey(
        GameMarket,
        on_delete=models.CASCADE,
        related_name='offers'
    )
    server = models.ForeignKey(
        Server,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offers',
        help_text="Optional: some offers are not server-specific"
    )
    item_type = models.ForeignKey(
        ItemType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offers',
        help_text="Optional: some markets don't have specific items"
    )
    
    # Offer details
    title = models.CharField(
        max_length=128,
        help_text="Offer title/headline"
    )
    description = models.TextField(
        max_length=5000,
        help_text="Detailed offer description"
    )
    
    # Pricing
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Price per unit in EGP"
    )
    available_stock = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Available quantity"
    )
    min_purchase = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Minimum purchase quantity"
    )
    
    # Delivery
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES
    )
    delivery_speed = models.CharField(
        max_length=100,
        help_text="E.g., '1-30 minutes', '1-2 hours'"
    )
    
    # Custom fields (game-specific)
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Game-specific fields as JSON"
    )
    
    # Status & stats
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ACTIVE,
        db_index=True
    )
    views_count = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Offer'
        verbose_name_plural = 'Offers'
        indexes = [
            models.Index(fields=['game_market', 'status', '-created_at']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['server', 'status']),
            models.Index(fields=['item_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.seller.email}"
    
    def is_in_stock(self):
        """Check if offer has stock available."""
        return self.available_stock > 0
    
    def can_purchase(self, quantity):
        """Check if purchase quantity is valid."""
        return (
            self.status == self.ACTIVE and
            quantity >= self.min_purchase and
            quantity <= self.available_stock
        )
    
    def calculate_total_price(self, quantity):
        """Calculate total price for quantity."""
        return self.price_per_unit * quantity
