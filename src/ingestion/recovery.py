"""Page-level extraction with local Tesseract OCR and explicit failure reports."""
import os


def extract_pdf(file_path: str) -> tuple[str, dict]:
    """Keep page order; never classify an unread scan as a blank page."""
    import pymupdf
    import pymupdf4llm

    report = {'pages': [], 'warnings': [], 'missing_pages': []}
    parts = []
    with pymupdf.open(file_path) as document:
        if document.needs_pass:
            raise ValueError('PDF được mã hóa, cần mật khẩu')
        for index, page in enumerate(document):
            entry = {'page': index + 1}
            text = ''
            try:
                native = page.get_text().strip()
                if native:
                    try:
                        text = pymupdf4llm.to_markdown(document, pages=[index], use_ocr=False)
                        if not text.strip():
                            raise ValueError('Empty Markdown')
                        entry['method'] = 'markdown'
                    except Exception as error:
                        text = native
                        entry.update(method='native_text', warning=str(error))
                else:
                    # Only pages without text, images, drawings or annotations are
                    # skipped automatically. Image-based white pages still use OCR.
                    if not page.get_images() and not page.get_drawings() and not list(page.annots() or []):
                        entry['method'] = 'blank'
                    else:
                        kwargs = {'language': os.getenv('OCR_LANGUAGE', 'vie+eng'), 'dpi': 300, 'full': True}
                        if os.getenv('TESSDATA_PREFIX'):
                            kwargs['tessdata'] = os.environ['TESSDATA_PREFIX']
                        textpage = page.get_textpage_ocr(**kwargs)
                        text = page.get_text(textpage=textpage).strip()
                        if not text:
                            raise ValueError('OCR không trả về văn bản; cần kiểm tra trang')
                        entry['method'] = 'ocr'
            except Exception as error:
                entry.update(method='failed', error=f'{type(error).__name__}: {error}')
                report['missing_pages'].append(index + 1)
            report['pages'].append(entry)
            parts.append(text)
    return '\n\n'.join(parts), report
