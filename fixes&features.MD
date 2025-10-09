# Fixes & Features

## Fix 1: Email Invoice Response Overwriting

- **Problem**: 
    When user requested invoice without order ID, the LLM generated a proper response asking for order ID, but then the code made a second LLM call that overwrote this response with a generic error message

- **Impact**: 
    Users received "I'm sorry, I couldn't process your request" instead of being asked for their order ID

- **Fix**: 
    Removed the redundant LLM call and preserved the original chatbot response (lines 154-157 in `chatbot.py`)

---

## Fix 2: Product Retrieval Response Overwriting

- **Problem**: 
    For vague queries like "I need glasses", the bot generated a helpful clarifying question but then immediately overwrote it with generic product recommendations

- **Impact**: 
    Users received random product lists instead of being asked what specific features they wanted

- **Fix**: 
    - Updated prompt to distinguish between specific and vague queries

---

## Fix 3: Unnecessary Order Retrieval

- **Problem**: 
    Prompt instructed LLM to retrieve orders even when no order ID was present in the query

- **Impact**: 
    Unnecessary database lookups and processing time

- **Fix**: 
    Updated prompt to only set `run_retrieval_orders=true` when actual order ID is detected

---

## Feature 1: OpenAI Integration

- **Description**: 
    Switched from GROQ agent to OpenAI agent for improved response quality

- **Changes**: 
    - Updated `dependencies.py` to use `OpenAIChat` instead of `Groq`
    - Added `OPENAI_API_KEY` and `OPENAI_MODEL_NAME` configuration in `config.py`
