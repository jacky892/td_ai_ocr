import argparse
import json
import sys
import os
import base64
import io
import re
import requests
import subprocess
import tempfile
from typing import Optional, Dict, Any, List

# --- dependency checks ---
try:
    from pdf2image import convert_from_path
except ImportError:
    print("Error: 'pdf2image' is required. Install via: pip install pdf2image", file=sys.stderr)
    print("Note: You also need 'poppler' installed on your system.", file=sys.stderr)
    sys.exit(1)

try:
    import json_repair
except ImportError:
    print("Error: 'json_repair' is required. Install via: pip install json_repair", file=sys.stderr)
    sys.exit(1)

try:
    from jsondiff import diff, Symbol
    JSONDIFF_AVAILABLE = True
except ImportError:
    JSONDIFF_AVAILABLE = False

# --- Configuration ---
OLLAMA_HOST = "http://localhost:11435"
#OLLAMA_HOST = "http://100.66.106.100:11435"
OLLAMA_DEFAULT_MODEL = "mistral-small3.2:latest"

# Gemini Configuration
GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_DEFAULT_MODEL = "gemini-2.5-pro"
#GEMINI_DEFAULT_MODEL = "gemini-3-pro"

# --- Prompts ---
DECLARATION_PROMPT = """You are a specialized trade document parser. Extract the following fields from the Export Declaration (报关单) and return the data in a strict JSON format.

**JSON Schema:**
{
  "document_info": {
    "document_type": "The type of document (e.g., Customs Export Declaration)",
    "customs_declaration_no": "The customs declaration number (报关单号)",
    "declaration_date": "The date of declaration (申报日期) in YYYY-MM-DD format",
    "export_date": "The date of export (出口日期) in YYYY-MM-DD format"
  },
  "parties": {
    "consignor": {
      "name": "The name of the domestic consignor (境内发货人)",
      "code": "The code of the domestic consignor"
    },
    "consignee": "The name of the overseas consignee (境外收货人)",
    "declaring_agent": "The name and code of the declaring agent (申报单位)"
  },
  "coded_attributes": {
    "trade_mode": "The trade mode (监管方式)",
    "levy_nature": "The nature of levy and exemption (征免性质)",
    "customs_office": "The customs office (备案号)",
    "exit_port": "The port of exit (出/境关别)",
    "transaction_mode": "The transaction mode (成交方式)",
    "transport_mode": "The mode of transport (运输方式)",
    "domestic_source_place": "The domestic source of goods (境内货源地)",
    "wrapping_type": "The wrapping type (包装种类)"
  },
  "logistics": {
    "trading_country": "The trading country (运抵国(地区))",
    "destination_country": "The destination country (指运港)",
    "destination_port": "The destination port (离境口岸)",
    "transport_tool_id": "The transport tool ID (运输工具名称及航次号)",
    "bill_of_lading_no": "The bill of lading number (提运单号)"
  },
  "items": [
    {
      "line_no": "The item line number",
      "hs_code": "The HS code (商品编号)",
      "product_name_cn": "The Chinese name of the product (商品名称)",
      "specification": "The product specification (规格型号)",
      "quantity": "The quantity (数量)",
      "unit": "The unit of quantity (单位)",
      "unit_price": "The unit price (单价)",
      "total_price": "The total price (总价)",
      "net_weight_kg": "The net weight in kg (净重)",
      "origin_country": "The country of origin (原产国)",
      "final_destination_country": "The final destination country (最终目的国)",
      "domestic_source_place": "The domestic source place (境内货源地)",
      "tax_mode": "The tax mode (征免)"
    }
  ],
  "summary": {
    "total_packages": "The total number of packages (件数)",
    "gross_weight_kg": "The gross weight in kg (毛重)",
    "net_weight_kg": "The net weight in kg (净重)"
  }
}

RETURN ONLY JSON. NO MARKDOWN.
"""

PROMPTS = {
    "declaration": DECLARATION_PROMPT,
    "notification": "You are a detailed data extractor. Parse the Customs Release Notification (通关无纸化出口放行通知书) into a strict JSON format as previously instructed. RETURN ONLY JSON. NO MARKDOWN.",
    "packing": "You are an inventory management assistant. Parse the Cargo List into a strict JSON format as previously instructed. RETURN ONLY JSON. NO MARKDOWN."
}

def get_pdf_page_image(pdf_path: str, page_num: int) -> Optional[Any]:
    """Converts a specific PDF page to a PIL Image."""
    try:
        images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
        if not images:
            print(f"Error: Page {page_num} not found or could not be converted in {pdf_path}", file=sys.stderr)
            return None
        return images[0]
    except Exception as e:
        print(f"Error converting PDF to image for '{pdf_path}': {e}", file=sys.stderr)
        return None

def image_to_base64(pil_image) -> str:
    """Helper to convert PIL image to base64 string."""
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def query_ollama(prompt: str, pil_image, model: str, timeout: int) -> Optional[str]:
    """Sends request to Ollama via the REST API."""
    image_b64 = image_to_base64(pil_image)
    url = f"{OLLAMA_HOST}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "format": "json"
    }

    print(f"Sending request to {url} (Model: {model}, Timeout: {timeout}s)...")
    try:
        response = requests.post(url, json=payload, timeout=timeout*2)
        response.raise_for_status()
        full_ollama_response = response.json() # This is the entire JSON response from Ollama
    except requests.exceptions.RequestException as e:
        print(f"Ollama API Error: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e: # Catch JSON decoding errors specifically
        print(f"Ollama API JSON Decode Error: {e}. Raw response: {response.text}", file=sys.stderr)
        return None

    # --- Debug Print: Full Ollama API Response (Raw) ---
    print("\n--- Full Ollama API Response (Raw) ---", file=sys.stderr)
    print(json.dumps(full_ollama_response, indent=2, ensure_ascii=False), file=sys.stderr)
    print("--- End Full Ollama API Response (Raw) ---\
", file=sys.stderr)
    # --- End Debug Print ---

    # Extract the 'response' field, which should contain the JSON string we need
    raw_response_content = full_ollama_response.get("response", "")

    if not raw_response_content or not raw_response_content.strip():
        # If 'response' is empty, try 'thinking' field (common for some Ollama models)
        raw_response_content = full_ollama_response.get("thinking", "")
        if raw_response_content:
            print("Info: 'response' field was empty, using 'thinking' field content.", file=sys.stderr)
        else:
            print("Error: Ollama API returned an empty 'response' field and 'thinking' field was also empty or missing.", file=sys.stderr)
            return None
        
    # Apply cleaning logic, just in case some models ignore `format: "json"` for this field.
    ansi_escape_pattern = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')
    clean_response = ansi_escape_pattern.sub('', raw_response_content)

    # Find the start of the first JSON object in the string.
    first_brace = clean_response.find('{')
    first_bracket = clean_response.find('[')
    
    if first_brace == -1 and first_bracket == -1:
        print("Ollama API Error: Could not find start of JSON in model output.", file=sys.stderr)
        return None
        
    if first_brace != -1 and first_bracket != -1:
        json_start = min(first_brace, first_bracket)
    elif first_brace != -1:
        json_start = first_brace
    else:
        json_start = first_bracket

    # Find the end of the JSON object
    last_brace = clean_response.rfind('}')
    last_bracket = clean_response.rfind(']')
    
    if last_brace == -1 and last_bracket == -1:
        json_end = len(clean_response)
    else:
        json_end = max(last_brace, last_bracket) + 1

    # Extract the potential JSON part of the string.
    potential_json = clean_response[json_start:json_end]
    return potential_json

def query_ollama_cli(prompt: str, pil_image, model: str, timeout: int) -> Optional[str]:
    """Sends request to Ollama via the command-line interface."""
    temp_image_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_image:
            pil_image.save(temp_image, format="JPEG")
            temp_image_path = temp_image.name

        full_prompt_text = f"{prompt} {temp_image_path}"
        command = ["ollama", "run", model]
        
        print(f"Running command: {' '.join(command)} (Timeout: {timeout}s)...")
        
        process = subprocess.run(
            command,
            input=full_prompt_text,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=timeout
        )
        
        raw_response = process.stdout
        
    except FileNotFoundError:
        print("Ollama CLI Error: 'ollama' command not found. Is it installed and in your PATH?", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired as e:
        print(f"Ollama CLI Error: Command timed out after {timeout} seconds.", file=sys.stderr)
        print("--- Stdout from Ollama CLI before timeout ---", file=sys.stderr)
        print(e.stdout if e.stdout else "(empty)", file=sys.stderr)
        print("--- Stderr from Ollama CLI before timeout ---", file=sys.stderr)
        print(e.stderr if e.stderr else "(empty)", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Ollama CLI execution: {e}", file=sys.stderr)
        return None
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)

    if process.returncode != 0:
        print(f"Ollama CLI Error (Exit Code {process.returncode}):", file=sys.stderr)
        print("--- Ollama CLI Stdout ---", file=sys.stderr)
        print(raw_response, file=sys.stderr)
        print("--- Ollama CLI Stderr ---", file=sys.stderr)
        print(process.stderr, file=sys.stderr)
        return None

    # 1. Strip ANSI escape codes used for spinners/etc.
    ansi_escape_pattern = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')
    clean_response = ansi_escape_pattern.sub('', raw_response)
    
    # 2. Find the start of the first JSON object in the string.
    first_brace = clean_response.find('{')
    first_bracket = clean_response.find('[')
    
    if first_brace == -1 and first_bracket == -1:
        print("Ollama CLI Error: Could not find start of JSON in the cleaned model output.", file=sys.stderr)
        print("--- Cleaned Ollama CLI Output ---", file=sys.stderr)
        print(clean_response, file=sys.stderr)
        return None

    if first_brace != -1 and first_bracket != -1:
        json_start = min(first_brace, first_bracket)
    elif first_brace != -1:
        json_start = first_brace
    else:
        json_start = first_bracket
        
    # Find the end of the JSON object
    last_brace = clean_response.rfind('}')
    last_bracket = clean_response.rfind(']')
    
    if last_brace == -1 and last_bracket == -1:
        json_end = len(clean_response)
    else:
        json_end = max(last_brace, last_bracket) + 1

    # 3. Extract the potential JSON part of the string.
    potential_json = clean_response[json_start:json_end]
    return potential_json


def query_gemini(prompt: str, pil_image, model_name: str, api_key: str, timeout: int) -> Optional[str]:
    """Sends request to Google Gemini API."""
    try:
        import google.generativeai as genai
    except ImportError:
        print("Error: 'google-generativeai' is required for Gemini. pip install google-generativeai", file=sys.stderr)
        return None

    print(f"Sending request to Gemini (Model: {model_name}, Timeout: {timeout}s)...")
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel(model_name)
    
    try:
        response = model.generate_content(
            [prompt, pil_image],
            request_options={"timeout": timeout}
        )
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}", file=sys.stderr)
        return None

def clean_and_parse_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to clean and parse JSON from a model's raw text output.
    """
    if not raw_text or not raw_text.strip():
        print("Error: AI model returned an empty response.", file=sys.stderr)
        return None

    clean_text = raw_text.strip()
    if clean_text.startswith("```json") and clean_text.endswith("```"):
        clean_text = clean_text[7:-3].strip()
    elif clean_text.startswith("```") and clean_text.endswith("```"):
        clean_text = clean_text[3:-3].strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        print("Standard JSON parse failed, attempting to repair...")
        try:
            return json_repair.repair_json(clean_text, return_objects=True)
        except Exception as e:
            print(f"Fatal: Could not repair JSON. Error: {e}", file=sys.stderr)
            print("--- Raw Model Output ---", file=sys.stderr)
            print(raw_text, file=sys.stderr)
            print("--- Raw Model Output End ---", file=sys.stderr)
            return None

def get_pdf_file_list(input_path: str) -> List[str]:
    """Scans an input path and returns a list of PDF file paths."""
    pdf_files = []
    if os.path.isdir(input_path):
        try:
            pdf_files = sorted([
                os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith('.pdf')
            ])
            print(f"Found {len(pdf_files)} PDF files in '{input_path}'.")
        except OSError as e:
            print(f"Error reading directory '{input_path}': {e}", file=sys.stderr)
            sys.exit(1)
    elif os.path.isfile(input_path):
        if not input_path.lower().endswith('.pdf'):
            print(f"Error: Input file must be a PDF. Got: {input_path}", file=sys.stderr)
            sys.exit(1)
        pdf_files.append(input_path)
    else:
        print(f"Error: Input path not found: '{input_path}'", file=sys.stderr)
        sys.exit(1)
    return pdf_files

def infer_provider_from_model_dir(model_dir_name: str) -> str:
    """Infers the provider ('gemini' or 'ollama') from the model directory name."""
    return "gemini" if "gemini" in model_dir_name.lower() else "ollama"

def convert_symbols_to_str(item: Any) -> Any:
    """Recursively converts jsondiff Symbol keys in a dictionary to strings."""
    if isinstance(item, dict):
        return {str(k) if isinstance(k, Symbol) else k: convert_symbols_to_str(v) for k, v in item.items()}
    if isinstance(item, list):
        return [convert_symbols_to_str(i) for i in item]
    return item

def run_generation_mode(args, pdf_files: List[str]):
    model_name, api_key = None, None
    if args.provider in ["ollama", "ollama_cli"]:
        model_name = args.model or OLLAMA_DEFAULT_MODEL
    elif args.provider == "gemini":
        model_name = args.model or GEMINI_DEFAULT_MODEL
        api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("Error: --api-key or GOOGLE_API_KEY is required for Gemini.", file=sys.stderr)
            sys.exit(1)

    output_dir = os.path.join("_multi_model_output", model_name.replace(":", "_").replace("/", "_"))
    os.makedirs(output_dir, exist_ok=True)
    print(f"Using model '{model_name}'. Output will be saved to directory: '{output_dir}/'")
    if args.compare:
        print(f"Comparing results against directory: '{args.compare}/'")

    processed_count, skipped_count, failed_count = 0, 0, 0
    all_diffs = {}

    for pdf_path in pdf_files:
        src_filename = os.path.basename(pdf_path)
        provider_suffix = "ollama" if args.provider in ["ollama", "ollama_cli"] else "gemini"
        current_base_filename = f"{src_filename}.{args.type}.{provider_suffix}.json"
        output_path = os.path.join(output_dir, current_base_filename)

        if os.path.exists(output_path) and not args.overwrite:
            print(f"\nSkipping '{src_filename}': output exists. Use --overwrite to force.")
            skipped_count += 1
            continue

        print(f"\n--- Processing: {src_filename} ---")
        pil_image = get_pdf_page_image(pdf_path, args.page)
        if not pil_image:
            failed_count += 1
            continue

        if args.rotate != 0:
            pil_image = pil_image.rotate(args.rotate, expand=True)

        prompt = PROMPTS[args.type]
        raw_response = None
        if args.provider == "ollama":
            raw_response = query_ollama(prompt, pil_image, model_name, args.timeout)
        elif args.provider == "ollama_cli":
            raw_response = query_ollama_cli(prompt, pil_image, model_name, args.timeout)
        elif args.provider == "gemini":
            raw_response = query_gemini(prompt, pil_image, model_name, api_key, args.timeout)
        
        if not raw_response:
            print(f"Failed to get a response from the AI provider for '{src_filename}'.")
            failed_count += 1
            continue

        data = clean_and_parse_json(raw_response)
        if not data:
            failed_count += 1
            continue

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[Save] Successfully saved to: {output_path}")
            processed_count += 1
        except IOError as e:
            print(f"[Save] Failed to write file '{output_path}': {e}", file=sys.stderr)
            failed_count += 1
            continue

        if args.compare:
            compare_provider = infer_provider_from_model_dir(args.compare)
            compare_base_filename = f"{src_filename}.{args.type}.{compare_provider}.json"
            old_output_path = os.path.join("_multi_model_output", args.compare.replace(":", "_").replace("/", "_"), compare_base_filename)
            
            if os.path.exists(old_output_path):
                try:
                    with open(old_output_path, 'r', encoding='utf-8') as f_old:
                        old_data = json.load(f_old)
                    the_diff = diff(old_data, data, syntax='symmetric')
                    if the_diff:
                        all_diffs[src_filename] = the_diff
                except (IOError, json.JSONDecodeError) as e:
                    print(f"[Compare] ERROR: Could not read or parse JSON for diffing. {e}", file=sys.stderr)
    
    if args.compare:
        generate_diff_report(all_diffs, model_name, args.compare)

    print(f"\n--- Batch Complete ---\nSummary: {processed_count} processed, {failed_count} failed, {skipped_count} skipped.")

def run_compare_only_mode(args, pdf_files: List[str]):
    if not args.compare:
        print("FATAL: --compare-only requires the --compare <directory> argument.", file=sys.stderr)
        sys.exit(1)
    if not args.provider:
         print("FATAL: --compare-only requires --provider to be specified.", file=sys.stderr)
         sys.exit(1)

    current_model_name = args.model or (GEMINI_DEFAULT_MODEL if args.provider == 'gemini' else OLLAMA_DEFAULT_MODEL)
    current_model_dir = os.path.join("_multi_model_output", current_model_name.replace(":", "_").replace("/", "_"))
    compare_model_dir = os.path.join("_multi_model_output", args.compare.replace(":", "_").replace("/", "_"))

    print("--- Running in Compare-Only Mode ---")
    print(f"Comparing outputs from '{current_model_dir}/' against '{compare_model_dir}/'")
    
    all_diffs = {}
    compared_count, missing_count = 0, 0

    for pdf_path in pdf_files:
        src_filename = os.path.basename(pdf_path)
        
        provider_suffix = "ollama" if args.provider in ["ollama", "ollama_cli"] else "gemini"
        current_base_filename = f"{src_filename}.{args.type}.{provider_suffix}.json"
        current_output_path = os.path.join(current_model_dir, current_base_filename)

        compare_provider = infer_provider_from_model_dir(args.compare)
        compare_base_filename = f"{src_filename}.{args.type}.{compare_provider}.json"
        old_output_path = os.path.join(compare_model_dir, compare_base_filename)

        if not os.path.exists(current_output_path) or not os.path.exists(old_output_path):
            missing_count += 1
        else:
            try:
                with open(current_output_path, 'r', encoding='utf-8') as f_new, \
                     open(old_output_path, 'r', encoding='utf-8') as f_old:
                    new_data = json.load(f_new)
                    old_data = json.load(f_old)
                
                the_diff = diff(old_data, new_data, syntax='symmetric')
                if the_diff:
                    all_diffs[src_filename] = the_diff
                compared_count += 1
            except (IOError, json.JSONDecodeError) as e:
                print(f"[Compare] ERROR for {src_filename}: Could not read or parse JSON. {e}", file=sys.stderr)
                missing_count += 1

    generate_diff_report(all_diffs, current_model_name, args.compare)
    
    print(f"\n--- Compare-Only Complete ---\nSummary: {compared_count} pairs compared, {missing_count} pairs skipped due to missing files.")

def generate_diff_report(all_diffs: Dict, current_model_name: str, compare_dir: str):
    print("\n" + "#"*70)
    print("###" + " FINAL COMPARISON REPORT".center(64) + "###")
    print("#"*70)

    if all_diffs:
        current_model_sanitized = current_model_name.replace(":", "_").replace("/", "_")
        compare_model_sanitized = compare_dir.replace(":", "_").replace("/", "_")
        diff_filename = f"{current_model_sanitized}_vs_{compare_model_sanitized}.diff.json"
        diff_output_path = os.path.join(compare_dir, diff_filename)

        serializable_diffs = convert_symbols_to_str(all_diffs)

        print(f"\n> Found differences in {len(serializable_diffs)} file(s).")
        print(f"> Attempting to write aggregate diff report to:\n  -> {diff_output_path}\n")
        try:
            with open(diff_output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_diffs, f, indent=2, ensure_ascii=False)
            print(">>> SUCCESS: Aggregate diff file was saved.")
        except (IOError, TypeError) as e:
            print(f">>> FAILED to write aggregate diff file: {e}", file=sys.stderr)
    else:
        print("\n> No differences were detected across any of the compared files.")
        print("> Therefore, no diff file was generated.\n")
    print("#"*70)

def main():
    parser = argparse.ArgumentParser(description="Batch-process Customs PDFs to extract structured JSON using AI Vision.")
    parser.add_argument("input_path", help="Path to a single PDF file or a directory of PDF files.")
    parser.add_argument("--page", type=int, required=True, help="Page number to extract from each PDF.")
    parser.add_argument("--type", choices=["declaration", "notification", "packing"], required=True, help="Type of document.")
    parser.add_argument("--compare-only", action="store_true", help="Skip generation, only compare existing JSON files.")
    parser.add_argument("--output", help="Optional: For single file mode, path to save the JSON output.")
    parser.add_argument("--rotate", type=int, default=0, help="Rotate image in degrees (e.g., -90 for clockwise).")
    parser.add_argument("--overwrite", action="store_true", help="Force processing and overwrite existing output files.")
    parser.add_argument("--compare", help="Directory of a previous run to compare against (e.g., 'gemini-2.5-pro').")
    parser.add_argument("--timeout", type=int, default=1800, help="Request timeout in seconds for the AI provider (default: 1800).")
    
    parser.add_argument("--provider", choices=["ollama", "ollama_cli", "gemini"], default="ollama", help="AI Provider.")
    parser.add_argument("--model", help=f"Specify model name (default: {OLLAMA_DEFAULT_MODEL} for ollama, {GEMINI_DEFAULT_MODEL} for gemini).")
    parser.add_argument("--api-key", help="API Key for providers like Gemini (or set GOOGLE_API_KEY).")

    args = parser.parse_args()

    if (args.compare or args.compare_only) and not JSONDIFF_AVAILABLE:
        print("\n" + "!"*70, file=sys.stderr)
        print("### FATAL: --compare or --compare-only requires 'jsondiff'".center(68), file=sys.stderr)
        print("### Please install it in the correct Python environment.".center(68), file=sys.stderr)
        print(f"### Python Executable: {sys.executable}".center(68), file=sys.stderr)
        print("### Run: pip install jsondiff".center(68), file=sys.stderr)
        print("!"*70, file=sys.stderr)
        sys.exit(1)

    pdf_files = get_pdf_file_list(args.input_path)
    if not pdf_files:
        return

    if args.compare_only:
        run_compare_only_mode(args, pdf_files)
    else:
        run_generation_mode(args, pdf_files)

if __name__ == "__main__":
    main()
