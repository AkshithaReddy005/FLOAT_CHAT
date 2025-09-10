#!/usr/bin/env python3
"""
Debug script to check environment variables and API key format
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_env_vars():
    """Debug environment variables"""
    
    print("=== Environment Variables Debug ===")
    
    # Check if .env file exists
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        print(f"✓ .env file exists at: {os.path.abspath(env_file_path)}")
        
        # Read .env file content
        with open(env_file_path, 'r') as f:
            content = f.read()
            print(f"✓ .env file size: {len(content)} characters")
    else:
        print("❌ .env file not found")
        return
    
    # Check environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL")
    
    print(f"\nEnvironment Variables:")
    print(f"OPENAI_API_KEY: {'Set' if api_key else 'Not set'}")
    if api_key:
        print(f"  - Length: {len(api_key)} characters")
        print(f"  - Starts with: {api_key[:10]}...")
        print(f"  - Ends with: ...{api_key[-4:]}")
        print(f"  - Format check: {'✓ Valid' if api_key.startswith('sk-or-v1-') else '❌ Invalid format'}")
    
    print(f"OPENAI_BASE_URL: {base_url}")
    print(f"OPENAI_MODEL: {model}")
    
    # Check for common issues
    print(f"\n=== Common Issues Check ===")
    
    if api_key:
        if api_key == "your_openrouter_api_key_here":
            print("❌ API key is still the placeholder value")
        elif not api_key.startswith("sk-or-v1-"):
            print("❌ API key doesn't start with 'sk-or-v1-'")
        elif len(api_key) < 50:
            print("❌ API key seems too short")
        else:
            print("✓ API key format looks correct")
    
    if base_url != "https://openrouter.ai/api/v1":
        print(f"❌ Base URL is incorrect: {base_url}")
    else:
        print("✓ Base URL is correct")

if __name__ == "__main__":
    debug_env_vars()
