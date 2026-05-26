# Báo Cáo Tổng Quan Dự Án: Hệ Thống AI Customer Service Chuyên Biệt Cho Thời Trang (Multi-Agent)

Dự án này đã trải qua nhiều đợt nâng cấp lớn và hiện tại đã trở thành một hệ thống Chăm sóc Khách hàng thông minh, hoàn chỉnh, đáp ứng được các yêu cầu khắt khe của ngành bán lẻ thời trang. 

Dưới đây là tổng hợp toàn bộ các tính năng cốt lõi và cách chúng hoạt động tính đến thời điểm hiện tại.

---

## 1. Hệ Thống Đa Tác Nhân (Multi-Agent AI)

Thay vì dùng 1 AI để trả lời tất cả mọi thứ, hệ thống hiện tại sử dụng **Tổ Hợp 8 AI Agent** làm việc theo dây chuyền:

1. **Khách hàng nhắn tin:** Tin nhắn được gửi lên Backend.
2. **Router Agent:** Phân tích câu hỏi xem khách đang hỏi về cái gì (VD: Size, Vận chuyển, hay Đổi trả).
3. **Specialist Agents:** Hệ thống sẽ gọi đúng chuyên gia (Agent) tương ứng (Ví dụ: Khách phàn nàn và đòi đổi trả $\rightarrow$ Gọi `Complaint Recovery Agent`). 
   - *Tính năng đặc biệt:* Nếu khách hỏi 2 vấn đề cùng lúc, hệ thống sẽ chạy 2 Agent song song.
4. **Composer Agent:** Nhận kết quả phân tích từ các chuyên gia, gộp lại và viết thành một câu trả lời duy nhất mang đậm phong cách Premium Fashion.
5. **Dự phòng rủi ro (Mock Mode):** Nếu OpenAI bị lỗi (hết tiền, sập mạng), hệ thống tự động chuyển sang chế độ "Giả lập thông minh" (Mock) dựa trên từ khóa để giữ cho hệ thống không bị gián đoạn.

## 2. Giao Diện Bán Hàng & Chăm Sóc Đa Kênh

- **Dashboard Quản Lý:** Giao diện được xây dựng bằng Next.js, hiển thị đầy đủ danh sách khách hàng, chia tag phân loại (Shopee, TikTok, Instagram, Web).
- **Real-time Chat (Socket.IO):** Tin nhắn của khách và AI hiển thị theo thời gian thực (giống hệt trải nghiệm dùng Facebook Messenger).
- **Hỗ Trợ Hình Ảnh (Vision AI):** Khách hàng có thể gửi kèm hình ảnh sản phẩm. Hệ thống đã được lập trình để lưu ảnh, hiển thị lên khung chat và truyền cho OpenAI Vision để AI có thể "nhìn" thấy áo/quần khách gửi và tư vấn.

## 3. Tích Hợp Dữ Liệu Vận Hành

Hệ thống AI không trả lời "bừa" mà được cấp dữ liệu thực tế từ hệ thống nội bộ:
- **Tồn kho (Inventory):** AI được kết nối với phần mềm Nhanh.vn (hiện đang dùng dữ liệu Mock giả lập: *Áo Polo Premium Đen Size S: 5 áo...*). Khi khách hỏi "còn hàng không", AI sẽ lấy số liệu thực tế này để báo khách.
- **Hồ Sơ Khách Hàng (Customer Memory):** Hệ thống ghi nhớ thông tin chiều cao, cân nặng, lịch sử mua hàng, và sở thích của từng cá nhân.
- **Tài Liệu Hướng Dẫn (Knowledge Base / RAG):** Các chính sách đổi trả, bảng size chuẩn được nạp vào Vector Database để AI đọc trước khi tư vấn.

## 4. Quản Trị Rủi Ro Chăm Sóc Khách Hàng

AI được thiết lập các giới hạn vô cùng khắt khe:
- **Không tranh cãi với khách.**
- **Không tự bịa ra tồn kho, mã giảm giá hay thời gian giao hàng ảo.**
- **Escalation (Chuyển người thật):** Khi phát hiện khách đang nóng giận (Angry), hoặc câu hỏi quá khó, độ tự tin thấp, AI sẽ lập tức báo `needs_human: true` để nhường quyền cho nhân viên trực tiếp xử lý, giúp bảo vệ uy tín thương hiệu.

---

> [!TIP]
> **Các tính năng nổi bật có thể trải nghiệm ngay lúc này (Nếu sử dụng Chế độ Giả Lập):**
> - Nhắn: *"Giá sản phẩm này còn giảm không shop?"* $\rightarrow$ AI trả lời câu hỏi trực tiếp.
> - Nhắn: *"Áo này còn hàng không?"* $\rightarrow$ AI báo tình trạng tồn kho giả lập.
> - Nhắn: *"Áo em mua mặc không vừa, shop làm ăn chán thế"* $\rightarrow$ AI nhận diện cảm xúc (Angry) và xoa dịu, đề xuất chuyển nhân viên.
> - Gửi tin nhắn **đính kèm 1 file hình ảnh** thông qua nút ở ô nhập liệu.

> [!IMPORTANT]
> **Bước Tiếp Theo Khuyến Nghị**
> Để hệ thống Multi-Agent AI thể hiện được sức mạnh tuyệt đối, anh cần **Cập nhật lại API Key OpenAI** (loại có sẵn số dư/credit). Khi đó, các luồng phân tích tâm lý, gộp ý, phân tích hình ảnh sẽ chính xác hơn gấp nhiều lần so với phiên bản Mock giả lập từ khóa hiện tại.
