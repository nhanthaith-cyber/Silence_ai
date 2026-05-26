# Kế Hoạch Triển Khai Multi-Agent System (Antigravity Architecture)

Anh đã cung cấp một prompt cực kỳ chi tiết và chuyên nghiệp, yêu cầu chuyển đổi hệ thống từ **Single-Agent** (một agent làm tất cả) sang **Multi-Agent Orchestration** (phân mảnh thành 8 agent chuyên biệt). Đây là một bản cập nhật kiến trúc lớn nhằm giúp hệ thống hoạt động thông minh, chính xác và có thể scale tốt hơn cho nghiệp vụ TMĐT thời trang.

## User Review Required

> [!WARNING]
> Việc chia nhỏ thành 8 agent có nghĩa là hệ thống sẽ phải thực hiện **nhiều API call tới OpenAI** cho một tin nhắn của khách hàng (VD: 1 call cho Router, 1 call cho Agent chuyên môn, 1 call cho Composer). Điều này làm tăng độ trễ (latency) và chi phí token. Em có thể tối ưu bằng cách gom các agent lại hoặc chạy song song (parallel), nhưng anh cần lưu ý về mặt chi phí và tốc độ phản hồi.

> [!IMPORTANT]
> Hiện tại hệ thống đang chạy "Mock" (giả lập) vì chưa có API Key OpenAI. Để Multi-Agent hoạt động đúng bản chất, hệ thống **bắt buộc phải kết nối với OpenAI**. Nếu chưa có Key, em sẽ tạm thời xây dựng bộ khung (Architecture) và dùng mock data, nhưng anh nên cung cấp `OPENAI_API_KEY` vào file `.env` sớm nhất có thể.

## Open Questions

1. **Độ trễ (Latency):** Việc chạy qua 3-4 agent cho mỗi tin nhắn sẽ tốn khoảng 3-8 giây. Anh có chấp nhận độ trễ này đổi lấy độ chính xác cao không, hay muốn em gom bớt các Agent lại (ví dụ gom Sales và Product lại làm một) để giảm latency?
2. **Luồng thực thi:** Em dự kiến xây dựng theo luồng tuần tự: `Router -> Memory (lấy từ DB) -> Các Agent Chuyên Môn (chạy song song nếu có nhiều intent) -> Composer tổng hợp`. Luồng này có đúng ý anh không?

## Proposed Changes

Em sẽ xây dựng thư mục `app/agents` để chứa các module chuyên biệt, và refactor lại `ai_service.py` để nó đóng vai trò là Orchestrator.

### Backend

#### [NEW] [orchestrator.py](file:///c:/Users/NEALAKADY/OneDrive/Desktop/Silence/backend/app/agents/orchestrator.py)
- Xây dựng class `MultiAgentOrchestrator` nhận đầu vào từ khách hàng.
- Thực thi theo pipeline: Router -> Load Memory -> Gọi Specialist Agents -> Gọi Composer.

#### [NEW] [router_agent.py](file:///c:/Users/NEALAKADY/OneDrive/Desktop/Silence/backend/app/agents/router_agent.py)
- Prompt chuyên biệt cho việc phân loại intent (Sizing, Logistics, Product, v.v.).
- Output là danh sách các Specialist Agent cần gọi.

#### [NEW] [specialist_agents.py](file:///c:/Users/NEALAKADY/OneDrive/Desktop/Silence/backend/app/agents/specialist_agents.py)
- Gộp các Agent chuyên môn (Product, Size, Logistics, Complaint, Sales) vào một file để dễ quản lý. Mỗi agent sẽ có một Prompt riêng.

#### [NEW] [composer_agent.py](file:///c:/Users/NEALAKADY/OneDrive/Desktop/Silence/backend/app/agents/composer_agent.py)
- Prompt chuyên biệt để gộp các context và kết quả từ specialist agent thành một câu trả lời hoàn chỉnh, mang đúng phong cách của thương hiệu thời trang cao cấp.

#### [MODIFY] [ai_service.py](file:///c:/Users/NEALAKADY/OneDrive/Desktop/Silence/backend/app/services/ai_service.py)
- Thay đổi `get_ai_response` để gọi `MultiAgentOrchestrator` thay vì tự gọi một function duy nhất như trước.

#### [MODIFY] [models.py](file:///c:/Users/NEALAKADY/OneDrive/Desktop/Silence/backend/app/models/models.py)
- Cập nhật bảng `AgentConfig` (nếu cần) để hỗ trợ lưu nhiều cấu hình prompt khác nhau cho từng Agent, hoặc lưu chung cấu trúc Multi-Agent.

## Verification Plan

### Manual Verification
1. Em sẽ khởi động lại hệ thống và dùng tính năng "Mock" (hoặc OpenAI thật nếu có key) để test một tin nhắn có độ phức tạp cao (ví dụ: *"Em ơi áo này còn size M không, đợt trước mua bị chật, với cả đơn hỏa tốc hôm nay có kịp không?"*).
2. Kiểm tra log backend để đảm bảo **Router** nhận diện ra 3 intent (Product, Size, Logistics) và gọi đúng 3 Agent, sau đó **Composer** gộp lại thành 1 câu mượt mà.
