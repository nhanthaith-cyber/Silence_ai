'use client';
import { useState, useEffect } from 'react';
import AppShell from '@/components/AppShell';
import { getTickets, getTicketStats, updateTicket } from '@/lib/api';
import { Package, Clock, CheckCircle, Search, Edit2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function WarehousePage() {
  const [stats, setStats] = useState({ open: 0, in_progress: 0, resolved: 0, closed: 0, total: 0 });
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modal state
  const [selectedTicket, setSelectedTicket] = useState<any>(null);
  const [note, setNote] = useState('');
  const [status, setStatus] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [statsData, ticketsData] = await Promise.all([
        getTicketStats('return'),
        getTickets({ category: 'return' })
      ]);
      setStats(statsData);
      setTickets(ticketsData);
    } catch (e) {
      toast.error('Lỗi khi tải dữ liệu kho');
    } finally {
      setLoading(false);
    }
  }

  function openModal(ticket: any) {
    setSelectedTicket(ticket);
    setNote(ticket.resolution || '');
    setStatus(ticket.status || 'open');
    setIsModalOpen(true);
  }

  async function handleSave() {
    if (!selectedTicket) return;
    try {
      await updateTicket(selectedTicket.id, {
        status: status,
        resolution: note
      });
      toast.success('Cập nhật thành công!');
      setIsModalOpen(false);
      loadData();
    } catch (e) {
      toast.error('Lỗi cập nhật');
    }
  }

  const getStatusBadge = (status: string) => {
    const map: Record<string, { label: string; className: string }> = {
      open: { label: 'Chờ xử lý', className: 'bg-red-500/20 text-red-400 border border-red-500/30' },
      in_progress: { label: 'Đang xử lý', className: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' },
      resolved: { label: 'Đã giải quyết', className: 'bg-green-500/20 text-green-400 border border-green-500/30' },
      closed: { label: 'Đã đóng', className: 'bg-gray-500/20 text-gray-400 border border-gray-500/30' },
    };
    const mapped = map[status] || { label: status, className: 'bg-gray-500/20 text-gray-400' };
    return <span className={`px-2 py-1 rounded-full text-xs font-medium ${mapped.className}`}>{mapped.label}</span>;
  };

  return (
    <AppShell>
      <div className="p-8 max-w-6xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
              <Package className="text-indigo-400" /> Báo Cáo Kho & Đổi Trả
            </h1>
            <p className="text-gray-400">Theo dõi và xử lý các yêu cầu đổi/trả hàng từ khách hàng</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[#2d3748] hover:bg-[#3f4a5f] text-white rounded-lg transition-colors">
            Làm mới
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[#1e2030] p-6 rounded-xl border border-[#2d3748] flex items-center gap-4">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Package className="text-blue-400" size={24} />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Tổng phiếu (Returns)</p>
              <h3 className="text-2xl font-bold text-white">{stats.total}</h3>
            </div>
          </div>
          
          <div className="bg-[#1e2030] p-6 rounded-xl border border-[#2d3748] flex items-center gap-4">
            <div className="p-3 bg-red-500/20 rounded-lg">
              <Clock className="text-red-400" size={24} />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Chờ xử lý (Open)</p>
              <h3 className="text-2xl font-bold text-white">{stats.open}</h3>
            </div>
          </div>

          <div className="bg-[#1e2030] p-6 rounded-xl border border-[#2d3748] flex items-center gap-4">
            <div className="p-3 bg-yellow-500/20 rounded-lg">
              <Search className="text-yellow-400" size={24} />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Đang xử lý (In Progress)</p>
              <h3 className="text-2xl font-bold text-white">{stats.in_progress}</h3>
            </div>
          </div>

          <div className="bg-[#1e2030] p-6 rounded-xl border border-[#2d3748] flex items-center gap-4">
            <div className="p-3 bg-green-500/20 rounded-lg">
              <CheckCircle className="text-green-400" size={24} />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Đã giải quyết</p>
              <h3 className="text-2xl font-bold text-white">{stats.resolved}</h3>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-[#1e2030] rounded-xl border border-[#2d3748] overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#2d3748]/50 border-b border-[#2d3748]">
                <th className="p-4 text-sm font-medium text-gray-400">Khách hàng</th>
                <th className="p-4 text-sm font-medium text-gray-400">Tiêu đề (Lý do)</th>
                <th className="p-4 text-sm font-medium text-gray-400">Trạng thái</th>
                <th className="p-4 text-sm font-medium text-gray-400">Ghi chú kho</th>
                <th className="p-4 text-sm font-medium text-gray-400">Thời gian</th>
                <th className="p-4 text-sm font-medium text-gray-400"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="p-8 text-center text-gray-400">Đang tải...</td></tr>
              ) : tickets.length === 0 ? (
                <tr><td colSpan={6} className="p-8 text-center text-gray-400">Không có phiếu đổi trả nào.</td></tr>
              ) : (
                tickets.map(t => (
                  <tr key={t.id} className="border-b border-[#2d3748]/50 hover:bg-[#2d3748]/20 transition-colors">
                    <td className="p-4 text-white font-medium">{t.customer_name}</td>
                    <td className="p-4 text-gray-300">
                      <div className="font-medium text-white">{t.title}</div>
                      <div className="text-xs text-gray-500 mt-1 line-clamp-1">{t.description}</div>
                    </td>
                    <td className="p-4">{getStatusBadge(t.status)}</td>
                    <td className="p-4 text-gray-400 text-sm italic max-w-xs truncate">
                      {t.resolution || '—'}
                    </td>
                    <td className="p-4 text-sm text-gray-400">
                      {new Date(t.created_at).toLocaleString('vi-VN')}
                    </td>
                    <td className="p-4 text-right">
                      <button 
                        onClick={() => openModal(t)}
                        className="p-2 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 rounded-lg transition-colors"
                      >
                        <Edit2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-[#1e2030] p-6 rounded-2xl w-full max-w-md border border-[#2d3748] shadow-2xl">
              <h2 className="text-xl font-bold text-white mb-4">Cập nhật Phiếu</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Trạng thái</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="w-full bg-[#11131f] border border-[#2d3748] text-white rounded-lg px-4 py-2 focus:border-indigo-500 outline-none"
                  >
                    <option value="open">Chờ xử lý</option>
                    <option value="in_progress">Đang xử lý</option>
                    <option value="resolved">Đã giải quyết</option>
                    <option value="closed">Đã đóng</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Ghi chú nội bộ (Kho)</label>
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Vd: Hàng lỗi do vận chuyển, đã nhập lại kho..."
                    rows={4}
                    className="w-full bg-[#11131f] border border-[#2d3748] text-white rounded-lg px-4 py-2 focus:border-indigo-500 outline-none resize-none"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-transparent text-gray-400 hover:text-white"
                >
                  Hủy
                </button>
                <button 
                  onClick={handleSave}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
                >
                  Lưu cập nhật
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
