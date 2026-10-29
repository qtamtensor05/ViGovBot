"""User intents mapped to the routing-aligned corpus taxonomy."""

import re
import unicodedata

from vigovbot.taxonomy import LEGACY_SECTION_FALLBACK

SECTION_INTENTS = {
    "OVERVIEW": ("Tổng quan thủ tục", ()),
    "GENERAL_INFORMATION": ("Thông tin chung", ("metadata_identity",)),
    "DOSSIER": ("Hồ sơ, giấy tờ", ("required_documents",)),
    "FORM": ("Mẫu đơn, tờ khai", ("required_documents",)),
    "PROCEDURE": ("Trình tự thực hiện", ("procedure_step",)),
    "PROCESSING_TIME": ("Thời hạn giải quyết", ("processing_time",)),
    "FEE": ("Phí và lệ phí", ("fee",)),
    "SUBMISSION_METHOD": ("Cách thức nộp hồ sơ", ("submission_method",)),
    "AUTHORITY": ("Cơ quan thực hiện", ("metadata_identity",)),
    "RESULT": ("Kết quả thực hiện", ("result",)),
    "LEGAL_BASIS": ("Căn cứ pháp lý", ("legal_basis",)),
    "ELIGIBILITY": ("Yêu cầu, điều kiện thực hiện", ("other",)),
    "OTHER_CONTENT": ("Nội dung khác", ("other",)),
}


def section_query(sections):
    labels = [SECTION_INTENTS[s][0] for s in sections]
    types = {} if any(not SECTION_INTENTS[s][1] for s in sections) else dict.fromkeys(
        t for s in sections for t in SECTION_INTENTS[s][1])
    return ", ".join(labels) + "".join(f"\nMục dữ liệu: {t}" for t in types)


def _fold(text):
    value = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d")


def explicit_section_intents(text):
    """Read explicit field words only; procedure identity remains the router's job."""
    folded = _fold(text)
    groups = (
        ("GENERAL_INFORMATION", ("thong tin chung",)),
        ("DOSSIER", ("ho so", "giay to", "thanh phan ho so")),
        ("FORM", ("mau don", "to khai", "bieu mau")),
        ("PROCEDURE", ("trinh tu", "quy trinh", "cac buoc", "buoc thuc hien")),
        ("PROCESSING_TIME", ("thoi han", "bao lau", "may ngay")),
        ("FEE", ("le phi", "chi phi", "muc phi")),
        ("SUBMISSION_METHOD", ("cach thuc nop", "hinh thuc nop", "nop o dau")),
        ("AUTHORITY", ("co quan thuc hien", "co quan giai quyet", "co quan tiep nhan")),
        ("LEGAL_BASIS", ("can cu phap ly", "co so phap ly", "can cu phap li", "co so phap li")),
        ("ELIGIBILITY", ("dieu kien thuc hien", "yeu cau thuc hien")),
        ("OVERVIEW", ("tong quan", "toan bo thu tuc")),
    )
    return [label for label, terms in groups
            if any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded) for term in terms)]


def available_sections(corpus_sections, *, eligibility=False, forms=False):
    corpus_sections = set(corpus_sections)
    return [s for s, (_, types) in SECTION_INTENTS.items()
            if s != "OVERVIEW" and (s != "ELIGIBILITY" or eligibility)
            and (s != "FORM" or forms)
            and (set(types) & corpus_sections or any(
                LEGACY_SECTION_FALLBACK.get(t) in corpus_sections
                or (t in LEGACY_SECTION_FALLBACK and LEGACY_SECTION_FALLBACK[t] is None and corpus_sections)
                for t in types))] + ["OVERVIEW"]
