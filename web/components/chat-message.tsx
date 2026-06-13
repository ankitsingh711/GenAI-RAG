"use client";

import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

export type Role = "user" | "assistant";
export type ChatMessage = { id: string; role: Role; content: string };

/** A single chat bubble. Assistant answers render as markdown; user text is plain. */
export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex w-full gap-3 px-4 py-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
        )}
      >
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-muted text-foreground rounded-tl-sm",
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
          // `prose` gives nice typography to the markdown; tuned for our bubble.
          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1.5 prose-pre:my-2 prose-ul:my-1.5">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        ) : (
          // Empty assistant content == waiting for the first token: show a pulse.
          <span className="inline-flex gap-1">
            <span className="size-2 animate-bounce rounded-full bg-foreground/40 [animation-delay:-0.3s]" />
            <span className="size-2 animate-bounce rounded-full bg-foreground/40 [animation-delay:-0.15s]" />
            <span className="size-2 animate-bounce rounded-full bg-foreground/40" />
          </span>
        )}
      </div>
    </div>
  );
}
