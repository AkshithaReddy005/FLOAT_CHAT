#!/usr/bin/env python3
"""
Test script to verify OpenRouter API configuration
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def test_openrouter_connection():
    """Test OpenRouter API connection and configuration"""
    
    # Get configuration from environment
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENAI_MODEL", "openai/gpt-4o")
    site_url = os.getenv("OPENROUTER_SITE_URL", "")
    site_name = os.getenv("OPENROUTER_SITE_NAME", "FloatChat")
    
    print("=== OpenRouter Configuration Test ===")
    print(f"API Key: {'✓ Set' if api_key else '✗ Missing'}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"Site URL: {site_url}")
    print(f"Site Name: {site_name}")
    print()
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenRouter API key in the .env file")
        return False
    
    # Prepare headers
    extra_headers = {}
    if site_url:
        extra_headers["HTTP-Referer"] = site_url
    if site_name:
        extra_headers["X-Title"] = site_name
    
    try:
        print("Creating OpenAI client...")
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=extra_headers if extra_headers else None
        )
        print("✓ Client created successfully")
        
        print("\nTesting API connection...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello! Please respond with 'OpenRouter connection successful'"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        print(f"✓ API Response: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Check if it's an authentication error
        if "401" in str(e) or "invalid_api_key" in str(e):
            print("\n🔍 Troubleshooting:")
            print("1. Verify your OpenRouter API key is correct")
            print("2. Check that OPENAI_BASE_URL=https://openrouter.ai/api/v1")
            print("3. Ensure your API key starts with 'sk-or-v1-'")
            print("4. Verify you have credits in your OpenRouter account")
        
        return False

if __name__ == "__main__":
    success = test_openrouter_connection()
    if success:
        print("\n🎉 OpenRouter configuration is working correctly!")
    else:
        print("\n❌ OpenRouter configuration needs to be fixed")
