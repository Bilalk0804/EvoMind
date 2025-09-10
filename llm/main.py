from dotenv import load_dotenv
import os
from typing import Annotated , Literal
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

class State(TypedDict):
    messages: Annotated[list, add_messages]
'''Type of info the grapg will carry to the next atates'''
    


'''state is a bunch of messages of type list'''
graph_builder=StateGraph(State)

def chatbot(state:State):
    return {"messages":[llm.invoke(state["messages"])]}

graph_builder.add_node("chatbot",chatbot)

graph_builder.add_edge(START,"chatbot")

graph_builder.add_edge("chatbot",END)

graph=graph_builder.compile()

user_input=input("enter a query:: ")

state=graph.invoke({"messages":[{"role":"user","content":user_input}]})

#print(state["messages"][-1].content)
#print(state["messages"])
graph_representation = graph.get_graph()
graph_representation.print_ascii()


'''Things to be added later '''
'''
Motivational Nudge Generator

Random gentle reminders: hydrate, stretch, rest, smile, breathe.

Live knowledge graph

Notion and its related functionalities:
Daily dairy
Mode tracker
Self care
Coping Tools
Notes and Resources
Progress and report

'''

'''
Cloud based services via api

Dialogflow: A more structured platform for building conversational interfaces. 
You can use it to create specific, goal-oriented conversations. For example, a user who 
says "I'm feeling anxious" could be guided through a specific flow you've designed to help them with 
anxiety, with Dialogflow handling the conversation logic.

Speech-to-Text & Text-to-Speech: To enable a voice-based interaction, these APIs are essential. 
Speech-to-Text transcribes the user's spoken words into text for your chatbot to process, and Text-to-Speech 
converts the chatbot's text responses into a natural-sounding voice.
'''