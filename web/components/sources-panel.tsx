"use client";

import { useEffect, useRef, useState } from "react";
import { Database, FileText, Loader2, RefreshCw, Trash2, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { deleteDocument, getSources, uploadDocument, type SourceDoc } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const ACCEPT = ".pdf,.txt,.md";

/** The inner content of the knowledge-base panel — reused on desktop and mobile. */
export function SourcesContent() {
  const [docs, setDocs] = useState<SourceDoc[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function load() {
    setError(null);
    try {
      setDocs(await getSources());
    } catch {
      setError("Can't reach the backend. Is it running on :8000?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        const result = await uploadDocument(file);
        toast.success(`Indexed “${result.source}” (${result.chunks} chunks)`);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : `Failed to upload ${file.name}`);
      }
    }
    setUploading(false);
    await load();
  }

  async function remove(source: string) {
    try {
      await deleteDocument(source);
      toast.success(`Removed “${source}”`);
      await load();
    } catch {
      toast.error(`Couldn't remove ${source}`);
    }
  }

  const totalChunks = docs?.reduce((sum, d) => sum + d.chunks, 0) ?? 0;

  return (
    <div
      className="flex h-full flex-col"
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
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

      {/* Upload control + dropzone */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = ""; // allow re-selecting the same file
        }}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className={cn(
          "mt-3 flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-border px-3 py-4 text-center text-xs transition-colors",
          "hover:border-foreground/30 hover:bg-accent/50 disabled:opacity-60",
          dragOver && "border-primary bg-primary/10",
        )}
      >
        {uploading ? (
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        ) : (
          <UploadCloud className="size-5 text-muted-foreground" />
        )}
        <span className="font-medium">{uploading ? "Indexing…" : "Drop a file or click to upload"}</span>
        <span className="text-muted-foreground">PDF, TXT, or MD · max 10 MB</span>
      </button>

      <div className="mt-3 flex flex-1 flex-col gap-2 overflow-y-auto">
        {error && <p className="px-1 text-xs text-destructive">{error}</p>}

        {!docs && !error &&
          [0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}

        {docs?.length === 0 && (
          <p className="px-1 text-xs text-muted-foreground">
            No documents yet — upload one above to start asking questions.
          </p>
        )}

        {docs?.map((doc) => (
          <div
            key={doc.source}
            className="group flex items-center gap-3 rounded-lg border border-border bg-background/60 p-3 transition-colors hover:border-foreground/20"
          >
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-sm" title={doc.source}>
              {doc.source}
            </span>
            <Badge variant="secondary" className="ml-auto shrink-0">
              {doc.chunks}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              className="size-6 shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
              onClick={() => remove(doc.source)}
              title={`Remove ${doc.source}`}
            >
              <Trash2 className="size-3.5" />
            </Button>
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
