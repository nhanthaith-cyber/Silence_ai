# AI Customer Service Agent — Hệ thống chăm sóc khách hàng đa sàn

Hệ thống **AI Agent + Unified Inbox + Human Handoff** cho Shopee, TikTok, Facebook, Instagram.

## 🚀 Khởi động nhanh

### Bước 1: Cài đặt Backend

```bash
cd backend
pip install -r requirements.txt
```

### Bước 2: Cấu hình môi trường

```bash
# Copy .env.example thành .env
cp .env.example .env

# Điền API key (tùy chọn — hệ thống vẫn chạy với mock nếu không có key)
# Mở file backend/.env và điền:
# OPENAI_API_KEY=sk-...  (để AI trả lời thật)
# FACEBOOK_PAGE_TOKEN=...  (để kết nối Facebook thật)
```

### Bước 3: Chạy Backend

```bash
cd backend
python main.py
# Hoặc:
uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
```

Backend sẽ chạy tại: http://localhost:8000
API Docs tại: http://localhost:8000/docs

### Bước 4: Cài & Chạy Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend sẽ chạy tại: http://localhost:3000

---

## 🎮 Demo nhanh

1. Mở http://localhost:3000
2. Nhấn **"🛍️ Shopee Mock"** hoặc **"🎵 TikTok Mock"** để tạo tin nhắn thử nghiệm
3. AI sẽ tự động trả lời trong vài giây
4. Xem tin nhắn trong **Unified Inbox**
5. Nhấn **"Chuyển NV"** để handoff sang nhân viên

---

## 📁 Cấu trúc dự án

```
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env                     # Cấu hình môi trường
│   └── app/
│       ├── core/
│       │   ├── config.py        # Settings
│       │   ├── database.py      # SQLAlchemy setup
│       │   └── socket_manager.py # Socket.IO
│       ├── models/
│       │   └── models.py        # DB models
│       ├── services/
│       │   ├── ai_service.py    # OpenAI integration
│       │   └── message_service.py # Message processing
│       ├── adapters/
│       │   ├── facebook_adapter.py
│       │   ├── instagram_adapter.py
│       │   ├── shopee_adapter.py  # Mock
│       │   └── tiktok_adapter.py  # Mock
│       └── routers/
│           ├── webhooks.py
│           ├── conversations.py
│           ├── tickets.py
│           ├── knowledge.py
│           ├── agents_config.py
│           └── analytics.py
│
└── frontend/
    └── src/
        ├── app/
        │   ├── inbox/page.tsx    # Unified Inbox
        │   ├── dashboard/page.tsx # Analytics
        │   ├── knowledge/page.tsx # Knowledge Base
        │   └── settings/page.tsx  # Cấu hình
        ├── components/
        │   ├── AppShell.tsx
        │   ├── inbox/ConversationList.tsx
        │   └── chat/ChatWindow.tsx
        ├── lib/
        │   ├── api.ts            # API client
        │   └── socket.ts         # Socket.IO client
        └── types/index.ts        # TypeScript types
```

---

## 🔧 API Endpoints chính

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/conversations` | Danh sách hội thoại |
| GET | `/api/conversations/{id}/messages` | Tin nhắn |
| POST | `/api/conversations/{id}/messages` | Gửi tin nhắn |
| POST | `/api/conversations/{id}/handoff` | Chuyển nhân viên |
| POST | `/webhook/shopee/mock` | Tạo tin nhắn Shopee mock |
| POST | `/webhook/tiktok/mock` | Tạo tin nhắn TikTok mock |
| POST | `/webhook/facebook` | Nhận webhook Facebook |
| GET | `/api/analytics/overview` | Dashboard stats |
| GET/POST/PUT/DELETE | `/api/knowledge` | Knowledge base CRUD |

---

## 🌐 Tích hợp thật (Production)

### Facebook & Instagram
1. Tạo Facebook App tại developers.facebook.com
2. Thêm Facebook Login + Messenger permissions
3. Cấu hình Webhook URL: `https://yourdomain.com/webhook/facebook`
4. Điền `FACEBOOK_PAGE_TOKEN` và `FACEBOOK_APP_SECRET` vào `.env`

### Shopee
1. Đăng ký Shopee Open Platform: open.shopee.com
2. Tạo ứng dụng và lấy Partner ID + Key
3. Cấu hình webhook URL tại Shopee Developer Portal

### TikTok
1. Đăng ký TikTok for Business: developers.tiktok.com
2. Yêu cầu TikTok Shop API access
3. Cấu hình webhook và lấy credentials

---

## ✨ Tính năng

- **Unified Inbox**: Tất cả tin nhắn từ 4 nền tảng vào 1 màn hình
- **AI Auto-Reply**: GPT-4o mini tự động trả lời với knowledge base
- **Smart Handoff**: AI tự nhận biết khi cần chuyển tay nhân viên
- **Real-time**: Socket.IO cập nhật tức thì không cần refresh
- **Knowledge Base**: Quản lý FAQ để AI học
- **Analytics Dashboard**: Thống kê hiệu suất
- **Mock Data**: Test ngay không cần API key thật
