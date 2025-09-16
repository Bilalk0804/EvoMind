from models.llm import llm 
from pydantic import BaseModel, Field
from typing import Any , Literal

class MessageClassifier(BaseModel):
    message_type: Literal['Logic','Therapist'] = Field(
        ...,
        description="classify that user require an emotional (therapist) or logical response"
    )

# def classify_message(state: State) -> State:
def classify_message(state: dict[str, Any]) -> dict[str, Any]:
    """Classifier: decides whether user query needs Logic or Therapist response"""
    last_message = state["messages"][-1].content
    
    classifier_llm = llm.with_structured_output(MessageClassifier)
    
    result = classifier_llm.invoke([
        {    
            "role":"system",
            "content":"""
                Classify the following message as either "Logic" or "Therapist".

                Definitions:
                - Logic: factual, reasoning-based, or task-oriented, practical analysis, logical and analysis
                - Therapist: expresses feelings, mood, stress, or self-doubt
            """
        },
        {"role":"user","content":last_message}
    ])
    
    return {"messages": state["messages"], "message_type": result.message_type}