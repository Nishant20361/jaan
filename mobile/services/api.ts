/**
 * API Client for Jaan AI Mobile Application
 */

export interface MessageItem {
  id: string | number;
  role: 'user' | 'companion' | 'system';
  content: string;
  timestamp?: string;
  media_uri?: string;
  media_type?: 'photo' | 'sticker' | 'gif';
  is_unsent?: boolean;
}

export interface ChatResponse {
  response: string;
  source: string;
  model: string;
  retrieved_chunks: number[];
  timestamp: string;
}

export interface MemoryStats {
  total_messages: number;
  total_chunks: number;
  companion_name: string;
  date_range: { earliest?: string; latest?: string };
  top_emojis: string[];
  key_phrases: string[];
  total_photos: number;
  total_stickers: number;
  total_gifs: number;
}

export interface MediaItem {
  uri: string;
  url: string;
  filename: string;
  timestamp?: number;
}

export interface MemoryNote {
  id: number;
  title: string;
  content: string;
  tag: string;
  created_at: string;
}

class ApiService {
  private baseUrl: string = 'http://localhost:8000';

  constructor() {
    // Check if running on Android Emulator where localhost is 10.0.2.2
    // User can customize baseUrl anytime in Settings screen
  }

  public setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/$/, '');
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/health`, { method: 'GET' });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  public async sendMessage(
    message: string,
    sessionId: string = 'default',
    model?: string,
    temperature?: number
  ): Promise<ChatResponse> {
    try {
      const res = await fetch(`${this.baseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          model,
          temperature,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.warn('API error, using local companion fallback:', err);
      // Graceful offline companion fallback in authentic Hinglish style
      return this.getLocalFallback(message);
    }
  }

  public async getMemoryStats(): Promise<MemoryStats | null> {
    try {
      const res = await fetch(`${this.baseUrl}/api/memories/stats`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return null;
  }

  public async getChunks(page: number = 1, pageSize: number = 10, query?: string) {
    try {
      const url = query
        ? `${this.baseUrl}/api/memories/chunks?page=${page}&page_size=${pageSize}&query=${encodeURIComponent(query)}`
        : `${this.baseUrl}/api/memories/chunks?page=${page}&page_size=${pageSize}`;
      const res = await fetch(url);
      if (res.ok) return await res.json();
    } catch (e) {}
    return { chunks: [], total: 0 };
  }

  public async searchMessages(query: string, limit: number = 40) {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/memories/search?q=${encodeURIComponent(query)}&limit=${limit}`
      );
      if (res.ok) return await res.json();
    } catch (e) {}
    return { results: [], count: 0 };
  }

  public async getPhotos(): Promise<MediaItem[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/media/photos`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return [];
  }

  public async getStickers(): Promise<MediaItem[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/media/stickers`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return [];
  }

  public async getGifs(): Promise<MediaItem[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/media/gifs`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return [];
  }

  public async getNotes(): Promise<MemoryNote[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/memories/notes`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return [];
  }

  public async addNote(title: string, content: string, tag: string = 'general'): Promise<MemoryNote | null> {
    try {
      const res = await fetch(`${this.baseUrl}/api/memories/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, tag }),
      });
      if (res.ok) return await res.json();
    } catch (e) {}
    return null;
  }

  public async deleteNote(id: number): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/memories/notes/${id}`, {
        method: 'DELETE',
      });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  public async clearHistory(sessionId: string = 'default'): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/chat/history?session_id=${sessionId}`, {
        method: 'DELETE',
      });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  public async getSettings() {
    try {
      const res = await fetch(`${this.baseUrl}/api/settings`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return null;
  }

  public async updateSettings(settings: any) {
    try {
      const res = await fetch(`${this.baseUrl}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) return await res.json();
    } catch (e) {}
    return null;
  }

  private getLocalFallback(msg: string): ChatResponse {
    const q = msg.toLowerCase();
    let text = "Kuch nhi jaan 😂 tum batao kya chal raha hai?";
    if (q.includes("khana") || q.includes("lunch") || q.includes("dinner")) {
      text = "Haan ji jaan humne kha liya 🥰 tumne khaya ki nahi? Sach bolna!";
    } else if (q.includes("love") || q.includes("pyar") || q.includes("miss") || q.includes("yaad")) {
      text = "I love you too mra jaan! Bht bht sara ❤️😘 call karo na jab free ho!";
    } else if (q.includes("kaha") || q.includes("kha ho")) {
      text = "Ghar pe hi hain jaan 🥰 tum kaha ho? Theek ho na?";
    } else if (q.includes("hi") || q.includes("hello") || q.includes("hlo")) {
      text = "Hlo jaan! ❤️ bolo na kya hua?";
    }
    return {
      response: text,
      source: "offline_companion_engine",
      model: "local-jaan",
      retrieved_chunks: [],
      timestamp: new Date().toISOString(),
    };
  }
}

export const api = new ApiService();

