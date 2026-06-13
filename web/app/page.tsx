import { Chat } from "@/components/chat";
import { SourcesPanel } from "@/components/sources-panel";

export default function Home() {
  return (
    <div className="flex h-dvh w-full overflow-hidden">
      <SourcesPanel />
      <main className="flex flex-1 flex-col overflow-hidden">
        <Chat />
      </main>
    </div>
  );
}
