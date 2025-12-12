# tests/test_config.py
"""
Tests for configuration and health endpoints.
"""

import pytest


def test_root_endpoint(client):
    """Test the root endpoint returns healthy status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "timestamp" in data


def test_config_endpoint(client):
    """Test the configuration endpoint returns expected data."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "themes" in data
    assert "art_styles" in data
    assert "prices" in data
    assert "character_options" in data
    
    # Check themes
    assert "christmas" in data["themes"]
    assert "space" in data["themes"]
    
    # Check art styles
    assert "watercolor" in data["art_styles"]
    
    # Check character options
    assert "genders" in data["character_options"]
    assert "skin_tones" in data["character_options"]
    assert "hair_colors" in data["character_options"]


def test_shipping_options_endpoint(client):
    """Test the shipping options endpoint."""
    response = client.get("/api/shipping-options")
    assert response.status_code == 200
    data = response.json()
    
    assert "options" in data
    assert "countdown" in data
    assert len(data["options"]) >= 1  # At least digital option
