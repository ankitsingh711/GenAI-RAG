"use client";

import { useEffect, useState } from "react";
import { FileText, Database, RefreshCw } from "lucide-react";

import { getSources, type SourceDoc } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

/** The inner content of the knowledge-base panel — reused on desktop and mobile. */
export function SourcesContent() {
  const [docs, setDocs] = useState<SourceDoc[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    setDocs(null);
    try {
      setDocs(await getSources());
    } catch {
      setError("Can't reach the backend. Is it running on :8000?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  const totalChunks = docs?.reduce((sum, d) => sum + d.chunks, 0) ?? 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-1">
        <Database className="size-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">Knowledge base</h2>
        <Button variant="ghost" size="icon" className="ml-auto size-7" onClick={load} title="Refresh">
          <RefreshCw className="size-3.5" />
        </Button>
      </div>
      <p className="mt-1 px-1 text-xs text-muted-foreground">
        {docs ? `${docs.length} document(s) · ${totalChunks} chunks indexed` : "Loading…"}
      </p>

      <div className="mt-4 flex flex-1 flex-col gap-2 overflow-y-auto">
        {error && <p className="px-1 text-xs text-destructive">{error}</p>}

        {!docs && !error &&
          [0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}

        {docs?.length === 0 && (
          <p className="px-1 text-xs text-muted-foreground">
            No documents indexed. Run lesson 04 to ingest some.
          </p>
        )}

        {docs?.map((doc) => (
          <div
            key={doc.source}
            className="flex items-center gap-3 rounded-lg border border-border bg-background/60 p-3 transition-colors hover:border-foreground/20"
          >
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-sm" title={doc.source}>
              {doc.source}
            </span>
            <Badge variant="secondary" className="ml-auto shrink-0">
              {doc.chunks}
            </Badge>
          </div>
        ))}
      </div>

      <div className="mt-auto px-1 pt-4 text-[11px] text-muted-foreground">
        Answers are grounded in these documents only. DocuMind says “I don’t know” when the
        answer isn’t here.
      </div>
    </div>
  );
}

/** Desktop sidebar (hidden on small screens; mobile uses a Sheet — see chat.tsx). */
export function SourcesPanel() {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-border bg-card/40 p-4 md:block">
      <SourcesContent />
    </aside>
  );
}
