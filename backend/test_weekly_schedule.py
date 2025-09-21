#!/usr/bin/env python3
"""
Test script for Weekly Schedule Notion database
"""
import os
from dotenv import load_dotenv

def test_weekly_schedule():
    """Test the weekly schedule database integration"""
    print("📅 Testing Weekly Schedule Notion Integration...")
    
    # Load environment variables
    load_dotenv()
    
    notion_token = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DEFAULT_DATABASE_ID")
    
    if not notion_token:
        print("❌ NOTION_API_KEY not found")
        return False
    
    if not database_id:
        print("❌ NOTION_DEFAULT_DATABASE_ID not found")
        return False
    
    print(f"✅ Using database ID: {database_id}")
    
    try:
        from local_mcp.tools.notion_tools import NotionClientWrapper
        
        notion = NotionClientWrapper(auth_token=notion_token, default_database_id=database_id)
        
        if not notion.enabled:
            print("❌ Notion client not enabled")
            return False
        
        print("✅ Notion client initialized")
        
        # Test querying the database
        print("🔍 Testing database query...")
        result = notion.query_database_tool(page_size=5)
        
        if "error" in result:
            print(f"❌ Query failed: {result['error']}")
            return False
        
        print(f"✅ Found {result.get('count', 0)} items in weekly schedule")
        
        # Test creating a task
        print("🔍 Testing task creation...")
        create_result = notion.create_page_tool(
            title="Test Task from AI Assistant",
            content="This is a test task created by the Universal AI Assistant for weekly schedule."
        )
        
        if "error" in create_result:
            print(f"❌ Task creation failed: {create_result['error']}")
            return False
        
        print(f"✅ Task created successfully - ID: {create_result.get('page_id', 'Unknown')}")
        
        print("\n🎉 Weekly Schedule integration is working!")
        print("You can now:")
        print("1. Create tasks in your weekly schedule")
        print("2. View existing tasks")
        print("3. Use the AI assistant to manage your schedule")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_weekly_schedule()
