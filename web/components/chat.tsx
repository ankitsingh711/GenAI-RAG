"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, PanelLeft, Plus, Sparkles, Square } from "lucide-react";
import { toast } from "sonner";

import { streamAsk } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { MessageBubble, type ChatMessage } from "@/components/chat-message";
import { SourcesContent } from "@/components/sources-panel";
import { ThemeToggle } from "@/components/theme-toggle";

const SUGGESTIONS = [
  "How long do password reset links last?",
  "What happens to my data if I cancel?",
  "When does the platform add a new instance?",
  "How much is the Growth plan?",
];

function newSessionId() {
  return typeof crypto !== "undefined" ? crypto.randomUUID() : `web-${Date.now()}`;
}

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(newSessionId);
  const [atBottom, setAtBottom] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to newest token while streaming — but only if the user is already at
  // the bottom (don't yank them down if they've scrolled up to read).
  useEffect(() => {
    if (atBottom) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, atBottom]);

  function onScroll() {
    const el = scrollRef.current;
    if (!el) return;
    setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 80);
  }

  function scrollToBottom() {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }

  function newChat() {
    if (busy) abortRef.current?.abort();
    setMessages([]);
    setSessionId(newSessionId()); // fresh server-side memory
    setInput("");
  }

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;

    setInput("");
    setBusy(true);
    setAtBottom(true);

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: "assistant", content: "" }]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamAsk(
        question,
        sessionId,
        (chunk) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + chunk } : m)),
          );
        },
        controller.signal,
      );
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      if (!aborted) toast.error("Couldn't reach the backend. Make sure it's running on port 8000.");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content || (aborted ? "_(stopped)_" : "⚠️ Request failed.") }
            : m,
        ),
      );
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-1 flex-col">
      {/* Header */}
      <header className="flex items-center gap-2 border-b border-border px-4 py-3 sm:px-6">
        {/* Mobile: open the knowledge base in a drawer */}
        <Sheet>
          <SheetTrigger
            render={
              <Button variant="ghost" size="icon" className="size-8 md:hidden" title="Documents">
                <PanelLeft className="size-4" />
              </Button>
            }
          />
          <SheetContent side="left" className="w-80 p-4">
            <SheetTitle className="sr-only">Knowledge base</SheetTitle>
            <SourcesContent />
          </SheetContent>
        </Sheet>

        <div className="flex size-7 items-center justify-center rounded-md bg-gradient-to-br from-violet-500 to-indigo-600 text-white">
          <Sparkles className="size-4" />
        </div>
        <div className="mr-auto">
          <h1 className="text-sm font-semibold leading-none">DocuMind</h1>
          <p className="text-xs text-muted-foreground">Ask questions about your documents</p>
        </div>

        <Button variant="ghost" size="sm" className="h-8 gap-1.5" onClick={newChat} disabled={empty && !busy}>
          <Plus className="size-4" />
          <span className="hidden sm:inline">New chat</span>
        </Button>
        <ThemeToggle />
      </header>

      {/* Messages */}
      <div className="relative flex-1 overflow-hidden">
        <div ref={scrollRef} onScroll={onScroll} className="h-full overflow-y-auto">
          {empty ? (
            <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center gap-6 px-6 text-center">
              <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/15 to-indigo-600/15 text-primary">
                <Sparkles className="size-7" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Ask your documents anything</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Answers are grounded in your indexed files — and it says so when it doesn&apos;t know.
                </p>
              </div>
              <div className="grid w-full gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-lg border border-border bg-card/50 px-3 py-2.5 text-left text-sm transition-colors hover:border-foreground/20 hover:bg-accent"
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

        {/* Scroll-to-bottom button, shown only when scrolled up */}
        {!empty && !atBottom && (
          <Button
            size="icon"
            variant="secondary"
            onClick={scrollToBottom}
            className="absolute bottom-4 left-1/2 size-9 -translate-x-1/2 rounded-full shadow-md"
            title="Scroll to bottom"
          >
            <ArrowDown className="size-4" />
          </Button>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-border p-4">
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-border bg-card/50 p-2 shadow-sm focus-within:ring-1 focus-within:ring-ring">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder="Ask about your documents…  (Enter to send, Shift+Enter for newline)"
            rows={1}
            className="max-h-40 min-h-0 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
          />
          {busy ? (
            <Button size="icon" variant="secondary" onClick={() => abortRef.current?.abort()} title="Stop">
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
