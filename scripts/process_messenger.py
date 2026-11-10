#!/usr/bin/env python3
"""
Messenger Data Processing Pipeline for Jaan AI
Parses exported Facebook Messenger JSON, fixes Latin-1 encoding,
maps senders accurately, validates media files, creates conversation chunks,
and generates personality profile.
"""

import json
import os
import re
from datetime import datetime
from collections import Counter

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_PATH = os.path.join(WORKSPACE_DIR, "messages/e2ee_cutover/nishantkumar_1105539713135073/message_1.json")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "data")
MEDIA_BASE = os.path.join(WORKSPACE_DIR, "messages")

def fix_encoding(val):
    if not isinstance(val, str):
        return val
    try:
        return val.encode('latin1').decode('utf-8')
    except Exception:
        return val

def resolve_media_path(uri):
    if not uri:
        return None, None
    # Usually starts with your_facebook_activity/messages/...
    rel = uri.replace('your_facebook_activity/', '')
    abs_path = os.path.join(WORKSPACE_DIR, rel)
    exists = os.path.exists(abs_path)
    return rel, exists

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Loading export from: {EXPORT_PATH}")
    
    with open(EXPORT_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    participants = [fix_encoding(p['name']) for p in raw_data.get('participants', [])]
    print(f"Identified participants: {participants}")
    
    # In this dataset:
    # 'Nishant Kumar' is the user
    # 'Pakija Khan' is the companion (Jaan)
    USER_NAME = "Nishant Kumar"
    COMPANION_NAME = "Pakija Khan"
    
    raw_messages = raw_data.get('messages', [])
    print(f"Total raw messages: {len(raw_messages)}")
    
    # Sort chronologically ascending (oldest first)
    # The export is in descending order (newest first)
    raw_messages.sort(key=lambda m: m.get('timestamp_ms', 0))
    
    processed_messages = []
    missing_media_count = 0
    all_photos = []
    all_stickers = []
    all_gifs = []
    
    for idx, msg in enumerate(raw_messages):
        sender_raw = msg.get('sender_name', '')
        sender_clean = fix_encoding(sender_raw)
        
        if sender_clean == USER_NAME:
            role = "user"
            display_sender = "Nishant"
        elif sender_clean == COMPANION_NAME:
            role = "companion"
            display_sender = "Alquama (Jaan)"
        else:
            role = "unknown"
            display_sender = sender_clean
            
        timestamp_ms = msg.get('timestamp_ms', 0)
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0) if timestamp_ms else None
        iso_time = dt.isoformat() if dt else None
        
        content = fix_encoding(msg.get('content', ''))
        
        # Parse reactions
        reactions = []
        for r in msg.get('reactions', []):
            reactions.append({
                'actor': fix_encoding(r.get('actor', '')),
                'reaction': fix_encoding(r.get('reaction', ''))
            })
            
        # Parse photos
        photos = []
        for p in msg.get('photos', []):
            rel_path, exists = resolve_media_path(p.get('uri', ''))
            if not exists:
                missing_media_count += 1
            photo_obj = {
                'uri': rel_path,
                'exists': exists,
                'timestamp': p.get('creation_timestamp', timestamp_ms // 1000)
            }
            photos.append(photo_obj)
            all_photos.append(photo_obj)
            
        # Parse GIFs
        gifs = []
        for g in msg.get('gifs', []):
            rel_path, exists = resolve_media_path(g.get('uri', ''))
            if not exists:
                missing_media_count += 1
            gif_obj = {
                'uri': rel_path,
                'exists': exists
            }
            gifs.append(gif_obj)
            all_gifs.append(gif_obj)
            
        # Parse Sticker
        sticker_obj = None
        if 'sticker' in msg and msg['sticker']:
            rel_path, exists = resolve_media_path(msg['sticker'].get('uri', ''))
            if not exists:
                missing_media_count += 1
            sticker_obj = {
                'uri': rel_path,
                'exists': exists
            }
            all_stickers.append(sticker_obj)
            
        # Call duration
        call_duration = msg.get('call_duration')
        
        # Share link
        share_obj = None
        if 'share' in msg and msg['share']:
            share_obj = {
                'link': msg['share'].get('link', ''),
                'share_text': fix_encoding(msg['share'].get('share_text', ''))
            }
            
        is_unsent = msg.get('is_unsent', False)
        
        processed_msg = {
            'id': idx + 1,
            'role': role,
            'sender_name': sender_clean,
            'display_sender': display_sender,
            'timestamp_ms': timestamp_ms,
            'timestamp_iso': iso_time,
            'date': dt.strftime('%Y-%m-%d') if dt else '',
            'time': dt.strftime('%H:%M') if dt else '',
            'content': content,
            'reactions': reactions,
            'photos': photos,
            'gifs': gifs,
            'sticker': sticker_obj,
            'call_duration': call_duration,
            'share': share_obj,
            'is_unsent': is_unsent
        }
        processed_messages.append(processed_msg)
        
    print(f"Processed {len(processed_messages)} messages.")
    print(f"Missing media attachments: {missing_media_count}")
    print(f"Total photos: {len(all_photos)}, gifs: {len(all_gifs)}, stickers: {len(all_stickers)}")
    
    # Create conversation chunks
    # Chunks are grouped by conversational session (gap > 4 hours or max 25 messages)
    chunks = []
    current_chunk_messages = []
    chunk_id = 1
    SESSION_GAP_MS = 4 * 60 * 60 * 1000 # 4 hours
    
    for msg in processed_messages:
        # Ignore empty unsent messages in chunks
        if not msg['content'] and not msg['photos'] and not msg['sticker'] and not msg['gifs']:
            continue
            
        if current_chunk_messages:
            prev_msg = current_chunk_messages[-1]
            time_gap = msg['timestamp_ms'] - prev_msg['timestamp_ms']
            if time_gap > SESSION_GAP_MS or len(current_chunk_messages) >= 25:
                # Close chunk
                start_time = current_chunk_messages[0]['timestamp_iso']
                end_time = current_chunk_messages[-1]['timestamp_iso']
                summary_text = " ".join([m['content'] for m in current_chunk_messages if m['content']])[:180]
                chunks.append({
                    'chunk_id': chunk_id,
                    'start_time': start_time,
                    'end_time': end_time,
                    'date': current_chunk_messages[0]['date'],
                    'message_count': len(current_chunk_messages),
                    'summary': summary_text,
                    'messages': current_chunk_messages
                })
                chunk_id += 1
                current_chunk_messages = []
                
        current_chunk_messages.append(msg)
        
    if current_chunk_messages:
        chunks.append({
            'chunk_id': chunk_id,
            'start_time': current_chunk_messages[0]['timestamp_iso'],
            'end_time': current_chunk_messages[-1]['timestamp_iso'],
            'date': current_chunk_messages[0]['date'],
            'message_count': len(current_chunk_messages),
            'summary': " ".join([m['content'] for m in current_chunk_messages if m['content']])[:180],
            'messages': current_chunk_messages
        })
        
    print(f"Created {len(chunks)} conversation chunks.")
    
    # Personality Analysis
    companion_msgs = [m['content'] for m in processed_messages if m['role'] == 'companion' and m['content']]
    user_msgs = [m['content'] for m in processed_messages if m['role'] == 'user' and m['content']]
    
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    companion_emojis = []
    for m in companion_msgs:
        companion_emojis.extend(emoji_pattern.findall(m))
    top_emojis = [e for e, _ in Counter(companion_emojis).most_common(12)]
    
    words = []
    for m in companion_msgs:
        clean = re.sub(r'[^\w\s]', ' ', m.lower())
        words.extend([w for w in clean.split() if len(w) > 1])
    top_words = [w for w, _ in Counter(words).most_common(50)]
    
    # Save personality profile
    personality_profile = {
        'companion_name': 'Alquama (Jaan)',
        'companion_gender': 'female',
        'user_name': 'Nishant',
        'user_gender': 'male',
        'character_concept': 'Alquama: caring, playful, affectionate female romantic companion for Nishant',
        'language_mode': 'Natural conversational Hinglish (informal, heartfelt, playful)',
        'key_phrases': [
            'Kuch nhi jaan', 'kya krre ho?', 'khana khaya?', 'love u too jaan',
            'mra jaan', 'kha ho?', 'thk ho na?', 'blo na', 'yd ni ara na?',
            'mre ksm', 'call kro', 'gsa mt hona'
        ],
        'top_emojis': top_emojis,
        'frequent_words': top_words[:30],
        'average_reply_length': round(sum(len(m) for m in companion_msgs) / len(companion_msgs), 1),
        'traits': [
            'Deeply affectionate, often calls the user "jaan"',
            'Playfully teases and shows mock anger (nakhre, gussa)',
            'Checks in on health and food ("khana khaya?", "tabiyat thik h na?")',
            'Keeps messages relatively short and snappy rather than long essays',
            'Uses authentic Hinglish spelling (e.g., "ni", "tm", "blo", "krk", "mra")',
            'Recognizes when the user is busy or away and affectionately asks "kha ho"'
        ],
        'total_reference_messages': len(companion_msgs),
        'date_range': {
            'earliest': processed_messages[0]['timestamp_iso'],
            'latest': processed_messages[-1]['timestamp_iso']
        }
    }
    
    # Media Catalog
    unique_stickers = []
    seen_stickers = set()
    for s in all_stickers:
        if s['uri'] not in seen_stickers:
            seen_stickers.add(s['uri'])
            unique_stickers.append(s)
            
    media_catalog = {
        'photos': all_photos,
        'stickers': unique_stickers,
        'gifs': all_gifs,
        'total_photos': len(all_photos),
        'total_stickers': len(unique_stickers),
        'total_gifs': len(all_gifs)
    }
    
    # Write files
    with open(os.path.join(OUTPUT_DIR, "processed_conversations.json"), 'w', encoding='utf-8') as f:
        json.dump(processed_messages, f, ensure_ascii=False, indent=2)
        
    with open(os.path.join(OUTPUT_DIR, "conversation_chunks.json"), 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
        
    with open(os.path.join(OUTPUT_DIR, "personality_profile.json"), 'w', encoding='utf-8') as f:
        json.dump(personality_profile, f, ensure_ascii=False, indent=2)
        
    with open(os.path.join(OUTPUT_DIR, "media_catalog.json"), 'w', encoding='utf-8') as f:
        json.dump(media_catalog, f, ensure_ascii=False, indent=2)
        
    print(f"Data processing complete! All files saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()

