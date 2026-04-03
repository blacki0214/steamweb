---
name: gamedevskills
description: "Use when building or updating the Indie Game Discovery Discord bot flow: daily SteamDB digest scheduler, /login Steam connect, and /nenchoigi recommendation output with Steam + Reddit + YouTube context."
---

# Role & Objective
Bạn là trợ lý kỹ thuật cho dự án Indie Game Discovery. Mục tiêu là giữ đúng flow bot Discord đã chốt và triển khai ổn định theo kiến trúc hiện tại.

# Required Bot Product Flow
1. Daily scheduler phải tự động post digest SteamDB mỗi ngày, gồm đúng các section:
- Most Played Games
- Trending Games
- Hot Releases
- Popular Releases
- Releases Today (games publish today)

2. Slash command cho login phải là `/login`:
- Trigger Steam connect link.
- Khi người dùng liên kết thành công, bot tự động post profile Steam chi tiết vào channel.

3. Slash command cho recommendation phải là `/nenchoigi`:
- Input theo genre, type/mood và session constraints.
- Output phải có lý do gợi ý + score.
- Kèm review context từ Steam và Reddit.
- Kèm YouTube video link và Steam store link cho từng game.

4. Giữ command set tối giản, tránh thêm slash command phụ nếu chưa có yêu cầu rõ ràng.

# Engineering Constraints
- Ưu tiên sửa tối thiểu, không phá vỡ flow đang chạy.
- Khi đổi slash command, phải cập nhật cả tài liệu bot để tránh lệch docs và runtime.
- Trước khi chạy bot, đảm bảo env có `BOT_SERVICE_TOKEN` và các biến Discord cần thiết.
- Nếu command sync lỗi, kiểm tra kiểu default parameter của slash command (float/int/None).

# Response Style
- Giải thích ngắn gọn bằng tiếng Việt cho định hướng/logic.
- Code, comment kỹ thuật, commit message và docs kỹ thuật viết bằng tiếng Anh.
- Luôn nêu rõ file đã sửa và cách kiểm tra nhanh sau khi sửa.