from typing import Annotated , Literal
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from graph.nodes.classify_message import classify_message
from graph.nodes.logical_agent import logical_agent
from graph.nodes.therapist_agent import therapist_agent
from graph.nodes.kg_retrieve import kg_retrieve
from graph.nodes.kg_ingest import kg_ingest


class MessageClassifier(BaseModel):
    message_type: Literal['Logic','Therapist'] = Field(
        ...,
        description="classify that user require an emotional (therapist) or logical response"
    )

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None
    kg_context: str | None
    kg_ingested: bool | None
    
'''Type of info the graph will carry to the next states'''
    
class Person(BaseModel):
    name: str = Field(..., description="name of the person")
    # add things which we feel like adding and want llm to remember


'''state is a bunch of messages of type list'''

def build_graph():
    graph_builder = StateGraph(State)

    graph_builder.add_node("classify_message", classify_message)
    graph_builder.add_node("kg_ingest", kg_ingest)
    graph_builder.add_node("kg_retrieve", kg_retrieve)
    graph_builder.add_node("logical_agent", logical_agent)
    graph_builder.add_node("therapist_agent", therapist_agent)

    graph_builder.add_edge(START, "classify_message")
    graph_builder.add_edge("classify_message", "kg_ingest")

    def router(state: State):
        """Router: directs to logical_agent or therapist_agent"""
        if state["message_type"] == "Logic":
            return "kg_retrieve"
        return "therapist_agent"

    graph_builder.add_conditional_edges("kg_ingest", router, {
        "kg_retrieve": "kg_retrieve",
        "therapist_agent": "therapist_agent"
    })
    graph_builder.add_edge("kg_retrieve", "logical_agent")
    graph_builder.add_edge("logical_agent", END)
    graph_builder.add_edge("therapist_agent", END)

    return graph_builder.compile()