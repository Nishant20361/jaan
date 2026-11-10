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
import { api } from '../services/api';

export default function SettingsScreen() {
  const router = useRouter();

  const [backendUrl, setBackendUrl] = useState(api.getBaseUrl());
  const [groqKey, setGroqKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('llama-3.3-70b-versatile');
  const [temperature, setTemperature] = useState('0.7');
  const [responseLength, setResponseLength] = useState('Medium');
  const [hinglishStyle, setHinglishStyle] = useState('Natural');

  const [isTesting, setIsTesting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'failed'>('idle');

  useEffect(() => {
    api.getSettings().then((s) => {
      if (s) {
        if (s.groq_model) setSelectedModel(s.groq_model);
        if (s.temperature) setTemperature(s.temperature.toString());
      }
    });
  }, []);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setConnectionStatus('idle');
    api.setBaseUrl(backendUrl);
    const ok = await api.checkHealth();
    setIsTesting(false);
    setConnectionStatus(ok ? 'success' : 'failed');
    try {
      if (ok) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } else {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
    } catch (e) {}
  };

  const handleSaveSettings = async () => {
    api.setBaseUrl(backendUrl);
    const payload: any = {
      groq_model: selectedModel,
      temperature: parseFloat(temperature) || 0.7,
    };
    if (groqKey.trim()) {
      payload.groq_api_key = groqKey.trim();
    }
    const res = await api.updateSettings(payload);
    try {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e) {}
    Alert.alert('Settings Saved', 'Your companion configuration has been updated successfully ❤️');
  };

  const handleClearHistory = () => {
    Alert.alert(
      'Clear Chat History',
      'Are you sure you want to clear your current active chat session? (Original Messenger history will remain untouched).',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            await api.clearHistory('default');
            try {
              Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
            } catch (e) {}
            Alert.alert('History Cleared', 'Active chat messages have been reset.');
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
        <Text style={styles.headerTitle}>Settings & AI Configuration ⚙️</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Section 1: Groq AI Model */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>AI Brain & Model (Groq API)</Text>
          <Text style={styles.sectionSubtitle}>
            Select the inference model for Jaan AI's conversational generation.
          </Text>

          <View style={styles.optionsList}>
            {[
              { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B (Deeply Romantic & Nuanced)' },
              { id: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B (Ultra Fast & Lightweight)' },
              { id: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B (High Context & Balanced)' },
            ].map((m) => (
              <TouchableOpacity
                key={m.id}
                style={[
                  styles.optionCard,
                  selectedModel === m.id && styles.optionCardActive,
                ]}
                onPress={() => setSelectedModel(m.id)}
              >
                <View style={styles.radioDot}>
                  {selectedModel === m.id && <View style={styles.radioDotInner} />}
                </View>
                <Text style={styles.optionText}>{m.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.fieldLabel}>Groq API Key (Optional Override)</Text>
          <TextInput
            style={styles.inputField}
            placeholder="gsk_... (Stored securely on backend only)"
            placeholderTextColor="#8a739e"
            value={groqKey}
            onChangeText={setGroqKey}
            secureTextEntry
          />
        </View>

        {/* Section 2: Conversational Tone & Temperament */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Conversational Temperament</Text>
          <Text style={styles.sectionSubtitle}>
            Adjust creativity, emotional warmth, and reply cadence.
          </Text>

          <Text style={styles.fieldLabel}>Creativity (Temperature: {temperature})</Text>
          <View style={styles.pillRow}>
            {[
              { val: '0.5', label: 'Calm & Sweet (0.5)' },
              { val: '0.7', label: 'Affectionate (0.7)' },
              { val: '0.9', label: 'Playful & Teasing (0.9)' },
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

          <Text style={styles.fieldLabel}>Response Cadence</Text>
          <View style={styles.pillRow}>
            {['Snappy (1 line)', 'Medium (2-3 lines)', 'Detailed'].map((len) => (
              <TouchableOpacity
                key={len}
                style={[
                  styles.segmentBtn,
                  responseLength === len && styles.segmentBtnActive,
                ]}
                onPress={() => setResponseLength(len)}
              >
                <Text
                  style={[
                    styles.segmentText,
                    responseLength === len && styles.segmentTextActive,
                  ]}
                >
                  {len}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Section 3: Backend Connectivity */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Backend Connection</Text>
          <Text style={styles.sectionSubtitle}>
            FastAPI Server URL running locally or on your LAN.
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
              onPress={handleTestConnection}
              disabled={isTesting}
            >
              {isTesting ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <Text style={styles.testBtnText}>Test Server Connection</Text>
              )}
            </TouchableOpacity>

            {connectionStatus === 'success' && (
              <Text style={styles.statusSuccess}>● Connected (200 OK)</Text>
            )}
            {connectionStatus === 'failed' && (
              <Text style={styles.statusFailed}>✕ Offline / Fallback Active</Text>
            )}
          </View>
        </View>

        {/* Section 4: Data & Chat History */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Data & Privacy</Text>
          <Text style={styles.sectionSubtitle}>
            Your Messenger chat history (1,813 messages) remains 100% private and stored locally.
          </Text>

          <TouchableOpacity
            style={styles.clearBtn}
            onPress={handleClearHistory}
            activeOpacity={0.8}
          >
            <Text style={styles.clearBtnText}>Clear Active Chat Session</Text>
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
            <Text style={styles.saveBtnText}>Save All Settings</Text>
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
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 4,
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
    fontSize: 13.5,
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
  },
  statusFailed: {
    color: '#ff5252',
    fontSize: 12,
    fontWeight: '600',
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
