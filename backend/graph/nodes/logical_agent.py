from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from models.llm import llm
from typing import Any

def logical_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Logical agent: structured reasoning and problem-solving grounded by KG context when available."""
    prompt = ChatPromptTemplate.from_template(
        '''
            You are a logical reasoning assistant.
            - Provide clear, factual, and step-by-step analysis.
            - Focus on problem-solving, reasoning, and clarity.
            - If it's a question, explain logically like a teacher or problem solver.
            - Keep responses structured and concise.

            If KG context is provided, you MUST ground your answer in it and prefer facts from it.
            If KG context is absent or insufficient, answer normally.

            KG context (may be empty):
            {kg_context}

            User query: {user_query}
            '''
    )
    formatted_prompt = prompt.format_prompt(
        user_query=state["messages"][-1].content,
        kg_context=state.get("kg_context") or ""
    )
    # Stream tokens to stdout (or hosting process) while building final response
    final_text_parts: list[str] = []
    for chunk in llm.stream(formatted_prompt.to_messages()):
        text = getattr(chunk, "content", None) or getattr(chunk, "text", "") or ""
        if text:
            print(text, end="", flush=True)
            final_text_parts.append(text)
    print()  # newline after stream

    response = AIMessage(content="".join(final_text_parts))
    return {"messages": state["messages"] + [response], "message_type": state["message_type"], "kg_context": state.get("kg_context")}