import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api, DEFAULT_GEMINI_KEY, DEFAULT_GEMINI_MODEL } from '../services/api';

const LOCAL_CHAT_STORAGE_KEY = '@jaan_chat_history';

export default function SettingsScreen() {
  const router = useRouter();

  const [geminiKey, setGeminiKey] = useState(DEFAULT_GEMINI_KEY);
  const [selectedGeminiModel, setSelectedGeminiModel] = useState(DEFAULT_GEMINI_MODEL);
  const [temperature, setTemperature] = useState('0.85');
  const [backendUrl, setBackendUrl] = useState(api.getBaseUrl());

  const [isTestingGemini, setIsTestingGemini] = useState(false);
  const [geminiStatus, setGeminiStatus] = useState<{ status: 'idle' | 'success' | 'failed'; msg?: string }>({
    status: 'idle',
  });

  const [isTestingServer, setIsTestingServer] = useState(false);
  const [serverStatus, setServerStatus] = useState<'idle' | 'success' | 'failed'>('idle');

  useEffect(() => {
    async function load() {
      await api.initSettings();
      setGeminiKey(api.getGeminiApiKey());
      setSelectedGeminiModel(api.getGeminiModel());
      setTemperature(api.getTemperature().toString());
      setBackendUrl(api.getBaseUrl());
    }
    load();
  }, []);

  const handleTestGemini = async () => {
    setIsTestingGemini(true);
    setGeminiStatus({ status: 'idle' });
    const res = await api.testGeminiConnection(geminiKey, selectedGeminiModel);
    setIsTestingGemini(false);
    if (res.ok) {
      setGeminiStatus({ status: 'success', msg: res.message });
      try {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } catch (e) {}
    } else {
      setGeminiStatus({ status: 'failed', msg: res.message });
      try {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      } catch (e) {}
    }
  };

  const handleTestServer = async () => {
    setIsTestingServer(true);
    setServerStatus('idle');
    api.setBaseUrl(backendUrl);
    const ok = await api.checkHealth();
    setIsTestingServer(false);
    setServerStatus(ok ? 'success' : 'failed');
    try {
      if (ok) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } else {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
    } catch (e) {}
  };

  const handleSaveSettings = async () => {
    api.setGeminiApiKey(geminiKey);
    api.setGeminiModel(selectedGeminiModel);
    api.setTemperature(parseFloat(temperature) || 0.85);
    api.setBaseUrl(backendUrl);

    try {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e) {}
    Alert.alert('Settings Saved ❤️', 'Alquama AI settings have been updated successfully.');
  };

  const handleClearHistory = () => {
    Alert.alert(
      'Clear All Messages',
      'Are you sure you want to delete all saved conversations from this phone?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: async () => {
            try {
              await AsyncStorage.removeItem(LOCAL_CHAT_STORAGE_KEY);
              await api.clearHistory('default');
              Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
            } catch (e) {}
            Alert.alert('Chat Cleared', 'All messages have been reset.');
          },
        },
      ]
    );
  };

  return (
    <LinearGradient colors={['#140722', '#0d0614', '#08030c']} style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backButton}
          activeOpacity={0.7}
        >
          <Text style={styles.backArrow}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Alquama Settings ⚙️</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Section 1: Gemini AI Engine */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderRow}>
            <Text style={styles.sectionTitle}>Google Gemini AI Engine</Text>
            <View style={styles.badgePrimary}>
              <Text style={styles.badgePrimaryText}>ACTIVE</Text>
            </View>
          </View>
          <Text style={styles.sectionSubtitle}>
            Direct Cloud connection. Works natively on mobile data and Wi-Fi anywhere in the world!
          </Text>

          <Text style={styles.fieldLabel}>Gemini Model</Text>
          <View style={styles.optionsList}>
            {[
              {
                id: 'gemini-flash-lite-latest',
                label: 'Gemini Flash Lite (Recommended • Ultra Fast & Emotional)',
              },
              {
                id: 'gemini-3.8-flash',
                label: 'Gemini 3.8 Flash (High Reasoning & Nuance)',
              },
              {
                id: 'gemini-flash-latest',
                label: 'Gemini Flash Latest (Classic)',
              },
            ].map((m) => (
              <TouchableOpacity
                key={m.id}
                style={[
                  styles.optionCard,
                  selectedGeminiModel === m.id && styles.optionCardActive,
                ]}
                onPress={() => setSelectedGeminiModel(m.id)}
              >
                <View style={styles.radioDot}>
                  {selectedGeminiModel === m.id && <View style={styles.radioDotInner} />}
                </View>
                <Text style={styles.optionText}>{m.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.fieldLabel}>Gemini API Key</Text>
          <TextInput
            style={styles.inputField}
            placeholder="Enter Gemini API Key (Saved securely on this phone)"
            placeholderTextColor="#8a739e"
            value={geminiKey}
            onChangeText={setGeminiKey}
            secureTextEntry={false}
            autoCapitalize="none"
          />

          <View style={styles.testRow}>
            <TouchableOpacity
              style={styles.testBtn}
              onPress={handleTestGemini}
              disabled={isTestingGemini}
            >
              {isTestingGemini ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <Text style={styles.testBtnText}>⚡ Test Gemini AI</Text>
              )}
            </TouchableOpacity>

            {geminiStatus.status === 'success' && (
              <Text style={styles.statusSuccess} numberOfLines={2}>
                ● Connected & Ready 🚀
              </Text>
            )}
            {geminiStatus.status === 'failed' && (
              <Text style={styles.statusFailed} numberOfLines={2}>
                ✕ {geminiStatus.msg || 'Connection Error'}
              </Text>
            )}
          </View>
        </View>

        {/* Section 2: Mood & Expressiveness */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Mood & Expressiveness</Text>
          <Text style={styles.sectionSubtitle}>
            Adjust warmth, emotional response dynamics, and playful fights/nakhre.
          </Text>

          <Text style={styles.fieldLabel}>Expressiveness (Temperature: {temperature})</Text>
          <View style={styles.pillRow}>
            {[
              { val: '0.6', label: 'Sweet & Calm (0.6)' },
              { val: '0.85', label: 'Affectionate & Nakhre (0.85)' },
              { val: '0.95', label: 'Playful & Sassy (0.95)' },
            ].map((p) => (
              <TouchableOpacity
                key={p.val}
                style={[
                  styles.segmentBtn,
                  temperature === p.val && styles.segmentBtnActive,
                ]}
                onPress={() => setTemperature(p.val)}
              >
                <Text
                  style={[
                    styles.segmentText,
                    temperature === p.val && styles.segmentTextActive,
                  ]}
                >
                  {p.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Section 3: Optional PC Backend Server */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Local Backend Server (Optional)</Text>
          <Text style={styles.sectionSubtitle}>
            Optional: If you run the backend on your PC, enter its Wi-Fi IP (e.g. http://192.168.1.15:8000). Otherwise, direct Gemini Cloud is used automatically!
          </Text>

          <TextInput
            style={styles.inputField}
            value={backendUrl}
            onChangeText={setBackendUrl}
            placeholder="http://localhost:8000"
            placeholderTextColor="#8a739e"
            autoCapitalize="none"
          />

          <View style={styles.testRow}>
            <TouchableOpacity
              style={styles.testBtn}
              onPress={handleTestServer}
              disabled={isTestingServer}
            >
              {isTestingServer ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <Text style={styles.testBtnText}>Test Server Connection</Text>
              )}
            </TouchableOpacity>

            {serverStatus === 'success' && (
              <Text style={styles.statusSuccess}>● Connected (200 OK)</Text>
            )}
            {serverStatus === 'failed' && (
              <Text style={styles.statusFailed}>✕ Offline (Using Gemini Cloud)</Text>
            )}
          </View>
        </View>

        {/* Section 4: Storage & Reset */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Phone Storage & Reset</Text>
          <Text style={styles.sectionSubtitle}>
            Your chats are preserved inside your phone's storage. You can start a completely fresh conversation anytime.
          </Text>

          <TouchableOpacity
            style={styles.clearBtn}
            onPress={handleClearHistory}
            activeOpacity={0.8}
          >
            <Text style={styles.clearBtnText}>🗑️ Clear All Saved Chats</Text>
          </TouchableOpacity>
        </View>

        {/* Save Button */}
        <TouchableOpacity
          style={styles.saveBtn}
          onPress={handleSaveSettings}
          activeOpacity={0.85}
        >
          <LinearGradient
            colors={['#ff3b88', '#e91e63', '#a824e8']}
            style={styles.saveGradient}
          >
            <Text style={styles.saveBtnText}>Save Preferences ❤️</Text>
          </LinearGradient>
        </TouchableOpacity>
      </ScrollView>
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
  backButton: {
    width: 38,
    height: 38,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  backArrow: {
    fontSize: 34,
    color: '#ff80ab',
    fontWeight: '300',
    marginTop: -4,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#ffffff',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  sectionCard: {
    backgroundColor: 'rgba(32, 12, 48, 0.75)',
    borderRadius: 18,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 90, 160, 0.2)',
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
  },
  badgePrimary: {
    backgroundColor: 'rgba(0, 230, 118, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#00e676',
  },
  badgePrimaryText: {
    color: '#00e676',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  sectionSubtitle: {
    fontSize: 12,
    color: '#bfa7d9',
    marginBottom: 14,
    lineHeight: 17,
  },
  optionsList: {
    marginBottom: 12,
  },
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  optionCardActive: {
    backgroundColor: 'rgba(255, 59, 136, 0.18)',
    borderColor: 'rgba(255, 59, 136, 0.5)',
  },
  radioDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: '#ff80ab',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  radioDotInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#ff3b88',
  },
  optionText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '500',
    flex: 1,
  },
  fieldLabel: {
    color: '#ff80ab',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 6,
    marginTop: 8,
  },
  inputField: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: '#ffffff',
    fontSize: 13,
    borderWidth: 1,
    borderColor: 'rgba(255, 100, 170, 0.2)',
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 8,
  },
  segmentBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 14,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255, 120, 180, 0.2)',
  },
  segmentBtnActive: {
    backgroundColor: 'rgba(255, 59, 136, 0.3)',
    borderColor: '#ff3b88',
  },
  segmentText: {
    color: '#d6c0ea',
    fontSize: 12,
    fontWeight: '500',
  },
  segmentTextActive: {
    color: '#ffffff',
    fontWeight: '700',
  },
  testRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    gap: 12,
  },
  testBtn: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(255, 100, 170, 0.3)',
  },
  testBtnText: {
    color: '#ffffff',
    fontSize: 12.5,
    fontWeight: '600',
  },
  statusSuccess: {
    color: '#00e676',
    fontSize: 12,
    fontWeight: '600',
    flex: 1,
  },
  statusFailed: {
    color: '#ff5252',
    fontSize: 12,
    fontWeight: '600',
    flex: 1,
  },
  clearBtn: {
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 12,
    backgroundColor: 'rgba(255, 50, 80, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(255, 50, 80, 0.4)',
  },
  clearBtnText: {
    color: '#ff6688',
    fontSize: 13,
    fontWeight: '700',
  },
  saveBtn: {
    borderRadius: 20,
    overflow: 'hidden',
    marginTop: 10,
    shadowColor: '#ff3b88',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
  },
  saveGradient: {
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveBtnText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
