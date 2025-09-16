from graph.agent import build_graph

# -------------------- Setup --------------------
# load_dotenv()
# if not os.environ.get("GOOGLE_API_KEY"):
#     os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

# llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai",temperature=0.5)

# -------------------- State Definitions --------------------
# class MessageClassifier(BaseModel):
#     message_type: Literal['Logic','Therapist'] = Field(
#         ...,
#         description="classify that user require an emotional (therapist) or logical response"
#     )

# class State(TypedDict):
#     messages: Annotated[list, add_messages]
#     message_type: str | None
    
# '''Type of info the graph will carry to the next states'''
    
# class Person(BaseModel):
#     name: str = Field(..., description="name of the person")
#     # add things which we feel like adding and want llm to remember


# '''state is a bunch of messages of type list'''
# graph_builder = StateGraph(State)

# # -------------------- Nodes --------------------
# def classify_message(state: State) -> State:
#     """Classifier: decides whether user query needs Logic or Therapist response"""
#     last_message = state["messages"][-1].content
    
#     classifier_llm = llm.with_structured_output(MessageClassifier)
    
#     result = classifier_llm.invoke([
#         {    
#             "role":"system",
#             "content":"""
# Classify the following message as either "Logic" or "Therapist".

# Definitions:
# - Logic: factual, reasoning-based, or task-oriented, practical analysis, logical and analysis
# - Therapist: expresses feelings, mood, stress, or self-doubt
#             """
#         },
#         {"role":"user","content":last_message}
#     ])
    
#     return {"messages": state["messages"], "message_type": result.message_type}
    
    
# def router(state: State):
#     """Router: directs to logical_agent or therapist_agent"""
#     if state["message_type"] == "Logic":
#         return "logical_agent"
#     return "therapist_agent"
    

# def logical_agent(state: State) -> State:
#     """Logical agent: structured reasoning and problem-solving"""
#     prompt = ChatPromptTemplate.from_template(
#         '''
# You are a logical reasoning assistant. 
# - Provide clear, factual, and step-by-step analysis.  
# - Focus on problem-solving, reasoning, and clarity.  
# - If it's a question, explain logically like a teacher or problem solver.  
# - Keep responses structured and concise.  

# User query: {user_query}
# '''
#     )
#     formatted_prompt = prompt.format_prompt(user_query=state["messages"][-1].content)
#     response = llm.invoke(formatted_prompt.to_messages())
#     return {"messages": state["messages"] + [response], "message_type": state["message_type"]}
    
    
# def therapist_agent(state: State) -> State:
#     """Therapist agent: empathetic, supportive companion"""
#     prompt = ChatPromptTemplate.from_template(
#         '''
# You are a warm, supportive, and empathetic mental wellness companion. 
# Your purpose is to listen, uplift, and gently guide people toward positivity and resilience.

# Tone & Style:
# Kind, encouraging, and non-judgmental
# Easy-to-understand, friendly, and calming
# Balance emotional support with gentle logic when needed

# Core Abilities:

# Message Classification:
# Identify if the user’s message is logical (factual, problem-solving, seeking information) or emotional (feelings, stress, self-doubt, overwhelm).
# Respond accordingly with empathy or clarity.

# Emotional Support:
# If the message is emotional → validate feelings, offer encouragement, remind them they are not alone, and suggest calming reflections.

# Positive Reminders:
# Share gentle affirmations and reminders, such as:
# “You’re making progress, even if it feels slow.”
# “Your feelings are valid, and it’s okay to take breaks.”
# “You bring value to the lives of others.”

# Logical Support:
# If the message is logical → provide clear, structured responses, and help with problem-solving in a calm, supportive way.

# Boundaries:
# Stay within general wellness and positivity.
# If the user expresses harmful thoughts, encourage them to seek professional help or reach out to a trusted person.

# Example Flow:
# User: “I feel like I’m not good enough.”
# Bot: “I hear how heavy that feels. Please remember, your worth isn’t defined by one moment. 
# You’ve overcome challenges before, and you’re stronger than you realize.🌸”

# User query: {user_query}
# '''
#     )
#     formatted_prompt = prompt.format_prompt(user_query=state["messages"][-1].content)
#     response = llm.invoke(formatted_prompt.to_messages())
#     return {"messages": state["messages"] + [response], "message_type": state["message_type"]}


# -------------------- Build Graph --------------------
# graph_builder.add_node("classify_message", classify_message)
# graph_builder.add_node("logical_agent", logical_agent)
# graph_builder.add_node("therapist_agent", therapist_agent)

# graph_builder.add_edge(START, "classify_message")
# graph_builder.add_conditional_edges("classify_message", router, {
#     "logical_agent": "logical_agent",
#     "therapist_agent": "therapist_agent"
# })
# graph_builder.add_edge("logical_agent", END)
# graph_builder.add_edge("therapist_agent", END)

# graph = graph_builder.compile()

# # -------------------- Run --------------------

graph= build_graph()

user_input = input("enter a query:: ")
state = graph.invoke({"messages":[{"role":"user","content":user_input}], "message_type": None})
print(state["messages"][-1].content)

graph_representation = graph.get_graph()

# Print the ASCII representation
graph_representation.print_ascii()


'''Things to be added later '''
'''
Motivational Nudge Generator

Random gentle reminders: hydrate, stretch, rest, smile, breathe.

Live knowledge graph

Notion and its related functionalities:
Daily diary
Mood tracker
Self care
Coping Tools
Notes and Resources
Progress and report

'''

'''
Cloud based services via API

Dialogflow: A more structured platform for building conversational interfaces. 
You can use it to create specific, goal-oriented conversations. For example, a user who 
says "I'm feeling anxious" could be guided through a specific flow you've designed to help them with 
anxiety, with Dialogflow handling the conversation logic.

Speech-to-Text & Text-to-Speech: To enable a voice-based interaction, these APIs are essential. 
Speech-to-Text transcribes the user's spoken words into text for your chatbot to process, and Text-to-Speech 
converts the chatbot's text responses into a natural-sounding voice.
'''
