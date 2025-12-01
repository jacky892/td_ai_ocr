import fitz # PyMuPDF

def extract_single_page(input_pdf_path, page_number, output_pdf_path):
    """
    Extracts a specific page from a PDF and saves it as a new PDF.

    Args:
        input_pdf_path (str): Path to the input PDF file.
        page_number (int): The 1-based index of the page to extract.
        output_pdf_path (str): Path to save the extracted page as a new PDF.
    """
    try:
        doc = fitz.open(input_pdf_path)
        if 1 <= page_number <= doc.page_count:
            output_doc = fitz.open()  # Create a new, empty PDF
            output_doc.insert_pdf(doc, from_page=page_number - 1, to_page=page_number - 1)
            output_doc.save(output_pdf_path)
            output_doc.close()
            print(f"Page {page_number} extracted successfully to {output_pdf_path}")
        else:
            print(f"Error: Page number {page_number} is out of range for {input_pdf_path}")
        doc.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract a single page from a PDF.")
    parser.add_argument("input_pdf", help="Path to the input PDF file.")
    parser.add_argument("page_num", type=int, help="The 1-based page number to extract.")
    parser.add_argument("output_pdf", help="Path to save the extracted page as a new PDF.")

    args = parser.parse_args()

    extract_single_page(args.input_pdf, args.page_num, args.output_pdf)
