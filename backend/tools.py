from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool

search = DuckDuckGoSearchRun()
search_tool = Tool(
    name="DuckDuckGoSearch",
    func=search.run,
    description="Search the web for information",
    return_direct=True
)
api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=2000, lang="en")
wiki_tool= WikipediaQueryRun(api_wrapper=api_wrapper)
