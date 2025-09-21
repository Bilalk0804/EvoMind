#!/usr/bin/env python3
"""
Test script for Notion integration
Run this to verify your Notion setup is working correctly
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_notion_connection():
    """Test the Notion API connection and database access"""
    print("🔍 Testing Notion Integration...")
    
    # Check environment variables
    notion_token = os.getenv("NOTION_API_KEY")
    default_db = os.getenv("NOTION_DEFAULT_DATABASE_ID")
    
    if not notion_token:
        print("❌ NOTION_API_KEY not found in environment variables")
        print("   Please add NOTION_API_KEY to your .env file")
        return False
    
    if not default_db:
        print("❌ NOTION_DEFAULT_DATABASE_ID not found in environment variables")
        print("   Please add NOTION_DEFAULT_DATABASE_ID to your .env file")
        return False
    
    print(f"✅ Environment variables found")
    print(f"   API Key: {notion_token[:10]}...")
    print(f"   Database ID: {default_db[:10]}...")
    
    try:
        # Test Notion client
        from local_mcp.tools.notion_tools import NotionClientWrapper
        
        notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
        
        if not notion.enabled:
            print("❌ Notion client not enabled - check your API key")
            return False
        
        print("✅ Notion client initialized successfully")
        
        # Test database query
        print("🔍 Testing database query...")
        result = notion.query_database_tool(page_size=5)
        
        if "error" in result:
            print(f"❌ Database query failed: {result['error']}")
            return False
        
        print(f"✅ Database query successful - found {result.get('count', 0)} pages")
        
        # Test page creation
        print("🔍 Testing page creation...")
        create_result = notion.create_page_tool(
            title="Test Page from AI Assistant",
            content="This is a test page created by the Universal AI Assistant integration."
        )
        
        if "error" in create_result:
            print(f"❌ Page creation failed: {create_result['error']}")
            return False
        
        print(f"✅ Page created successfully - ID: {create_result.get('page_id', 'Unknown')}")
        
        print("\n🎉 All tests passed! Your Notion integration is working correctly.")
        print("\nNext steps:")
        print("1. Start the backend server: python api_server.py")
        print("2. Start the frontend: cd frontend && npm run dev")
        print("3. Open the Notion tab in the web interface")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Please install the notion-client package: pip install notion-client")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_notion_connection()
    sys.exit(0 if success else 1)
