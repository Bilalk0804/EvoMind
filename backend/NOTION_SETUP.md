# Notion Integration Setup Guide

## Prerequisites

1. **Notion Account**: You need a Notion account
2. **Notion Integration**: Create a Notion integration to get API access

## Step 1: Create Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name (e.g., "Universal AI Assistant")
4. Select the workspace you want to connect
5. Click "Submit"
6. Copy the "Internal Integration Token" - this is your `NOTION_API_KEY`

## Step 2: Create Notion Database

1. In your Notion workspace, create a new page
2. Add a database to the page
3. Set up the database with at least a "Name" property (title)
4. Copy the database ID from the URL (the long string after the last slash and before the `?`)
5. This is your `NOTION_DEFAULT_DATABASE_ID`

## Step 3: Share Database with Integration

1. Open your database in Notion
2. Click "Share" in the top right
3. Click "Invite" and search for your integration name
4. Select your integration and give it "Can edit" permissions

## Step 4: Configure Environment Variables

Create a `.env` file in the backend directory with:

```env
# Notion Integration
NOTION_API_KEY=your_integration_token_here
NOTION_DEFAULT_DATABASE_ID=your_database_id_here

# Other required variables
GROQ_API_KEY=your_groq_api_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
```

## Step 5: Install Dependencies

Make sure the Notion client is installed:

```bash
pip install notion-client
```

## Step 6: Test the Integration

1. Start the backend server: `python api_server.py`
2. Open the frontend and go to the Notion tab
3. Click "Refresh" to test the connection
4. Try creating a new page using the templates

## Troubleshooting

- **"Notion API key not configured"**: Check your `.env` file and restart the server
- **"Missing database id"**: Verify your `NOTION_DEFAULT_DATABASE_ID` is correct
- **"Notion not configured"**: Make sure the `notion-client` package is installed
- **Permission errors**: Ensure your integration has access to the database

## Database ID Format

The database ID should look like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

You can find it in the Notion URL:
`https://www.notion.so/your-workspace/a1b2c3d4e5f67890abcdef1234567890?v=...`
