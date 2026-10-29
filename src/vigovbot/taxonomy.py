"""Shared corpus taxonomy and read-only migration compatibility."""

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
