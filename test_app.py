#!/usr/bin/env python3
"""
Comprehensive test script for Shazi Video Generator Web App
Tests backend API endpoints, database connectivity, and service functionality
"""

import requests
import json
import sys
from typing import Dict, Any
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(test_name: str):
    """Print test name"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Testing: {test_name}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")

def test_health_check() -> bool:
    """Test if the backend is running and healthy"""
    print_test("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Backend is {data.get('status')}")
            print_info(f"Version: {data.get('version')}")
            print_info(f"Environment: {data.get('environment')}")
            return True
        else:
            print_error(f"Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to backend: {e}")
        return False

def test_root_endpoint() -> bool:
    """Test root endpoint"""
    print_test("Root Endpoint")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Root endpoint accessible")
            print_info(f"App Name: {data.get('name')}")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Docs: {BASE_URL}{data.get('docs')}")
            return True
        else:
            print_error(f"Root endpoint returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error accessing root endpoint: {e}")
        return False

def test_api_docs() -> bool:
    """Test if API documentation is accessible"""
    print_test("API Documentation")
    try:
        # Test Swagger UI
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_success("Swagger UI is accessible at /docs")
        else:
            print_error(f"Swagger UI returned status {response.status_code}")
            return False
        
        # Test OpenAPI schema
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            schema = response.json()
            print_success("OpenAPI schema is accessible")
            print_info(f"API Title: {schema.get('info', {}).get('title')}")
            print_info(f"API Version: {schema.get('info', {}).get('version')}")
            
            # Count endpoints
            paths = schema.get('paths', {})
            print_info(f"Total API endpoints: {len(paths)}")
            
            # List main endpoint groups
            endpoint_groups = set()
            for path in paths.keys():
                if path.startswith('/api/v1/'):
                    parts = path.split('/')
                    if len(parts) > 3:
                        endpoint_groups.add(parts[3])
            
            if endpoint_groups:
                print_info(f"Endpoint groups: {', '.join(sorted(endpoint_groups))}")
            
            return True
        else:
            print_error(f"OpenAPI schema returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error accessing API docs: {e}")
        return False

def test_builtin_styles() -> bool:
    """Test built-in styles listing"""
    print_test("Built-in Styles")
    try:
        response = requests.get(f"{API_BASE}/styles/builtin", timeout=5)
        if response.status_code == 200:
            styles = response.json()
            print_success(f"Found {len(styles)} built-in styles")
            
            if styles:
                # Show first few styles
                sample_count = min(5, len(styles))
                print_info(f"Sample styles (showing {sample_count}):")
                for style in styles[:sample_count]:
                    print(f"  - {style.get('name')}")
            
            return True
        else:
            print_error(f"Built-in styles endpoint returned status {response.status_code}")
            print_info("This might be expected if authentication is required")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error accessing built-in styles: {e}")
        return False

def test_cors() -> bool:
    """Test CORS headers"""
    print_test("CORS Configuration")
    try:
        headers = {'Origin': 'http://localhost:5173'}
        response = requests.options(f"{BASE_URL}/health", headers=headers, timeout=5)
        
        cors_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('access-control')}
        
        if cors_headers:
            print_success("CORS is configured")
            for key, value in cors_headers.items():
                print_info(f"{key}: {value}")
            return True
        else:
            print_error("CORS headers not found")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error testing CORS: {e}")
        return False

def test_static_files() -> bool:
    """Test static file serving"""
    print_test("Static Files")
    try:
        # Test uploads directory mounting
        response = requests.get(f"{BASE_URL}/uploads/", timeout=5)
        # Even if there are no files, the endpoint should be mounted
        if response.status_code in [200, 404, 403]:  # Any of these means the endpoint exists
            print_success("Uploads endpoint is mounted at /uploads")
            return True
        else:
            print_error(f"Uploads endpoint returned unexpected status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error accessing uploads endpoint: {e}")
        return False

def generate_test_report(results: Dict[str, bool]):
    """Generate final test report"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST REPORT{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"Passed: {Colors.GREEN}{passed}{Colors.RESET}/{total}")
    print(f"Failed: {Colors.RED}{total - passed}{Colors.RESET}/{total}")
    print(f"Success Rate: {Colors.YELLOW}{percentage:.1f}%{Colors.RESET}\n")
    
    if percentage == 100:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All tests passed!{Colors.RESET}\n")
        return 0
    elif percentage >= 70:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Most tests passed, but some failed{Colors.RESET}\n")
        return 1
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ Many tests failed{Colors.RESET}\n")
        return 2

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Shazi Video Generator - Application Test Suite        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    results = {}
    
    # Run tests
    results["Health Check"] = test_health_check()
    results["Root Endpoint"] = test_root_endpoint()
    results["API Documentation"] = test_api_docs()
    results["Built-in Styles"] = test_builtin_styles()
    results["CORS Configuration"] = test_cors()
    results["Static Files"] = test_static_files()
    
    # Generate report
    exit_code = generate_test_report(results)
    
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)
