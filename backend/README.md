## Backend

This backend contains the agent graph, KG utilities, model setup, and an MCP server.

### MCP Server (Planning, Scheduling, Notion)

We provide a lightweight Model Context Protocol (MCP) server that exposes:

- plan_tasks(goal, deadline?, max_steps?)
- get_schedule(date?)
- add_event(title, start, end, description?)
- create_page_tool(parent_database_id?, title, properties?, content?)
- update_page_tool(page_id, properties?)
- query_database_tool(database_id?, filter?, sorts?, page_size?)

Environment variables:

- NOTION_API_KEY
- NOTION_DEFAULT_DATABASE_ID (optional)

Install deps and run:

```bash
pip install -r requirements.txt
python -m backend.mcp.server
```

This starts the MCP server named "genai_mcp". Your client can connect using the standard MCP transport.


