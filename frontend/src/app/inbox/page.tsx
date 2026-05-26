'use client';
import { useState, useEffect, useCallback } from 'react';
import AppShell from '@/components/AppShell';
import ConversationList from '@/components/inbox/ConversationList';
import ChatWindow from '@/components/chat/ChatWindow';
import { getConversations, simulateShopeeMock, simulateTikTokMock } from '@/lib/api';
import { getSocket } from '@/lib/socket';
import { Conversation } from '@/types';
import toast from 'react-hot-toast';
import { Search, Filter, Zap, MessageSquare, RefreshCw } from 'lucide-react';

const PLATFORMS = ['all', 'facebook', 'instagram', 'shopee', 'tiktok'];
const STATUSES = ['all', 'open', 'ai_handling', 'waiting_human', 'human_handling', 'resolved'];

const STATUS_LABELS: Record<string, string> = {
  all: 'Tất cả', open: 'Mở', ai_handling: 'AI đang xử lý',
  waiting_human: 'Chờ NV', human_handling: 'NV đang xử lý', resolved: 'Đã xong'
};

const PLATFORM_LABELS: Record<string, string> = {
  all: '🌐 Tất cả', facebook: '📘 Facebook', instagram: '📷 Instagram',
  shopee: '🛍️ Shopee', tiktok: '🎵 TikTok'
};

export default function InboxPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [platform, setPlatform] = useState('all');
  const [status, setStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);

  const loadConversations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getConversations({ platform, status, search });
      setConversations(data.items);
    } catch {
      toast.error('Không tải được danh sách hội thoại');
    } finally {
      setLoading(false);
    }
  }, [platform, status, search]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Real-time socket updates
  useEffect(() => {
    const socket = getSocket();
    socket.on('conversation_updated', () => loadConversations());
    return () => { socket.off('conversation_updated'); };
  }, [loadConversations]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(loadConversations, 10000);
    return () => clearInterval(interval);
  }, [loadConversations]);

  async function simulate(type: 'shopee' | 'tiktok') {
    setSimulating(true);
    try {
      if (type === 'shopee') await simulateShopeeMock();
      else await simulateTikTokMock();
      toast.success(`Đã tạo tin nhắn mock từ ${type === 'shopee' ? '🛍️ Shopee' : '🎵 TikTok'}`);
      await loadConversations();
    } catch {
      toast.error('Lỗi khi simulate');
    } finally {
      setSimulating(false);
    }
  }

  const waitingCount = conversations.filter(c => c.status === 'waiting_human').length;
  const unreadTotal = conversations.reduce((s, c) => s + (c.unread_count || 0), 0);

  return (
    <AppShell>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>
            📬 Unified Inbox
            {unreadTotal > 0 && (
              <span style={{
                marginLeft: 8, background: 'var(--accent-primary)',
                color: 'white', fontSize: 11, padding: '2px 8px',
                borderRadius: 'var(--radius-full)', fontWeight: 700
              }}>{unreadTotal}</span>
            )}
          </h1>
          <div className="subtitle">
            {conversations.length} hội thoại • {waitingCount > 0 && (
              <span style={{ color: 'var(--yellow)' }}>{waitingCount} chờ nhân viên</span>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="sim-btn"
            onClick={() => simulate('shopee')}
            disabled={simulating}
            title="Tạo tin nhắn Shopee mock"
          >
            🛍️ Shopee Mock
          </button>
          <button
            className="sim-btn"
            onClick={() => simulate('tiktok')}
            disabled={simulating}
            title="Tạo tin nhắn TikTok mock"
          >
            🎵 TikTok Mock
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={loadConversations}
            title="Làm mới"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Inbox Layout */}
      <div className="inbox-layout">
        {/* Left Panel - Conversation List */}
        <div className="conversation-list-panel">
          {/* Search */}
          <div className="list-header">
            <div className="search-bar">
              <Search size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              <input
                type="text"
                placeholder="Tìm kiếm hội thoại..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              {loading && <div className="spinner" style={{ width: 14, height: 14 }} />}
            </div>
          </div>

          {/* Platform Filter */}
          <div className="filter-tabs">
            {PLATFORMS.map(p => (
              <button
                key={p}
                className={`filter-tab ${platform === p ? 'active' : ''}`}
                onClick={() => setPlatform(p)}
              >
                {PLATFORM_LABELS[p]}
              </button>
            ))}
          </div>

          {/* Status Filter */}
          <div className="filter-tabs" style={{ paddingTop: 8 }}>
            {STATUSES.slice(0, 4).map(s => (
              <button
                key={s}
                className={`filter-tab ${status === s ? 'active' : ''}`}
                onClick={() => setStatus(s)}
              >
                {STATUS_LABELS[s]}
              </button>
            ))}
          </div>

          {/* List */}
          <ConversationList
            conversations={conversations}
            selectedId={selectedConv?.id || null}
            onSelect={conv => setSelectedConv(conv)}
          />
        </div>

        {/* Right Panel - Chat */}
        <div>
          {selectedConv ? (
            <ChatWindow
              conversation={selectedConv}
              onUpdate={() => {
                loadConversations();
                // Update selected conv status
                setConversations(prev =>
                  prev.map(c => c.id === selectedConv.id
                    ? { ...c }
                    : c
                  )
                );
              }}
            />
          ) : (
            <div className="empty-state" style={{ height: '100%' }}>
              <div className="empty-state-icon">
                <MessageSquare size={56} strokeWidth={1} />
              </div>
              <h3>Chọn một hội thoại</h3>
              <p>Chọn từ danh sách bên trái để xem tin nhắn</p>
              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                <button className="sim-btn" onClick={() => simulate('shopee')}>
                  🛍️ Tạo tin Shopee
                </button>
                <button className="sim-btn" onClick={() => simulate('tiktok')}>
                  🎵 Tạo tin TikTok
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
