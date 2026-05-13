import { useCallback } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import { RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { API_URL, CHATKIT_DOMAIN_KEY } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function ChatKitPanel({ onRefreshHistory }: { onRefreshHistory: () => void }) {
  const { token } = useAuth();

  const authenticatedFetch = useCallback(
    (input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      if (token) headers.set("Authorization", `Bearer ${token}`);
      return fetch(input, { ...init, headers });
    },
    [token],
  );

  const chatkit = useChatKit({
    api: {
      url: `${API_URL}/chatkit`,
      domainKey: CHATKIT_DOMAIN_KEY,
      fetch: authenticatedFetch,
    },
  });

  return (
    <Card className="flex h-full flex-col overflow-hidden border-none bg-transparent shadow-none">
      <CardHeader className="flex-none flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between pb-4 px-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Sparkles className="h-5 w-5" />
            Liquid AI Chatbot
          </CardTitle>
        </div>
        <Button type="button" variant="outline" className="rounded-full bg-white hover:bg-slate-100 border-slate-200 text-slate-700 shadow-sm transition-all" onClick={onRefreshHistory}>
          <RefreshCw className="h-4 w-4" />
          Refresh history
        </Button>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col p-0">
        <div className="flex-1 overflow-hidden rounded-xl border-none bg-white shadow-none">
          <ChatKit control={chatkit.control} className="h-full w-full" />
        </div>
      </CardContent>
    </Card>
  );
}
