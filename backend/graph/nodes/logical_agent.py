from langchain_core.prompts import ChatPromptTemplate
from models.llm import llm
from typing import Any , Literal

def logical_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Logical agent: structured reasoning and problem-solving"""
    prompt = ChatPromptTemplate.from_template(
        '''
            You are a logical reasoning assistant. 
            - Provide clear, factual, and step-by-step analysis.  
            - Focus on problem-solving, reasoning, and clarity.  
            - If it's a question, explain logically like a teacher or problem solver.  
            - Keep responses structured and concise.  

            User query: {user_query}
            '''
    )
    formatted_prompt = prompt.format_prompt(user_query=state["messages"][-1].content)
    response = llm.invoke(formatted_prompt.to_messages())
    return {"messages": state["messages"] + [response], "message_type": state["message_type"]}