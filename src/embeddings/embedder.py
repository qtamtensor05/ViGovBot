"""Nạp encoder dùng cho câu hỏi; cùng mô hình/revision với vector tài liệu."""


def load_encoder(model="BAAI/bge-m3", revision=None, device="cpu"):
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(model, revision=revision, device=device)
    if encoder.get_sentence_embedding_dimension() != 1024:
        raise ValueError("Encoder phải tạo vector 1024 chiều như chỉ mục unified")
    return encoder
