
import argparse
import subprocess
import json
import tempfile
import os
import sys
import requests
import base64
import io
import re
from typing import Optional, Dict, Any, List
from pdf2image import convert_from_path
from shutil import which
from cpdf2txt import extract_text_from_pdf
from tradeutil.trade_declare_support import get_trade_declaration_field_mapping

try:
    from tradeutil.config_utils import get_ollama_host
except ImportError as e:
    print(f"Warning: Could not import get_ollama_host from tradeutil.config_utils: {e}", file=sys.stderr)
    # Fallback if import fails
    def get_ollama_host():
        return os.environ.get("OLLAMA_HOST", "http://localhost:11435")

# Set OLLAMA_HOST env var for subprocess calls
ollama_host = get_ollama_host()
if ollama_host:
    os.environ["OLLAMA_HOST"] = ollama_host

def image_to_base64(pil_image) -> str:
    """Helper to convert PIL image to base64 string."""
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def query_ollama_api(prompt: str, pil_image_path: str, model: str) -> Optional[str]:
    """Sends request to Ollama via the REST API."""
    from PIL import Image
    try:
        pil_image = Image.open(pil_image_path)
    except Exception as e:
        print(f"Error opening image {pil_image_path}: {e}", file=sys.stderr)
        return None

    image_b64 = image_to_base64(pil_image)
    url = f"{ollama_host}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "format": "json"
    }

    print(f"Sending request to {url} (Model: {model})...")
    try:
        response = requests.post(url, json=payload, timeout=300) # 5 min timeout
        response.raise_for_status()
        full_ollama_response = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ollama API Error: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Ollama API JSON Decode Error: {e}. Raw response: {response.text}", file=sys.stderr)
        return None

    raw_response = full_ollama_response.get("response", "")
    if not raw_response or not raw_response.strip():
        # If 'response' is empty, try 'thinking' field (common for some Ollama models)
        raw_response = full_ollama_response.get("thinking", "")

    return raw_response

def check_poppler():
    """Check if poppler is installed."""
    if which("pdftoppm") is None:
        print("ERROR: Poppler is not installed or not in your PATH.")
        print("Please install Poppler to continue.")
        print("On macOS (using Homebrew): brew install poppler")
        print("On Debian/Ubuntu: sudo apt-get install poppler-utils")
        exit(1)

def get_document_label(field_name_input):
    """
    Translates an English field name to its Chinese equivalent for the document,
    or returns the input if it's already a Chinese label.
    """
    all_mappings = get_trade_declaration_field_mapping()
    reverse_mapping = {v: k for k, v in all_mappings.items()}

    # Check if the input is an English field name
    if field_name_input in reverse_mapping:
        return reverse_mapping[field_name_input]
    # Check if the input is already a Chinese field name from the mapping
    elif field_name_input in all_mappings:
        return field_name_input
    else:
        # If it contains a dot, it's likely an English key not found in our mapping
        if '.' in field_name_input:
            print(f"Warning: English field name '{field_name_input}' not found in mapping. "
                  "Attempting to use it as-is in the prompt, which may lead to incorrect results. "
                  "Please ensure this field name exists in tradeutil/trade_declare_support.py mapping.")
        return field_name_input # Assume it's a direct Chinese label or a custom string

def verify_field(pdf_path, page_number, field_name_input, model, rotate_pages=None):
    """
    Extracts a specific page from a PDF, converts it to an image,
    and then uses an LLM to extract a specific field from that image.
    Also uses text extraction for better context.
    """
    check_poppler()

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return None

    # Determine the actual label to look for on the document (Chinese)
    label_on_document = get_document_label(field_name_input)

    # Extract text context
    print(f"Extracting text context for page {page_number}...", file=sys.stderr)
    extracted_text = extract_text_from_pdf(
        pdf_path=pdf_path,
        pages=[page_number],
        rotate_pages=rotate_pages,
        use_ocr=True # Always try OCR for verification context
    )
    
    # If extraction returned nothing useful, provide a placeholder
    if not extracted_text or not extracted_text.strip():
        extracted_text = "(No text could be extracted)"

    temp_image_path = None # Initialize to None

    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_image_file:
            # Convert the specific page to an image
            images = convert_from_path(
                pdf_path,
                first_page=page_number,
                last_page=page_number,
                single_file=True,
                output_folder=os.path.dirname(temp_image_file.name),
                output_file=os.path.basename(temp_image_file.name.replace(".jpg", "")),
                fmt="jpeg"
            )
            
            temp_image_path = images[0].filename # Get the actual filename created by pdf2image
            
            # Handle rotation for the image passed to LLM if needed
            # Note: cpdf2txt handles rotation for text extraction, but here we are preparing the image for the LLM (Ollama).
            # If the user specified rotation, we should probably rotate this image too so the LLM sees it upright.
            if rotate_pages and page_number in rotate_pages:
                 from PIL import Image
                 img = Image.open(temp_image_path)
                 # Rotate 90 degrees clockwise (which is -90 in PIL)
                 img = img.rotate(-90, expand=True)
                 img.save(temp_image_path)
                 print(f"Rotated verification image for page {page_number}.", file=sys.stderr)

        # Define the prompt template directly
        PROMPT_TEMPLATE = """You are an expert OCR data extraction tool. Your task is to extract a single field from the provided image of a document page.

The field to extract is: '{{FIELD_NAME}}'

Here is the text extracted from the page (may contain errors):
\"\"\"
{{EXTRACTED_TEXT}}
\"\"\"

Analyze the image carefully. Return your answer as a JSON object with the following structure:
{
  "field_name": "{{FIELD_NAME}}",
  "value": "The extracted value for the field.",
  "confidence": "high|medium|low",
  "reasoning": "A brief explanation if the value is ambiguous or hard to read."
}

Return ONLY the JSON object. Do not include any other text or markdown formatting."""

        # Substitute the placeholders
        final_prompt = PROMPT_TEMPLATE.replace("{{FIELD_NAME}}", label_on_document)
        final_prompt = final_prompt.replace("{{EXTRACTED_TEXT}}", extracted_text)

        # Prepare and run the ollama command (via API)
        print(f"Running ollama command for field: '{label_on_document}'")
        raw_output = query_ollama_api(final_prompt, temp_image_path, model)

        if raw_output is None:
            print("Error running ollama API.", file=sys.stderr)
            return None
        
        try:
            # Find the JSON part of the output (robustly)
            json_start = raw_output.find('{')
            json_end = raw_output.rfind('}') + 1

            # If JSON object found, try to parse it
            if json_start != -1 and json_end > json_start:
                json_str = raw_output[json_start:json_end]
                parsed_json = json.loads(json_str)
                
                # Add the original requested field_name_input to the output for clarity
                parsed_json['requested_field_name'] = field_name_input
                # Add the actual label used in the prompt
                parsed_json['label_on_document'] = label_on_document
                # Add the extracted text for reference
                parsed_json['extracted_text_context'] = extracted_text
                
                return parsed_json
            else:
                print("Error: No JSON object found in the model's output.", file=sys.stderr)
                print("Raw output:", raw_output, file=sys.stderr)
                return None

        except json.JSONDecodeError:
            print("Error: Could not decode JSON from the model's output.", file=sys.stderr)
            print("Raw output:", raw_output, file=sys.stderr)
            return None

    finally:
        # Clean up the temporary image file
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            # pdf2image sometimes creates additional files (e.g., .ppm) which we should also clean
            # It usually names them with a prefix from output_file argument
            base_temp_name = os.path.basename(temp_image_file.name.replace(".jpg", ""))
            parent_dir = os.path.dirname(temp_image_path)
            for f in os.listdir(parent_dir):
                if f.startswith(base_temp_name) and f != os.path.basename(temp_image_path):
                    os.remove(os.path.join(parent_dir, f))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify a single field in a PDF using an LLM.")
    parser.add_argument("pdf_path", help="Path to the PDF file.")
    parser.add_argument("page_number", type=int, help="The page number to analyze (1-based).")
    parser.add_argument(
        "field_name",
        help="The name of the field to extract (can be Chinese or English from the mapping)."
    )
    parser.add_argument(
        "--model",
#        default="qwen3-vl:235b-cloud",
        default="qwen3-vl:32b",
        help="The ollama model to use for verification."
    )
    # Removed --prompt argument as it's now generated on the fly
    parser.add_argument(
        "--rotate",
        help="Page numbers to rotate 90 degrees clockwise (e.g., '1' or '1,2')."
    )

    args = parser.parse_args()
    
    # Parse rotate args
    rotate_pages = []
    if args.rotate:
        for part in args.rotate.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                rotate_pages.extend(range(start, end + 1))
            else:
                try:
                    rotate_pages.append(int(part))
                except ValueError:
                    pass

    result = verify_field(args.pdf_path, args.page_number, args.field_name, args.model, rotate_pages=rotate_pages)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
