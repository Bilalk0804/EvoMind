import os
import asyncio
from typing import Any, Dict, List, Optional

# Minimal MCP server using mcp (model context protocol) reference impl
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise RuntimeError("mcp not installed. Add 'mcp' to requirements.")

from tools.notion_tools import NotionClientWrapper
from tools.planning_tools import plan_tasks_tool, get_schedule_tool, add_event_tool


def create_server() -> FastMCP:
    server = FastMCP("genai_mcp")

    notion_token = os.getenv("NOTION_API_KEY")
    default_db = os.getenv("NOTION_DEFAULT_DATABASE_ID")
    notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)

    # Planning and scheduling tools (LLM-agnostic business logic)
    server.tool()(plan_tasks_tool)
    server.tool()(get_schedule_tool)
    server.tool()(add_event_tool)

    # Notion tools (wrap Notion API)
    server.tool()(notion.create_page_tool)
    server.tool()(notion.update_page_tool)
    server.tool()(notion.query_database_tool)

    return server


async def amain() -> None:
    server = create_server()
    await server.run()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()


