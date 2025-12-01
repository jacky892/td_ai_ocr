import fitz  # PyMuPDF
import argparse
import os
import pytesseract
from PIL import Image
import io

def pdf_to_text(pdf_path, page_number=None, lang='chi_sim+eng'):
    """
    Extracts text from a specified page of a PDF file, using OCR if necessary.

    :param pdf_path: Path to the PDF file.
    :param page_number: The 1-based page number to extract text from. 
                        If None, extracts text from all pages.
    :param lang: Language for Tesseract OCR.
    :return: The extracted text.
    """
    if not os.path.exists(pdf_path):
        return "Error: PDF file not found."

    doc = fitz.open(pdf_path)
    text = ""

    try:
        # Check if Tesseract is installed
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        return "Error: Tesseract is not installed or not in your PATH. Please install Tesseract."

    if page_number is not None:
        if 1 <= page_number <= len(doc):
            page = doc.load_page(page_number - 1)
            text = page.get_text()
            if not text.strip():  # If no text, use OCR
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(img, lang=lang)
        else:
            return f"Error: Page number {page_number} is out of range. The document has {len(doc)} pages."
    else:
        for i in range(len(doc)):
            page = doc.load_page(i)
            page_text = page.get_text()
            if not page_text.strip():  # If no text, use OCR
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(img, lang=lang)
            
            text += f"--- Page {i+1} ---\n"
            text += page_text
            text += "\n"

    doc.close()
    return text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a PDF file to text, page by page, using OCR if necessary.")
    parser.add_argument("pdfname", help="The path to the PDF file.")
    parser.add_argument("-page", type=int, help="The page number to convert to text (1-based).")
    parser.add_argument("-lang", type=str, default='chi_sim+eng', help="Language for Tesseract OCR (e.g., 'eng', 'chi_sim').")

    args = parser.parse_args()

    extracted_text = pdf_to_text(args.pdfname, args.page, args.lang)
    print(extracted_text)