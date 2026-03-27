# Research Notes: Wikipedia Vandalism & Intelligence Analysis

Tài liệu này tổng hợp các phương pháp, công cụ và đặc trưng (features) phổ biến được sử dụng bởi các hệ thống hàng đầu trên Wikipedia để phát hiện phá hoại (vandalism) và tin giả.

---

## 🛡️ 1. Các công cụ hàng đầu (Benchmarks)

### **ORES (Objective Revision Evaluation Service)**
- **Bản chất**: Web service cung cấp Machine Learning scores cho Wikimedia.
- **Phương pháp**: Train model dựa trên các edits bị "reverted" (hoàn tác).
- **Phân loại**: 
  - *Damaging*: Edit có gây hại không?
  - *Good faith*: Edit có thiện chí không (dù có thể sai)?
- **Bài học**: Sử dụng kết quả của cộng đồng (reverts) làm ground truth cho training.

### **STiki (Spatio-Temporal Detection)**
- **Bản chất**: Tập trung vào các đặc trưng phi văn bản (siêu dữ liệu).
- **Phương pháp**: Sử dụng Support Vector Regression (SVR).
- **Các đặc trưng chính**:
  - Thời gian trong ngày/tuần.
  - Tuổi của tài khoản (time since registration).
  - Khoảng cách thời gian giữa các lần edit.
  - Danh tiếng của User và Bài viết (Reputation).

### **ClueBot NG**
- **Bản chất**: Bot tự động lùng sục và hoàn tác vandalism ngay lập tức.
- **Phương pháp**: Hybrid (Bayesian Classifier + Artificial Neural Network).
- **Đặc trưng**:
  - Bayesian: Tính xác suất vandalism của từng từ/cụm từ thêm vào.
  - ANN: Nhận diện pattern phức tạp từ các thống kê nạp vào.

---

## 📊 2. Các Đặc trưng (Features) để phân tích

Để xây dựng Rule Engine và ML model hiệu quả, ta cần trích xuất các nhóm sau:

### **Nhóm A: Nội dung (Content-based)**
1. **Word Lists**: Danh sách từ thô tục, spam URL, biệt danh, hoặc các cụm từ cảm tính (opinionated words).
2. **NLP Sentiment**: Sử dụng BERT/DistilBERT để nhận diện giọng văn không trung lập.
3. **Statistical Language Models**: So sánh từ ngữ mới với vốn từ cũ của bài viết (phát hiện từ lạ/rác).
4. **Markup ratio**: Tỷ lệ mã Wiki (links, tags) so với văn bản thuần. Vandal thường xóa markup hoặc chèn rác vào.
5. **Uppercase ratio**: Tỷ lệ chữ hoa đột biến (biểu thị sự văng tục/gào thét).
6. **Digit-to-Letter ratio**: Tỷ lệ số/chữ cao thường xuất hiện trong spam hoặc tọa độ rác.
7. **Non-alphanumeric ratio**: Tỷ lệ ký tự đặc biệt đột biến.
8. **Longest Repeated Sequence**: Phát hiện các hành vi gõ phím rác (ví dụ: "aaaaaaa...").
9. **Diff Compression**: Sử dụng thuật toán nén (như LZW) trên đoạn text thay đổi. Nếu tỷ lệ nén quá cao = text lặp lại/đơn giản (rác).

### **Nhóm B: Siêu dữ liệu (Metadata-based)**
1. **Size Delta**: Thay đổi kích thước bài viết. Xóa quá nhiều (blanking) hoặc thêm quá nhiều (spam) đều đáng nghi.
2. **Diff distance**: Khoảng cách chỉnh sửa (Levenshtein distance) giữa 2 phiên bản.
3. **Comment Analysis**: Comment trống, hoặc comment chứa từ khóa lẩn tránh.
4. **Namespace**: Tập trung vào Namespace 0 (Article).
5. **Temporal features**: Giờ cao điểm của vandalism (thường là giờ hành chính/học tập khi "trolls" rảnh rỗi).

### **Nhóm C: Người dùng (User-based)**
1. **User Reputation**: Lịch sử revert của user đó.
2. **IP vs Account**: User IP (Anonymous) có xác suất phá hoại cao hơn ~10-20 lần user có tài khoản.
3. **Registration Age**: Tài khoản mới tạo < 1 ngày có rủi ro cực cao.
4. **Geography**: GeoIP của user (có những dải IP thường xuyên phá hoại).

---

## 🕵️ 3. Phân biệt Vandalism vs. Misinformation (Tin giả)

| Đặc điểm | Vandalism (Phá hoại) | Misinformation (Tin giả) |
|---|---|---|
| **Cường độ** | Rõ ràng, dễ thấy (chửi thề, xóa bài). | Tinh vi, khó phát hiện (thay đổi số liệu, ngày tháng). |
| **Mục đích** | Gây rối, mua vui, giải tỏa. | Định hướng dư luận, bôi nhọ, trục lợi. |
| **Phương pháp** | Rule-based phát hiện tốt (~80-90%). | Cần NLP AI cao cấp + Fact-checking. |
| **Nguồn** | Cá nhân trolls. | Có thể là các chiến dịch có tổ chức (Disinformation). |

---

## 🚀 4. Đề xuất cải tiến cho project hiện tại

1. **Hybrid Scoring**: Không chỉ dùng rules đơn lẻ, mà cộng dồn điểm (Weighted Scoring).
   - Ví dụ: `(Anonymous +2) + (Blanking +5) + (Empty Comment +1) = 8/10` -> Cực kỳ nguy hiểm.
2. **Ground Truth Verification**: Trong khi thu thập data, ta nên lưu lại cả ID của trang để sau này script có thể kiểm tra xem edit đó *đã bị revert chưa* (đây là cách gán nhãn tự động chuẩn nhất).
3. **Focus on Diffs**: Thay vì chỉ nhìn metadata, ta cần lấy nội dung thực sự thay đổi (diff) để nạp vào NLP model.
4. **Fact-Checking Integration**: Với các edits thay đổi con số (ngày sinh, dân số, v.v.), Rule Engine nên đánh dấu "Potential Misinformation" để chuyển qua module verify.

---

## 📚 Tài liệu tham khảo
- MediaWiki ORES Documentation
- STiki: An Anti-Vandalism Tool for Wikipedia (UPenn)
- ClueBot NG source code & methodology
- PAN Wikipedia Vandalism Corpus (CLEF)
