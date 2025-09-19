user_input = input("enter a query:: ")
state = graph.invoke({"messages":[{"role":"user","content":user_input}], "message_type": None})
print(state["messages"][-1].content)