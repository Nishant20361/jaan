import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Image,
  Modal,
  Dimensions,
  Animated,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { api, MessageItem, MediaItem } from '../services/api';

const { width } = Dimensions.get('window');

const QUICK_EMOJIS = ['😘', '🥰', '😂', '🤪', '😉', '❤️', '💕', '💋', '🌹', '🥺', '😏', '🙈'];
const LOCAL_AVATAR_MODAL_KEY = '__LOCAL_ALQUAMA_DP__';
const LOCAL_CHAT_STORAGE_KEY = '@alquama_local_chat_history_v1';

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function ChatScreen() {
  const router = useRouter();
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showStickerPicker, setShowStickerPicker] = useState(false);
  const [availableStickers, setAvailableStickers] = useState<MediaItem[]>([]);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const flatListRef = useRef<FlatList>(null);
  const typingDot1 = useRef(new Animated.Value(0)).current;
  const typingDot2 = useRef(new Animated.Value(0)).current;
  const typingDot3 = useRef(new Animated.Value(0)).current;

  // Load offline phone storage history first, then sync server history + stickers
  useEffect(() => {
    let mounted = true;

    async function init() {
      // 1. Instantly load chats from local phone storage (offline first)
      try {
        const cachedLocal = await AsyncStorage.getItem(LOCAL_CHAT_STORAGE_KEY);
        if (cachedLocal && mounted) {
          const parsed = JSON.parse(cachedLocal);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setMessages(parsed);
          }
        }
      } catch (e) {
        console.log('[PhoneStorage] Error reading offline chat cache:', e);
      }

      api.getStickers().then((stickers) => {
        if (mounted) setAvailableStickers(stickers);
      });

      // 2. Fetch server history and persist to phone storage
      try {
        const history = await api.getHistory('default', 100);
        if (!mounted) return;

        if (history && history.length > 0) {
          let lastUserIdx = -1;
          history.forEach((m: any, idx: number) => {
            if (m.role === 'user') lastUserIdx = idx;
          });

          const formatted: MessageItem[] = [];
          history.forEach((m: any, idx: number) => {
            const timeStr = m.created_at
              ? new Date(m.created_at + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const role = m.role === 'user' ? 'user' : 'companion';
            const cleanContent = m.content === '[Sent Sticker]' ? '' : (m.content || '');
            const resolvedMedia = api.resolveMediaUrl(m.media_uri);
            const isLastAnsweredUser = idx === lastUserIdx && lastUserIdx < history.length - 1;

            if (m.media_type === 'sticker' && resolvedMedia && cleanContent) {
              formatted.push({
                id: `hist-${m.id}-txt`,
                role,
                content: cleanContent,
                timestamp: timeStr,
              });
              formatted.push({
                id: `hist-${m.id}-stk`,
                role,
                content: '',
                media_uri: resolvedMedia,
                media_type: 'sticker',
                timestamp: timeStr,
                receipt: isLastAnsweredUser ? 'seen' : undefined,
              });
            } else {
              formatted.push({
                id: `hist-${m.id}`,
                role,
                content: cleanContent,
                media_uri: resolvedMedia,
                media_type: m.media_type || undefined,
                timestamp: timeStr,
                receipt: isLastAnsweredUser ? 'seen' : undefined,
              });
            }
          });
          setMessages(formatted);
          AsyncStorage.setItem(LOCAL_CHAT_STORAGE_KEY, JSON.stringify(formatted)).catch(() => {});
          return;
        }
      } catch (e) {
        console.log('[PhoneStorage] Network offline, using local phone storage:', e);
      }

      // If no local and no server history, show initial greeting
      if (mounted) {
        setMessages((prev) => {
          if (prev.length > 0) return prev;
          return [{
            id: 'init-1',
            role: 'companion',
            content: 'Hlo jaan 😘 kya haal hai aaj?',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }];
        });
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, []);

  // Auto-save any new messages to phone local storage
  useEffect(() => {
    if (messages.length > 0) {
      AsyncStorage.setItem(LOCAL_CHAT_STORAGE_KEY, JSON.stringify(messages.slice(-150))).catch(() => {});
    }
  }, [messages]);

  // Typing dots animation
  useEffect(() => {
    if (isTyping) {
      const animateDot = (dot: Animated.Value, delay: number) => {
        return Animated.loop(
          Animated.sequence([
            Animated.delay(delay),
            Animated.timing(dot, {
              toValue: -6,
              duration: 340,
              useNativeDriver: true,
            }),
            Animated.timing(dot, {
              toValue: 0,
              duration: 340,
              useNativeDriver: true,
            }),
          ])
        );
      };
      const a1 = animateDot(typingDot1, 0);
      const a2 = animateDot(typingDot2, 170);
      const a3 = animateDot(typingDot3, 340);
      a1.start();
      a2.start();
      a3.start();

      return () => {
        a1.stop();
        a2.stop();
        a3.stop();
      };
    }
  }, [isTyping]);

  const handleSend = async (overrideText?: string, stickerRelativeUrl?: string) => {
    if (isSending) return;
    const textToSend = overrideText !== undefined ? overrideText : inputText.trim();
    if (!textToSend && !stickerRelativeUrl) return;

    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch (e) {}

    const userMsgId = `u-${Date.now()}`;
    const fullStickerUri = api.resolveMediaUrl(stickerRelativeUrl);
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: MessageItem = {
      id: userMsgId,
      role: 'user',
      content: textToSend,
      media_uri: fullStickerUri,
      media_type: fullStickerUri ? 'sticker' : undefined,
      receipt: 'sent',
      timestamp: nowTime,
    };

    // Strip old receipts and append new user message as "Sent ✓"
    setMessages((prev) => [
      ...prev.map((m) => (m.receipt ? { ...m, receipt: undefined } : m)),
      userMsg,
    ]);
    if (overrideText === undefined) setInputText('');
    setShowEmojiPicker(false);
    setShowStickerPicker(false);
    setIsSending(true);

    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 80);

    try {
      const query = textToSend || (stickerRelativeUrl ? '[Sent Sticker]' : 'Hlo');
      const fetchPromise = api.sendMessage(
        query,
        'default',
        undefined,
        undefined,
        stickerRelativeUrl || undefined,
        stickerRelativeUrl ? 'sticker' : undefined
      );

      // Simulate realistic reading pause -> "✓✓ Seen" -> "typing..."
      await sleep(480);
      setMessages((prev) =>
        prev.map((m) => (m.id === userMsgId ? { ...m, receipt: 'seen' } : m))
      );

      await sleep(360);
      setIsTyping(true);
      const typingStartedAt = Date.now();
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 60);

      const res = await fetchPromise;
      const minTypingMs = res.typing_delay_ms || 1100;
      const elapsed = Date.now() - typingStartedAt;
      if (elapsed < minTypingMs) {
        await sleep(minTypingMs - elapsed);
      }

      setIsTyping(false);
      const replyTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      if (res.photo_url) {
        const photoMsg: MessageItem = {
          id: `c-photo-${Date.now()}`,
          role: 'companion',
          content: res.response || '',
          media_uri: api.resolveMediaUrl(res.photo_url),
          media_type: 'photo',
          timestamp: replyTime,
        };
        setMessages((prev) => [...prev, photoMsg]);
      } else if (res.sticker_url) {
        if (res.response) {
          const textReply: MessageItem = {
            id: `c-txt-${Date.now()}`,
            role: 'companion',
            content: res.response,
            timestamp: replyTime,
          };
          setMessages((prev) => [...prev, textReply]);
          setIsTyping(true);
          await sleep(480);
          setIsTyping(false);
        }
        const stickerReply: MessageItem = {
          id: `c-stk-${Date.now() + 1}`,
          role: 'companion',
          content: '',
          media_uri: api.resolveMediaUrl(res.sticker_url),
          media_type: 'sticker',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, stickerReply]);
      } else {
        const textReply: MessageItem = {
          id: `c-txt-${Date.now()}`,
          role: 'companion',
          content: res.response,
          timestamp: replyTime,
        };
        setMessages((prev) => [...prev, textReply]);
      }

      try {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } catch (e) {}
    } catch (err) {
      console.error('Chat error:', err);
      setIsTyping(false);
    } finally {
      setIsTyping(false);
      setIsSending(false);
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  };

  const handleSendSticker = (sticker: MediaItem) => {
    handleSend('', sticker.url);
  };

  const renderMessageItem = ({ item }: { item: MessageItem }) => {
    const isUser = item.role === 'user';
    return (
      <View style={styles.messageGroup}>
        <View
          style={[
            styles.messageRow,
            isUser ? styles.messageRowUser : styles.messageRowCompanion,
          ]}
        >
          {!isUser && (
            <Image
              source={require('../assets/alquama_dp.jpg')}
              style={styles.bubbleAvatar}
            />
          )}

          <View style={styles.bubbleWrapper}>
            {item.media_uri && item.media_type === 'sticker' ? (
              <TouchableOpacity
                activeOpacity={0.9}
                onPress={() => setSelectedImage(item.media_uri || null)}
              >
                <Image
                  source={{ uri: item.media_uri }}
                  style={styles.stickerImage}
                  resizeMode="contain"
                />
                <Text
                  style={[
                    styles.timestampText,
                    isUser ? styles.timestampUser : styles.timestampCompanion,
                  ]}
                >
                  {item.timestamp}
                </Text>
              </TouchableOpacity>
            ) : item.media_uri && item.media_type === 'photo' ? (
              <LinearGradient
                colors={['#28133a', '#1a0b26']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={[styles.bubble, styles.bubbleCompanion, styles.photoBubble]}
              >
                <TouchableOpacity
                  activeOpacity={0.9}
                  onPress={() => setSelectedImage(item.media_uri || null)}
                >
                  <Image
                    source={{ uri: item.media_uri }}
                    style={styles.photoImage}
                    resizeMode="cover"
                  />
                </TouchableOpacity>
                {!!item.content && (
                  <Text style={[styles.messageText, styles.textCompanion, styles.photoCaption]}>
                    {item.content}
                  </Text>
                )}
                <Text style={[styles.timestampText, styles.timestampCompanion, { paddingHorizontal: 6, paddingBottom: 4 }]}>
                  {item.timestamp}
                </Text>
              </LinearGradient>
            ) : (
              <LinearGradient
                colors={isUser ? ['#ff3b88', '#d81b60'] : ['#28133a', '#1a0b26']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={[
                  styles.bubble,
                  isUser ? styles.bubbleUser : styles.bubbleCompanion,
                ]}
              >
                <Text
                  style={[
                    styles.messageText,
                    isUser ? styles.textUser : styles.textCompanion,
                  ]}
                >
                  {item.content}
                </Text>
                <Text
                  style={[
                    styles.timestampText,
                    isUser ? styles.timestampUser : styles.timestampCompanion,
                  ]}
                >
                  {item.timestamp}
                </Text>
              </LinearGradient>
            )}
          </View>
        </View>

        {isUser && item.receipt && (
          <Text
            style={[
              styles.receiptText,
              item.receipt === 'seen' && styles.receiptSeenText,
            ]}
          >
            {item.receipt === 'seen' ? '✓✓ Seen' : 'Sent ✓'}
          </Text>
        )}
      </View>
    );
  };

  return (
    <LinearGradient
      colors={['#140722', '#0d0614', '#08030c']}
      style={styles.container}
    >
      {/* Chat Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.headerIconButton}
          activeOpacity={0.7}
        >
          <Text style={styles.backArrow}>‹</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.headerProfile}
          activeOpacity={0.8}
          onPress={() => setSelectedImage(LOCAL_AVATAR_MODAL_KEY)}
        >
          <View style={styles.avatarMiniContainer}>
            <Image
              source={require('../assets/alquama_dp.jpg')}
              style={styles.avatarMini}
            />
            <View style={styles.miniOnlineDot} />
          </View>
          <View>
            <Text style={styles.headerTitle}>Alquama ❤️</Text>
            <Text style={[styles.headerSubtitle, isTyping && styles.headerSubtitleTyping]}>
              {isTyping ? 'typing...' : 'Online'}
            </Text>
          </View>
        </TouchableOpacity>

        <View style={styles.headerActions}>
          <TouchableOpacity
            onPress={() => router.push('/settings')}
            style={styles.headerActionBtn}
            activeOpacity={0.7}
          >
            <Text style={styles.headerActionIcon}>⚙️</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Messages List */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderMessageItem}
        contentContainerStyle={styles.listContent}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        ListFooterComponent={
          isTyping ? (
            <View style={styles.typingContainer}>
              <Image
                source={require('../assets/alquama_dp.jpg')}
                style={styles.bubbleAvatar}
              />
              <View style={styles.typingBubble}>
                <Animated.View
                  style={[styles.typingDot, { transform: [{ translateY: typingDot1 }] }]}
                />
                <Animated.View
                  style={[styles.typingDot, { transform: [{ translateY: typingDot2 }] }]}
                />
                <Animated.View
                  style={[styles.typingDot, { transform: [{ translateY: typingDot3 }] }]}
                />
              </View>
            </View>
          ) : null
        }
      />

      {/* Emoji Picker Drawer */}
      {showEmojiPicker && (
        <View style={styles.drawerContainer}>
          <View style={styles.drawerHeader}>
            <Text style={styles.drawerTitle}>Emojis</Text>
            <TouchableOpacity onPress={() => setShowEmojiPicker(false)}>
              <Text style={styles.drawerClose}>✕</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.emojiGrid}>
            {QUICK_EMOJIS.map((emoji) => (
              <TouchableOpacity
                key={emoji}
                style={styles.emojiBtn}
                onPress={() => {
                  setInputText((prev) => prev + emoji);
                  try {
                    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                  } catch (e) {}
                }}
              >
                <Text style={styles.emojiText}>{emoji}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Sticker Picker Drawer */}
      {showStickerPicker && (
        <View style={styles.drawerContainer}>
          <View style={styles.drawerHeader}>
            <Text style={styles.drawerTitle}>Stickers ❤️</Text>
            <TouchableOpacity onPress={() => setShowStickerPicker(false)}>
              <Text style={styles.drawerClose}>✕</Text>
            </TouchableOpacity>
          </View>
          <FlatList
            horizontal
            data={availableStickers}
            keyExtractor={(item) => item.uri}
            renderItem={({ item }) => {
              const fullUrl = api.resolveMediaUrl(item.url) || '';
              return (
                <TouchableOpacity
                  style={styles.stickerThumbBtn}
                  onPress={() => handleSendSticker(item)}
                >
                  <Image
                    source={{ uri: fullUrl }}
                    style={styles.stickerThumb}
                    resizeMode="contain"
                  />
                </TouchableOpacity>
              );
            }}
          />
        </View>
      )}

      {/* Input Bar */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.inputContainer}>
          <TouchableOpacity
            style={styles.toolBtn}
            onPress={() => {
              setShowEmojiPicker((prev) => !prev);
              setShowStickerPicker(false);
            }}
          >
            <Text style={styles.toolIcon}>😊</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.toolBtn}
            onPress={() => {
              setShowStickerPicker((prev) => !prev);
              setShowEmojiPicker(false);
            }}
          >
            <Text style={styles.toolIcon}>🎨</Text>
          </TouchableOpacity>

          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={setInputText}
            placeholder="Message..."
            placeholderTextColor="#89759c"
            multiline
            maxLength={1000}
          />

          <TouchableOpacity
            style={[
              styles.sendButton,
              (!inputText.trim() || isSending) && styles.sendButtonDisabled,
            ]}
            onPress={() => handleSend()}
            disabled={!inputText.trim() || isSending}
          >
            <LinearGradient
              colors={
                inputText.trim() && !isSending
                  ? ['#ff3b88', '#a824e8']
                  : ['#442354', '#2d143b']
              }
              style={styles.sendGradient}
            >
              <Text style={styles.sendIcon}>➤</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Full Screen Image Modal */}
      <Modal visible={!!selectedImage} transparent={true} animationType="fade">
        <View style={styles.modalBg}>
          <TouchableOpacity
            style={styles.modalCloseBtn}
            onPress={() => setSelectedImage(null)}
          >
            <Text style={styles.modalCloseText}>✕ Close</Text>
          </TouchableOpacity>
          {selectedImage === LOCAL_AVATAR_MODAL_KEY ? (
            <Image
              source={require('../assets/alquama_dp.jpg')}
              style={styles.modalImage}
              resizeMode="contain"
            />
          ) : selectedImage ? (
            <Image
              source={{ uri: selectedImage }}
              style={styles.modalImage}
              resizeMode="contain"
            />
          ) : null}
        </View>
      </Modal>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: Platform.OS === 'ios' ? 52 : 36,
    paddingBottom: 12,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(20, 7, 34, 0.85)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 90, 160, 0.2)',
  },
  headerIconButton: {
    width: 38,
    height: 38,
    justifyContent: 'center',
    alignItems: 'center',
  },
  backArrow: {
    fontSize: 34,
    color: '#ff80ab',
    fontWeight: '300',
    marginTop: -4,
  },
  headerProfile: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginLeft: 4,
  },
  avatarMiniContainer: {
    position: 'relative',
    marginRight: 10,
  },
  avatarMini: {
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 1.5,
    borderColor: '#ff3b88',
  },
  miniOnlineDot: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#00e676',
    borderWidth: 1.5,
    borderColor: '#140722',
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
  },
  headerSubtitle: {
    fontSize: 11,
    color: '#9ee8be',
    fontWeight: '500',
  },
  headerSubtitleTyping: {
    color: '#ff80ab',
    fontWeight: '600',
  },
  headerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  headerActionBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerActionIcon: {
    fontSize: 16,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  messageGroup: {
    marginVertical: 4,
  },
  messageRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowCompanion: {
    justifyContent: 'flex-start',
  },
  receiptText: {
    alignSelf: 'flex-end',
    fontSize: 10,
    color: 'rgba(215, 195, 240, 0.72)',
    marginTop: 3,
    paddingRight: 4,
  },
  receiptSeenText: {
    color: '#ff80ab',
    fontWeight: '600',
  },
  bubbleAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    marginRight: 8,
    marginBottom: 4,
  },
  bubbleWrapper: {
    maxWidth: width * 0.76,
  },
  bubble: {
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  bubbleUser: {
    borderBottomRightRadius: 4,
  },
  bubbleCompanion: {
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(255, 120, 180, 0.25)',
  },
  photoBubble: {
    padding: 5,
    paddingBottom: 6,
    overflow: 'hidden',
  },
  photoImage: {
    width: width * 0.62,
    height: width * 0.72,
    borderRadius: 14,
    backgroundColor: '#1d0b2e',
  },
  photoCaption: {
    paddingHorizontal: 6,
    paddingTop: 7,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  textUser: {
    color: '#ffffff',
  },
  textCompanion: {
    color: '#f0e6ff',
  },
  timestampText: {
    fontSize: 9.5,
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  timestampUser: {
    color: 'rgba(255, 255, 255, 0.75)',
  },
  timestampCompanion: {
    color: 'rgba(215, 195, 240, 0.65)',
  },
  stickerImage: {
    width: 126,
    height: 126,
  },
  typingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 8,
  },
  typingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(40, 19, 58, 0.9)',
    borderWidth: 1,
    borderColor: 'rgba(255, 90, 160, 0.3)',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 11,
  },
  typingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#ff80ab',
    marginHorizontal: 3,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: 'rgba(20, 7, 34, 0.95)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 90, 160, 0.2)',
  },
  toolBtn: {
    width: 36,
    height: 36,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 4,
  },
  toolIcon: {
    fontSize: 20,
  },
  textInput: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    color: '#ffffff',
    fontSize: 14.5,
    maxHeight: 90,
    marginRight: 8,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    overflow: 'hidden',
  },
  sendButtonDisabled: {
    opacity: 0.6,
  },
  sendGradient: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendIcon: {
    color: '#ffffff',
    fontSize: 16,
    marginLeft: 2,
  },
  drawerContainer: {
    backgroundColor: '#1d0b2e',
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 90, 160, 0.3)',
  },
  drawerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  drawerTitle: {
    color: '#ff80ab',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  drawerClose: {
    color: '#bfa7d9',
    fontSize: 14,
    paddingHorizontal: 4,
  },
  emojiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  emojiBtn: {
    width: '16%',
    paddingVertical: 6,
    alignItems: 'center',
  },
  emojiText: {
    fontSize: 26,
  },
  stickerThumbBtn: {
    marginRight: 10,
    padding: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
  },
  stickerThumb: {
    width: 64,
    height: 64,
  },
  modalBg: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.92)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalCloseBtn: {
    position: 'absolute',
    top: 50,
    right: 20,
    padding: 10,
    backgroundColor: 'rgba(255, 59, 136, 0.3)',
    borderRadius: 20,
    zIndex: 10,
  },
  modalCloseText: {
    color: '#ffffff',
    fontWeight: '700',
  },
  modalImage: {
    width: width * 0.88,
    height: width * 0.88,
  },
});
