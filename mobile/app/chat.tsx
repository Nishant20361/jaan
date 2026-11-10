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
  ActivityIndicator,
  Animated,
} from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { api, MessageItem, MediaItem } from '../services/api';

const { width } = Dimensions.get('window');

const QUICK_EMOJIS = ['😘', '🥰', '😂', '🤪', '😉', '❤️', '💕', '👋', '🌹', '🥺', '💖', '🤗'];

export default function ChatScreen() {
  const router = useRouter();
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showStickerPicker, setShowStickerPicker] = useState(false);
  const [availableStickers, setAvailableStickers] = useState<MediaItem[]>([]);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const flatListRef = useRef<FlatList>(null);
  const typingDot1 = useRef(new Animated.Value(0)).current;
  const typingDot2 = useRef(new Animated.Value(0)).current;
  const typingDot3 = useRef(new Animated.Value(0)).current;

  // Initial greeting
  useEffect(() => {
    const initialGreeting: MessageItem = {
      id: 'init-1',
      role: 'companion',
      content: 'Hlo jaan! 🥰 Kaisi ho? Khana khaya tumne?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages([initialGreeting]);

    // Fetch available stickers
    api.getStickers().then((stickers) => {
      setAvailableStickers(stickers);
    });
  }, []);

  // Typing dots animation
  useEffect(() => {
    if (isTyping) {
      const animateDot = (dot: Animated.Value, delay: number) => {
        return Animated.loop(
          Animated.sequence([
            Animated.delay(delay),
            Animated.timing(dot, {
              toValue: -6,
              duration: 350,
              useNativeDriver: true,
            }),
            Animated.timing(dot, {
              toValue: 0,
              duration: 350,
              useNativeDriver: true,
            }),
          ])
        );
      };
      const a1 = animateDot(typingDot1, 0);
      const a2 = animateDot(typingDot2, 180);
      const a3 = animateDot(typingDot3, 360);
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

  const handleSend = async (overrideText?: string, stickerUri?: string) => {
    const textToSend = overrideText !== undefined ? overrideText : inputText.trim();
    if (!textToSend && !stickerUri) return;

    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch (e) {}

    const userMsg: MessageItem = {
      id: Date.now().toString(),
      role: 'user',
      content: textToSend,
      media_uri: stickerUri,
      media_type: stickerUri ? 'sticker' : undefined,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (overrideText === undefined) setInputText('');
    setShowEmojiPicker(false);
    setShowStickerPicker(false);
    setIsTyping(true);

    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);

    try {
      const query = textToSend || (stickerUri ? '[Sent Sticker]' : 'Hlo');
      const res = await api.sendMessage(query);
      
      const aiMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: 'companion',
        content: res.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, aiMsg]);
      try {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } catch (e) {}
    } catch (err) {
      console.error('Chat error:', err);
    } finally {
      setIsTyping(false);
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  };

  const handleSendSticker = (sticker: MediaItem) => {
    const fullUrl = sticker.url.startsWith('http')
      ? sticker.url
      : `${api.getBaseUrl()}${sticker.url}`;
    handleSend('', fullUrl);
  };

  const renderMessageItem = ({ item }: { item: MessageItem }) => {
    const isUser = item.role === 'user';
    return (
      <View
        style={[
          styles.messageRow,
          isUser ? styles.messageRowUser : styles.messageRowCompanion,
        ]}
      >
        {!isUser && (
          <Image
            source={require('../assets/avatar.png')}
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
          ) : (
            <LinearGradient
              colors={
                isUser
                  ? ['#ff3b88', '#d81b60']
                  : ['#28133a', '#1a0b26']
              }
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
    );
  };

  return (
    <LinearGradient
      colors={['#140722', '#0d0614', '#08030c']}
      style={styles.container}
    >
      {/* Companion Chat Header */}
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
          onPress={() => router.push('/memories')}
        >
          <View style={styles.avatarMiniContainer}>
            <Image
              source={require('../assets/avatar.png')}
              style={styles.avatarMini}
            />
            <View style={styles.miniOnlineDot} />
          </View>
          <View>
            <Text style={styles.headerTitle}>Jaan ❤️</Text>
            <Text style={styles.headerSubtitle}>Online • AI Companion</Text>
          </View>
        </TouchableOpacity>

        <View style={styles.headerActions}>
          <TouchableOpacity
            onPress={() => router.push('/memories')}
            style={styles.headerActionBtn}
            activeOpacity={0.7}
          >
            <Text style={styles.headerActionIcon}>📸</Text>
          </TouchableOpacity>
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
                source={require('../assets/avatar.png')}
                style={styles.bubbleAvatar}
              />
              <View style={styles.typingBubble}>
                <Text style={styles.typingLabel}>Jaan is typing</Text>
                <Animated.View
                  style={[
                    styles.typingDot,
                    { transform: [{ translateY: typingDot1 }] },
                  ]}
                />
                <Animated.View
                  style={[
                    styles.typingDot,
                    { transform: [{ translateY: typingDot2 }] },
                  ]}
                />
                <Animated.View
                  style={[
                    styles.typingDot,
                    { transform: [{ translateY: typingDot3 }] },
                  ]}
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
            <Text style={styles.drawerTitle}>Expressive Emojis</Text>
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
            <Text style={styles.drawerTitle}>Original Messenger Stickers</Text>
            <TouchableOpacity onPress={() => setShowStickerPicker(false)}>
              <Text style={styles.drawerClose}>✕</Text>
            </TouchableOpacity>
          </View>
          <FlatList
            horizontal
            data={availableStickers}
            keyExtractor={(item) => item.uri}
            renderItem={({ item }) => {
              const fullUrl = item.url.startsWith('http')
                ? item.url
                : `${api.getBaseUrl()}${item.url}`;
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
            placeholder="Type a loving message in Hinglish..."
            placeholderTextColor="#89759c"
            multiline
            maxLength={1000}
          />

          <TouchableOpacity
            style={[
              styles.sendButton,
              !inputText.trim() && styles.sendButtonDisabled,
            ]}
            onPress={() => handleSend()}
            disabled={!inputText.trim()}
          >
            <LinearGradient
              colors={
                inputText.trim()
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
          {selectedImage && (
            <Image
              source={{ uri: selectedImage }}
              style={styles.modalImage}
              resizeMode="contain"
            />
          )}
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
    color: '#ff80ab',
    fontWeight: '500',
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
  messageRow: {
    flexDirection: 'row',
    marginVertical: 6,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowCompanion: {
    justifyContent: 'flex-start',
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
    width: 130,
    height: 130,
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
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  typingLabel: {
    color: '#ff80ab',
    fontSize: 12,
    fontWeight: '500',
    marginRight: 8,
  },
  typingDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: '#ff3b88',
    marginHorizontal: 2,
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
  },
  modalCloseText: {
    color: '#ffffff',
    fontWeight: '700',
  },
  modalImage: {
    width: width * 0.85,
    height: width * 0.85,
  },
});
