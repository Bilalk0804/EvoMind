// API service layer for AI Assistant
const RAW_API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '';
const RAW_WS_BASE_URL = (import.meta as any).env?.VITE_WS_BASE_URL || '';

function normalizeBaseUrl(url: string): string {
  if (!url) return '';
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

function deriveWsBaseUrlFromApi(apiBaseUrl: string): string {
  if (!apiBaseUrl) return '';
  const u = new URL(apiBaseUrl);
  const proto = u.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${u.host}`;
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
  timestamp: string;
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
      this.ws = new WebSocket(`${WS_BASE_URL}/ws/chat/${this.sessionId}`);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.connectionHandlers.forEach(handler => handler(true));
        resolve();
      };

      this.ws.onmessage = (event) => {
        const response: ChatResponse = JSON.parse(event.data);
        this.messageHandlers.forEach(handler => handler(response));
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.connectionHandlers.forEach(handler => handler(false));
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
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
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const base = API_BASE_URL || '';
    const url = `${base}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }

  // Health check
  static async healthCheck(): Promise<any> {
    return this.request('/health');
  }

  // Chat endpoint
  static async sendChatMessage(request: ChatMessage): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Session management
  static async getActiveSessions(): Promise<any> {
    return this.request('/api/sessions');
  }

  static async deleteSession(sessionId: string): Promise<any> {
    return this.request(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  static async getSessionAnalysis(sessionId: string): Promise<any> {
    return this.request(`/api/kg/${sessionId}`);
  }
}

// Utility functions
export const generateSessionId = (): string => {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleTimeString();
};
