# JAAN AI ❤️ — Premium 3D Romantic AI Companion

**Jaan AI** is a production-quality, Android-first mobile application and premium 3D romantic web experience. It features a fictional AI companion inspired by the conversational patterns, memories, authentic Hinglish expressions, and shared media from your exported Facebook Messenger history.

---

## 🌟 Key Highlights & Architecture

1. **AI Personality Engine & RAG Retrieval**
   - Learns authentic vocabulary from 1,813 real messages: `"jaan"`, `"mra jaan"`, `"tm"`, `"ni"`, `"blo"`, `"kha ho?"`, `"khana khaya?"`, `"love u too jaan"`, `"call kro"`, `"gsa mt hona"`.
   - Accurate sender mapping: **Nishant Kumar** = `user`, **Pakija Khan** = `companion` (Jaan).
   - Fixed Facebook's Latin-1 mojibake encoding for pristine emoji rendering (`😘`, `🥰`, `😂`, `🤪`, `😉`).
   - BM25 contextual retrieval across 84 conversation chunks and 1,813 messages.
   - Groq API integration supporting `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, and `mixtral-8x7b-32768`.
   - High-fidelity offline personality fallback engine so the app remains responsive even without an API key.

2. **Premium 3D Experience & UI**
   - Three.js WebGL 3D Heart with metallic shaders, pulsing heartbeat animation, dual rim lighting, and interactive 3D drag rotation.
   - 350+ orbiting starry glitter particles.
   - Deep midnight purple, vibrant neon pink, lavender, and glassmorphism.
   - Synthesized gentle audio chime on message receive via Web Audio API.

3. **Digital Memories Gallery ❤️**
   - Full search over all 1,813 real messages (2020 to 2023).
   - Photo Gallery featuring all 34 authentic shared photos with full-screen lightbox.
   - Sticker Gallery with all 26 authentic stickers from your chat.
   - User-defined memory notes (CRUD) stored persistently in SQLite.

4. **Android-First Mobile Application (Expo & React Native)**
   - Built with Expo SDK 51, React Native, TypeScript, Expo Router, Linear Gradient, Haptics, and Reanimated.
   - Strictly typed (`tsc --noEmit` passes with 0 errors).
   - App Name: **Jaan AI**
   - Package: `com.nishant.jaanai`
   - Linked EAS Project: `@nishant20361/jaan-ai` (ID: `405c0c43-5105-4436-babf-1e89ee3f0f1b`)
   - Preconfigured `eas.json` profiles for direct APK (`preview`) and Google Play Store (`production`).

---

## 🚀 How to Run the Live 3D Web Companion

The FastAPI backend server is already running on port **8000**!

1. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```
2. You will see:
   - The interactive 3D Heart beating in real-time.
   - "Start Chatting" button to enter the romantic chat.
   - Real-time conversation with Jaan in natural Hinglish.
   - Emoji drawer and Sticker drawer with authentic stickers.
   - "Memories & Media" gallery to search past messages and view photos.
   - "Settings" to select Groq models or enter your `GROQ_API_KEY`.

To restart the server at any time:
```bash
./bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## 📱 How to Run or Build the Android App

### 1. Run Mobile App in Expo Go / Development
Inside the `mobile/` directory:
```bash
cd mobile
../bin/pnpm start
```
Scan the QR code with the Expo Go app on your Android phone!

### 2. Generate the Android APK via EAS Build
The project is already initialized and linked to your Expo account (`@nishant20361/jaan-ai`):
```bash
cd mobile
./node_modules/.bin/eas build --platform android --profile preview
```
This triggers Expo's cloud build and generates a downloadable `.apk` file you can install directly on any Android phone!

For Google Play Store distribution (AAB):
```bash
cd mobile
./node_modules/.bin/eas build --platform android --profile production
```

---

## 🔒 Privacy & Safety Guarantee
- Your original Messenger export (`messages/`) remains 100% untouched.
- All messages and photos are served locally from your machine.
- The companion is explicitly framed as an AI companion inspired by memories, not pretending to be a living person messaging live.
