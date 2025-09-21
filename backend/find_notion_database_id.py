#!/usr/bin/env python3
"""
Script to help find the correct Notion database ID
"""
import os
from dotenv import load_dotenv

def find_database_id():
    """Help user find the correct database ID"""
    print("🔍 Finding your Notion Database ID...")
    print("\nTo get the correct database ID:")
    print("1. Go to your Notion workspace")
    print("2. Open the database you want to use")
    print("3. Look at the URL in your browser")
    print("4. The URL should look like:")
    print("   https://www.notion.so/your-workspace/a1b2c3d4-e5f6-7890-abcd-ef1234567890?v=...")
    print("5. Copy the part that looks like: a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    print("\nThe database ID should be:")
    print("✅ 32 characters long")
    print("✅ Have hyphens in the right places")
    print("✅ Look like: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    print("\n❌ NOT like: Weekly-Schedule-27592a42a75380d2aa27c92bbab00483")
    
    # Load current config
    load_dotenv()
    current_id = os.getenv("NOTION_DEFAULT_DATABASE_ID")
    
    if current_id:
        print(f"\nCurrent database ID in .env: {current_id}")
        
        # Check if it looks like a valid UUID
        if len(current_id) == 36 and current_id.count('-') == 4:
            print("✅ This looks like a valid UUID format!")
        else:
            print("❌ This doesn't look like a valid UUID format.")
            print("   Please get the correct database ID from your Notion URL.")
    else:
        print("\nNo database ID found in .env file.")

if __name__ == "__main__":
    find_database_id()
