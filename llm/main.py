from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent,AgentExecutor
from pydantic import BaseModel

from lanf
load_dotenv()
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

# response = llm.invoke("Sing a ballad of LangChain.")
# print(response.content)

'''main model building starts from here'''

class Response(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]
parcer = PydanticOutputParser(pydantic_object=Response)


prompt=ChatPromptTemplate.from_messages(
  [
  ("system",
  """
  You are a Youth Wellness Assistant.
Your role is to provide empathetic, supportive, and non-clinical guidance to young people.
Do not give medical or therapeutic advice, diagnosis, or treatment.
Instead, focus on:

Active listening and showing empathy.

Motivational nudges (e.g., “remember to take a break,” “stay hydrated,” “you’re doing your best”).

Sharing general resources (articles, self-help guides, wellness apps).

Encouraging healthy habits (rest, exercise, journaling, mindfulness).

Suggesting coping skills (deep breathing, grounding techniques, positive affirmations).

Including disclaimers when sensitive topics arise, reminding the user you are not a therapy bot.

If a user mentions urgent distress, encourage them to reach out to a trusted adult, counselor, or local emergency helpline.

Tone: Supportive, kind, empathetic, and encouraging.
Boundaries: No medical advice, no diagnoses, no therapy.
   
   """),
  ("placeholder", "{chat_history}"),
  ("human", "{query}"),
  ("placeholder", "{agent_scratchpad}")
    ]).partial(format_instructions=parcer.get_format_instructions())

tools=[search_tool,wiki_tool]

'''Things to be added later '''
'''
Motivational Nudge Generator

Random gentle reminders: hydrate, stretch, rest, smile, breathe.

Can be context-aware (if user says "I'm tired," suggest rest).

Mood Tracker

Simple check-in: “How are you feeling today? (happy, sad, anxious, okay)”

Graph over time to spot patterns.

Wellness Resource Recommender

Share links to safe resources (e.g., mindfulness apps, helplines, motivational videos, journaling prompts).

Micro-Coping Exercises

Breathing exercises (box breathing, 4-7-8).

Quick gratitude prompts (“name 3 things you’re grateful for”).

Small mindfulness practices.

Reflection Journal Tool

Daily/weekly prompts for self-reflection.

Users can store and revisit their responses.

Disclaimers + Safety Net

Clear disclaimers when topics get sensitive.

Always encourage reaching out to real people (friends, family, professionals) when needed.

Gamified Wellness Goals

Daily challenges (drink 8 glasses of water, take a 5-min walk).

Reward system (streaks, badges).
'''
