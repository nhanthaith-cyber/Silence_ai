'use client';
import { useState, useEffect } from 'react';
import AppShell from '@/components/AppShell';
import { getAnalyticsOverview } from '@/lib/api';
import { AnalyticsOverview } from '@/types';
import {
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer,
  XAxis, YAxis, Tooltip, Legend
} from 'recharts';
import { MessageSquare, Bot, Clock, CheckCircle, TrendingUp, Users } from 'lucide-react';

const PLATFORM_COLORS: Record<string, string> = {
  facebook: '#1877F2',
  instagram: '#e1306c',
  shopee: '#ee4d2d',
  tiktok: '#69b4ff',
};

const PLATFORM_LABELS: Record<string, string> = {
  facebook: '📘 Facebook',
  instagram: '📷 Instagram',
  shopee: '🛍️ Shopee',
  tiktok: '🎵 TikTok',
};

const STATUS_COLORS: Record<string, string> = {
  open: '#3b82f6',
  ai_handling: '#6366f1',
  waiting_human: '#f59e0b',
  human_handling: '#10b981',
  resolved: '#6b7280',
  closed: '#374151',
};

export default function DashboardPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalyticsOverview()
      .then(setOverview)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <AppShell>
        <div className="page-header">
          <div><h1>📊 Dashboard</h1></div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
          <div className="spinner" />
        </div>
      </AppShell>
    );
  }

  const metrics = [
    {
      label: 'Tổng hội thoại',
      value: overview?.total_conversations ?? 0,
      icon: <MessageSquare size={20} />,
      color: '#6366f1',
      bg: 'rgba(99,102,241,0.15)',
      gradient: 'linear-gradient(90deg,#6366f1,#8b5cf6)',
    },
    {
      label: 'Đang mở',
      value: overview?.open_conversations ?? 0,
      icon: <Clock size={20} />,
      color: '#3b82f6',
      bg: 'rgba(59,130,246,0.15)',
      gradient: 'linear-gradient(90deg,#3b82f6,#06b6d4)',
    },
    {
      label: 'Chờ nhân viên',
      value: overview?.waiting_human ?? 0,
      icon: <Users size={20} />,
      color: '#f59e0b',
      bg: 'rgba(245,158,11,0.15)',
      gradient: 'linear-gradient(90deg,#f59e0b,#f97316)',
    },
    {
      label: 'AI tự động trả lời',
      value: `${overview?.ai_auto_reply_rate ?? 0}%`,
      icon: <Bot size={20} />,
      color: '#10b981',
      bg: 'rgba(16,185,129,0.15)',
      gradient: 'linear-gradient(90deg,#10b981,#06b6d4)',
    },
  ];

  const platformData = (overview?.platform_stats ?? []).map(p => ({
    name: PLATFORM_LABELS[p.platform] || p.platform,
    value: p.count,
    color: PLATFORM_COLORS[p.platform] || '#6366f1',
  }));

  const statusData = (overview?.status_stats ?? [])
    .filter(s => s.count > 0)
    .map(s => ({
      name: s.status,
      value: s.count,
      color: STATUS_COLORS[s.status] || '#6366f1',
    }));

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h1>📊 Dashboard Analytics</h1>
          <div className="subtitle">Tổng quan hiệu suất hệ thống chăm sóc khách hàng</div>
        </div>
      </div>

      <div style={{ overflow: 'auto', height: 'calc(100vh - 65px)' }}>
        {/* Metric Cards */}
        <div className="dashboard-grid">
          {metrics.map((m, i) => (
            <div key={i} className="metric-card animate-fadeIn" style={{
              '--gradient': m.gradient,
              animationDelay: `${i * 80}ms`
            } as React.CSSProperties}>
              <div className="metric-icon" style={{ background: m.bg }}>
                <span style={{ color: m.color }}>{m.icon}</span>
              </div>
              <div className="metric-value">{m.value}</div>
              <div className="metric-label">{m.label}</div>
            </div>
          ))}
        </div>

        {/* Charts Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', padding: '0 24px 24px' }}>
          {/* Platform Distribution */}
          <div className="chart-container">
            <div className="chart-title">📱 Phân bổ theo nền tảng</div>
            {platformData.every(d => d.value === 0) ? (
              <div className="empty-state" style={{ height: 200 }}>
                <p>Chưa có dữ liệu. Hãy dùng Shopee/TikTok Mock.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={platformData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <XAxis dataKey="name" tick={{ fill: '#8892a4', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#8892a4', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: '#1a1d2e',
                      border: '1px solid #252840',
                      borderRadius: 8,
                      color: '#e2e8f0'
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {platformData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Status Distribution */}
          <div className="chart-container">
            <div className="chart-title">📊 Trạng thái hội thoại</div>
            {statusData.length === 0 ? (
              <div className="empty-state" style={{ height: 200 }}>
                <p>Chưa có dữ liệu</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#1a1d2e',
                      border: '1px solid #252840',
                      borderRadius: 8,
                      color: '#e2e8f0'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Summary Stats */}
        <div style={{ padding: '0 24px 24px', display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16 }}>
          {[
            { label: '💬 Tổng tin nhắn', value: overview?.total_messages ?? 0 },
            { label: '🤖 Tin AI tạo ra', value: overview?.ai_messages ?? 0 },
            { label: '✅ Đã giải quyết', value: overview?.resolved_today ?? 0 },
          ].map((stat, i) => (
            <div key={i} className="metric-card" style={{ '--gradient': 'linear-gradient(90deg,#6366f1,#8b5cf6)' } as React.CSSProperties}>
              <div className="metric-value">{stat.value}</div>
              <div className="metric-label">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
