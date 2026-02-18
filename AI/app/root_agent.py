from app.agents.multi.faq_agent import build_faq_agent

# ADK-Web expects this variable name to exist:
# Using build_faq_agent directly enables conversation history,
# allowing MiMi to remember she has already greeted the customer.
root_agent = build_faq_agent("mizumi")