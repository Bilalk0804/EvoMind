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
        
        # For weekly schedule database, create appropriate properties
        if "Weekly-Schedule" in dbid or "schedule" in dbid.lower():
            # Properties for a weekly schedule database
            props = properties or {
                "Task": {"title": [{"text": {"content": title}}]},
                "Status": {"select": {"name": "Not Started"}},
                "Priority": {"select": {"name": "Medium"}},
                "Notes": {"rich_text": [{"text": {"content": content or ""}}]}
            }
        else:
            # Default properties for other databases
            props = properties or {"Name": {"title": [{"text": {"content": title}}]}}
        
        children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": content or ""}}]}}]
        
        try:
            page = self._client.pages.create(parent={"database_id": dbid}, properties=props, children=children)
            return {"status": "created", "page_id": page.get("id")}
        except Exception as e:
            return {"error": f"Failed to create page: {str(e)}", "status": "failed"}

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
        
        try:
            res = self._client.databases.query(database_id=dbid, filter=filter, sorts=sorts, page_size=page_size)
            items = []
            for r in res.get("results", []):
                # Extract relevant information based on database type
                item = {
                    "id": r.get("id"),
                    "properties": r.get("properties", {}),
                    "last_edited_time": r.get("last_edited_time"),
                    "created_time": r.get("created_time")
                }
                
                # For weekly schedule, extract task-specific info
                if "Weekly-Schedule" in dbid or "schedule" in dbid.lower():
                    props = r.get("properties", {})
                    item["title"] = (
                        props.get("Task", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled") or
                        props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled") or
                        "Untitled"
                    )
                    item["status"] = props.get("Status", {}).get("select", {}).get("name", "Unknown")
                    item["priority"] = props.get("Priority", {}).get("select", {}).get("name", "Unknown")
                else:
                    # Default title extraction
                    item["title"] = (
                        props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled") or
                        props.get("Task", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled") or
                        "Untitled"
                    )
                
                items.append(item)
            
            return {"count": len(items), "results": items}
        except Exception as e:
            return {"error": f"Failed to query database: {str(e)}", "status": "failed"}


