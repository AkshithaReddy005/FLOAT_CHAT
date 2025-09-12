#!/usr/bin/env python3
"""
Test script to verify Gemini API integration
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_connection():
    """Test Gemini API connection and configuration"""
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("=== Gemini Configuration Test ===")
    
    if not api_key:
        print("X GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key in the .env file")
        return False
        
    if api_key == "your_gemini_api_key_here":
        print("X GEMINI_API_KEY still contains placeholder value")
        print("Please update the .env file with your actual Gemini API key")
        return False
    
    try:
        import google.generativeai as genai
        print("+ Google Generative AI library imported successfully")
        
        # Configure the API
        genai.configure(api_key=api_key)
        print("+ API key configured successfully")
        
        # Create a model instance
        model = genai.GenerativeModel('gemini-2.0-flash')
        print("+ Gemini 2.0 Flash model initialized")
        
        # Test a simple generation
        print("\n=== Testing API Call ===")
        response = model.generate_content("Hello! Please respond with 'Gemini connection successful'")
        
        if response and response.text:
            print("+ API call successful!")
            print(f"Response: {response.text}")
            return True
        else:
            print("X API call returned empty response")
            return False
            
    except ImportError as e:
        print(f"X Import error: {e}")
        print("Please run: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"X Error testing Gemini connection: {e}")
        print("Troubleshooting steps:")
        print("1. Verify your Gemini API key is correct")
        print("2. Check that you have credits/quota in your Google Cloud account")
        print("3. Ensure the Gemini API is enabled in your Google Cloud project")
        return False

if __name__ == "__main__":
    success = test_gemini_connection()
    
    if success:
        print("\n+ Gemini configuration is working correctly!")
        sys.exit(0)
    else:
        print("\nX Gemini configuration needs to be fixed")
        sys.exit(1)