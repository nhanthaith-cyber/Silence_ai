'use client';
import { useState, useEffect, useRef } from 'react';
import { Message, Conversation, CustomerMemory } from '@/types';
import { getMessages, sendMessage, sendMockInboundMessage, handoffConversation, resolveConversation, createKnowledge, getCustomerMemory } from '@/lib/api';
import { getSocket } from '@/lib/socket';
import toast from 'react-hot-toast';
import { Send, UserCheck, CheckCircle, Bot, Zap, GraduationCap, X, Check, Image as ImageIcon } from 'lucide-react';

function formatTime(dateStr: string) {
  return new Date(dateStr).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

const PLATFORM_LABELS: Record<string, string> = {
  facebook: '📘 Facebook',
  instagram: '📷 Instagram',
  shopee: '🛍️ Shopee',
  tiktok: '🎵 TikTok',
};

interface Props {
  conversation: Conversation;
  onUpdate: () => void;
}

export default function ChatWindow({ conversation, onUpdate }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isAiTyping, setIsAiTyping] = useState(false);
  const [showHandoff, setShowHandoff] = useState(false);
  const [agentName, setAgentName] = useState('');
  const [handoffNote, setHandoffNote] = useState('');
  const [sending, setSending] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageBase64, setImageBase64] = useState<string>('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Teach AI Mode States
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<Message | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<Message | null>(null);
  const [showTeachModal, setShowTeachModal] = useState(false);
  const [teachForm, setTeachForm] = useState({ question: '', answer: '' });
  const [memory, setMemory] = useState<CustomerMemory | null>(null);

  useEffect(() => {
    getCustomerMemory(conversation.customer_id, conversation.platform)
      .then(setMemory)
      .catch(() => setMemory(null));
  }, [conversation.customer_id, conversation.platform]);

  useEffect(() => {
    loadMessages();
    const socket = getSocket();
    socket.emit('join_conversation', { conversation_id: conversation.id });
    socket.on('new_message', (msg: Message) => {
      if (msg.conversation_id === conversation.id) {
        setMessages(prev => {
          if (prev.find(m => m.id === msg.id)) return prev;
          return [...prev, msg];
        });
      }
    });
    socket.on('ai_typing', (data: { typing: boolean }) => setIsAiTyping(data.typing));

    return () => {
      socket.off('new_message');
      socket.off('ai_typing');
    };
  }, [conversation.id]);

  useEffect(() => {
    if (!isSelectMode) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isAiTyping, isSelectMode]);

  async function loadMessages() {
    try {
      const data = await getMessages(conversation.id);
      setMessages(data);
    } catch {}
  }

  async function handleSend() {
    if ((!inputText.trim() && !imageBase64) || sending) return;
    setSending(true);
    try {
      const text = inputText.trim();
      if (text.startsWith('/khach ')) {
        const customerMsg = text.replace('/khach ', '');
        await sendMockInboundMessage(conversation.id, customerMsg, imageBase64);
      } else {
        await sendMessage(conversation.id, text, imageBase64);
      }
      setInputText('');
      setImageFile(null);
      setImageBase64('');
      onUpdate();
    } catch {
      toast.error('Gửi tin nhắn thất bại');
    } finally {
      setSending(false);
    }
  }

  async function handleHandoff() {
    if (!agentName.trim()) return toast.error('Nhập tên nhân viên');
    try {
      await handoffConversation(conversation.id, agentName, handoffNote);
      toast.success(`Đã chuyển cho ${agentName}`);
      setShowHandoff(false);
      onUpdate();
    } catch {
      toast.error('Chuyển tay thất bại');
    }
  }

  async function handleResolve() {
    try {
      await resolveConversation(conversation.id);
      toast.success('Đã đánh dấu là đã giải quyết');
      onUpdate();
    } catch {
      toast.error('Lỗi');
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (file.size > 5 * 1024 * 1024) {
      return toast.error('Kích thước ảnh tối đa là 5MB');
    }
    
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => {
      if (ev.target?.result) {
        setImageBase64(ev.target.result.toString());
      }
    };
    reader.readAsDataURL(file);
  }

  // --- Teach AI logic ---
  function handleToggleSelectMode() {
    setIsSelectMode(!isSelectMode);
    setSelectedQuestion(null);
    setSelectedAnswer(null);
  }

  function handleMessageSelect(msg: Message) {
    if (!isSelectMode) return;
    
    if (msg.direction === 'inbound') {
      setSelectedQuestion(msg);
    } else {
      setSelectedAnswer(msg);
    }
  }

  function openTeachModal() {
    if (!selectedQuestion || !selectedAnswer) {
      return toast.error('Vui lòng chọn 1 câu hỏi (khách) và 1 câu trả lời (nhân viên/AI)');
    }
    setTeachForm({
      question: selectedQuestion.content,
      answer: selectedAnswer.content
    });
    setShowTeachModal(true);
  }

  async function handleSaveTeach() {
    if (!teachForm.question.trim() || !teachForm.answer.trim()) {
      return toast.error('Vui lòng điền đủ câu hỏi và trả lời');
    }
    try {
      await createKnowledge({
        category: 'general',
        question: teachForm.question,
        answer: teachForm.answer,
        tags: 'training, human_handoff',
        is_active: false // Lưu dưới dạng nháp (cần duyệt)
      });
      toast.success('Đã lưu bài học vào Nháp! Hãy chờ Quản lý duyệt.');
      setShowTeachModal(false);
      setIsSelectMode(false);
    } catch (e) {
      toast.error('Lỗi khi lưu bài học');
    }
  }

  const isWaiting = conversation.status === 'waiting_human';

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%' }}>
      <div className="chat-panel" style={{ flex: 1, borderRight: '1px solid var(--border)', position: 'relative' }}>
      {/* Header */}
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: 40, height: 40, borderRadius: '50%',
              background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 700, color: 'white'
            }}
          >
            {conversation.customer_name.charAt(0)}
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{conversation.customer_name}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              {PLATFORM_LABELS[conversation.platform]} ·&nbsp;
              <span className={`status-badge status-${conversation.status}`}>{conversation.status}</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {isSelectMode ? (
            <>
              <button className="btn btn-secondary btn-sm" onClick={handleToggleSelectMode}>
                <X size={14} /> Hủy chọn
              </button>
              <button className="btn btn-primary btn-sm" onClick={openTeachModal}>
                <Check size={14} /> Tiếp tục
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost btn-sm" onClick={handleToggleSelectMode} style={{ color: 'var(--accent-primary)', background: 'var(--accent-glow)' }}>
                <GraduationCap size={14} /> Dạy AI
              </button>
              {conversation.status !== 'resolved' && (
                <>
                  <button className="btn btn-secondary btn-sm" onClick={() => setShowHandoff(true)}>
                    <UserCheck size={14} /> Chuyển NV
                  </button>
                  <button className="btn btn-success btn-sm" onClick={handleResolve}>
                    <CheckCircle size={14} /> Xong
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Select Mode Alert */}
      {isSelectMode && (
        <div style={{
          background: 'rgba(99,102,241,0.1)',
          border: '1px solid rgba(99,102,241,0.3)',
          padding: '10px 20px',
          fontSize: '12px',
          color: '#818cf8',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <GraduationCap size={14} />
          <strong>Chế độ Dạy AI:</strong> Vui lòng click chọn 1 tin nhắn của khách (Câu hỏi) và 1 tin nhắn của bạn (Câu trả lời).
        </div>
      )}

      {/* Waiting Human Alert */}
      {isWaiting && !isSelectMode && (
        <div style={{
          background: 'rgba(245,158,11,0.1)',
          border: '1px solid rgba(245,158,11,0.3)',
          padding: '10px 20px',
          fontSize: '12px',
          color: '#f59e0b',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <Zap size={14} />
          AI cần hỗ trợ từ nhân viên. Hãy xem xét và trả lời hoặc chuyển cho nhân viên phù hợp.
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages" style={{ paddingBottom: isSelectMode ? 24 : 0 }}>
        {messages.map((msg) => {
          const isSelected = selectedQuestion?.id === msg.id || selectedAnswer?.id === msg.id;
          return (
            <div 
              key={msg.id} 
              className={`message-group ${msg.direction} animate-fadeIn ${isSelectMode ? 'selectable' : ''}`}
              onClick={() => handleMessageSelect(msg)}
              style={{
                cursor: isSelectMode ? 'pointer' : 'default',
                opacity: isSelectMode && !isSelected ? 0.5 : 1,
                transition: 'opacity 0.2s',
              }}
            >
              <div className={`message-bubble ${msg.direction} ${msg.is_ai_generated ? 'ai' : ''} ${isSelected ? 'selected' : ''}`}>
                {msg.image_url && (
                  <div style={{ marginBottom: 8, borderRadius: 8, overflow: 'hidden' }}>
                    <img 
                      src={`http://localhost:8000${msg.image_url}`} 
                      alt="Attached" 
                      style={{ maxWidth: '100%', maxHeight: 200, objectFit: 'contain' }}
                      onError={(e) => {
                        // Fallback if full url is stored or relative path breaks
                        const target = e.target as HTMLImageElement;
                        if (!target.src.includes('localhost') && msg.image_url?.startsWith('/')) {
                          target.src = `http://localhost:8000${msg.image_url}`;
                        } else if (!msg.image_url?.startsWith('/')) {
                          target.src = msg.image_url || '';
                        }
                      }}
                    />
                  </div>
                )}
                {msg.content}
                {isSelected && (
                  <div style={{
                    position: 'absolute', top: -8, right: -8, 
                    background: 'var(--accent-primary)', borderRadius: '50%', padding: 2,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
                  }}>
                    <Check size={12} color="white" />
                  </div>
                )}
              </div>
              <div className="message-meta">
                {msg.direction === 'outbound' && msg.is_ai_generated && (
                  <span className="ai-tag">
                    <Bot size={8} style={{ display: 'inline' }} /> AI
                  </span>
                )}
                <span>{msg.created_at ? formatTime(msg.created_at) : ''}</span>
              </div>
            </div>
          );
        })}

        {isAiTyping && !isSelectMode && (
          <div className="message-group inbound">
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
            <div className="message-meta">
              <span className="ai-tag"><Bot size={8} style={{ display: 'inline' }} /> AI đang xử lý</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {!isSelectMode && (
        <div className="chat-input-area" style={{ flexDirection: 'column', gap: 8 }}>
          {imageBase64 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 16px' }}>
              <div style={{ position: 'relative', display: 'inline-block' }}>
                <img src={imageBase64} alt="preview" style={{ height: 60, borderRadius: 8, border: '1px solid var(--border)' }} />
                <button 
                  onClick={() => { setImageFile(null); setImageBase64(''); }}
                  style={{
                    position: 'absolute', top: -6, right: -6,
                    background: 'var(--red)', color: 'white', border: 'none', borderRadius: '50%',
                    width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer'
                  }}
                >
                  <X size={12} />
                </button>
              </div>
            </div>
          )}
          <div className="chat-input-box">
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept="image/*"
              onChange={handleFileChange}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                background: 'transparent',
                color: 'var(--text-muted)',
                border: 'none',
                padding: '8px',
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}
              title="Đính kèm ảnh"
            >
              <ImageIcon size={20} />
            </button>
            <textarea
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
              }}
              placeholder="Nhập tin nhắn... (Dùng /khach để giả lập khách gửi)"
              rows={1}
            />
            <button
              onClick={handleSend}
              disabled={(!inputText.trim() && !imageBase64) || sending}
              style={{
                background: (inputText.trim() || imageBase64) ? 'var(--accent-primary)' : 'var(--border)',
                color: 'white',
                width: 36, height: 36,
                borderRadius: 'var(--radius-md)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'var(--transition)',
                flexShrink: 0
              }}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Handoff Modal */}
      {showHandoff && (
        <div className="modal-overlay" onClick={() => setShowHandoff(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🤝 Chuyển tay sang nhân viên</div>
            <div className="form-group">
              <label className="form-label">Tên nhân viên *</label>
              <input
                className="form-input"
                value={agentName}
                onChange={e => setAgentName(e.target.value)}
                placeholder="Ví dụ: Nguyễn Văn A"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Ghi chú (tùy chọn)</label>
              <textarea
                className="form-textarea"
                value={handoffNote}
                onChange={e => setHandoffNote(e.target.value)}
                placeholder="Thông tin bổ sung cho nhân viên..."
                style={{ minHeight: 80 }}
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowHandoff(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={handleHandoff}>
                <UserCheck size={14} /> Chuyển tay
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Teach AI Modal */}
      {showTeachModal && (
        <div className="modal-overlay" onClick={() => setShowTeachModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ minWidth: 500 }}>
            <div className="modal-title">🎓 Tạo bài học mới cho AI</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
              Bài học này sẽ được lưu vào mục <strong>Knowledge Base</strong> dưới dạng <strong>Bản Nháp</strong> để quản lý duyệt.
            </div>

            <div className="form-group">
              <label className="form-label" style={{ color: '#ec4899' }}>Câu hỏi của khách (Inbound)</label>
              <textarea
                className="form-textarea"
                value={teachForm.question}
                onChange={e => setTeachForm(f => ({ ...f, question: e.target.value }))}
                style={{ minHeight: 60 }}
              />
            </div>

            <div className="form-group">
              <label className="form-label" style={{ color: '#8b5cf6' }}>Câu trả lời của bạn (Outbound)</label>
              <textarea
                className="form-textarea"
                value={teachForm.answer}
                onChange={e => setTeachForm(f => ({ ...f, answer: e.target.value }))}
                style={{ minHeight: 100 }}
              />
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowTeachModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={handleSaveTeach}>
                <GraduationCap size={14} /> Lưu bản nháp
              </button>
            </div>
          </div>
        </div>
      )}
      </div>

      {/* Customer Memory Panel */}
      <div style={{ width: 320, background: 'var(--bg-primary)', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Thông tin khách hàng</h3>
        </div>
        <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {memory ? (
            <>
              {memory.satisfaction_score !== null && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Mức độ hài lòng</span>
                  <span style={{ 
                    fontSize: 12, fontWeight: 600, 
                    color: memory.satisfaction_score > 0.7 ? 'var(--green)' : memory.satisfaction_score < 0.5 ? 'var(--red)' : 'var(--yellow)' 
                  }}>
                    {Math.round(memory.satisfaction_score * 100)}%
                  </span>
                </div>
              )}
              {memory.body_measurements && (() => {
                const b = JSON.parse(memory.body_measurements);
                return (
                  <div style={{ background: 'var(--bg-card)', padding: 12, borderRadius: 8, border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Chỉ số cơ thể</div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                      {b.height ? `${b.height}cm` : ''} {b.height && b.weight ? ' - ' : ''} {b.weight ? `${b.weight}kg` : ''}
                    </div>
                  </div>
                );
              })()}
              {(memory.preferred_sizes || memory.preferred_fit) && (
                <div style={{ background: 'var(--bg-card)', padding: 12, borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Size & Fit</div>
                  {memory.preferred_sizes && (
                    <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 2 }}>
                      Size: {(() => {
                        const s = JSON.parse(memory.preferred_sizes);
                        return [s.top && `Áo ${s.top}`, s.bottom && `Quần ${s.bottom}`].filter(Boolean).join(' | ');
                      })()}
                    </div>
                  )}
                  {memory.preferred_fit && (
                    <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>Fit: {memory.preferred_fit}</div>
                  )}
                </div>
              )}
              {memory.style_preferences && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Phong cách</div>
                  <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{memory.style_preferences}</div>
                </div>
              )}
              {memory.purchase_history_summary && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Lịch sử mua hàng</div>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.5 }}>{memory.purchase_history_summary}</div>
                </div>
              )}
              {memory.complaint_history && (
                <div style={{ background: 'rgba(239,68,68,0.1)', padding: 12, borderRadius: 8, border: '1px solid rgba(239,68,68,0.2)' }}>
                  <div style={{ fontSize: 11, color: 'var(--red)', marginBottom: 4, fontWeight: 600 }}>Lịch sử khiếu nại</div>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.5 }}>{memory.complaint_history}</div>
                </div>
              )}
              {memory.notes && (
                <div style={{ background: 'rgba(245,158,11,0.1)', padding: 12, borderRadius: 8, border: '1px solid rgba(245,158,11,0.2)' }}>
                  <div style={{ fontSize: 11, color: 'var(--yellow)', marginBottom: 4, fontWeight: 600 }}>Ghi chú</div>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.5 }}>{memory.notes}</div>
                </div>
              )}
            </>
          ) : (
            <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', marginTop: 20 }}>
              Chưa có thông tin khách hàng
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
