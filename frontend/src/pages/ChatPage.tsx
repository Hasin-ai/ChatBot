import { useState } from "react";
import { LogOut, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChatKitPanel } from "@/components/ChatKitPanel";
import { HistoryPanel } from "@/components/HistoryPanel";
import { useAuth } from "@/lib/auth-context";

export function ChatPage() {
  const { user, logout } = useAuth();
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <main className="flex h-screen flex-row bg-white overflow-hidden font-sans text-slate-900">
      
      {/* Sidebar */}
      <div 
        className={`flex flex-col bg-[#F0F4F9] transition-all duration-300 ease-in-out ${isSidebarOpen ? "w-[300px] p-4" : "w-[68px] p-4 items-center"}`}
      >
        <div className={`flex ${isSidebarOpen ? "justify-start" : "justify-center"} items-center mb-6`}>
          <Button variant="ghost" size="icon" className="rounded-full hover:bg-[#E1E5EA] text-slate-600" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
             <Menu className="h-6 w-6" />
          </Button>
        </div>
        
        <div className={`flex-1 overflow-hidden min-h-0 ${!isSidebarOpen ? "hidden" : "block"}`}>
          <HistoryPanel refreshSignal={refreshSignal} />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex w-full flex-1 flex-col min-w-0">
        <header className="flex-none flex items-center justify-between p-4 h-16">
          <div className="flex items-center gap-2">
            {/* Space for title if needed */}
          </div>
          <div className="flex items-center gap-4">
             <div className="text-sm font-medium text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full">
               {user?.name ?? "Student"}
             </div>
             <Button type="button" variant="ghost" className="rounded-full hover:bg-slate-100 text-slate-600 transition-all font-medium" onClick={logout}>
               <LogOut className="h-4 w-4 mr-2" />
               Sign out
             </Button>
          </div>
        </header>

        <div className="flex-1 flex min-h-0">
          <div className="flex-1 h-full mx-auto max-w-5xl px-4 md:px-8 pb-4">
            <ChatKitPanel onRefreshHistory={() => setRefreshSignal((value) => value + 1)} />
          </div>
        </div>
      </div>
    </main>
  );
}
