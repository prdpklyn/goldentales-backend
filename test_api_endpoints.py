#!/usr/bin/env python3
"""
GoldenTales API Endpoint Testing Script
========================================
Interactive script to test API endpoints with proper formatting.
"""

import requests
import json
import sys
from typing import Optional, Dict, Any

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
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.CYAN}{text}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")


def print_test(description: str, endpoint: str, method: str = "GET"):
    """Print test information."""
    print(f"{Colors.BLUE}Testing:{Colors.NC} {description}")
    print(f"{Colors.YELLOW}Endpoint:{Colors.NC} {method} {endpoint}")


def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    description: str = ""
) -> None:
    """
    Make an API request and display the response.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        data: Optional request body data
        description: Test description
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
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            print(f"{Colors.RED}Unsupported method: {method}{Colors.NC}")
            return
        
        # Print test info
        if description:
            print_test(description, endpoint, method)
        
        # Print status
        if 200 <= response.status_code < 300:
            print(f"{Colors.GREEN}✓ Success (HTTP {response.status_code}){Colors.NC}")
        else:
            print(f"{Colors.YELLOW}✗ Failed (HTTP {response.status_code}){Colors.NC}")
        
        # Print headers (if deprecation-related)
        deprecation_headers = {
            "Deprecation": response.headers.get("Deprecation"),
            "Sunset": response.headers.get("Sunset"),
            "X-API-Warning": response.headers.get("X-API-Warning"),
            "X-API-Version": response.headers.get("X-API-Version"),
            "X-API-Status": response.headers.get("X-API-Status"),
        }
        
        if any(deprecation_headers.values()):
            print(f"\n{Colors.YELLOW}Deprecation Headers:{Colors.NC}")
            for key, value in deprecation_headers.items():
                if value:
                    print(f"  {key}: {value}")
        
        # Print response body
        try:
            body = response.json()
            print(f"\n{Colors.CYAN}Response:{Colors.NC}")
            print(json.dumps(body, indent=2))
        except ValueError:
            print(f"\n{Colors.CYAN}Response:{Colors.NC}")
            print(response.text)
        
        print(f"\n{Colors.CYAN}{'-'*60}{Colors.NC}\n")
        
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}✗ Connection Error: Is the server running at {BASE_URL}?{Colors.NC}\n")
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.NC}\n")


def main():
    """Run API endpoint tests."""
    print_header("GoldenTales API Endpoint Tester")
    print(f"Base URL: {BASE_URL}")
    if API_KEY:
        print(f"API Key: {API_KEY[:10]}...")
    else:
        print("API Key: Not set (using dev mode if enabled)")
    print()
    
    # Test 1: Root endpoint
    make_request("GET", "/", description="Root health check")
    
    # Test 2: Health check (version-agnostic)
    make_request("GET", "/api/health", description="Health check endpoint")
    
    # Test 3: Health check (v1)
    make_request("GET", "/api/v1/health", description="V1 health check endpoint")
    
    # Test 4: Config endpoint (legacy - should show deprecation)
    make_request("GET", "/api/config", description="Legacy config endpoint (deprecated)")
    
    # Test 5: Config endpoint (v1 - should show current)
    make_request("GET", "/api/v1/config", description="V1 config endpoint (current)")
    
    # Test 6: OpenAPI docs
    make_request("GET", "/docs", description="OpenAPI documentation")
    
    print_header("Testing Complete!")
    print("\nTo test with a specific API key:")
    print("  export API_KEY=your-api-key")
    print("  python test_api_endpoints.py")
    print("\nTo test against a different server:")
    print("  export BASE_URL=https://api.goldentales.app")
    print("  python test_api_endpoints.py")


if __name__ == "__main__":
    # Allow override via environment variables
    import os
    BASE_URL = os.getenv("BASE_URL", BASE_URL)
    API_KEY = os.getenv("API_KEY", API_KEY)
    
    main()

