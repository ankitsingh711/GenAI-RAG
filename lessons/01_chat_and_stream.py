"""
LESSON 01 — System prompts, multi-turn memory, and streaming.

Three ideas every AI engineer must own:

1. SYSTEM PROMPT: separate from the conversation. It sets the rules/persona/role.
   This is where you put "You are a support agent for ACME. Be concise. Never invent
   policy." It's the single biggest lever on behaviour.

2. THE API IS STATELESS. Claude has NO memory between calls. "Chat memory" is an
   illusion you create by re-sending the ENTIRE conversation history every time.
   This matters: longer history = more input tokens = more cost. (Lesson 08 fixes
   this with prompt caching.)

3. STREAMING: instead of waiting for the whole answer, you receive it token-by-token.
   Essential for UX (the "typing" effect) and to avoid timeouts on long answers.

Run:  uv run python lessons/01_chat_and_stream.py
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key.")

client = Anthropic()
MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You are DocuMind, a precise technical assistant. "
    "Answer in at most 3 sentences. If you are unsure, say so plainly."
)

# `history` IS the memory. We append every turn to it and resend it each call.
history: list[dict] = []


def ask(user_text: str) -> str:
    """Send one turn, streaming the reply, while maintaining conversation memory."""
    history.append({"role": "user", "content": user_text})

    print(f"\n> {user_text}")
    print("DocuMind: ", end="", flush=True)

    pieces: list[str] = []
    # .stream() is a context manager. text_stream yields text as it arrives.
    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,          # <-- the system prompt, kept OUT of messages
        messages=history,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            pieces.append(text)
    print()  # newline after the streamed answer

    answer = "".join(pieces)
    # CRITICAL: append the assistant's reply too, so the next turn "remembers" it.
    history.append({"role": "assistant", "content": answer})
    return answer


# A 3-turn conversation. Notice turn 3 only works because turns 1-2 are in history.
ask("My name is Ankit and I'm learning RAG.")
ask("What's the single most important concept in RAG?")
ask("What did I say my name was?")  # proves the model 'remembers' via resent history

print(f"\n[history now holds {len(history)} messages — this is what gets resent each call]")

# ----------------------------------------------------------------------------
# TRY IT YOURSELF:
#   1. Comment out the two `history.append(...)` lines. Re-run. Turn 3 now fails to
#      recall your name — because you destroyed the memory. THIS is what "context" is.
#   2. Change SYSTEM_PROMPT to "Answer only in JSON" and watch every reply change shape.
# ----------------------------------------------------------------------------
