import { Conversation } from '@/types';

const PLATFORM_CONFIG = {
  facebook: { label: 'FB', icon: '📘', color: '#1877F2', bg: '#1877F2' },
  instagram: { label: 'IG', icon: '📷', color: '#e1306c', bg: 'linear-gradient(135deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)' },
  shopee: { label: 'SP', icon: '🛍️', color: '#ee4d2d', bg: '#ee4d2d' },
  tiktok: { label: 'TT', icon: '🎵', color: '#69b4ff', bg: '#010101' },
};

const STATUS_LABELS: Record<string, string> = {
  open: 'Mở',
  ai_handling: 'AI',
  waiting_human: 'Chờ NV',
  human_handling: 'NV',
  resolved: 'Xong',
  closed: 'Đóng',
};

function timeAgo(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const diff = Math.floor((now.getTime() - then.getTime()) / 1000);

  if (diff < 60) return 'Vừa xong';
  if (diff < 3600) return `${Math.floor(diff / 60)} phút`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ`;
  return `${Math.floor(diff / 86400)} ngày`;
}

function getAvatarColor(name: string): string {
  const colors = ['#6366f1','#8b5cf6','#ec4899','#06b6d4','#10b981','#f59e0b','#ef4444'];
  return colors[name.charCodeAt(0) % colors.length];
}

interface Props {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (conv: Conversation) => void;
}

export default function ConversationList({ conversations, selectedId, onSelect }: Props) {
  if (conversations.length === 0) {
    return (
      <div className="empty-state" style={{ height: '300px' }}>
        <div className="empty-state-icon">💬</div>
        <h3>Chưa có tin nhắn</h3>
        <p>Dùng nút Simulate để tạo dữ liệu demo</p>
      </div>
    );
  }

  return (
    <div className="conversation-list">
      {conversations.map((conv, i) => {
        const platform = PLATFORM_CONFIG[conv.platform] || PLATFORM_CONFIG.facebook;
        const isActive = conv.id === selectedId;
        const isUnread = conv.unread_count > 0;
        const initial = conv.customer_name.charAt(0).toUpperCase();

        return (
          <div
            key={conv.id}
            className={`conversation-item ${isActive ? 'active' : ''} ${isUnread ? 'unread' : ''} animate-slideIn`}
            style={{ animationDelay: `${i * 30}ms` }}
            onClick={() => onSelect(conv)}
          >
            {/* Avatar */}
            <div className="conv-avatar" style={{ background: getAvatarColor(conv.customer_name) }}>
              {initial}
              <div
                className="platform-dot"
                style={{ background: platform.bg }}
                title={conv.platform}
              >
                <span style={{ fontSize: '8px' }}>{platform.label}</span>
              </div>
            </div>

            {/* Info */}
            <div className="conv-info">
              <div className="conv-header">
                <span className="conv-name">{conv.customer_name}</span>
                <span className="conv-time">{conv.last_message_at ? timeAgo(conv.last_message_at) : ''}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="conv-preview">{conv.last_message}</span>
                {isUnread && <span className="unread-badge">{conv.unread_count}</span>}
              </div>
              <div style={{ marginTop: '4px' }}>
                <span className={`status-badge status-${conv.status}`}>
                  {STATUS_LABELS[conv.status] || conv.status}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
