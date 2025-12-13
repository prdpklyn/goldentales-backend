# app/models/enums.py
"""
GoldenTales Enums
=================
All enums used across the application.
"""

from enum import Enum


class ArtStyle(str, Enum):
    """Available illustration art styles."""
    WATERCOLOR = "watercolor"
    CARTOON = "cartoon"
    ANIME = "anime"
    STORYBOOK = "storybook"
    PIXAR = "pixar"
    GHIBLI = "ghibli"


class Theme(str, Enum):
    """Available story themes."""
    CHRISTMAS = "christmas"
    SPACE = "space"
    OCEAN = "ocean"
    FOREST = "forest"
    DINOSAUR = "dinosaur"
    SUPERHERO = "superhero"
    BIRTHDAY = "birthday"
    BEDTIME = "bedtime"


class ShippingTier(str, Enum):
    """Shipping options."""
    DIGITAL = "digital"
    STANDARD = "standard"
    EXPRESS = "express"


class BookFormat(str, Enum):
    """Book format options."""
    DIGITAL = "digital"
    SOFTCOVER = "softcover"
    HARDCOVER = "hardcover"


class GenerationQuality(str, Enum):
    """Image generation quality tiers."""
    PREVIEW = "preview"      # Fast, cheap - for initial preview
    STANDARD = "standard"    # Balanced - for user approval
    PRINT = "print"          # High quality - for final print


class OrderStatus(str, Enum):
    """Order processing stages."""
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    GENERATING_PRINT_FILES = "generating_print_files"
    CREATING_PDF = "creating_pdf"
    UPLOADING_TO_PRINTER = "uploading_to_printer"
    SENT_TO_PRINTER = "sent_to_printer"
    PRINTING = "printing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    FAILED = "failed"
