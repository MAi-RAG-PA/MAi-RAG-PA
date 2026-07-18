//* frontend/src/api/websocket.ts
/**
 * WebSocket client for MAi-RAG-PA real-time updates.
 * Auto-reconnects with exponential backoff.
 */

type MessageHandler = (data: any) => void;

class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private intentionalClose = false;

  constructor(url?: string) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = url || `${protocol}//${window.location.host}/ws`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.intentionalClose = false;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WS] Connected');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type = data.type || 'unknown';

          // Notify type-specific handlers
          const typeHandlers = this.handlers.get(type) || [];
          typeHandlers.forEach((handler) => handler(data));

          // Notify wildcard handlers
          const wildcardHandlers = this.handlers.get('*') || [];
          wildcardHandlers.forEach((handler) => handler(data));
        } catch (err) {
          console.error('[WS] Failed to parse message:', err);
        }
      };

      this.ws.onclose = () => {
        console.log('[WS] Disconnected');
        if (!this.intentionalClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        console.error('[WS] Error:', err);
      };
    } catch (err) {
      console.error('[WS] Connection failed:', err);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[WS] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => this.connect(), delay);
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.ws?.close();
    this.ws = null;
  }

  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.handlers.get(type);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) handlers.splice(index, 1);
      }
    };
  }

  send(message: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[WS] Cannot send - not connected');
    }
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Singleton instance
export const wsClient = new WSClient();
