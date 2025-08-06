from transformers import AutoModelForCausalLM, AutoTokenizer

# Chọn một trong các mô hình nhỏ sau:
# 1. Phi-1.5 (1.3B)
model_name = "microsoft/phi-1_5"

# 2. Gemma-2B
# model_name = "google/gemma-2b"

# 3. Mistral-7B (nếu bạn có đủ RAM)
# model_name = "mistralai/Mistral-7B-v0.1"

# Tải mô hình và tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Lưu mô hình ban đầu để so sánh sau này
model.save_pretrained("models/student_initial")
tokenizer.save_pretrained("models/student_initial")
