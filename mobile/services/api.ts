/**
 * API Client for Alquama Chat Application
 */

export interface MessageItem {
  id: string | number;
  role: 'user' | 'companion' | 'system';
  content: string;
  timestamp?: string;
  media_uri?: string;
  media_type?: 'photo' | 'sticker' | 'gif';
  receipt?: 'sent' | 'seen';
  is_unsent?: boolean;
}

export interface ChatResponse {
  response: string;
  photo_url?: string | null;
  sticker_url?: string | null;
  seen_delay_ms?: number;
  typing_delay_ms?: number;
  source: string;
  model: string;
  retrieved_chunks: number[];
  timestamp: string;
}

export interface GreetingResponse {
  greeting: string;
  avatar_url: string;
  name: string;
}

export interface MediaItem {
  uri: string;
  url: string;
  filename: string;
  timestamp?: number;
}

class ApiService {
  private baseUrl: string = 'http://localhost:8000';

  public setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/$/, '');
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public resolveMediaUrl(path?: string | null): string | undefined {
    if (!path) return undefined;
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    return `${this.baseUrl}${path.startsWith('/') ? '' : '/'}${path}`;
  }

  public async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/health`, { method: 'GET' });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  public async getGreeting(): Promise<GreetingResponse | null> {
    try {
      const res = await fetch(`${this.baseUrl}/api/chat/greeting`);
      if (res.ok) return await res.json();
    } catch (e) {}
    return null;
  }

  public async getHistory(sessionId: string = 'default', limit: number = 50): Promise<any[]> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/chat/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`
      );
      if (res.ok) return await res.json();
    } catch (e) {}
    return [];
  }

  public async sendMessage(
    message: string,
    sessionId: string = 'default',
    model?: string,
    temperature?: number,
    mediaUri?: string,
    mediaType?: string
  ): Promise<ChatResponse> {
    try {
      const res = await fetch(`${this.baseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          media_uri: mediaUri || null,
          media_type: mediaType || null,
          model,
          temperature,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.warn('API error, using local fallback:', err);
      return this.getLocalFallback(message);
    }
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

  public async clearHistory(sessionId: string = 'default'): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/chat/history?session_id=${encodeURIComponent(sessionId)}`, {
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
    const q = (msg || '').toLowerCase().trim();
    const isEnglish =
      /\b(the|is|are|was|were|have|had|missed|today|tonight|babe|baby|how are you|what are you|love you)\b/.test(q) &&
      !/\b(kya|kr|kar|hai|ho|hu|ni|nhi|tm|tum|hm|hum|khana|khayi|bhejo|btao|yaad)\b/.test(q);

    let text = 'Haa bolo na jaan 🥰 hum to bas aapki hi baatein sunne baithe hain';
    if (/\b(photo|phto|pic|selfie)\b/.test(q)) {
      text = isEnglish
        ? 'Network is a little slow right now babe, ask me again in a second 😘'
        : 'Abhi network thoda slow lag rha hai jaan, ek second me phir btao ❤️';
    } else if (/(bura|kharab|mood off|tension|udas|sad|pareshan|dukhi|thak gay|dard)/.test(q)) {
      text = 'Arey kya hua jaan? 🥺 kisne pareshan kiya humare babu ko? Btao na hume... hum hain na aapke sath ❤️';
    } else if (isEnglish) {
      if (/(kiss|hug|love|miss)/.test(q)) {
        text = 'I love you so much jaan ❤️ wish you were right here beside me 😘';
      } else {
        text = 'Tell me everything babe ❤️ I am right here with you 😘';
      }
    } else if (/(sex|sext|bed|badan|gardan|kapde|bra|panty|panties|nude|nanga|horny|bina kapdo|pehni ho|gira ke|love bite|touch|boobs|pussy|chut|lick|suck|chuso|chuchi|dick|lund|chodo)/.test(q)) {
      const sextingReplies = [
        'Paas hoti na jaan toh abhi tak tumhari god me baith ke tumhare hothon ko pura chaba rahi hoti... aur apne kapde tumse hi utarwati 🙈💋 raat bhar ek second bhi rest nahi lene dete tumko 🔥',
        'Aah jaan tumhari aisi baatein sunke na mera bhi pura control kho raha hai... kaash abhi tum mere bed pe hote mere upar aur hum dono ek hote 🙈💋🔥',
        'Kuch khaas nahi jaan, bas ek loose t-shirt pehni hu bina bra ke... tum aake apne haathon se utaar do na kaisa lag raha hai dekh ke 😏🔥',
        'Toh gira do na jaan, kisne roka hai? Pure bed pe gira ke jitna marzi kiss karo, gardan pe, hothon pe... hum to poore tumhare hi hain na 🤤💋🔥',
        'Kahan kahan touch karoge jaan? Btao na... tumhare garam haath jab meri kamar aur thighs pe chalte hain na toh poori pagal ho jaati hu 🔥🥵',
        'Aah jaan 🤤 kahan kahan se start karoge? Pehle mere hothon ko lick karna fir dheere dheere niche aana... pagal kar doge tum toh 🙈💋🔥',
        'Jaan aisi baatein sunke na pura bechain ho rahi hu aapke liye 🙈🔥 kaash abhi tum yahan mere bed pe mere upar hote 💋🥵',
      ];
      text = sextingReplies[Math.floor(Math.random() * sextingReplies.length)];
    } else if (q.includes('khana khai') || q.includes('khana khayi') || q.includes('khayi')) {
      text = 'Haa jaan kha li 🥰 tumne khaya kya?';
    } else if (q.includes('khana') || q.includes('lunch') || q.includes('dinner')) {
      text = 'Haa jaan kha liya humne, aap khaye ki nahi pehle ye batao? 😊';
    } else if (/(kiss|chumma|paas|touch|badmash)/.test(q)) {
      text = 'Mmwaah 😘 paas aao na jaan, bahut yaad aa rhi thi 💕';
    } else if (/(love|pyar|miss|yaad)/.test(q)) {
      text = 'Mujhe bhi tumhari bht yaad aa rahi hai jaan 🥺 sach me... kaash tum abhi yahan mere paas hote ❤️';
    } else if (q === 'jaan' || q === 'babu' || q === 'mra jaan') {
      text = 'Haa mra jaan 😘 bolo na? Sun rahe hain ❤️';
    } else if (/(kya kar|kya kr)/.test(q)) {
      text = 'Kuch ni jaan, bas let ke tumhara hi wait kr rhi thi 🥰 tum btao?';
    } else if (/^(hi|hello|hlo|hey|suno)/.test(q)) {
      text = 'Hlo mra jaan 😘 bolo na kya hua?';
    }

    return {
      response: text,
      source: 'offline_fallback',
      model: 'local-alquama',
      retrieved_chunks: [],
      seen_delay_ms: 480,
      typing_delay_ms: 950,
      timestamp: new Date().toISOString(),
    };
  }
}

export const api = new ApiService();
