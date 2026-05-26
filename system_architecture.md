# Sơ đồ Kiến trúc Hệ thống CS Agent

Dưới đây là sơ đồ chi tiết về cấu trúc kỹ thuật và luồng xử lý dữ liệu của hệ thống, đặc biệt là khi có một tin nhắn mới từ khách hàng gửi đến.

```mermaid
graph TD
    %% Định nghĩa các Actor và System
    Customer([Khách hàng])
    Staff([Nhân viên CSKH])
    
    subgraph Frontend [Frontend (Next.js)]
        Inbox[Unified Inbox UI]
        MemPanel[Customer Memory Panel]
        SocketClient[Socket.IO Client]
    end

    subgraph Backend [Backend (FastAPI)]
        Webhook[Webhook Router]
        MsgService[Message Service]
        AIService[AI Brain / OpenAI]
        MemService[Memory Service]
        ProdService[Product / Inventory Service]
        SocketServer[Socket.IO Server]
    end

    subgraph Database [SQLite Database]
        DB_Conv[(Conversations & Messages)]
        DB_Mem[(Customer Memories)]
        DB_Prod[(Product Catalog & Stock)]
    end

    %% Luồng giao tiếp cơ bản
    Customer -- "Gửi tin (Shopee/TikTok)" --> Webhook
    Inbox <--> SocketClient
    SocketClient <--> SocketServer
    Staff -- "Xem & Chat" --> Inbox

    %% Luồng xử lý tin nhắn chi tiết
    Webhook --> MsgService
    
    %% Bước 1: Lấy Memory
    MsgService -- "1. Query KH cũ" --> MemService
    MemService -- "Đọc" --> DB_Mem
    
    %% Bước 2: Gửi AI
    MsgService -- "2. Context (Msg + Memory)" --> AIService
    
    %% Bước 3: AI Check kho
    AIService -- "3. Tool Call: check_stock" --> ProdService
    ProdService -- "Tra cứu" --> DB_Prod
    ProdService -. "Trả kết quả tồn kho/size" .-> AIService
    
    %% Bước 4: Lưu Memory mới và tạo câu trả lời
    AIService -- "4. Trả kết quả & Memory update" --> MsgService
    MsgService -- "Cập nhật dữ liệu mới" --> MemService
    MemService -- "Ghi" --> DB_Mem
    
    %% Bước 5: Lưu tin nhắn và Broadcast
    MsgService -- "Lưu lịch sử chat" --> DB_Conv
    MsgService -- "5. Broadcast Update" --> SocketServer
    
    %% Hiển thị lên UI
    SocketServer -. "Cập nhật Chat & Memory" .-> SocketClient
    SocketClient --> MemPanel
```

## Các giai đoạn trong luồng xử lý:
1. **Tiếp nhận & Tải Memory**: Khách hàng gửi tin nhắn. Backend nhận diện khách hàng và tải toàn bộ hồ sơ sở thích, số đo, lịch sử mua hàng từ `Customer Memories`.
2. **AI Suy luận**: Tin nhắn + Memory được gửi cho AI. AI phân tích ý định (Intent).
3. **Gọi API Kho**: Nếu khách hỏi size, AI gọi tool `check_stock`, truy vấn vào bảng Products. *(Ở Phase 2, đoạn này sẽ gọi ra API Inventory của bên anh).*
4. **Phản hồi & Cập nhật**: AI đưa ra tư vấn size chuẩn xác, ghi nhận lại số đo mới của khách (nếu có) vào Memory.
5. **Đồng bộ Real-time**: Kết quả bắn ngược lên Frontend ngay lập tức để nhân viên thấy được tin nhắn trả lời và Panel thông tin khách hàng được làm mới.
