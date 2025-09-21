import * as React from "react";
import { 
  Send, 
  Paperclip, 
  Moon, 
  Sun, 
  MessageSquare, 
  Plus, 
  Settings, 
  Trash2, 
  Edit3,
  MoreHorizontal,
  Bot,
  User,
  AudioLines
} from "lucide-react";
import { ChatWebSocketService, ApiService, generateSessionId, formatTimestamp } from "@/services/api";
import { NavLink } from "react-router-dom";
import { useTheme } from "next-themes";
import {
  SidebarProvider,
  SidebarTrigger,
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: string;
}

interface ChatHistory {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  isActive?: boolean;
}

// Theme Toggle Component
function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      className="transition-smooth hover:scale-105"
    >
      <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}

// Chat Message Component
interface ChatMessageProps {
  message: string;
  isUser: boolean;
  timestamp?: string;
}

function ChatMessage({ message, isUser, timestamp }: ChatMessageProps) {
  return (
    <div className={cn("flex gap-3 max-w-4xl mx-auto p-4", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
          <Bot className="h-4 w-4 text-primary-foreground" />
        </div>
      )}
      
      <div className={cn(
        "rounded-lg px-4 py-3 max-w-[70%] transition-smooth",
        isUser 
          ? "chat-message-user ml-auto" 
          : "chat-message-ai"
      )}>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message}</p>
        {timestamp && (
          <p className="text-xs opacity-70 mt-2">{timestamp}</p>
        )}
      </div>
      
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
          <User className="h-4 w-4 text-primary-foreground" />
        </div>
      )}
    </div>
  );
}

// App Sidebar Component
function AppSidebar() {
  const { state } = useSidebar();
  const isCollapsed = state === "collapsed";
  
  const mockChatHistory: ChatHistory[] = [
    {
      id: "1",
      title: "Current Chat",
      lastMessage: "Hello! I'm your AI assistant...",
      timestamp: "Just now",
      isActive: true,
    },
    {
      id: "2", 
      title: "Project Planning Discussion",
      lastMessage: "Let's break down the project requirements...",
      timestamp: "2 hours ago",
    },
    {
      id: "3",
      title: "Code Review Help",
      lastMessage: "Can you help me review this React component?",
      timestamp: "Yesterday",
    },
    {
      id: "4",
      title: "Database Design",
      lastMessage: "What's the best approach for user authentication?",
      timestamp: "2 days ago",
    },
  ];

  const [chatHistory, setChatHistory] = React.useState(mockChatHistory);

  const handleNewChat = () => {
    console.log("Creating new chat...");
  };

  const handleDeleteChat = (chatId: string) => {
    setChatHistory(prev => prev.filter(chat => chat.id !== chatId));
  };

  const handleRenameChat = (chatId: string) => {
    console.log("Renaming chat:", chatId);
  };

  return (
    <Sidebar className={cn(isCollapsed ? "w-14" : "w-72")} collapsible="icon">
      <SidebarContent className="flex flex-col h-full">
        {/* New Chat Button */}
        <div className="flex w-full py-3 px-3 border-b border-border justify-center">
          <Button 
            onClick={handleNewChat}
            className={cn(
              "w-full gap-2 transition-smooth items-center hover:scale-[0.98]", isCollapsed ? "h-9 w-9" : ""
            )}
            variant="outline"
          >
            <Plus className="h-5 w-5" />
            {!isCollapsed && <span>New Chat</span>}
          </Button>
        </div>

        {/* Chat History */}
        <SidebarGroup className="flex-1">
          <SidebarGroupLabel className="text-xs font-medium text-muted-foreground px-3">
            {!isCollapsed && "Recent Chats"}
          </SidebarGroupLabel>
          
          <SidebarGroupContent>
            <SidebarMenu>
              {chatHistory.map((chat) => (
                <SidebarMenuItem key={chat.id}>
                  <div className={cn(
                    "group flex items-center w-full rounded-md transition-smooth",
                    chat.isActive && "bg-black"
                  )}>
                    <SidebarMenuButton 
                      asChild 
                      className="flex-1 justify-start p-2 h-auto"
                    >
                      <NavLink 
                        to={`/chat/${chat.id}`} 
                        className="flex items-start gap-2 w-full"
                      >
                        <MessageSquare className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        {!isCollapsed && (
                          <div className="flex-1 min-w-0">
                            <p className={cn("text-sm font-medium truncate", chat.isActive && "text-white")}>
                              {chat.title}
                            </p>
                            <p className={cn("text-xs text-muted-foreground truncate", chat.isActive && "text-white")}>
                              {chat.lastMessage}
                            </p>
                            <p className={cn("text-xs text-muted-foreground mt-1", chat.isActive && "text-white")}>
                              {chat.timestamp}
                            </p>
                          </div>
                        )}
                      </NavLink>
                    </SidebarMenuButton>
                    
                    {!isCollapsed && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0 mr-2"
                          >
                            <MoreHorizontal className="h-3 w-3" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleRenameChat(chat.id)}>
                            <Edit3 className="h-3 w-3 mr-2" />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDeleteChat(chat.id)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-3 w-3 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Settings Section */}
        <SidebarFooter className="border-t border-border w-[100%]">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild>
                <NavLink 
                  to="/settings" 
                  className="flex justify-center gap-2 p-2 transition-smooth hover:bg-black hover:text-white rounded-md"
                >
                  <Settings className="h-4 w-4" />
                  {!isCollapsed && <span className="text-sm">Settings</span>}
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </SidebarContent>
    </Sidebar>
  );
}

// Main Chat Interface Component
function ChatInterface() {
  const [messages, setMessages] = React.useState<Message[]>([
    {
      id: "1",
      text: "Hello! I'm your AI assistant. How can I help you today?",
      isUser: false,
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [inputValue, setInputValue] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [isConnected, setIsConnected] = React.useState(false);
  const [sessionId] = React.useState(() => generateSessionId());
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const wsService = React.useRef<ChatWebSocketService | null>(null);

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize WebSocket connection
  React.useEffect(() => {
    const initializeWebSocket = async () => {
      try {
        // Check backend health first
        await ApiService.healthCheck();
        
        // Initialize WebSocket
        wsService.current = new ChatWebSocketService(sessionId);
        
        // Set up message handler
        wsService.current.onMessage((response) => {
          const aiMessage: Message = {
            id: Date.now().toString(),
            text: response.response,
            isUser: false,
            timestamp: formatTimestamp(response.timestamp)
          };
          setMessages(prev => [...prev, aiMessage]);
          setIsLoading(false);
        });

        // Set up connection handler
        wsService.current.onConnectionChange((connected) => {
          setIsConnected(connected);
        });

        // Connect
        await wsService.current.connect();
      } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
        setIsConnected(false);
      }
    };

    initializeWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsService.current) {
        wsService.current.disconnect();
      }
    };
  }, [sessionId]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      isUser: true,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    const messageText = inputValue;
    setInputValue("");
    setIsLoading(true);

    // Send message via WebSocket
    if (wsService.current && isConnected) {
      wsService.current.sendMessage(messageText);
    } else {
      // Fallback to REST API if WebSocket fails
      try {
        const response = await ApiService.sendChatMessage({
          message: messageText,
          session_id: sessionId
        });
        
        const aiMessage: Message = {
          id: Date.now().toString(),
          text: response.response,
          isUser: false,
          timestamp: formatTimestamp(response.timestamp)
        };
        setMessages(prev => [...prev, aiMessage]);
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to send message:', error);
        setIsLoading(false);
      }
    }
  };

  const handleVoiceInput = () => {
    console.log("Voice input activated!");
    // Implement voice input logic here
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileAttach = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      console.log("File selected:", file.name);
    }
  };

  return (
    <div className="flex flex-col h-screen chat-container">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className={cn("flex pb-0 justify-center")}>
            <SidebarTrigger size="lg" className={cn("w-full bg-background/80 backdrop-blur-sm border border-border shadow-sm hover:bg-accent transition-smooth h-9 w-9")} />
          </div>
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">AI</span>
          </div>
          <div>
            <h1 className="font-semibold text-lg">AI Chat Assistant</h1>
            <p className="text-xs text-muted-foreground">
              {isConnected ? "Connected to backend" : "Connecting..."}
            </p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      {/* Chat Messages */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 p-0">
        <div className="py-4">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message.text}
              isUser={message.isUser}
              timestamp={message.timestamp}
            />
          ))}
          
          {isLoading && (
            <div className="flex gap-3 max-w-4xl mx-auto p-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <div className="w-2 h-2 bg-primary-foreground rounded-full animate-pulse"></div>
              </div>
              <div className="chat-message-ai rounded-lg px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t border-border bg-card/50 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto">
          <div className="chat-input-container rounded-lg p-2 flex gap-2">
            <Button
              onClick={handleFileAttach}
              variant="ghost"
              size="icon"
              className="flex-shrink-0 transition-spring hover:scale-105"
            >
              <Paperclip className="h-4 w-4" />
            </Button>
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Type your message here..."
              className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
              disabled={isLoading}
            />
            
            <Button
              onClick={inputValue.trim() ? handleSendMessage : handleVoiceInput}
              disabled={isLoading || (!isConnected && !inputValue.trim())}
              size="icon"
              className="transition-spring hover:scale-105 disabled:hover:scale-100"
            >
              {inputValue.trim() ? (
                <Send className="h-4 w-4" />
              ) : (
                <AudioLines className="h-4 w-4" />
              )}
            </Button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.txt"
          />
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}

// Main AIChat Component (Layout + Interface)
export function AIChat() {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        
        <main className="flex-1">
          <ChatInterface />
        </main>
      </div>
    </SidebarProvider>
  );
}
