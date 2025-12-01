import sys
import os
from pdf2image import convert_from_path

def extract_page_as_jpg(pdf_path, page_num, output_path):
    """
    Extracts a specific page from a PDF as a JPG image.
    Page numbers are 1-based for the CLI usage.
    """
    try:
        # Convert just the specified page (f=from_page, l=last_page)
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            fmt='jpeg',
            single_file=True # Ensures the output filename is exactly as specified
        )

        if images:
            # Save the image with the specified filename
            images[0].save(output_path, 'JPEG')
            print(f"Successfully extracted page {page_num} to {output_path}")
        else:
            print(f"Could not extract page {page_num}.")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Ensure Poppler utilities are installed and in your system's PATH.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python pdf_page_to_jpg.py <pdf_file_path> <page_number> <output_image_path.jpg>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    page_number = int(sys.argv[2])
    output_image = sys.argv[3]

    if not output_image.lower().endswith('.jpg') and not output_image.lower().endswith('.jpeg'):
        print("Output file must have a .jpg or .jpeg extension.")
        sys.exit(1)

    extract_page_as_jpg(pdf_file, page_number, output_image)

