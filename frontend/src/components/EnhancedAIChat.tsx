import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, Paperclip, Mic, Plus, Settings, Brain, MessageSquare, FileText, Calendar, BarChart3,
  Search, Filter, Archive, Star, Clock, Zap, Target, TrendingUp, Sparkles, Wand2,
  Bot, User, ChevronDown, MoreHorizontal, Edit3, Trash2, Pin, Copy, Share2,
  Moon, Sun, Palette, Volume2, VolumeX, Maximize2, Minimize2, ChevronLeft, ChevronRight
} from 'lucide-react';
import { ApiService } from '../services/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: string;
  metadata?: any;
}

interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  messageCount: number;
  category: 'therapy' | 'planning' | 'general' | 'work';
  isPinned: boolean;
  isStarred: boolean;
  tags: string[];
}

const EnhancedAIChat: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'chat' | 'notion' | 'planning' | 'analytics'>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([
    { 
      id: '1', 
      title: 'Engineering Exam Stress', 
      lastMessage: 'That level of stress sounds overwhelming...', 
      timestamp: '2 hours ago',
      messageCount: 24,
      category: 'therapy',
      isPinned: true,
      isStarred: false,
      tags: ['stress', 'exams', 'engineering']
    },
    { 
      id: '2', 
      title: 'Career Path Discussion', 
      lastMessage: 'What draws you to literature?', 
      timestamp: 'Yesterday',
      messageCount: 18,
      category: 'planning',
      isPinned: false,
      isStarred: true,
      tags: ['career', 'literature', 'future']
    },
    { 
      id: '3', 
      title: 'Social Confidence Building', 
      lastMessage: 'Has this preference for solitude...', 
      timestamp: '3 days ago',
      messageCount: 31,
      category: 'therapy',
      isPinned: false,
      isStarred: false,
      tags: ['social', 'confidence', 'anxiety']
    },
    { 
      id: '4', 
      title: 'Study Schedule Optimization', 
      lastMessage: 'Let me help you create a better routine...', 
      timestamp: '1 week ago',
      messageCount: 12,
      category: 'planning',
      isPinned: false,
      isStarred: false,
      tags: ['study', 'schedule', 'productivity']
    }
  ]);
  const [currentSessionId, setCurrentSessionId] = useState('1');
  const [isTyping, setIsTyping] = useState(false);
  const [notionPages, setNotionPages] = useState<any[]>([]);
  const [notionLoading, setNotionLoading] = useState(false);
  const [notionError, setNotionError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Filter chat sessions based on search and category
  const filteredSessions = chatSessions.filter(session => {
    const matchesSearch = session.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         session.lastMessage.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         session.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesCategory = selectedCategory === 'all' || session.category === selectedCategory;
    return matchesSearch && matchesCategory;
  }).sort((a, b) => {
    // Sort by pinned first, then by timestamp
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  // Toggle session pin status
  const togglePin = (sessionId: string) => {
    setChatSessions(prev => prev.map(session => 
      session.id === sessionId ? { ...session, isPinned: !session.isPinned } : session
    ));
  };

  // Toggle session star status
  const toggleStar = (sessionId: string) => {
    setChatSessions(prev => prev.map(session => 
      session.id === sessionId ? { ...session, isStarred: !session.isStarred } : session
    ));
  };

  // Delete session
  const deleteSession = (sessionId: string) => {
    setChatSessions(prev => prev.filter(session => session.id !== sessionId));
    if (currentSessionId === sessionId) {
      const remainingSessions = chatSessions.filter(s => s.id !== sessionId);
      if (remainingSessions.length > 0) {
        setCurrentSessionId(remainingSessions[0].id);
      } else {
        // Create new session if no sessions left
        const newSessionId = Date.now().toString();
        setCurrentSessionId(newSessionId);
        setMessages([]);
      }
    }
  };

  // Get category color
  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'therapy': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'planning': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'work': return 'bg-green-100 text-green-700 border-green-200';
      case 'general': return 'bg-gray-100 text-gray-700 border-gray-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  // Fetch Notion pages
  const fetchNotionPages = async () => {
    setNotionLoading(true);
    setNotionError(null);
    try {
      const response = await ApiService.getRecentNotionPages();
      if (response.success) {
        setNotionPages(response.data.results || []);
      } else {
        setNotionError(response.message || 'Failed to fetch Notion pages');
      }
    } catch (error) {
      setNotionError('Error connecting to Notion. Please check your API configuration.');
      console.error('Notion fetch error:', error);
    } finally {
      setNotionLoading(false);
    }
  };

  // Create new Notion page
  const createNotionPage = async (title: string, content: string = '') => {
    try {
      const response = await ApiService.createNotionPage({ title, content });
      if (response.success) {
        // Refresh the pages list
        await fetchNotionPages();
        return true;
      } else {
        setNotionError(response.message || 'Failed to create page');
        return false;
      }
    } catch (error) {
      setNotionError('Error creating Notion page');
      console.error('Notion create error:', error);
      return false;
    }
  };

  // Load Notion data when Notion tab is selected
  useEffect(() => {
    if (activeTab === 'notion') {
      fetchNotionPages();
    }
  }, [activeTab]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      sender: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    const messageContent = inputMessage;
    setInputMessage('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageContent,
          session_id: currentSessionId
        })
      });

      const data = await response.json();
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        sender: 'ai',
        timestamp: data.timestamp,
        metadata: data.metadata
      };

      setMessages(prev => [...prev, aiMessage]);
      
      // Update session with new message
      setChatSessions(prev => prev.map(session => 
        session.id === currentSessionId 
          ? { 
              ...session, 
              lastMessage: data.response.substring(0, 50) + '...', 
              timestamp: 'Just now',
              messageCount: session.messageCount + 2
            } 
          : session
      ));
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleQuickAction = async (action: string) => {
    let endpoint = '';
    let payload = {};
    let actionName = '';

    switch (action) {
      case 'create-task':
        endpoint = '/api/mcp/notion/create-page';
        payload = { title: 'New Task', content: 'Task created from AI chat' };
        actionName = 'Task Created';
        break;
      case 'schedule':
        endpoint = '/api/mcp/schedule';
        payload = { date: new Date().toISOString().split('T')[0] };
        actionName = 'Schedule Updated';
        break;
      case 'plan-goal':
        endpoint = '/api/mcp/plan-tasks';
        payload = { goal: 'Goal from AI chat', max_steps: 5 };
        actionName = 'Goal Planned';
        break;
      case 'analyze':
        actionName = 'Analysis Complete';
        break;
      default:
        return;
    }

    try {
      if (endpoint) {
        const response = await fetch(`http://localhost:8000${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        console.log(`${action} result:`, data);
      }
      
      // Add system message about the action
      const systemMessage: Message = {
        id: Date.now().toString(),
        content: `${actionName} - Action completed successfully! The AI assistant has processed your request.`,
        sender: 'ai',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, systemMessage]);
    } catch (error) {
      console.error(`Error with ${action}:`, error);
    }
  };

  const TabButton = ({ tab, icon: Icon, label }: { tab: string, icon: any, label: string }) => (
    <Button
      variant={activeTab === tab ? 'default' : 'ghost'}
      onClick={() => setActiveTab(tab as any)}
      className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all duration-300 ${
        activeTab === tab 
          ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/25 scale-105' 
          : 'text-gray-600 hover:bg-gray-100 hover:scale-105'
      }`}
    >
      <Icon size={20} />
      <span className="font-medium">{label}</span>
    </Button>
  );

  const renderChatTab = () => (
    <TooltipProvider>
      <div className="flex h-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        {/* Enhanced Chat Sidebar */}
        <div className={`${sidebarCollapsed ? 'w-16' : 'w-80'} bg-white/80 backdrop-blur-xl border-r border-gray-200/50 transition-all duration-300 flex flex-col`}>
          {/* Sidebar Header */}
          <div className="p-4 border-b border-gray-200/50">
            <div className="flex items-center justify-between mb-4">
              {!sidebarCollapsed && (
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-white" />
                  </div>
                  <span className="font-semibold text-gray-800">Conversations</span>
                </div>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
              </Button>
            </div>
            
            {!sidebarCollapsed && (
              <>
                <Button 
                  onClick={() => {
                    const newSessionId = Date.now().toString();
                    setCurrentSessionId(newSessionId);
                    setMessages([]);
                  }}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-xl shadow-lg shadow-blue-500/25 transition-all duration-300 hover:scale-105"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  New Conversation
                </Button>
                
                {/* Search and Filter */}
                <div className="mt-4 space-y-2">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                    <Input
                      placeholder="Search conversations..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 bg-gray-50/50 border-gray-200/50 rounded-lg"
                    />
                  </div>
                  
                  <div className="flex gap-1 flex-wrap">
                    {['all', 'therapy', 'planning', 'work', 'general'].map(category => (
                      <Button
                        key={category}
                        variant={selectedCategory === category ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setSelectedCategory(category)}
                        className={`text-xs px-2 py-1 rounded-lg ${
                          selectedCategory === category 
                            ? 'bg-blue-100 text-blue-700 border border-blue-200' 
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        {category.charAt(0).toUpperCase() + category.slice(1)}
                      </Button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Chat Sessions List */}
          {!sidebarCollapsed && (
            <ScrollArea className="flex-1 px-4">
              <div className="space-y-2 py-2">
                {filteredSessions.map(session => (
                  <Card
                    key={session.id}
                    className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                      currentSessionId === session.id 
                        ? 'bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200 shadow-md' 
                        : 'bg-white/50 hover:bg-white/80'
                    }`}
                    onClick={() => setCurrentSessionId(session.id)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {session.isPinned && <Pin className="w-3 h-3 text-blue-600" />}
                            {session.isStarred && <Star className="w-3 h-3 text-yellow-500 fill-current" />}
                            <Badge className={`text-xs ${getCategoryColor(session.category)}`}>
                              {session.category}
                            </Badge>
                          </div>
                          <h4 className="font-medium text-sm truncate text-gray-800">{session.title}</h4>
                          <p className="text-xs text-gray-500 truncate mt-1">{session.lastMessage}</p>
                          <div className="flex items-center justify-between mt-2">
                            <span className="text-xs text-gray-400">{session.timestamp}</span>
                            <div className="flex items-center gap-1">
                              <MessageSquare className="w-3 h-3 text-gray-400" />
                              <span className="text-xs text-gray-400">{session.messageCount}</span>
                            </div>
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="p-1 h-6 w-6">
                              <MoreHorizontal className="w-3 h-3" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => togglePin(session.id)}>
                              <Pin className="w-4 h-4 mr-2" />
                              {session.isPinned ? 'Unpin' : 'Pin'}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleStar(session.id)}>
                              <Star className="w-4 h-4 mr-2" />
                              {session.isStarred ? 'Unstar' : 'Star'}
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Edit3 className="w-4 h-4 mr-2" />
                              Rename
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Copy className="w-4 h-4 mr-2" />
                              Copy Link
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => deleteSession(session.id)} className="text-red-600">
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col bg-white/50 backdrop-blur-sm">
          {/* Chat Header */}
          <div className="p-4 border-b border-gray-200/50 bg-white/80 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Avatar className="w-8 h-8">
                  <AvatarImage src="/ai-avatar.png" />
                  <AvatarFallback className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                    <Bot className="w-4 h-4" />
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h3 className="font-semibold text-gray-800">AI Assistant</h3>
                  <p className="text-xs text-gray-500">
                    {isTyping ? 'Typing...' : 'Online'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <Share2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Share conversation</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <Settings className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Settings</TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-6">
              {messages.map(message => (
                <div
                  key={message.id}
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex items-start gap-3 max-w-2xl ${message.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                    <Avatar className="w-8 h-8 flex-shrink-0">
                      {message.sender === 'user' ? (
                        <AvatarFallback className="bg-gradient-to-r from-green-500 to-blue-500 text-white">
                          <User className="w-4 h-4" />
                        </AvatarFallback>
                      ) : (
                        <AvatarFallback className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                          <Bot className="w-4 h-4" />
                        </AvatarFallback>
                      )}
                    </Avatar>
                    <div
                      className={`px-4 py-3 rounded-2xl shadow-sm ${
                        message.sender === 'user'
                          ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                          : 'bg-white border border-gray-200'
                      }`}
                    >
                      <div className="text-sm leading-relaxed">{message.content}</div>
                      <div className={`text-xs mt-2 ${message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex items-start gap-3">
                    <Avatar className="w-8 h-8">
                      <AvatarFallback className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                        <Bot className="w-4 h-4" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl shadow-sm">
                      <div className="flex items-center gap-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                        </div>
                        <span className="text-sm text-gray-600">AI is thinking...</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="p-4 border-t border-gray-200/50 bg-white/80 backdrop-blur-xl">
            <div className="flex items-end gap-3 mb-3">
              <div className="flex-1 relative">
                <Input
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                  placeholder="Type your message..."
                  className="pr-12 py-3 rounded-xl border-gray-200 focus:border-blue-500 focus:ring-blue-500/20"
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="sm" className="p-1 h-8 w-8">
                        <Paperclip className="w-4 h-4 text-gray-400" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Attach file</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="sm" className="p-1 h-8 w-8">
                        <Mic className="w-4 h-4 text-gray-400" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Voice message</TooltipContent>
                  </Tooltip>
                </div>
              </div>
              <Button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-xl shadow-lg shadow-blue-500/25 transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>

            {/* Quick Actions */}
            <Card className="bg-gradient-to-r from-gray-50 to-blue-50 border-gray-200/50">
              <CardContent className="p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  <span className="text-sm font-medium text-gray-700">Quick Actions</span>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button
                    onClick={() => handleQuickAction('create-task')}
                    variant="outline"
                    size="sm"
                    className="bg-white/50 hover:bg-white border-green-200 text-green-700 hover:text-green-800 rounded-full"
                  >
                    <Target className="w-3 h-3 mr-1" />
                    Create Task
                  </Button>
                  <Button
                    onClick={() => handleQuickAction('schedule')}
                    variant="outline"
                    size="sm"
                    className="bg-white/50 hover:bg-white border-blue-200 text-blue-700 hover:text-blue-800 rounded-full"
                  >
                    <Calendar className="w-3 h-3 mr-1" />
                    Schedule
                  </Button>
                  <Button
                    onClick={() => handleQuickAction('plan-goal')}
                    variant="outline"
                    size="sm"
                    className="bg-white/50 hover:bg-white border-purple-200 text-purple-700 hover:text-purple-800 rounded-full"
                  >
                    <Zap className="w-3 h-3 mr-1" />
                    Set Goal
                  </Button>
                  <Button
                    onClick={() => handleQuickAction('analyze')}
                    variant="outline"
                    size="sm"
                    className="bg-white/50 hover:bg-white border-orange-200 text-orange-700 hover:text-orange-800 rounded-full"
                  >
                    <TrendingUp className="w-3 h-3 mr-1" />
                    Analyze
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );

  const renderNotionTab = () => (
    <div className="p-6 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 h-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          Notion Integration
        </h2>
        <Button
          onClick={fetchNotionPages}
          disabled={notionLoading}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-xl shadow-lg shadow-blue-500/25"
        >
          {notionLoading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>

      {/* Error Message */}
      {notionError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-red-800 font-medium">Notion Connection Error</div>
          <div className="text-red-600 text-sm mt-1">{notionError}</div>
          <div className="text-red-500 text-xs mt-2">
            Make sure your NOTION_API_KEY and NOTION_DEFAULT_DATABASE_ID are configured in the backend.
            <br />Using Weekly Schedule database: {process.env.REACT_APP_NOTION_DB_ID || 'Weekly-Schedule-27592a42a75380d2aa27c92bbab00483'}
          </div>
        </div>
      )}

      {/* Action Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Card className="cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105 bg-white/80 backdrop-blur-sm border-gray-200/50">
          <CardContent 
            className="p-6 text-left"
            onClick={() => createNotionPage('New Task', 'Task created from AI Assistant')}
          >
            <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center mb-4">
              <Plus className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Create New Page</h3>
            <p className="text-sm text-gray-600">Start a new document or task</p>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105 bg-white/80 backdrop-blur-sm border-gray-200/50">
          <CardContent 
            className="p-6 text-left"
            onClick={fetchNotionPages}
          >
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center mb-4">
              <Search className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Query Database</h3>
            <p className="text-sm text-gray-600">Search your existing content</p>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105 bg-white/80 backdrop-blur-sm border-gray-200/50">
          <CardContent className="p-6 text-left">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mb-4">
              <Edit3 className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Update Existing</h3>
            <p className="text-sm text-gray-600">Modify current pages</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Pages */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold mb-4">Recent Pages:</h3>
        {notionLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-gray-600">Loading Notion pages...</span>
          </div>
        ) : notionPages.length > 0 ? (
          <div className="space-y-3">
            {notionPages.map((page, index) => {
              const title = page.properties?.Name?.title?.[0]?.text?.content || 
                           page.properties?.title?.title?.[0]?.text?.content || 
                           `Page ${index + 1}`;
              const lastEdited = page.last_edited_time ? 
                new Date(page.last_edited_time).toLocaleDateString() : 'Unknown';
              
              return (
                <Card key={page.id} className="cursor-pointer transition-all duration-200 hover:shadow-md bg-white/80 backdrop-blur-sm border-gray-200/50">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                          <FileText className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <div className="font-medium text-gray-800">{title}</div>
                          <div className="text-sm text-gray-600">Updated {lastEdited}</div>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-xs text-gray-400">
                        {page.id.substring(0, 8)}...
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <Card className="bg-white/50 backdrop-blur-sm border-gray-200/50">
            <CardContent className="text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-r from-gray-400 to-gray-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-white" />
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">No Notion pages found</h3>
              <p className="text-sm text-gray-600">Create your first page or check your Notion configuration</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Quick Templates */}
      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Wand2 className="w-5 h-5 text-purple-600" />
          Quick Templates
        </h3>
        <div className="grid grid-cols-3 gap-3">
          {[
            { name: 'Journal Entry', icon: Edit3, content: 'Today I want to reflect on...', color: 'from-blue-500 to-cyan-500' },
            { name: 'Task List', icon: Target, content: 'Tasks to complete:\n- \n- \n-', color: 'from-green-500 to-emerald-500' },
            { name: 'Goal Setting', icon: Zap, content: 'My goals for this week:\n1. \n2. \n3.', color: 'from-purple-500 to-pink-500' },
            { name: 'Study Plan', icon: Calendar, content: 'Study schedule:\n- Morning: \n- Afternoon: \n- Evening:', color: 'from-orange-500 to-red-500' },
            { name: 'Ideas', icon: Sparkles, content: 'Ideas to explore:\n- \n- \n-', color: 'from-yellow-500 to-orange-500' },
            { name: 'Progress Tracker', icon: TrendingUp, content: 'Progress tracking:\n- Completed: \n- In Progress: \n- Next Steps:', color: 'from-indigo-500 to-purple-500' }
          ].map(template => (
            <Card
              key={template.name}
              className="cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105 bg-white/80 backdrop-blur-sm border-gray-200/50"
              onClick={() => createNotionPage(template.name, template.content)}
            >
              <CardContent className="p-4 text-center">
                <div className={`w-10 h-10 bg-gradient-to-r ${template.color} rounded-xl flex items-center justify-center mx-auto mb-3`}>
                  <template.icon className="w-5 h-5 text-white" />
                </div>
                <h4 className="font-medium text-sm text-gray-800">{template.name}</h4>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );

  const renderPlanningTab = () => (
    <div className="p-6 bg-gradient-to-br from-slate-50 via-green-50 to-emerald-50 h-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg flex items-center justify-center">
            <Calendar className="w-4 h-4 text-white" />
          </div>
          Smart Planning & Scheduling
        </h2>
      </div>
      
      {/* Action Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Card className="cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105 bg-white/80 backdrop-blur-sm border-gray-200/50">
          <CardContent className="p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Target className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Plan Tasks</h3>
            <p className="text-sm text-gray-600">Break down your goals into actionable steps</p>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105 bg-white/80 backdrop-blur-sm border-gray-200/50">
          <CardContent className="p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Calendar className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">View Schedule</h3>
            <p className="text-sm text-gray-600">See your timeline and upcoming events</p>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105 bg-white/80 backdrop-blur-sm border-gray-200/50">
          <CardContent className="p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Plus className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Add Event</h3>
            <p className="text-sm text-gray-600">Schedule new activities and meetings</p>
          </CardContent>
        </Card>
      </div>

      {/* Current Goals */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-blue-600" />
          Current Goals
        </h3>
        <Card className="bg-white/80 backdrop-blur-sm border-gray-200/50">
          <CardContent className="p-6">
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                    <Target className="w-4 h-4 text-white" />
                  </div>
                  <span className="font-semibold text-gray-800">Prepare for Engineering Exam</span>
                </div>
                <Badge className="bg-green-100 text-green-700 border-green-200">67% complete</Badge>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div className="bg-gradient-to-r from-green-500 to-emerald-500 h-3 rounded-full transition-all duration-500" style={{ width: '67%' }}></div>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                <input type="checkbox" checked className="rounded text-green-600" />
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-gradient-to-r from-blue-400 to-blue-500 rounded-lg flex items-center justify-center">
                    <Calendar className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-sm line-through text-gray-500">Complete Math Revision (3 days)</span>
                </div>
              </div>
              <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                <input type="checkbox" className="rounded text-green-600" />
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-gradient-to-r from-purple-400 to-purple-500 rounded-lg flex items-center justify-center">
                    <Zap className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-sm text-gray-700">Physics Practice Tests (2 days)</span>
                </div>
              </div>
              <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                <input type="checkbox" className="rounded text-green-600" />
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-gradient-to-r from-orange-400 to-orange-500 rounded-lg flex items-center justify-center">
                    <Edit3 className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-sm text-gray-700">Mock Exams (1 day)</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Today's Schedule */}
      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-green-600" />
          Today's Schedule
        </h3>
        <div className="space-y-2">
          {[
            { time: '9:00 AM - 10:00 AM', status: 'Available', color: 'from-green-400 to-green-500' },
            { time: '11:00 AM - 12:00 PM', status: 'Available', color: 'from-blue-400 to-blue-500' },
            { time: '2:00 PM - 3:00 PM', status: 'Available', color: 'from-purple-400 to-purple-500' },
            { time: '4:00 PM - 5:00 PM', status: 'Available', color: 'from-orange-400 to-orange-500' }
          ].map((slot, index) => (
            <Card key={index} className="cursor-pointer transition-all duration-200 hover:shadow-md bg-white/80 backdrop-blur-sm border-gray-200/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 bg-gradient-to-r ${slot.color} rounded-lg flex items-center justify-center`}>
                    <Clock className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-800">{slot.time}</div>
                    <div className="text-sm text-gray-600">{slot.status}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );

  const renderAnalyticsTab = () => (
    <div className="p-6 bg-gradient-to-br from-slate-50 via-purple-50 to-pink-50 h-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          Progress Analytics & Insights
        </h2>
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Card className="bg-white/80 backdrop-blur-sm border-gray-200/50 hover:shadow-lg transition-all duration-300">
          <CardContent className="p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <MessageSquare className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Chat Stats</h3>
            <div className="text-3xl font-bold text-blue-600 mb-1">45</div>
            <div className="text-sm text-gray-600 mb-1">messages</div>
            <Badge className="bg-green-100 text-green-700 border-green-200 text-xs">3 insights</Badge>
          </CardContent>
        </Card>
        <Card className="bg-white/80 backdrop-blur-sm border-gray-200/50 hover:shadow-lg transition-all duration-300">
          <CardContent className="p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Notion Stats</h3>
            <div className="text-3xl font-bold text-green-600 mb-1">12</div>
            <div className="text-sm text-gray-600 mb-1">pages</div>
            <Badge className="bg-green-100 text-green-700 border-green-200 text-xs">8 tasks done</Badge>
          </CardContent>
        </Card>
        <Card className="bg-white/80 backdrop-blur-sm border-gray-200/50 hover:shadow-lg transition-all duration-300">
          <CardContent className="p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Target className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Goal Progress</h3>
            <div className="text-3xl font-bold text-purple-600 mb-1">67%</div>
            <div className="text-sm text-gray-600">complete</div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Insights */}
      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-600" />
          Recent Insights
        </h3>
        <div className="space-y-3">
          <Card className="bg-white/80 backdrop-blur-sm border-gray-200/50 hover:shadow-md transition-all duration-200">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="font-medium text-gray-800">"You seem to work best in morning sessions"</div>
                  <div className="text-sm text-gray-600 mt-1">Based on your activity patterns</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white/80 backdrop-blur-sm border-gray-200/50 hover:shadow-md transition-all duration-200">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="font-medium text-gray-800">"Literature interests align with communication skills"</div>
                  <div className="text-sm text-gray-600 mt-1">Consider exploring related career paths</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white/80 backdrop-blur-sm border-gray-200/50 hover:shadow-md transition-all duration-200">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Target className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="font-medium text-gray-800">"Consider breaking large goals into smaller steps"</div>
                  <div className="text-sm text-gray-600 mt-1">This improves completion rates by 40%</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  return (
    <TooltipProvider>
      <div className="h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex flex-col">
        {/* Enhanced Header */}
        <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">Universal AI Assistant</h1>
                <p className="text-xs text-gray-500">Intelligent conversations & productivity</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" className="p-2 hover:bg-gray-100 rounded-lg">
                    <Sun className="w-4 h-4 text-gray-600" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Toggle theme</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" className="p-2 hover:bg-gray-100 rounded-lg">
                    <Settings className="w-4 h-4 text-gray-600" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Settings</TooltipContent>
              </Tooltip>
            </div>
          </div>
        </header>

        {/* Enhanced Tab Navigation */}
        <nav className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 p-4 shadow-sm">
          <div className="flex gap-2 justify-center">
            <TabButton tab="chat" icon={MessageSquare} label="Chat" />
            <TabButton tab="notion" icon={FileText} label="Notion" />
            <TabButton tab="planning" icon={Calendar} label="Planning" />
            <TabButton tab="analytics" icon={BarChart3} label="Analytics" />
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 overflow-hidden">
          {activeTab === 'chat' && renderChatTab()}
          {activeTab === 'notion' && renderNotionTab()}
          {activeTab === 'planning' && renderPlanningTab()}
          {activeTab === 'analytics' && renderAnalyticsTab()}
        </main>
      </div>
    </TooltipProvider>
  );
};

export default EnhancedAIChat;
