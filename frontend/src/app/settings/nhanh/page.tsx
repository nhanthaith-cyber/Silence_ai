'use client';
import { useState, useEffect } from 'react';
import AppShell from '@/components/AppShell';
import toast from 'react-hot-toast';

export default function NhanhSettingsPage() {
  const [businessId, setBusinessId] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    async function loadConfig() {
      try {
        const res = await fetch('http://localhost:8000/api/nhanh/config');
        const data = await res.json();
        if (data.configured) {
          setBusinessId(data.business_id);
          setAccessToken(data.access_token);
        }
      } catch (e) {
        toast.error('Lỗi khi tải cấu hình Nhanh.vn');
      } finally {
        setFetching(false);
      }
    }
    loadConfig();
  }, []);

  const handleSave = async () => {
    if (!businessId || !accessToken) {
      toast.error('Vui lòng nhập đầy đủ thông tin');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/nhanh/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_id: businessId, access_token: accessToken }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        toast.success(data.message);
      } else {
        toast.error(data.message || 'Lỗi lưu cấu hình');
      }
    } catch (e) {
      toast.error('Lỗi kết nối máy chủ');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h1>Cấu hình Nhanh.vn</h1>
          <div className="subtitle">Quản lý kết nối tồn kho Nhanh.vn (V2 API)</div>
        </div>
      </div>

      <div style={{ padding: '24px', maxWidth: '600px', margin: '0 auto' }}>
        <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <h2 style={{ fontSize: '16px', marginBottom: '16px', fontWeight: 600 }}>Cài đặt API Nhanh.vn</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: '13px' }}>
            Để lấy được Token này, anh cần cấu hình Webhook/App trên Nhanh.vn hoặc xin trực tiếp từ bộ phận kỹ thuật.
          </p>

          {fetching ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>Đang tải...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px', fontWeight: 500 }}>Business ID (ID doanh nghiệp)</label>
                <input 
                  type="text" 
                  value={businessId}
                  onChange={(e) => setBusinessId(e.target.value)}
                  placeholder="Ví dụ: 123456"
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'var(--bg-primary)' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px', fontWeight: 500 }}>Access Token (Nhanh.vn V2)</label>
                <input 
                  type="text" 
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  placeholder="Nhập access token..."
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'var(--bg-primary)' }}
                />
              </div>

              <button 
                onClick={handleSave}
                disabled={loading}
                style={{ 
                  marginTop: '16px',
                  padding: '12px', 
                  background: 'var(--accent-primary)', 
                  color: 'white', 
                  borderRadius: 'var(--radius-md)',
                  fontWeight: 600,
                  opacity: loading ? 0.7 : 1
                }}
              >
                {loading ? 'Đang lưu...' : 'Lưu cấu hình'}
              </button>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
