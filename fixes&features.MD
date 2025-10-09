# Fix 1

- Problem: 
    When user requested invoice without order ID, the LLM generated a proper response asking for order ID, but then the code made a second LLM call that overwrote this response with a generic error message

- Impact: 
    Users received "I'm sorry, I couldn't process your request" instead of being asked for their order ID

- Fix: 
    Removed the redundant LLM call and preserved the original chatbot response

# Feature 2

- Using OpenAI Agent instead of GROQ


