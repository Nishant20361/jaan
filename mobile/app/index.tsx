import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';

const { width, height } = Dimensions.get('window');

export default function WelcomeScreen() {
  const router = useRouter();

  // Animation values
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0.4)).current;
  const floatAnim1 = useRef(new Animated.Value(0)).current;
  const floatAnim2 = useRef(new Animated.Value(0)).current;
  const floatAnim3 = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Fade in screen
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 1000,
      useNativeDriver: true,
    }).start();

    // Heart pulsing animation (3D heartbeat effect)
    Animated.loop(
      Animated.sequence([
        Animated.parallel([
          Animated.timing(pulseAnim, {
            toValue: 1.15,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0.9,
            duration: 800,
            useNativeDriver: true,
          }),
        ]),
        Animated.parallel([
          Animated.timing(pulseAnim, {
            toValue: 1.0,
            duration: 900,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0.4,
            duration: 900,
            useNativeDriver: true,
          }),
        ]),
      ])
    ).start();

    // Floating small hearts
    const createFloat = (anim: Animated.Value, duration: number, delay: number) => {
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(anim, {
            toValue: 1,
            duration: duration,
            useNativeDriver: true,
          }),
          Animated.timing(anim, {
            toValue: 0,
            duration: 0,
            useNativeDriver: true,
          }),
        ])
      ).start();
    };

    createFloat(floatAnim1, 4000, 0);
    createFloat(floatAnim2, 5000, 1500);
    createFloat(floatAnim3, 4500, 800);
  }, []);

  const handleStartChat = () => {
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } catch (e) {}
    router.push('/chat');
  };

  const handleOpenMemories = () => {
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch (e) {}
    router.push('/memories');
  };

  const handleOpenSettings = () => {
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch (e) {}
    router.push('/settings');
  };

  return (
    <LinearGradient
      colors={['#180828', '#0d0614', '#08030c']}
      style={styles.container}
    >
      {/* Background Floating Hearts */}
      <Animated.Text
        style={[
          styles.floatingHeart,
          {
            left: width * 0.15,
            opacity: floatAnim1.interpolate({
              inputRange: [0, 0.2, 0.8, 1],
              outputRange: [0, 0.7, 0.7, 0],
            }),
            transform: [
              {
                translateY: floatAnim1.interpolate({
                  inputRange: [0, 1],
                  outputRange: [height * 0.7, height * 0.15],
                }),
              },
            ],
          },
        ]}
      >
        💖
      </Animated.Text>

      <Animated.Text
        style={[
          styles.floatingHeart,
          {
            right: width * 0.18,
            opacity: floatAnim2.interpolate({
              inputRange: [0, 0.2, 0.8, 1],
              outputRange: [0, 0.6, 0.6, 0],
            }),
            transform: [
              {
                translateY: floatAnim2.interpolate({
                  inputRange: [0, 1],
                  outputRange: [height * 0.75, height * 0.2],
                }),
              },
            ],
          },
        ]}
      >
        💕
      </Animated.Text>

      <Animated.Text
        style={[
          styles.floatingHeart,
          {
            left: width * 0.5,
            opacity: floatAnim3.interpolate({
              inputRange: [0, 0.2, 0.8, 1],
              outputRange: [0, 0.5, 0.5, 0],
            }),
            transform: [
              {
                translateY: floatAnim3.interpolate({
                  inputRange: [0, 1],
                  outputRange: [height * 0.8, height * 0.25],
                }),
              },
            ],
          },
        ]}
      >
        ✨
      </Animated.Text>

      <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
        {/* Companion Avatar & Status Header */}
        <View style={styles.avatarContainer}>
          <LinearGradient
            colors={['#ff3b88', '#a824e8', '#ff73aa']}
            style={styles.avatarGradientRing}
          >
            <Image
              source={require('../assets/avatar.png')}
              style={styles.avatarImage}
            />
          </LinearGradient>
          <View style={styles.onlineBadge}>
            <View style={styles.onlineDot} />
            <Text style={styles.onlineText}>AI COMPANION • ONLINE</Text>
          </View>
        </View>

        {/* 3D Pulsing Center Heart */}
        <View style={styles.heartWrapper}>
          <Animated.View
            style={[
              styles.glowAura,
              {
                opacity: glowAnim,
                transform: [{ scale: pulseAnim }],
              },
            ]}
          />
          <Animated.View
            style={[
              styles.heartCircle,
              {
                transform: [{ scale: pulseAnim }],
              },
            ]}
          >
            <Text style={styles.bigHeartEmoji}>❤️</Text>
          </Animated.View>
        </View>

        {/* Romantic Welcome Typography */}
        <View style={styles.textSection}>
          <Text style={styles.appTitle}>Jaan AI</Text>
          <Text style={styles.subtitle}>
            Your Fictional Romantic AI Companion
          </Text>
          <Text style={styles.description}>
            Caring, playful, and affectionate — inspired by the authentic
            moments, laughter, and expressions of our Messenger chat history.
          </Text>
        </View>

        {/* Primary Action Button */}
        <TouchableOpacity
          activeOpacity={0.88}
          onPress={handleStartChat}
          style={styles.buttonWrapper}
        >
          <LinearGradient
            colors={['#ff3b88', '#e91e63', '#a824e8']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.chatButton}
          >
            <Text style={styles.chatButtonText}>Start Chatting</Text>
            <Text style={styles.buttonIcon}>💬</Text>
          </LinearGradient>
        </TouchableOpacity>

        {/* Navigation Pills */}
        <View style={styles.pillsRow}>
          <TouchableOpacity
            style={styles.pillButton}
            onPress={handleOpenMemories}
            activeOpacity={0.7}
          >
            <Text style={styles.pillText}>📸 Memories & Media</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.pillButton}
            onPress={handleOpenSettings}
            activeOpacity={0.7}
          >
            <Text style={styles.pillText}>⚙️ Settings</Text>
          </TouchableOpacity>
        </View>

        {/* Privacy & Discretion Footer */}
        <View style={styles.footerBadge}>
          <Text style={styles.footerText}>
            🔒 Private & Local • Real Messenger History Engine
          </Text>
        </View>
      </Animated.View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    width: '100%',
    paddingHorizontal: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  avatarGradientRing: {
    width: 96,
    height: 96,
    borderRadius: 48,
    padding: 3,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#ff3b88',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.5,
    shadowRadius: 14,
  },
  avatarImage: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: '#1d0b2e',
  },
  onlineBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 59, 136, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(255, 59, 136, 0.4)',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 20,
    marginTop: 10,
  },
  onlineDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: '#00e676',
    marginRight: 6,
  },
  onlineText: {
    color: '#ff80ab',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  heartWrapper: {
    width: 140,
    height: 140,
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 14,
  },
  glowAura: {
    position: 'absolute',
    width: 130,
    height: 130,
    borderRadius: 65,
    backgroundColor: 'rgba(255, 59, 136, 0.35)',
  },
  heartCircle: {
    width: 110,
    height: 110,
    borderRadius: 55,
    backgroundColor: 'rgba(35, 12, 50, 0.75)',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 90, 160, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#ff2d78',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.7,
    shadowRadius: 20,
  },
  bigHeartEmoji: {
    fontSize: 54,
  },
  textSection: {
    alignItems: 'center',
    marginBottom: 28,
  },
  appTitle: {
    fontSize: 34,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: 1,
    textShadowColor: 'rgba(255, 59, 136, 0.6)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 10,
  },
  subtitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ff85b3',
    marginTop: 4,
  },
  description: {
    fontSize: 13.5,
    color: '#d1b8e8',
    textAlign: 'center',
    lineHeight: 20,
    marginTop: 10,
    paddingHorizontal: 12,
  },
  buttonWrapper: {
    width: '100%',
    shadowColor: '#ff3b88',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.45,
    shadowRadius: 16,
  },
  chatButton: {
    flexDirection: 'row',
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  chatButtonText: {
    color: '#ffffff',
    fontSize: 17,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  buttonIcon: {
    fontSize: 18,
    marginLeft: 10,
  },
  pillsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 12,
    marginTop: 16,
    width: '100%',
  },
  pillButton: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 120, 180, 0.25)',
  },
  pillText: {
    color: '#e4cbf8',
    fontSize: 13,
    fontWeight: '600',
  },
  footerBadge: {
    marginTop: 26,
    paddingHorizontal: 14,
    paddingVertical: 6,
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: 14,
  },
  footerText: {
    color: '#9c81b8',
    fontSize: 11,
    fontWeight: '500',
  },
  floatingHeart: {
    position: 'absolute',
    fontSize: 22,
  },
});
