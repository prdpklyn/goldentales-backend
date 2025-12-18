#!/usr/bin/env python3
"""
Test Create Book and Create Order APIs
========================================
Comprehensive test script for book creation and order creation endpoints.

Note: This is a standalone script, not a pytest test.
Run directly: python test_create_book_and_order.py
"""

import requests
import json
import sys
from typing import Optional, Dict, Any

# Skip these functions when run by pytest
try:
    import pytest
    _skip_decorator = pytest.mark.skip(reason="Standalone script - run directly: python test_create_book_and_order.py")
except ImportError:
    _skip_decorator = lambda f: f  # No-op if pytest not available

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY: Optional[str] = None  # Set your API key here or via environment


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
    print(f"{Colors.CYAN}{text}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")


def print_test(description: str, endpoint: str, method: str = "POST"):
    """Print test information."""
    print(f"{Colors.BLUE}Testing:{Colors.NC} {description}")
    print(f"{Colors.YELLOW}Endpoint:{Colors.NC} {method} {endpoint}")


def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    description: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Make an API request and display the response.
    
    Returns:
        Response JSON if successful, None otherwise
    """
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            print(f"{Colors.RED}Unsupported method: {method}{Colors.NC}")
            return None
        
        # Print test info
        if description:
            print_test(description, endpoint, method)
        
        # Print status
        if 200 <= response.status_code < 300:
            print(f"{Colors.GREEN}✓ Success (HTTP {response.status_code}){Colors.NC}")
        else:
            print(f"{Colors.RED}✗ Failed (HTTP {response.status_code}){Colors.NC}")
            try:
                error_data = response.json()
                print(f"{Colors.RED}Error: {error_data.get('detail', 'Unknown error')}{Colors.NC}")
            except:
                print(f"{Colors.RED}Error: {response.text}{Colors.NC}")
            return None
        
        # Print response body
        try:
            body = response.json()
            print(f"\n{Colors.CYAN}Response:{Colors.NC}")
            print(json.dumps(body, indent=2))
            print(f"\n{Colors.CYAN}{'-'*70}{Colors.NC}\n")
            return body
        except ValueError:
            print(f"\n{Colors.CYAN}Response:{Colors.NC}")
            print(response.text)
            print(f"\n{Colors.CYAN}{'-'*70}{Colors.NC}\n")
            return None
        
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}✗ Connection Error: Is the server running at {BASE_URL}?{Colors.NC}\n")
        return None
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.NC}\n")
        return None


@_skip_decorator
def test_create_book():
    """Test creating a book."""
    print_header("Test 1: Create Book")
    
    # Example book creation request
    book_request = {
        "child_name": "Emma",
        "child_gender": "girl",
        "child_age": 6,
        "skin_tone": "light",
        "hair_color": "brown",
        "hair_style": "pigtails",
        "eye_color": "blue",
        "body_type": "average",
        "has_freckles": True,
        "favorite_color": "purple",
        "theme": "adventure",
        "art_style": "watercolor",
        "occasion": "birthday",
        "special_details": "Emma loves unicorns and fairy tales"
    }
    
    print(f"{Colors.YELLOW}Request Body:{Colors.NC}")
    print(json.dumps(book_request, indent=2))
    print()
    
    response = make_request(
        "POST",
        "/api/v1/books/create",
        data=book_request,
        description="Create a personalized storybook"
    )
    
    return response


@_skip_decorator
def test_get_book(book_id: str):
    """Test getting a book by ID."""
    print_header(f"Test 2: Get Book (ID: {book_id})")
    
    response = make_request(
        "GET",
        f"/api/v1/books/{book_id}",
        description=f"Retrieve book {book_id}"
    )
    
    return response


@_skip_decorator
def test_get_book_preview(book_id: str):
    """Test getting book preview images."""
    print_header(f"Test 3: Get Book Preview (ID: {book_id})")
    
    response = make_request(
        "GET",
        f"/api/v1/books/{book_id}/preview",
        description=f"Get preview images for book {book_id}"
    )
    
    return response


@_skip_decorator
def test_get_book_price(book_id: str):
    """Test getting book price."""
    print_header(f"Test 4: Get Book Price (ID: {book_id})")
    
    # Test different formats and shipping options
    test_cases = [
        {"format": "digital", "shipping": "digital", "gift_wrap": False},
        {"format": "softcover", "shipping": "standard", "gift_wrap": False},
        {"format": "hardcover", "shipping": "express", "gift_wrap": True},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{Colors.BLUE}Price Test {i}:{Colors.NC} {test_case['format']} + {test_case['shipping']} shipping")
        
        params = "&".join([f"{k}={v}" for k, v in test_case.items()])
        response = make_request(
            "GET",
            f"/api/v1/orders/books/{book_id}/price?{params}",
            description=f"Calculate price for {test_case['format']} book"
        )


@_skip_decorator
def test_create_order(book_id: str):
    """Test creating an order."""
    print_header(f"Test 5: Create Order (Book ID: {book_id})")
    
    # Example order request
    order_request = {
        "book_id": book_id,
        "format": "hardcover",
        "shipping_tier": "standard",
        "gift_wrap": True,
        "gift_message": "Happy Birthday! Love, Grandma",
        "recipient_email": "recipient@example.com",
        "recipient_address": {
            "name": "Emma Smith",
            "street": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94102",
            "country": "USA"
        }
    }
    
    print(f"{Colors.YELLOW}Request Body:{Colors.NC}")
    print(json.dumps(order_request, indent=2))
    print()
    
    response = make_request(
        "POST",
        "/api/v1/orders/create",
        data=order_request,
        description="Create an order for the book"
    )
    
    return response


@_skip_decorator
def test_get_order_status(order_id: str):
    """Test getting order status."""
    print_header(f"Test 6: Get Order Status (ID: {order_id})")
    
    response = make_request(
        "GET",
        f"/api/v1/orders/{order_id}/status",
        description=f"Get status for order {order_id}"
    )
    
    return response


@_skip_decorator
def test_shipping_options():
    """Test getting shipping options."""
    print_header("Test 7: Get Shipping Options")
    
    response = make_request(
        "GET",
        "/api/v1/orders/shipping-options",
        description="Get available shipping options"
    )
    
    return response


def main():
    """Run all tests."""
    import os
    
    # Allow override via environment variables
    global BASE_URL, API_KEY
    BASE_URL = os.getenv("BASE_URL", BASE_URL)
    API_KEY = os.getenv("API_KEY", API_KEY)
    
    print_header("GoldenTales API - Book & Order Creation Tests")
    print(f"Base URL: {BASE_URL}")
    if API_KEY:
        print(f"API Key: {API_KEY[:10]}...")
    else:
        print("API Key: Not set (using dev mode if enabled)")
    print()
    
    # Test 1: Create a book
    book_response = test_create_book()
    if not book_response:
        print(f"{Colors.RED}Failed to create book. Cannot continue with other tests.{Colors.NC}")
        return
    
    book_id = book_response.get("book_id")
    if not book_id:
        print(f"{Colors.RED}No book_id in response. Cannot continue.{Colors.NC}")
        return
    
    print(f"{Colors.GREEN}✓ Book created successfully! Book ID: {book_id}{Colors.NC}\n")
    
    # Test 2: Get the book
    test_get_book(book_id)
    
    # Test 3: Get book preview
    test_get_book_preview(book_id)
    
    # Test 4: Get book price
    test_get_book_price(book_id)
    
    # Test 5: Create an order
    order_response = test_create_order(book_id)
    if not order_response:
        print(f"{Colors.YELLOW}⚠ Order creation failed or not implemented yet.{Colors.NC}\n")
    else:
        order_id = order_response.get("order_id")
        if order_id:
            # Test 6: Get order status
            test_get_order_status(order_id)
    
    # Test 7: Get shipping options
    test_shipping_options()
    
    print_header("All Tests Complete!")
    print(f"\n{Colors.GREEN}Book ID created: {book_id}{Colors.NC}")
    if order_response and order_response.get("order_id"):
        print(f"{Colors.GREEN}Order ID created: {order_response.get('order_id')}{Colors.NC}")
    print("\nYou can now use these IDs to test other endpoints.")


if __name__ == "__main__":
    main()

