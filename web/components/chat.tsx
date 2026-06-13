"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Sparkles, Square } from "lucide-react";

import { streamAsk } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MessageBubble, type ChatMessage } from "@/components/chat-message";

// One stable session id per browser tab → the backend keeps multi-turn memory.
const SESSION_ID = typeof crypto !== "undefined" ? crypto.randomUUID() : "web-session";

const SUGGESTIONS = [
  "How long do password reset links last?",
  "What happens to my data if I cancel?",
  "When does the platform add a new instance?",
  "How much is the Growth plan?",
];

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the newest token as the answer streams in.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;

    setInput("");
    setBusy(true);

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    const assistantId = crypto.randomUUID();
    // Add the user message + an empty assistant message (renders the typing dots).
    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: "assistant", content: "" }]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamAsk(
        question,
        SESSION_ID,
        (chunk) => {
          // Append each streamed chunk to the assistant message in place.
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + chunk } : m)),
          );
        },
        controller.signal,
      );
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content:
                  m.content ||
                  (aborted
                    ? "_(stopped)_"
                    : "⚠️ Couldn't reach the backend. Make sure it's running on port 8000."),
              }
            : m,
        ),
      );
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-1 flex-col">
      {/* Header */}
      <header className="flex items-center gap-2 border-b border-border px-6 py-4">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Sparkles className="size-4" />
        </div>
        <div>
          <h1 className="text-sm font-semibold leading-none">DocuMind</h1>
          <p className="text-xs text-muted-foreground">Ask questions about your documents</p>
        </div>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {empty ? (
          <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center gap-6 px-6 text-center">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Sparkles className="size-7" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Ask your documents anything</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Answers are grounded in your indexed files and cite nothing it can&apos;t find.
              </p>
            </div>
            <div className="grid w-full gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-lg border border-border bg-card/50 px-3 py-2.5 text-left text-sm transition-colors hover:bg-accent"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-4">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-border p-4">
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-border bg-card/50 p-2 focus-within:ring-1 focus-within:ring-ring">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // Enter sends; Shift+Enter makes a newline.
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder="Ask about your documents…"
            rows={1}
            className="max-h-40 min-h-0 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
          />
          {busy ? (
            <Button size="icon" variant="secondary" onClick={stop} title="Stop">
              <Square className="size-4" />
            </Button>
          ) : (
            <Button size="icon" onClick={() => send(input)} disabled={!input.trim()} title="Send">
              <ArrowUp className="size-4" />
            </Button>
          )}
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
          DocuMind can be wrong. Verify important answers against the source documents.
        </p>
      </div>
    </div>
  );
}
