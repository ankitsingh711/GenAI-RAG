"""
LESSON 00 — Your first LLM call.

Big idea: an LLM API is just an HTTP endpoint. You send a list of messages,
you get back generated text + metadata. The `anthropic` SDK is a thin wrapper
over that HTTP call so you don't hand-write requests.

Run:  uv run python lessons/00_hello_claude.py

What to notice in the output:
  - The text Claude generated.
  - `usage`: how many TOKENS went in and came out. Tokens ~= word pieces.
    You are billed per token. This is THE number to watch in production.
  - `stop_reason`: why it stopped ("end_turn" = it finished naturally).
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

# load_dotenv reads the .env file and puts ANTHROPIC_API_KEY into os.environ.
# The SDK automatically reads ANTHROPIC_API_KEY from the environment, so we
# don't pass the key explicitly — never hard-code secrets.
load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key.")

client = Anthropic()

# This is THE core call you'll make thousands of times.
#   model      -> which Claude to use. Opus = most capable. (Sonnet/Haiku = cheaper/faster.)
#   max_tokens -> hard cap on the OUTPUT length. Not a target, a ceiling.
#   messages   -> the conversation so far. role is "user" or "assistant".
response = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "In 3 sentences, explain what an LLM is to a software engineer."}
    ],
)

# response.content is a LIST of "content blocks", not a plain string.
# (Later, blocks can be tool calls or thinking — so always iterate and check .type.)
for block in response.content:
    if block.type == "text":
        print("\n=== Claude says ===")
        print(block.text)

# The metadata that matters:
print("\n=== Metadata ===")
print(f"model:        {response.model}")
print(f"stop_reason:  {response.stop_reason}")
print(f"input tokens:  {response.usage.input_tokens}")
print(f"output tokens: {response.usage.output_tokens}")

# Rough cost estimate (Opus 4.8 = $5 / 1M input, $25 / 1M output as of now).
cost = response.usage.input_tokens * 5 / 1_000_000 + response.usage.output_tokens * 25 / 1_000_000
print(f"approx cost:   ${cost:.6f}")

# ----------------------------------------------------------------------------
# TRY IT YOURSELF:
#   1. Change the prompt. Ask it to answer in one word — watch output tokens drop.
#   2. Lower max_tokens to 10 and ask for a long answer — stop_reason becomes
#      "max_tokens" (it got cut off). This is a real bug source in production.
# ----------------------------------------------------------------------------
