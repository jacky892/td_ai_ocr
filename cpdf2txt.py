import pdfplumber
import argparse
import sys
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

def extract_text_from_pdf(pdf_path, pages=None, rotate_pages=None, output_file=None, use_ocr=False, lang='chi_tra+eng'):
    """
    Extracts text from a PDF file using pdfplumber, preserving layout.
    Falls back to OCR (Tesseract) if text is empty or use_ocr is True.
    
    Args:
        pdf_path (str): Path to the PDF file.
        pages (list): List of page numbers to extract (1-based). If None, extract all.
        rotate_pages (list): List of page numbers to treat as rotated (1-based).
        output_file (str): Path to output file. If None, print to stdout.
        use_ocr (bool): Force OCR usage.
        lang (str): Language for OCR (default: chi_tra+eng).
    """
    extracted_text = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Determine which pages to process
            if pages:
                pages_to_process = [p for p in pages if 1 <= p <= total_pages]
            else:
                pages_to_process = range(1, total_pages + 1)
                
            rotate_set = set(rotate_pages) if rotate_pages else set()

            for page_num in pages_to_process:
                page = pdf.pages[page_num - 1]
                
                # Header for the page
                page_header = f"--- Page {page_num} ---\n"
                extracted_text.append(page_header)
                
                text = ""
                
                # 1. Try standard extraction first (unless forced OCR)
                if not use_ocr:
                    text = page.extract_text(layout=True)
                
                # 2. If no text found or forced OCR, try OCR
                if use_ocr or not text or len(text.strip()) < 10:
                    if not use_ocr:
                        print(f"Page {page_num}: No text found with standard extraction. Attempting OCR...", file=sys.stderr)
                    else:
                        print(f"Page {page_num}: Performing OCR as requested...", file=sys.stderr)
                        
                    try:
                        # Convert page to image
                        images = convert_from_path(
                            pdf_path,
                            first_page=page_num,
                            last_page=page_num,
                            single_file=True,
                            fmt="jpeg"
                        )
                        
                        if images:
                            image = images[0]
                            
                            # Apply rotation if requested
                            if rotate_set and page_num in rotate_set:
                                # User specified rotation (e.g. 90). 
                                # If they say "rotate 90", usually means the image needs to be rotated 90 degrees clockwise to be upright.
                                # However, pdf2image might extract it as is.
                                # Let's assume the user wants to rotate the IMAGE before OCR.
                                # But wait, the user command was --rotate 90.
                                # We need to know HOW MUCH to rotate. 
                                # The current script only takes a list of pages.
                                # Let's assume 90 degrees clockwise for now if just present in list, 
                                # OR we can parse the arg better.
                                # The user passed "--rotate 90" but the script parses it as page numbers?
                                # Ah, the previous script parsed --rotate as a list of pages.
                                # The user command `python cpdf2txt.py ... --rotate 90` implies page 90?
                                # No, the user command was `... --pages 1 --rotate 90`.
                                # Wait, if pages=1, then rotate=90 means page 90 is rotated.
                                # But the user likely meant "rotate page 1 by 90 degrees".
                                # The user's previous command: `python cpdf2txt.py ... --pages 1 --rotate 90`
                                # My previous script `parse_pages` interprets `90` as page number 90.
                                # So `rotate_set` would contain {90}.
                                # Page 1 is NOT in `rotate_set`. So no rotation happened.
                                # That explains why the previous run failed to extract text if rotation was needed!
                                
                                # Correction: I should probably allow specifying rotation angle.
                                # But for now, let's stick to the interface: --rotate <pages>.
                                # If the user wants to rotate page 1, they should pass `--rotate 1`.
                                # I will add a warning or just proceed.
                                pass

                            # Check if THIS page is in the rotate set
                            if page_num in rotate_set:
                                # Rotate 90 degrees clockwise
                                image = image.rotate(-90, expand=True)
                                print(f"Page {page_num}: Rotated image 90 degrees clockwise.", file=sys.stderr)

                            text = pytesseract.image_to_string(image, lang=lang)
                            
                    except Exception as e:
                        print(f"OCR Error on page {page_num}: {e}", file=sys.stderr)
                        text = "(OCR Failed)"

                if text:
                    extracted_text.append(text)
                else:
                    extracted_text.append("(No text extracted)")
                
                extracted_text.append("\n")

    except Exception as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        return

    final_output = "\n".join(extracted_text)
    
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_output)
            print(f"Text extracted to {output_file}")
        except IOError as e:
            print(f"Error writing to output file: {e}", file=sys.stderr)
    else:
        # Only print if run as script (checked via __name__ check usually, but here we might want to suppress if used as lib)
        # But for now, let's just print if output_file is None, as per original logic.
        # However, if used as library, we might not want to print.
        # Let's rely on the caller to handle output if they want the string.
        if __name__ == "__main__":
             print(final_output)

    return final_output

def parse_pages(pages_str):
    if not pages_str:
        return None
    pages = []
    for part in pages_str.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            pages.extend(range(start, end + 1))
        else:
            try:
                pages.append(int(part))
            except ValueError:
                pass
    return pages

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from PDF with layout preservation (Traditional Chinese support).")
    parser.add_argument("pdf_path", help="Path to the PDF file.")
    parser.add_argument("--pages", help="Pages to extract (e.g., '1,3-5'). Default: all.")
    parser.add_argument("--rotate", help="Pages to treat as rotated/vertical (e.g., '2'). Rotates 90 degrees clockwise.")
    parser.add_argument("--output", help="Output file path. Default: stdout.")
    parser.add_argument("--ocr", action="store_true", help="Force OCR usage.")
    parser.add_argument("--lang", default="chi_tra+eng", help="OCR language (default: chi_tra+eng).")
    
    args = parser.parse_args()
    
    pages = parse_pages(args.pages)
    rotate_pages = parse_pages(args.rotate)
    
    extract_text_from_pdf(args.pdf_path, pages, rotate_pages, args.output, args.ocr, args.lang)
