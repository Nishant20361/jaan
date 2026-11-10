import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  TextInput,
  Image,
  Dimensions,
  Modal,
  ScrollView,
  Platform,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { api, MediaItem, MemoryNote, MemoryStats } from '../services/api';

const { width } = Dimensions.get('window');

type TabType = 'conversations' | 'photos' | 'stickers' | 'notes';

export default function MemoriesScreen() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>('conversations');
  const [stats, setStats] = useState<MemoryStats | null>(null);

  // Search in conversation
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Media
  const [photos, setPhotos] = useState<MediaItem[]>([]);
  const [stickers, setStickers] = useState<MediaItem[]>([]);
  const [selectedMedia, setSelectedMedia] = useState<string | null>(null);

  // Notes
  const [notes, setNotes] = useState<MemoryNote[]>([]);
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [showAddNote, setShowAddNote] = useState(false);

  useEffect(() => {
    // Load stats and media
    api.getMemoryStats().then(setStats);
    api.getPhotos().then(setPhotos);
    api.getStickers().then(setStickers);
    api.getNotes().then(setNotes);

    // Initial search
    handleSearch('jaan');
  }, []);

  const handleSearch = async (term: string) => {
    setIsSearching(true);
    try {
      const res = await api.searchMessages(term || 'jaan', 40);
      setSearchResults(res.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddNote = async () => {
    if (!noteTitle.trim() || !noteContent.trim()) {
      Alert.alert('Required', 'Please enter both a title and memory description.');
      return;
    }
    const created = await api.addNote(noteTitle.trim(), noteContent.trim(), 'romantic');
    if (created) {
      setNotes((prev) => [created, ...prev]);
      setNoteTitle('');
      setNoteContent('');
      setShowAddNote(false);
      try {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } catch (e) {}
    }
  };

  const handleDeleteNote = async (id: number) => {
    const ok = await api.deleteNote(id);
    if (ok) {
      setNotes((prev) => prev.filter((n) => n.id !== id));
      try {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      } catch (e) {}
    }
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
        <View style={styles.headerTitleGroup}>
          <Text style={styles.headerTitle}>Digital Memory Gallery ❤️</Text>
          <Text style={styles.headerSubtitle}>
            {stats ? `${stats.total_messages} messages • 2020 to 2023` : 'Preserved Memories'}
          </Text>
        </View>
      </View>

      {/* Tabs Bar */}
      <View style={styles.tabsRow}>
        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'conversations' && styles.tabBtnActive]}
          onPress={() => {
            setActiveTab('conversations');
            try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); } catch(e){}
          }}
        >
          <Text style={[styles.tabText, activeTab === 'conversations' && styles.tabTextActive]}>
            Chat 💬
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'photos' && styles.tabBtnActive]}
          onPress={() => {
            setActiveTab('photos');
            try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); } catch(e){}
          }}
        >
          <Text style={[styles.tabText, activeTab === 'photos' && styles.tabTextActive]}>
            Photos ({photos.length}) 📸
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'stickers' && styles.tabBtnActive]}
          onPress={() => {
            setActiveTab('stickers');
            try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); } catch(e){}
          }}
        >
          <Text style={[styles.tabText, activeTab === 'stickers' && styles.tabTextActive]}>
            Stickers ({stickers.length}) 🎨
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'notes' && styles.tabBtnActive]}
          onPress={() => {
            setActiveTab('notes');
            try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); } catch(e){}
          }}
        >
          <Text style={[styles.tabText, activeTab === 'notes' && styles.tabTextActive]}>
            Notes ({notes.length}) 📝
          </Text>
        </TouchableOpacity>
      </View>

      {/* Tab 1: Conversations Search */}
      {activeTab === 'conversations' && (
        <View style={styles.tabContent}>
          <View style={styles.searchBar}>
            <TextInput
              style={styles.searchInput}
              placeholder="Search past memories (e.g. 'jaan', 'khana', 'love')..."
              placeholderTextColor="#8d72a3"
              value={searchQuery}
              onChangeText={setSearchQuery}
              onSubmitEditing={() => handleSearch(searchQuery)}
            />
            <TouchableOpacity
              style={styles.searchActionBtn}
              onPress={() => handleSearch(searchQuery)}
            >
              <Text style={styles.searchActionIcon}>🔍</Text>
            </TouchableOpacity>
          </View>

          <FlatList
            data={searchResults}
            keyExtractor={(item) => item.id.toString()}
            contentContainerStyle={styles.resultsList}
            renderItem={({ item }) => {
              const isUser = item.role === 'user';
              return (
                <View style={styles.searchCard}>
                  <View style={styles.searchCardHeader}>
                    <Text
                      style={[
                        styles.senderBadge,
                        isUser ? styles.badgeUser : styles.badgeCompanion,
                      ]}
                    >
                      {item.display_sender}
                    </Text>
                    <Text style={styles.dateStamp}>
                      {item.date} • {item.time}
                    </Text>
                  </View>
                  <Text style={styles.cardContent}>{item.content || '[Media attachment]'}</Text>
                  {item.reactions && item.reactions.length > 0 && (
                    <View style={styles.reactionsRow}>
                      {item.reactions.map((r: any, idx: number) => (
                        <Text key={idx} style={styles.reactionTag}>
                          {r.reaction} {r.actor}
                        </Text>
                      ))}
                    </View>
                  )}
                </View>
              );
            }}
          />
        </View>
      )}

      {/* Tab 2: Photos Gallery */}
      {activeTab === 'photos' && (
        <View style={styles.tabContent}>
          <FlatList
            data={photos}
            numColumns={3}
            keyExtractor={(item) => item.uri}
            contentContainerStyle={styles.gridContent}
            renderItem={({ item }) => {
              const fullUrl = item.url.startsWith('http')
                ? item.url
                : `${api.getBaseUrl()}${item.url}`;
              return (
                <TouchableOpacity
                  style={styles.photoThumbWrapper}
                  activeOpacity={0.8}
                  onPress={() => setSelectedMedia(fullUrl)}
                >
                  <Image source={{ uri: fullUrl }} style={styles.photoThumb} />
                </TouchableOpacity>
              );
            }}
          />
        </View>
      )}

      {/* Tab 3: Stickers Gallery */}
      {activeTab === 'stickers' && (
        <View style={styles.tabContent}>
          <FlatList
            data={stickers}
            numColumns={4}
            keyExtractor={(item) => item.uri}
            contentContainerStyle={styles.gridContent}
            renderItem={({ item }) => {
              const fullUrl = item.url.startsWith('http')
                ? item.url
                : `${api.getBaseUrl()}${item.url}`;
              return (
                <TouchableOpacity
                  style={styles.stickerCard}
                  activeOpacity={0.8}
                  onPress={() => setSelectedMedia(fullUrl)}
                >
                  <Image
                    source={{ uri: fullUrl }}
                    style={styles.stickerGridImage}
                    resizeMode="contain"
                  />
                </TouchableOpacity>
              );
            }}
          />
        </View>
      )}

      {/* Tab 4: User Saved Notes */}
      {activeTab === 'notes' && (
        <View style={styles.tabContent}>
          <TouchableOpacity
            style={styles.addNoteBtn}
            onPress={() => setShowAddNote(true)}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={['#ff3b88', '#a824e8']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.addNoteGradient}
            >
              <Text style={styles.addNoteText}>+ Add Special Memory Note</Text>
            </LinearGradient>
          </TouchableOpacity>

          <FlatList
            data={notes}
            keyExtractor={(item) => item.id.toString()}
            contentContainerStyle={styles.notesList}
            renderItem={({ item }) => (
              <View style={styles.noteCard}>
                <View style={styles.noteCardHeader}>
                  <Text style={styles.noteTitle}>{item.title}</Text>
                  <TouchableOpacity onPress={() => handleDeleteNote(item.id)}>
                    <Text style={styles.deleteNoteIcon}>🗑️</Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.noteDesc}>{item.content}</Text>
                <Text style={styles.noteDate}>
                  {new Date(item.created_at).toLocaleDateString()}
                </Text>
              </View>
            )}
          />
        </View>
      )}

      {/* Add Note Modal */}
      <Modal visible={showAddNote} transparent animationType="slide">
        <View style={styles.modalBg}>
          <View style={styles.modalForm}>
            <Text style={styles.modalFormTitle}>Add Special Memory Note 💕</Text>
            <TextInput
              style={styles.formInput}
              placeholder="Title (e.g., Favorite song, First gift)..."
              placeholderTextColor="#8a739e"
              value={noteTitle}
              onChangeText={setNoteTitle}
            />
            <TextInput
              style={[styles.formInput, styles.formArea]}
              placeholder="Describe the memory in detail so Jaan AI can remember..."
              placeholderTextColor="#8a739e"
              value={noteContent}
              onChangeText={setNoteContent}
              multiline
            />
            <View style={styles.formActions}>
              <TouchableOpacity
                style={styles.formCancelBtn}
                onPress={() => setShowAddNote(false)}
              >
                <Text style={styles.formCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.formSaveBtn}
                onPress={handleAddNote}
              >
                <Text style={styles.formSaveText}>Save Memory</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Full-screen Media Modal */}
      <Modal visible={!!selectedMedia} transparent animationType="fade">
        <View style={styles.fullscreenBg}>
          <TouchableOpacity
            style={styles.fullscreenClose}
            onPress={() => setSelectedMedia(null)}
          >
            <Text style={styles.fullscreenCloseText}>✕ Close</Text>
          </TouchableOpacity>
          {selectedMedia && (
            <Image
              source={{ uri: selectedMedia }}
              style={styles.fullscreenImage}
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
  backButton: {
    width: 38,
    height: 38,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 6,
  },
  backArrow: {
    fontSize: 34,
    color: '#ff80ab',
    fontWeight: '300',
    marginTop: -4,
  },
  headerTitleGroup: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#ffffff',
  },
  headerSubtitle: {
    fontSize: 11.5,
    color: '#ff80ab',
    marginTop: 2,
  },
  tabsRow: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: 'rgba(24, 9, 38, 0.9)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 90, 160, 0.15)',
  },
  tabBtn: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 16,
    marginHorizontal: 3,
  },
  tabBtnActive: {
    backgroundColor: 'rgba(255, 59, 136, 0.25)',
    borderWidth: 1,
    borderColor: 'rgba(255, 59, 136, 0.6)',
  },
  tabText: {
    color: '#a994be',
    fontSize: 12,
    fontWeight: '600',
  },
  tabTextActive: {
    color: '#ffffff',
    fontWeight: '700',
  },
  tabContent: {
    flex: 1,
    paddingHorizontal: 14,
    paddingTop: 12,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    paddingHorizontal: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 100, 170, 0.25)',
  },
  searchInput: {
    flex: 1,
    height: 44,
    color: '#ffffff',
    fontSize: 14,
  },
  searchActionBtn: {
    padding: 6,
  },
  searchActionIcon: {
    fontSize: 16,
  },
  resultsList: {
    paddingBottom: 24,
  },
  searchCard: {
    backgroundColor: 'rgba(35, 14, 52, 0.75)',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 90, 160, 0.2)',
  },
  searchCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  senderBadge: {
    fontSize: 11,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  badgeUser: {
    backgroundColor: 'rgba(255, 59, 136, 0.3)',
    color: '#ff80ab',
  },
  badgeCompanion: {
    backgroundColor: 'rgba(168, 36, 232, 0.3)',
    color: '#e0a8ff',
  },
  dateStamp: {
    color: '#8b75a1',
    fontSize: 11,
  },
  cardContent: {
    color: '#f0e6ff',
    fontSize: 14,
    lineHeight: 20,
  },
  reactionsRow: {
    flexDirection: 'row',
    marginTop: 6,
    gap: 6,
  },
  reactionTag: {
    fontSize: 11,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    color: '#ffc1e3',
  },
  gridContent: {
    paddingBottom: 24,
  },
  photoThumbWrapper: {
    width: (width - 40) / 3,
    height: (width - 40) / 3,
    margin: 2,
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#1b0c2a',
  },
  photoThumb: {
    width: '100%',
    height: '100%',
  },
  stickerCard: {
    width: (width - 44) / 4,
    height: (width - 44) / 4,
    margin: 2,
    padding: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stickerGridImage: {
    width: '100%',
    height: '100%',
  },
  addNoteBtn: {
    marginBottom: 14,
    borderRadius: 16,
    overflow: 'hidden',
  },
  addNoteGradient: {
    paddingVertical: 12,
    alignItems: 'center',
  },
  addNoteText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  notesList: {
    paddingBottom: 24,
  },
  noteCard: {
    backgroundColor: 'rgba(35, 14, 52, 0.8)',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 120, 180, 0.25)',
  },
  noteCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  noteTitle: {
    color: '#ff80ab',
    fontSize: 15,
    fontWeight: '700',
  },
  deleteNoteIcon: {
    fontSize: 16,
  },
  noteDesc: {
    color: '#f0e6ff',
    fontSize: 13.5,
    lineHeight: 19,
    marginBottom: 6,
  },
  noteDate: {
    color: '#846e99',
    fontSize: 10.5,
  },
  modalBg: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    padding: 20,
  },
  modalForm: {
    backgroundColor: '#1d0b2e',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 90, 160, 0.4)',
  },
  modalFormTitle: {
    color: '#ffffff',
    fontSize: 17,
    fontWeight: '700',
    marginBottom: 14,
  },
  formInput: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: '#ffffff',
    fontSize: 14,
    marginBottom: 12,
  },
  formArea: {
    height: 90,
    textAlignVertical: 'top',
  },
  formActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
    marginTop: 6,
  },
  formCancelBtn: {
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  formCancelText: {
    color: '#bfa7d9',
    fontWeight: '600',
  },
  formSaveBtn: {
    backgroundColor: '#ff3b88',
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 12,
  },
  formSaveText: {
    color: '#ffffff',
    fontWeight: '700',
  },
  fullscreenBg: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fullscreenClose: {
    position: 'absolute',
    top: 50,
    right: 20,
    padding: 10,
    backgroundColor: 'rgba(255, 59, 136, 0.3)',
    borderRadius: 20,
    zIndex: 10,
  },
  fullscreenCloseText: {
    color: '#ffffff',
    fontWeight: '700',
  },
  fullscreenImage: {
    width: width * 0.92,
    height: width * 0.92,
  },
});

