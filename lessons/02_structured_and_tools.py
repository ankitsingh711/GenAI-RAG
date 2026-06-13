"""
LESSON 02 — Structured output and tool use (a.k.a. "function calling").

Two capabilities that turn a chatbot into a useful system component.

PART A — STRUCTURED OUTPUT
   Problem: free text is hard to parse in code. You want GUARANTEED JSON that
   matches a schema, so you can do `result.priority` instead of regexing prose.
   Solution: hand the API a schema (here, a Pydantic model) and it returns data
   that validates against it. This is how you wire an LLM into a real pipeline.

PART B — TOOL USE
   Problem: the model can't do things — it can't search your DB, call an API,
   or do reliable math. It can only generate text.
   Solution: you describe "tools" (functions) it's allowed to request. When it
   wants one, it returns a `tool_use` block with arguments. YOUR code runs the
   function and sends the result back. The model then continues.

   This request -> tool_use -> you execute -> send result -> continue cycle is
   THE AGENT LOOP. It's also the foundation of "agentic RAG": the search step in
   RAG can be exposed as a tool the model decides to call.

Run:  uv run python lessons/02_structured_and_tools.py
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel  # ships with the anthropic SDK

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key.")

client = Anthropic()
MODEL = "claude-opus-4-8"


# ============================================================================
# PART A — Structured output
# ============================================================================

class SupportTicket(BaseModel):
    """The shape we want back. The model is forced to fill exactly these fields."""
    category: str          # e.g. "billing", "bug", "feature_request"
    priority: str          # "low" | "medium" | "high"
    summary: str
    needs_human: bool


def classify_ticket(message: str) -> SupportTicket:
    # messages.parse() validates the response against the Pydantic model and
    # returns a typed object. If the model returns junk, you get a clear error
    # instead of a silent bad parse downstream.
    response = client.messages.parse(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": f"Classify this support message:\n\n{message}"}],
        output_format=SupportTicket,
    )
    return response.parsed_output


print("=== PART A: structured output ===")
ticket = classify_ticket(
    "I was charged twice this month and the export button throws a 500 error. Furious."
)
# `ticket` is a real typed object — use it like any Python object:
print(f"category:    {ticket.category}")
print(f"priority:    {ticket.priority}")
print(f"needs_human: {ticket.needs_human}")
print(f"summary:     {ticket.summary}")


# ============================================================================
# PART B — Tool use (the agent loop)
# ============================================================================

# 1) A normal Python function. The model can't see inside it — only its results.
KNOWLEDGE = {
    "rag": "Retrieval-Augmented Generation: fetch relevant text, then ask the LLM with it.",
    "embedding": "A list of numbers representing meaning, so similar text sits close together.",
    "token": "A word-piece; the unit LLMs read and that you are billed for.",
}


def lookup_definition(term: str) -> str:
    return KNOWLEDGE.get(term.lower().strip(), f"No definition found for '{term}'.")


# 2) Describe the tool to the model: name, when to use it, and its input schema.
#    The model uses `description` to decide WHEN to call it — be prescriptive.
TOOLS = [
    {
        "name": "lookup_definition",
        "description": "Look up the precise definition of a technical term from the internal "
                       "glossary. Call this whenever the user asks what a term means.",
        "input_schema": {
            "type": "object",
            "properties": {
                "term": {"type": "string", "description": "The term to define, e.g. 'embedding'"}
            },
            "required": ["term"],
        },
    }
]

# Maps a tool name -> the real function. This is YOUR dispatch table.
DISPATCH = {"lookup_definition": lookup_definition}


def run_agent(user_question: str) -> str:
    """The agent loop: keep calling the model until it stops requesting tools."""
    messages = [{"role": "user", "content": user_question}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        # If the model is done (no tool requested), return its text.
        if response.stop_reason != "tool_use":
            return next((b.text for b in response.content if b.type == "text"), "")

        # Otherwise it asked for one or more tools. Append its turn verbatim
        # (the tool_use blocks must be preserved), then run each tool.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [model called {block.name}({block.input})]")
                output = DISPATCH[block.name](**block.input)  # run YOUR code
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,        # must match the request id
                    "content": output,
                })

        # Send the results back as a user turn; loop so the model can continue.
        messages.append({"role": "user", "content": tool_results})


print("\n=== PART B: tool use ===")
print("Q: What does 'embedding' mean, and why does it matter for RAG?")
answer = run_agent("What does 'embedding' mean, and why does it matter for RAG?")
print(f"\nDocuMind: {answer}")

# ----------------------------------------------------------------------------
# TRY IT YOURSELF:
#   1. Add a second tool, e.g. add_numbers(a, b), and ask a question that needs
#      both tools. Watch the loop call them in sequence.
#   2. Ask something NOT in the glossary ("what is kubernetes?"). The model will
#      either call the tool and get "No definition found", or answer from its own
#      knowledge. Notice you don't control that — the description guides it.
#   3. Connect the dots: in lesson 05, `lookup_definition` becomes `search_documents`,
#      backed by the vector store you build in lessons 03-04. Same loop, real data.
# ----------------------------------------------------------------------------
