"""
Simple script to test the Login API
Run this script to verify the API is working correctly
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Change this to your server URL
LOGIN_ENDPOINT = f"{BASE_URL}/accounts/api/login/"
PROFILE_ENDPOINT = f"{BASE_URL}/accounts/api/user-profile/"
LOGOUT_ENDPOINT = f"{BASE_URL}/accounts/api/logout/"

def test_login(username, password):
    """Test the login API"""
    print("\n" + "="*50)
    print("Testing Login API")
    print("="*50)
    
    data = {
        "username": username,
        "password": password
    }
    
    print(f"\nRequest URL: {LOGIN_ENDPOINT}")
    print(f"Request Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(LOGIN_ENDPOINT, json=data)
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✓ Login Successful!")
            return response.cookies
        else:
            print("\n✗ Login Failed!")
            return None
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return None

def test_get_profile(cookies):
    """Test the get profile API"""
    print("\n" + "="*50)
    print("Testing Get Profile API")
    print("="*50)
    
    print(f"\nRequest URL: {PROFILE_ENDPOINT}")
    
    try:
        response = requests.get(PROFILE_ENDPOINT, cookies=cookies)
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✓ Profile Retrieved Successfully!")
        else:
            print("\n✗ Failed to Retrieve Profile!")
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")

def test_logout(cookies):
    """Test the logout API"""
    print("\n" + "="*50)
    print("Testing Logout API")
    print("="*50)
    
    print(f"\nRequest URL: {LOGOUT_ENDPOINT}")
    
    try:
        response = requests.post(LOGOUT_ENDPOINT, cookies=cookies)
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✓ Logout Successful!")
        else:
            print("\n✗ Logout Failed!")
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")

def main():
    """Main test function"""
    print("\n" + "="*50)
    print("School Management System - Login API Test")
    print("="*50)
    
    # Get credentials from user
    print("\nEnter test credentials:")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    if not username or not password:
        print("\n✗ Username and password are required!")
        return
    
    # Test login
    cookies = test_login(username, password)
    
    if cookies:
        # Test get profile
        test_get_profile(cookies)
        
        # Test logout
        test_logout(cookies)
    
    print("\n" + "="*50)
    print("Test Complete")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
