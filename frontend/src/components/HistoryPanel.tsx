import { useCallback, useEffect, useMemo, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { MessagesSquare, RefreshCw, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Message, ThreadSummary, apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

type HistoryPanelProps = {
  refreshSignal: number;
};

export function HistoryPanel({ refreshSignal }: HistoryPanelProps) {
  const { token } = useAuth();
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === selectedThreadId) ?? null,
    [selectedThreadId, threads],
  );

  const loadThreads = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ThreadSummary[]>("/api/threads", token);
      setThreads(data);
      if (!selectedThreadId && data.length > 0) {
        setSelectedThreadId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load history");
    } finally {
      setLoading(false);
    }
  }, [selectedThreadId, token]);

  const loadMessages = useCallback(async (threadId: string) => {
    if (!token) return;
    setError(null);
    try {
      const data = await apiFetch<Message[]>(`/api/threads/${threadId}/messages`, token);
      setMessages(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load messages");
    }
  }, [token]);

  useEffect(() => {
    void loadThreads();
  }, [loadThreads, refreshSignal]);

  useEffect(() => {
    if (selectedThreadId) {
      void loadMessages(selectedThreadId);
    } else {
      setMessages([]);
    }
  }, [loadMessages, selectedThreadId, refreshSignal]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadThreads();
      if (selectedThreadId) void loadMessages(selectedThreadId);
    }, 12000);
    return () => window.clearInterval(interval);
  }, [loadMessages, loadThreads, selectedThreadId]);

  const deleteThread = async (threadId: string) => {
    if (!token) return;
    await apiFetch<void>(`/api/threads/${threadId}`, token, { method: "DELETE" });
    setThreads((current) => current.filter((thread) => thread.id !== threadId));
    if (selectedThreadId === threadId) {
      setSelectedThreadId(null);
      setMessages([]);
    }
  };

  return (
    <Card className="flex h-full flex-col overflow-hidden border-none bg-transparent shadow-none">
      <CardHeader className="flex-none space-y-3 pb-4 px-2">
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <MessagesSquare className="h-5 w-5" />
              Chat history
            </CardTitle>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={() => void loadThreads()} aria-label="Reload history">
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </Button>
        </div>
        {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col pt-0 px-2">
        <div className="flex-1 space-y-2 overflow-y-auto pr-2">
          {threads.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-500">
              No conversations yet. Start a chat and refresh this panel.
            </div>
          ) : (
            threads.map((thread) => (
              <div
                key={thread.id}
                className={cn(
                  "w-full rounded-full px-4 py-2 transition-all duration-200 flex items-center justify-between group",
                  selectedThreadId === thread.id ? "bg-[#D3E3FD] text-slate-900 font-medium" : "bg-transparent text-slate-700 hover:bg-[#E1E5EA]",
                )}
              >
                <button
                  type="button"
                  onClick={() => setSelectedThreadId(thread.id)}
                  className="flex-1 min-w-0 text-left"
                >
                  <p className="truncate text-sm text-slate-800">{thread.title || "Untitled chat"}</p>
                </button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 rounded-full opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-red-600 hover:bg-red-50"
                  onClick={(e) => {
                    e.stopPropagation();
                    void deleteThread(thread.id);
                  }}
                  aria-label="Delete chat"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))
          )}
        </div>


      </CardContent>
    </Card>
  );
}
