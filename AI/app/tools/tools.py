from app.retrieval import search_kb

def retrieve_tool(query: str) -> dict:
    """
    Retrieve top-k knowledge snippets from the local FAISS index.
    """
    k = 5 
    return search_kb(query=query, k=k)

#def handoff_to_human(issue: str, contact: str | None = None) -> dict:
#    """
#    Escalate the conversation to a human agent (stub).
#    Replace with Slack/Zendesk/CRM webhook later.
#    """
#    ticket_id = "T-" + str(abs(hash(issue)))[:8]
#    return {"status": "handed_off", "ticket_id": ticket_id, "contact": contact}
