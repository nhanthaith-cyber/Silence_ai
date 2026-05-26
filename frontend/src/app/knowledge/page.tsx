'use client';
import { useState, useEffect, useRef } from 'react';
import AppShell from '@/components/AppShell';
import { getKnowledge, createKnowledge, updateKnowledge, deleteKnowledge, getDocuments, uploadDocument, deleteDocument } from '@/lib/api';
import { KnowledgeItem, Document } from '@/types';
import toast from 'react-hot-toast';
import { Plus, Edit2, Trash2, Search, BookOpen, FileText, UploadCloud, File as FileIcon } from 'lucide-react';

const CATEGORIES = [
  { value: 'all', label: '📚 Tất cả' },
  { value: 'order', label: '📦 Đơn hàng' },
  { value: 'return', label: '🔄 Đổi trả' },
  { value: 'shipping', label: '🚚 Vận chuyển' },
  { value: 'product', label: '🛍️ Sản phẩm' },
  { value: 'payment', label: '💳 Thanh toán' },
  { value: 'general', label: '💬 Chung' },
];

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<'faq' | 'documents'>('faq');
  
  // FAQ state
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<KnowledgeItem | null>(null);
  const [form, setForm] = useState({ category: 'general', question: '', answer: '', tags: '' });

  // Document state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (activeTab === 'faq') {
      loadItems();
    } else {
      loadDocuments();
    }
  }, [category, search, activeTab]);

  async function loadItems() {
    try {
      const data = await getKnowledge({ category: category !== 'all' ? category : undefined, search });
      setItems(data);
    } catch {}
  }

  async function loadDocuments() {
    try {
      const data = await getDocuments();
      setDocuments(data);
    } catch {}
  }

  // --- FAQ Handlers ---
  async function handleSubmitFAQ() {
    if (!form.question.trim() || !form.answer.trim()) {
      return toast.error('Vui lòng điền đầy đủ câu hỏi và câu trả lời');
    }
    try {
      if (editingItem) {
        await updateKnowledge(editingItem.id, form);
        toast.success('Đã cập nhật FAQ');
      } else {
        await createKnowledge(form);
        toast.success('Đã thêm FAQ mới');
      }
      setShowForm(false);
      setEditingItem(null);
      setForm({ category: 'general', question: '', answer: '', tags: '' });
      loadItems();
    } catch {
      toast.error('Lỗi khi lưu FAQ');
    }
  }

  async function handleDeleteFAQ(id: string) {
    if (!confirm('Xóa FAQ này?')) return;
    try {
      await deleteKnowledge(id);
      toast.success('Đã xóa FAQ');
      loadItems();
    } catch { toast.error('Lỗi khi xóa FAQ'); }
  }

  function startEditFAQ(item: KnowledgeItem) {
    setEditingItem(item);
    setForm({ category: item.category, question: item.question, answer: item.answer, tags: item.tags });
    setShowForm(true);
  }

  // --- Document Handlers ---
  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Check extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['txt', 'pdf', 'docx'].includes(ext || '')) {
      return toast.error('Chỉ hỗ trợ file .txt, .pdf, .docx');
    }
    
    setIsUploading(true);
    const loadingToast = toast.loading('Đang xử lý tài liệu và tạo vector embeddings...');
    
    try {
      await uploadDocument(file);
      toast.success('Đã học xong tài liệu!', { id: loadingToast });
      loadDocuments();
    } catch (err: any) {
      toast.error(err.message || 'Lỗi khi upload', { id: loadingToast });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleDeleteDocument(id: string) {
    if (!confirm('Xóa tài liệu này? Hệ thống AI sẽ không còn sử dụng thông tin trong tài liệu này nữa.')) return;
    try {
      await deleteDocument(id);
      toast.success('Đã xóa tài liệu');
      loadDocuments();
    } catch { toast.error('Lỗi khi xóa tài liệu'); }
  }

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h1>📚 Knowledge Base</h1>
          <div className="subtitle">Quản lý nguồn tri thức (FAQs & Tài liệu) để AI tự động học</div>
        </div>
        <div>
          <div style={{ display: 'flex', gap: 8, background: 'var(--bg-secondary)', padding: 4, borderRadius: 'var(--radius-md)' }}>
            <button 
              className={`btn ${activeTab === 'faq' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setActiveTab('faq')}
              style={{ padding: '6px 12px', fontSize: 13 }}
            >
              Hỏi đáp (FAQ)
            </button>
            <button 
              className={`btn ${activeTab === 'documents' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setActiveTab('documents')}
              style={{ padding: '6px 12px', fontSize: 13 }}
            >
              Tài liệu (RAG)
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'faq' ? (
        <div className="kb-grid">
          {/* Sidebar */}
          <div className="kb-sidebar">
            <div style={{ marginBottom: 16 }}>
              <div className="search-bar">
                <Search size={14} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Tìm kiếm FAQ..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>
            </div>

            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
              Danh mục FAQ
            </div>
            {CATEGORIES.map(cat => (
              <button
                key={cat.value}
                onClick={() => setCategory(cat.value)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 13,
                  color: category === cat.value ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  background: category === cat.value ? 'var(--accent-glow)' : 'transparent',
                  transition: 'var(--transition)',
                  marginBottom: 2
                }}
              >
                {cat.label}
              </button>
            ))}

            <div className="divider" />
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {items.length} mục FAQ
            </div>
          </div>

          {/* Main */}
          <div className="kb-main">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <h3 style={{ fontSize: 16, margin: 0 }}>Danh sách câu hỏi mẫu</h3>
              <button
                className="btn btn-primary"
                onClick={() => { setEditingItem(null); setForm({ category: 'general', question: '', answer: '', tags: '' }); setShowForm(true); }}
                style={{ padding: '6px 12px', fontSize: 13 }}
              >
                <Plus size={14} /> Thêm FAQ
              </button>
            </div>

            {items.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon"><BookOpen size={48} strokeWidth={1} /></div>
                <h3>Chưa có FAQ nào</h3>
                <p>Thêm câu hỏi và câu trả lời để AI học nhanh</p>
                <button className="btn btn-primary" onClick={() => setShowForm(true)} style={{ marginTop: 12 }}>
                  <Plus size={16} /> Thêm FAQ đầu tiên
                </button>
              </div>
            ) : (
              items.map((item, i) => (
                <div key={item.id} className="kb-card animate-fadeIn" style={{ animationDelay: `${i * 40}ms` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                        <span style={{
                          background: 'var(--accent-glow)', color: 'var(--accent-primary)',
                          fontSize: 10, padding: '2px 8px', borderRadius: 'var(--radius-full)', fontWeight: 600
                        }}>
                          {item.category}
                        </span>
                        {!item.is_active && (
                          <span style={{
                            background: 'rgba(245,158,11,0.2)', color: '#f59e0b', border: '1px solid #f59e0b',
                            fontSize: 10, padding: '1px 6px', borderRadius: '4px', fontWeight: 600
                          }}>
                            [Bản Nháp] Cần duyệt
                          </span>
                        )}
                        {item.tags?.includes('training') && (
                          <span style={{ color: 'var(--text-muted)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                            🎓 Từ nhân viên dạy
                          </span>
                        )}
                      </div>
                      <div className="kb-question">❓ {item.question}</div>
                      <div className="kb-answer">💬 {item.answer}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                      <button 
                        className={`btn ${item.is_active ? 'btn-secondary' : 'btn-success'} btn-sm`} 
                        onClick={async () => {
                          try {
                            await updateKnowledge(item.id, { is_active: !item.is_active });
                            toast.success(item.is_active ? 'Đã tắt' : 'Đã duyệt & Bật');
                            loadItems();
                          } catch { toast.error('Lỗi cập nhật'); }
                        }}
                        style={{ padding: '0 8px', height: 28 }}
                        title={item.is_active ? 'Tắt' : 'Duyệt & Bật'}
                      >
                        {item.is_active ? 'Tắt' : 'Duyệt'}
                      </button>
                      <button className="btn btn-secondary btn-icon" onClick={() => startEditFAQ(item)} title="Sửa" style={{ height: 28, width: 28 }}>
                        <Edit2 size={13} />
                      </button>
                      <button className="btn btn-danger btn-icon" onClick={() => handleDeleteFAQ(item.id)} title="Xóa">
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      ) : (
        <div className="kb-main" style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', gap: 24 }}>
            {/* Upload Section */}
            <div style={{ flex: 1, maxWidth: 300 }}>
              <div className="settings-card" style={{ textAlign: 'center', padding: 24, background: 'var(--bg-secondary)' }}>
                <UploadCloud size={48} style={{ color: 'var(--accent-primary)', margin: '0 auto 16px' }} />
                <h3 style={{ margin: '0 0 8px 0', fontSize: 16 }}>Tải lên tài liệu</h3>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
                  Hỗ trợ định dạng .txt, .pdf, .docx. <br/>
                  AI sẽ tự động đọc, trích xuất và lưu trữ để tìm kiếm.
                </p>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileUpload} 
                  style={{ display: 'none' }}
                  accept=".txt,.pdf,.docx"
                />
                <button 
                  className="btn btn-primary" 
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                >
                  {isUploading ? 'Đang xử lý...' : 'Chọn File Upload'}
                </button>
              </div>
            </div>

            {/* Document List */}
            <div style={{ flex: 2 }}>
              <h3 style={{ fontSize: 16, margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
                <FileText size={18} />
                Tài liệu đã học
              </h3>
              
              {documents.length === 0 ? (
                <div className="empty-state" style={{ minHeight: 200 }}>
                  <FileIcon size={32} style={{ color: 'var(--border-color)' }} />
                  <p style={{ marginTop: 12 }}>Chưa có tài liệu nào được tải lên.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {documents.map((doc, i) => (
                    <div key={doc.id} className="kb-card animate-fadeIn" style={{ animationDelay: `${i * 40}ms`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div style={{ width: 40, height: 40, borderRadius: 8, background: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <FileIcon size={20} style={{ color: 'var(--accent-primary)' }} />
                        </div>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{doc.filename}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                            {new Date(doc.created_at || '').toLocaleString('vi-VN')}
                          </div>
                        </div>
                      </div>
                      <button className="btn btn-danger btn-icon" onClick={() => handleDeleteDocument(doc.id)} title="Xóa tài liệu">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* FAQ Form Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ minWidth: 520 }}>
            <div className="modal-title">
              {editingItem ? '✏️ Sửa FAQ' : '➕ Thêm FAQ mới'}
            </div>

            <div className="form-group">
              <label className="form-label">Danh mục</label>
              <select
                className="form-select"
                value={form.category}
                onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              >
                {CATEGORIES.filter(c => c.value !== 'all').map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Câu hỏi của khách *</label>
              <input
                className="form-input"
                value={form.question}
                onChange={e => setForm(f => ({ ...f, question: e.target.value }))}
                placeholder="Ví dụ: Chính sách đổi trả của shop như thế nào?"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Câu trả lời của AI *</label>
              <textarea
                className="form-textarea"
                value={form.answer}
                onChange={e => setForm(f => ({ ...f, answer: e.target.value }))}
                placeholder="Câu trả lời đầy đủ và chi tiết..."
                style={{ minHeight: 120 }}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Từ khóa ưu tiên (Tags)</label>
              <input
                className="form-input"
                value={form.tags}
                onChange={e => setForm(f => ({ ...f, tags: e.target.value }))}
                placeholder="VD: mở cửa, vịt cao su, địa chỉ (cách nhau bởi dấu phẩy)"
              />
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Nếu khách nhắn chứa các từ này, AI sẽ ưu tiên trả lời bằng câu này (cộng thêm điểm).
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowForm(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={handleSubmitFAQ}>
                {editingItem ? '💾 Cập nhật' : '➕ Thêm mới'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
