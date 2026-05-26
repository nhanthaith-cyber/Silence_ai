'use client';
import { useState, useEffect } from 'react';
import AppShell from '@/components/AppShell';
import { getAgentConfigs, updateAgentConfig } from '@/lib/api';
import { AgentConfig } from '@/types';
import toast from 'react-hot-toast';
import { Save, Bot, Link, AlertCircle } from 'lucide-react';

export default function SettingsPage() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [activeAgent, setActiveAgent] = useState<AgentConfig | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getAgentConfigs().then(data => {
      setAgents(data);
      if (data.length > 0) setActiveAgent(data[0]);
    });
  }, []);

  async function saveAgent() {
    if (!activeAgent) return;
    setSaving(true);
    try {
      await updateAgentConfig(activeAgent.id, {
        name: activeAgent.name,
        system_prompt: activeAgent.system_prompt,
        temperature: activeAgent.temperature,
        auto_reply: activeAgent.auto_reply,
        confidence_threshold: activeAgent.confidence_threshold,
        greeting_message: activeAgent.greeting_message,
      });
      toast.success('✅ Đã lưu cấu hình AI Agent');
    } catch {
      toast.error('Lỗi khi lưu');
    } finally {
      setSaving(false);
    }
  }

  function update(field: keyof AgentConfig, value: unknown) {
    setActiveAgent(prev => prev ? { ...prev, [field]: value } : prev);
  }

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h1>⚙️ Cài đặt hệ thống</h1>
          <div className="subtitle">Cấu hình AI Agent và kết nối nền tảng</div>
        </div>
        <button className="btn btn-primary" onClick={saveAgent} disabled={saving}>
          {saving ? <div className="spinner" style={{ width: 16, height: 16 }} /> : <Save size={16} />}
          Lưu thay đổi
        </button>
      </div>

      <div className="settings-layout">
        {/* AI Agent Config */}
        <div className="settings-section">
          <div className="settings-title">
            <Bot size={16} style={{ display: 'inline', marginRight: 8 }} />
            Cấu hình AI Agent
          </div>

          {activeAgent && (
            <>
              <div className="form-group">
                <label className="form-label">Tên Agent</label>
                <input
                  className="form-input"
                  value={activeAgent.name}
                  onChange={e => update('name', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">System Prompt (Hướng dẫn cho AI)</label>
                <textarea
                  className="form-textarea"
                  value={activeAgent.system_prompt}
                  onChange={e => update('system_prompt', e.target.value)}
                  style={{ minHeight: 150 }}
                />
                <div className="hint">Đây là hướng dẫn cơ bản mà AI sẽ dùng khi trả lời khách hàng</div>
              </div>

              <div className="form-group">
                <label className="form-label">Lời chào mặc định</label>
                <input
                  className="form-input"
                  value={activeAgent.greeting_message || ''}
                  onChange={e => update('greeting_message', e.target.value)}
                  placeholder="Xin chào! Mình có thể giúp gì cho bạn? 😊"
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">
                    Temperature: <strong>{activeAgent.temperature}</strong>
                  </label>
                  <input
                    type="range"
                    min="0" max="1" step="0.1"
                    value={activeAgent.temperature}
                    onChange={e => update('temperature', parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
                  />
                  <div className="hint">0 = chính xác hơn, 1 = sáng tạo hơn</div>
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Ngưỡng handoff: <strong>{Math.round(activeAgent.confidence_threshold * 100)}%</strong>
                  </label>
                  <input
                    type="range"
                    min="0.3" max="0.95" step="0.05"
                    value={activeAgent.confidence_threshold}
                    onChange={e => update('confidence_threshold', parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
                  />
                  <div className="hint">Dưới mức này → chuyển tay nhân viên</div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderTop: '1px solid var(--border)', marginTop: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>Tự động trả lời</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>AI sẽ tự động phản hồi tin nhắn mới</div>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={activeAgent.auto_reply}
                    onChange={e => update('auto_reply', e.target.checked)}
                  />
                  <span className="toggle-slider" />
                </label>
              </div>
            </>
          )}
        </div>

        {/* Platform Connections */}
        <div className="settings-section">
          <div className="settings-title">
            <Link size={16} style={{ display: 'inline', marginRight: 8 }} />
            Kết nối nền tảng
          </div>

          {[
            {
              platform: 'Facebook Messenger',
              icon: '📘',
              status: 'Cần cấu hình',
              color: '#1877F2',
              fields: ['FACEBOOK_PAGE_TOKEN', 'FACEBOOK_APP_SECRET', 'FACEBOOK_VERIFY_TOKEN']
            },
            {
              platform: 'Instagram DM',
              icon: '📷',
              status: 'Cần cấu hình',
              color: '#e1306c',
              fields: ['INSTAGRAM_ACCESS_TOKEN']
            },
            {
              platform: 'Shopee',
              icon: '🛍️',
              status: '⚡ Mock (Demo)',
              color: '#ee4d2d',
              fields: ['SHOPEE_PARTNER_ID', 'SHOPEE_PARTNER_KEY']
            },
            {
              platform: 'TikTok Shop',
              icon: '🎵',
              status: '⚡ Mock (Demo)',
              color: '#69b4ff',
              fields: ['TIKTOK_APP_KEY', 'TIKTOK_APP_SECRET']
            },
          ].map((p, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              padding: '14px 0',
              borderBottom: '1px solid var(--border)'
            }}>
              <div style={{
                width: 44, height: 44,
                background: `${p.color}20`,
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 20,
                flexShrink: 0
              }}>
                {p.icon}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{p.platform}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  Biến môi trường: {p.fields.join(', ')}
                </div>
              </div>
              <div style={{
                fontSize: 11, fontWeight: 600,
                color: p.status.includes('Mock') ? 'var(--yellow)' : 'var(--text-muted)',
                padding: '3px 10px',
                background: p.status.includes('Mock') ? 'rgba(245,158,11,0.1)' : 'var(--bg-secondary)',
                borderRadius: 'var(--radius-full)',
                border: `1px solid ${p.status.includes('Mock') ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`
              }}>
                {p.status}
              </div>
            </div>
          ))}

          <div style={{
            marginTop: 16,
            background: 'rgba(99,102,241,0.08)',
            border: '1px solid rgba(99,102,241,0.2)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            fontSize: 12,
            color: 'var(--text-secondary)',
            display: 'flex',
            gap: 8
          }}>
            <AlertCircle size={14} style={{ color: 'var(--accent-primary)', flexShrink: 0, marginTop: 2 }} />
            <div>
              Cấu hình API keys trong file <code style={{ background: 'var(--bg-primary)', padding: '1px 6px', borderRadius: 4 }}>backend/.env</code>.
              Xem hướng dẫn chi tiết trong <code>backend/.env.example</code>.
            </div>
          </div>
        </div>

        {/* OpenAI Config */}
        <div className="settings-section">
          <div className="settings-title">🤖 OpenAI API</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            <p>Hệ thống sử dụng <strong>OpenAI GPT-4o mini</strong> cho AI responses.</p>
            <p style={{ marginTop: 8 }}>
              Nếu chưa có API key, hệ thống sẽ dùng <strong>mock responses</strong> để demo.
              Lấy API key tại: <a href="https://platform.openai.com" target="_blank" style={{ color: 'var(--accent-primary)' }}>platform.openai.com</a>
            </p>
          </div>
          <div style={{ marginTop: 12, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', fontFamily: 'monospace', fontSize: 12, color: 'var(--green)' }}>
            OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
          </div>
        </div>
      </div>
    </AppShell>
  );
}
