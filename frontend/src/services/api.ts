// API service layer for Universal AI Assistant
const RAW_API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '';
const RAW_WS_BASE_URL = (import.meta as any).env?.VITE_WS_BASE_URL || '';

function normalizeBaseUrl(url: string): string {
  if (!url) return '';
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

function deriveWsBaseUrlFromApi(apiBaseUrl: string): string {
  if (!apiBaseUrl) return '';
  try {
    const u = new URL(apiBaseUrl);
    const proto = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${u.host}`;
  } catch {
    return '';
  }
}

const API_BASE_URL = normalizeBaseUrl(RAW_API_BASE_URL);
const WS_BASE_URL = normalizeBaseUrl(
  RAW_WS_BASE_URL || deriveWsBaseUrlFromApi(API_BASE_URL) || `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`
);

// Types
export interface ChatMessage {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  message_type: string;
  timestamp: string;
  metadata?: {
    qa_pairs_count: number;
    llm2_analyzing: boolean;
    has_insights: boolean;
  };
}

export interface TaskPlanRequest {
  goal: string;
  deadline?: string;
  max_steps?: number;
}

export interface NotionPageRequest {
  title: string;
  content?: string;
  database_id?: string;
}

export interface ScheduleRequest {
  date?: string;
}

export interface EventRequest {
  title: string;
  start: string;
  end: string;
  description?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

// WebSocket Chat Service
export class ChatWebSocketService {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private messageHandlers: ((message: ChatResponse) => void)[] = [];
  private connectionHandlers: ((connected: boolean) => void)[] = [];

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(`${WS_BASE_URL}/ws/chat/${this.sessionId}`);
        
        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.connectionHandlers.forEach(handler => handler(true));
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const response: ChatResponse = JSON.parse(event.data);
            this.messageHandlers.forEach(handler => handler(response));
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          this.connectionHandlers.forEach(handler => handler(false));
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  sendMessage(message: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ message }));
    } else {
      console.error('WebSocket not connected');
    }
  }

  onMessage(handler: (message: ChatResponse) => void): void {
    this.messageHandlers.push(handler);
  }

  onConnectionChange(handler: (connected: boolean) => void): void {
    this.connectionHandlers.push(handler);
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// REST API Service
export class ApiService {
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const base = API_BASE_URL || '';
    const url = `${base}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Health check
  static async healthCheck(): Promise<any> {
    return this.request('/health');
  }

  // Chat endpoints
  static async sendChatMessage(request: ChatMessage): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Session management
  static async getActiveSessions(): Promise<ApiResponse<any[]>> {
    return this.request<ApiResponse<any[]>>('/api/sessions');
  }

  static async deleteSession(sessionId: string): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  static async getSessionAnalysis(sessionId: string): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>(`/api/kg/sessions/${sessionId}`);
  }

  // MCP Tools endpoints
  static async planTasks(request: TaskPlanRequest): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>('/api/mcp/plan-tasks', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  static async getSchedule(request: ScheduleRequest): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>('/api/mcp/schedule', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  static async addEvent(request: EventRequest): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>('/api/mcp/add-event', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Notion endpoints
  static async createNotionPage(request: NotionPageRequest): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>('/api/mcp/notion/create-page', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  static async getRecentNotionPages(): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>('/api/mcp/notion/recent-pages');
  }

  static async queryNotionDatabase(databaseId?: string): Promise<ApiResponse<any>> {
    const params = databaseId ? `?database_id=${databaseId}` : '';
    return this.request<ApiResponse<any>>(`/api/mcp/notion/query-database${params}`);
  }
}

// Utility functions
export const generateSessionId = (): string => {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleTimeString();
};
