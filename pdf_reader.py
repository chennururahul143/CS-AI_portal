import fitz
import os

MAX_CHARS = 6000

def extract_text(filepath):
    try:
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) >= MAX_CHARS:
                break
        doc.close()
        text = text.strip()
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[Document truncated for processing...]"
        if not text:
            return None, "The PDF appears to be empty or image-based (scanned). Text extraction is not supported for scanned PDFs."
        return text, None
    except Exception as e:
        return None, f"Could not read PDF: {str(e)}"

def cleanup_upload(filepath):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except:
        pass