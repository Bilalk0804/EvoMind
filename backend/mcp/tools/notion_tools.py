from typing import Any, Dict, List, Optional

try:
    from notion_client import Client as NotionClient
except Exception as e:
    NotionClient = None  # type: ignore


class NotionClientWrapper:
    def __init__(self, auth_token: Optional[str], default_database_id: Optional[str] = None) -> None:
        self.default_database_id = default_database_id
        self.enabled = bool(auth_token and NotionClient is not None)
        self._client = NotionClient(auth=auth_token) if self.enabled else None

    # Tools are instance methods to capture config
    def create_page_tool(self, parent_database_id: Optional[str] = None, title: str = "Untitled", properties: Dict[str, Any] | None = None, content: str | None = None) -> Dict[str, Any]:
        if not self.enabled or self._client is None:
            return {"error": "Notion not configured", "status": "disabled"}
        dbid = parent_database_id or self.default_database_id
        if not dbid:
            return {"error": "Missing database id"}
        props = properties or {"Name": {"title": [{"text": {"content": title}}]}}
        children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": content or ""}}]}}]
        page = self._client.pages.create(parent={"database_id": dbid}, properties=props, children=children)
        return {"status": "created", "page_id": page.get("id")}

    def update_page_tool(self, page_id: str, properties: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self.enabled or self._client is None:
            return {"error": "Notion not configured", "status": "disabled"}
        if not page_id:
            return {"error": "Missing page_id"}
        props = properties or {}
        page = self._client.pages.update(page_id=page_id, properties=props)
        return {"status": "updated", "page_id": page.get("id")}

    def query_database_tool(self, database_id: Optional[str] = None, filter: Dict[str, Any] | None = None, sorts: List[Dict[str, Any]] | None = None, page_size: int = 10) -> Dict[str, Any]:
        if not self.enabled or self._client is None:
            return {"error": "Notion not configured", "status": "disabled"}
        dbid = database_id or self.default_database_id
        if not dbid:
            return {"error": "Missing database id"}
        res = self._client.databases.query(database_id=dbid, filter=filter, sorts=sorts, page_size=page_size)
        items = [{"id": r.get("id"), "properties": r.get("properties", {})} for r in res.get("results", [])]
        return {"count": len(items), "results": items}


