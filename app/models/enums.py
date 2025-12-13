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
    # Payment
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_FAILED = "payment_failed"

    # Production
    GENERATING_PRINT_FILES = "generating_print_files"
    UPSCALING_IMAGES = "upscaling_images"
    CREATING_PDF = "creating_pdf"
    PDF_READY = "pdf_ready"

    # Fulfillment
    UPLOADING_TO_PRINTER = "uploading_to_printer"
    SENT_TO_PRINTER = "sent_to_printer"
    PRINTING = "printing"
    QUALITY_CHECK = "quality_check"

    # Shipping
    READY_TO_SHIP = "ready_to_ship"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"

    # Digital delivery
    DIGITAL_READY = "digital_ready"
    DIGITAL_SENT = "digital_sent"

    # Issues
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ON_HOLD = "on_hold"
