import os
import sys
import json
import csv
import argparse
from collections import defaultdict

# Import necessary functions from existing scripts
from compare_ocr_output_detailed import discover_processed_files, FIELDS_MAPPING, get_nested_value
from verify_field import verify_field
from tradedec_notes_ocr_v7 import generate_single_pdf_output, OLLAMA_DEFAULT_MODEL, GEMINI_DEFAULT_MODEL, PROMPTS, get_pdf_file_list

def find_pdf_file(pdf_dir, filename):
    """
    Searches for a PDF file in the given directory (recursively).
    """
    for root, dirs, files in os.walk(pdf_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

def normalize_value(value):
    """
    Normalizes a value for comparison (strip whitespace, lowercase).
    """
    if value is None:
        return ""
    return str(value).strip().lower()

# Models to compare (module-level constants)
MODEL_A = "gemini-2.5-pro"
MODEL_B = "qwen3-vl_235b-cloud"
VERIFY_MODEL = "qwen3-vl:235b-cloud" # Model used by verify_field.py (Ollama model name)

def main():
    parser = argparse.ArgumentParser(description="Verify conflicting fields between models and optionally generate missing model outputs.")
    parser.add_argument("--output-dir", default="_multi_model_output", help="Root directory of model outputs.")
    parser.add_argument("--pdf-dir", required=True, help="Directory containing source PDF files.")
    parser.add_argument("--format", choices=["csv", "md"], default="csv", help="Output format.")
    parser.add_argument("--output-file", help="Optional output file path.")

    # Arguments for model output generation (from tradedec_notes_ocr_v7.py)
    parser.add_argument("--page", type=int, default=1, help="Page number to extract from each PDF (for generation).")
    parser.add_argument("--type", choices=list(PROMPTS.keys()), default="declaration", help="Type of document (for generation).")
    parser.add_argument("--provider", choices=["ollama", "ollama_cli", "gemini"], default="ollama", help="AI Provider (for generation).")
    parser.add_argument("--model", help=f"Specify model name (default: {OLLAMA_DEFAULT_MODEL} for ollama, {GEMINI_DEFAULT_MODEL} for gemini, for generation).")
    parser.add_argument("--api-key", help="API Key for providers like Gemini (or set GOOGLE_API_KEY, for generation).")
    parser.add_argument("--rotate", type=int, default=0, help="Rotate image in degrees (e.g., -90 for clockwise, for generation).")
    parser.add_argument("--timeout", type=int, default=1800, help="Request timeout in seconds for the AI provider (default: 1800, for generation).")
    parser.add_argument("--debug", action="store_true", help="Print debug information during generation.")
    parser.add_argument("--overwrite-generated", action="store_true", help="Force regeneration of model output even if it exists.")

    args = parser.parse_args()

    # Determine model names for generation based on args.model or defaults
    MODEL_A_GEN_NAME = args.model or GEMINI_DEFAULT_MODEL if args.provider == "gemini" else OLLAMA_DEFAULT_MODEL
    MODEL_B_GEN_NAME = args.model or GEMINI_DEFAULT_MODEL if args.provider == "gemini" else OLLAMA_DEFAULT_MODEL

    all_pdf_files = get_pdf_file_list(args.pdf_dir)
    generated_count = 0
    failed_generation = []
    
    print("\n--- Starting Model Output Generation Phase ---", file=sys.stderr)
    for pdf_path in all_pdf_files:
        src_filename = os.path.basename(pdf_path)
        
        # --- Generate for MODEL_A ---
        model_a_output_dir = os.path.join(args.output_dir, MODEL_A.replace(":", "_").replace("/", "_"))
        os.makedirs(model_a_output_dir, exist_ok=True)
        model_a_output_path = os.path.join(model_a_output_dir, f"{src_filename}.{args.type}.gemini.json") # Assuming gemini for MODEL_A from its name

        should_generate_a = args.overwrite_generated or not os.path.exists(model_a_output_path)
        
        if should_generate_a:
            print(f"Generating output for {src_filename} with {MODEL_A}...", file=sys.stderr)
            data_a = generate_single_pdf_output(
                pdf_path=pdf_path,
                page_num=args.page,
                doc_type=args.type,
                provider=args.provider, # Using the general provider from args
                model_name=MODEL_A_GEN_NAME,
                api_key=args.api_key,
                rotate=args.rotate,
                timeout=args.timeout,
                debug=args.debug
            )
            if data_a:
                try:
                    with open(model_a_output_path, 'w', encoding='utf-8') as f:
                        json.dump(data_a, f, indent=2, ensure_ascii=False)
                    print(f"Successfully saved {MODEL_A} output to: {model_a_output_path}", file=sys.stderr)
                    generated_count += 1
                except IOError as e:
                    print(f"Failed to write {MODEL_A} output for {src_filename}: {e}", file=sys.stderr)
                    failed_generation.append(src_filename)
            else:
                print(f"Failed to generate {MODEL_A} output for {src_filename}.", file=sys.stderr)
                failed_generation.append(src_filename)
        else:
            print(f"Skipping generation for {src_filename} with {MODEL_A}: output exists.", file=sys.stderr)

        # --- Generate for MODEL_B ---
        model_b_output_dir = os.path.join(args.output_dir, MODEL_B.replace(":", "_").replace("/", "_"))
        os.makedirs(model_b_output_dir, exist_ok=True)
        # Assuming ollama for MODEL_B from its name 'qwen3-vl_235b-cloud'
        model_b_output_path = os.path.join(model_b_output_dir, f"{src_filename}.{args.type}.ollama.json") 
        
        should_generate_b = args.overwrite_generated or not os.path.exists(model_b_output_path)

        if should_generate_b:
            print(f"Generating output for {src_filename} with {MODEL_B}...", file=sys.stderr)
            data_b = generate_single_pdf_output(
                pdf_path=pdf_path,
                page_num=args.page,
                doc_type=args.type,
                provider=args.provider, # Using the general provider from args
                model_name=MODEL_B_GEN_NAME,
                api_key=args.api_key,
                rotate=args.rotate,
                timeout=args.timeout,
                debug=args.debug
            )
            if data_b:
                try:
                    with open(model_b_output_path, 'w', encoding='utf-8') as f:
                        json.dump(data_b, f, indent=2, ensure_ascii=False)
                    print(f"Successfully saved {MODEL_B} output to: {model_b_output_path}", file=sys.stderr)
                    generated_count += 1
                except IOError as e:
                    print(f"Failed to write {MODEL_B} output for {src_filename}: {e}", file=sys.stderr)
                    if src_filename not in failed_generation: # Avoid duplicates
                        failed_generation.append(src_filename)
            else:
                print(f"Failed to generate {MODEL_B} output for {src_filename}.", file=sys.stderr)
                if src_filename not in failed_generation: # Avoid duplicates
                    failed_generation.append(src_filename)
        else:
            print(f"Skipping generation for {src_filename} with {MODEL_B}: output exists.", file=sys.stderr)
    
    print(f"\n--- Generation Phase Complete: {generated_count} files generated, {len(failed_generation)} files failed. ---", file=sys.stderr)

    discovered_files = discover_processed_files(args.output_dir)
    results = []

    unverified_pdfs = []
    for pdf_path in all_pdf_files:
        src_filename = os.path.basename(pdf_path)
        if src_filename not in discovered_files or \
           MODEL_A not in discovered_files[src_filename] or \
           MODEL_B not in discovered_files[src_filename]:
            unverified_pdfs.append(src_filename)
    
    if unverified_pdfs:
        print("\n--- PDFs with Missing Model Outputs (Unverified) ---", file=sys.stderr)
        for pdf in unverified_pdfs:
            print(f"  - {pdf}", file=sys.stderr)
        print("---------------------------------------------------\n", file=sys.stderr)
    else:
        print("\n--- All PDFs have model outputs for both comparison models. ---", file=sys.stderr)

    # --- Report on unverified outputs (outputs without a source PDF in the dir) ---
    pdf_basenames = {os.path.basename(p) for p in all_pdf_files}
    unverified_outputs = []
    for pdf_filename in discovered_files.keys():
        if pdf_filename not in pdf_basenames:
            unverified_outputs.append(pdf_filename)
    
    if unverified_outputs:
        print("\n--- Model Outputs without a matching PDF in the directory ---", file=sys.stderr)
        for pdf in unverified_outputs:
            print(f"  - {pdf}", file=sys.stderr)
        print("----------------------------------------------------------\n", file=sys.stderr)

    print(f"Scanning for conflicts between {MODEL_A} and {MODEL_B}...", file=sys.stderr)

    for pdf_filename, model_map in discovered_files.items():
        if MODEL_A not in model_map or MODEL_B not in model_map:
            continue # Skip if we don't have both models

        # Find source PDF
        pdf_path = find_pdf_file(args.pdf_dir, pdf_filename)
        if not pdf_path:
            print(f"Warning: Source PDF '{pdf_filename}' not found in '{args.pdf_dir}'. Skipping.", file=sys.stderr)
            continue

        # Load data
        try:
            with open(model_map[MODEL_A], 'r', encoding='utf-8') as f:
                data_a = json.load(f)
            with open(model_map[MODEL_B], 'r', encoding='utf-8') as f:
                data_b = json.load(f)
        except Exception as e:
            print(f"Error loading JSON for {pdf_filename}: {e}", file=sys.stderr)
            continue

        # Compare fields with best-effort and graceful error handling
        for group_name, fields in FIELDS_MAPPING.items():
            if group_name == "items":
                continue # Skip items for now (complexity)

            for field_path, (display_name, model_specific_paths) in fields.items():
                try:
                    # Get value for Model A
                    default_path = f"{group_name}.{field_path}"
                    path_a = model_specific_paths.get(MODEL_A, default_path)
                    val_a = get_nested_value(data_a, path_a)

                    # Get value for Model B
                    path_b = model_specific_paths.get(MODEL_B, default_path)
                    val_b = get_nested_value(data_b, path_b)

                    # Compare - a conflict exists if normalized values are different
                    if normalize_value(val_a) != normalize_value(val_b):
                        print(f"Conflict found in {pdf_filename} - {display_name}: '{val_a}' vs '{val_b}'", file=sys.stderr)
                        
                        # Verify the conflict
                        print(f"  Verifying...", file=sys.stderr)
                        verification_result = verify_field(
                            pdf_path=pdf_path,
                            page_number=1, # Assumption: Page 1
                            field_name_input=display_name, # Use display name (English)
                            model=VERIFY_MODEL
                        )

                        verified_value = "Verification Failed"
                        explanation = ""
                        if verification_result:
                            verified_value = verification_result.get("value", "N/A")
                            explanation = verification_result.get("explanation", "")

                        results.append({
                            "Filename": pdf_filename,
                            "Field": display_name,
                            f"{MODEL_A} Value": val_a if val_a is not None else "N/A",
                            f"{MODEL_B} Value": val_b if val_b is not None else "N/A",
                            "Verified Value": verified_value,
                            "Explanation": explanation
                        })
                except Exception as e:
                    print(f"Error comparing field '{display_name}' in {pdf_filename}: {e}", file=sys.stderr)
                    # Optionally, you could add this error to a separate report
                    continue

    # Output
    output_stream = sys.stdout
    if args.output_file:
        output_stream = open(args.output_file, 'w', encoding='utf-8')

    try:
        if args.format == "csv":
            fieldnames = ["Filename", "Field", f"{MODEL_A} Value", f"{MODEL_B} Value", "Verified Value", "Explanation"]
            writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        elif args.format == "md":
            output_stream.write(f"| Filename | Field | {MODEL_A} | {MODEL_B} | Verified Value | Explanation |\n")
            output_stream.write("|---|---|---|---|---|---|\n")
            for row in results:
                output_stream.write(f"| {row['Filename']} | {row['Field']} | {row[f'{MODEL_A} Value']} | {row[f'{MODEL_B} Value']} | {row['Verified Value']} | {row['Explanation']} |\n")
    finally:
        if args.output_file:
            output_stream.close()
            print(f"Results written to {args.output_file}", file=sys.stderr)

if __name__ == "__main__":
    main()
