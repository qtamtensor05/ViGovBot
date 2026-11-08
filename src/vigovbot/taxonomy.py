"""Shared corpus taxonomy and read-only migration compatibility."""

import re

from vigovbot.utils.text import fold_vietnamese

ROUTING_SECTION_TYPES = frozenset({
    "metadata_identity", "procedure_step", "required_documents", "submission_method",
    "processing_time", "fee", "result", "legal_basis", "other",
})

# New ingestion never emits the aggregate type. This bridge only reads corpus
# revisions published before the routing and chunking taxonomies were aligned.
LEGACY_SECTION_FALLBACK = {
    "submission_method": "submission_deadline_fee",
    "processing_time": "submission_deadline_fee",
    "fee": "submission_deadline_fee",
    "result": None,
}


def legacy_section_matches(section_type, hit):
    """Match one legacy chunk without widening a missing section to the procedure."""
    if section_type not in LEGACY_SECTION_FALLBACK and section_type != "procedure_step":
        return False
    fallback = LEGACY_SECTION_FALLBACK.get(section_type)
    if fallback is not None:
        return hit.get("section_type") == fallback
    text = "\n".join(str(hit.get(key) or "") for key in ("context_prefix", "text_content"))[:800]
    folded = fold_vietnamese(text)
    if section_type == "procedure_step":
        return hit.get("section_type") == "other" and (
            "trinh tu thuc hien" in folded
            or bool(re.search(r"(?<!\w)buoc\s+(?:thu\s+)?\d+(?!\w)", folded))
        )
    if section_type == "result":
        return "ket qua xu ly" in folded or "ket qua thuc hien" in folded
    return False
