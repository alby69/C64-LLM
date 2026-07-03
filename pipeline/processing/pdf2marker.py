import os
import sys
import json
import time
import re
from pathlib import Path

_MARKER_AVAILABLE = False
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    _MARKER_AVAILABLE = True
except ImportError:
    pass


def convert_pdf(pdf_path, output_dest, force_ocr=False, use_llm=False):
    if _MARKER_AVAILABLE:
        ext = os.path.splitext(pdf_path)[1].lower()
        if ext == ".pdf":
            return _convert_with_marker(pdf_path, output_dest, force_ocr, use_llm)
        return {"status": "error", "error": f"Unsupported format: {ext}"}
    else:
        return _convert_with_fitz(pdf_path, output_dest)


def _convert_with_marker(pdf_path, output_dest, force_ocr=False, use_llm=False):
    start = time.time()

    converter = PdfConverter(
        artifact_dict=create_model_dict(),
    )
    rendered = converter(pdf_path)

    md_text, md_metadata, md_images = text_from_rendered(rendered)

    if output_dest.endswith(".txt"):
        base = output_dest[:-4]
    else:
        base = output_dest

    md_path = base + ".md"
    txt_path = base + ".txt"
    meta_path = base + ".meta.json"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "source": pdf_path,
            "pages": md_metadata.get("page_stats", []),
            "toc": md_metadata.get("table_of_contents", []),
            "total_time": round(time.time() - start, 2),
        }, f, indent=2)

    plain_text = _strip_markdown(md_text)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)

    return {
        "status": "ok",
        "markdown": md_path,
        "text": txt_path,
        "metadata": meta_path,
        "engine": "marker-pdf",
        "total_time": round(time.time() - start, 2),
    }


def _convert_with_fitz(pdf_path, output_dest):
    import fitz

    start = time.time()

    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        blocks = page.get_text("blocks")
        block_text = "\n".join([b[4] for b in blocks])
        full_text += block_text + "\n\f"
    doc.close()

    if output_dest.endswith(".txt"):
        base = output_dest[:-4]
    else:
        base = output_dest

    txt_path = base + ".txt"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    return {
        "status": "ok",
        "text": txt_path,
        "engine": "fitz (PyMuPDF)",
        "total_time": round(time.time() - start, 2),
    }


def _strip_markdown(md_text):
    text = re.sub(r'```.*?```', '', md_text, flags=re.DOTALL)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[([^\]]*)\]\(.*?\)', r'\1', text)
    text = re.sub(r'[#*_~`>|]{1,}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def main():
    if len(sys.argv) < 3:
        print("Usage: python pipeline/pdf2marker.py <input.pdf> <output>")
        print("  output: path without extension (produces .md, .txt, .meta.json with marker-pdf)")
        print("       or: path ending in .txt (produces .txt with fallback fitz)")
        print()
        if _MARKER_AVAILABLE:
            print("Engine: marker-pdf (full markdown + OCR)")
        else:
            print("Engine: fitz/PyMuPDF (fallback — install 'pip install marker-pdf' for markdown+OCR)")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dest = sys.argv[2]

    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_dest) or ".", exist_ok=True)

    result = convert_pdf(pdf_path, output_dest)
    if result["status"] == "ok":
        print(f"[OK] {result['engine']} — {result['total_time']:.1f}s")
        for key in ("text", "markdown", "metadata"):
            if key in result:
                print(f"  {key}: {result[key]}")
    else:
        print(f"[ERR] {result.get('error', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
