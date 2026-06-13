/**
 * api.ts — the bridge between the Next.js UI and the FastAPI DocuMind backend.
 *
 * The interesting part is `streamAsk`. The backend returns a STREAMING text body
 * (token by token). Instead of awaiting the whole response, we read the body as a
 * ReadableStream and decode chunks as they arrive, calling `onToken` for each one.
 * That's what produces the live "typing" effect in the UI — the same UX you see in
 * ChatGPT/Claude. This is the front-end half of the StreamingResponse you built in
 * documind/api/app.py.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SourceDoc = { source: string; chunks: number };

/** Fetch the list of documents the backend has indexed. */
export async function getSources(): Promise<SourceDoc[]> {
  const res = await fetch(`${API_URL}/sources`);
  if (!res.ok) throw new Error(`Failed to load sources (${res.status})`);
  const data = await res.json();
  return data.documents as SourceDoc[];
}

/**
 * Stream an answer for `question`. Calls `onToken` for every chunk of text the
 * backend emits. Pass `signal` to allow cancelling an in-flight request.
 */
export async function streamAsk(
  question: string,
  sessionId: string,
  onToken: (chunk: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`Request failed (${res.status})`);
  }

  // res.body is a ReadableStream of bytes. Decode it to text chunk-by-chunk.
  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onToken(decoder.decode(value, { stream: true }));
  }
}
