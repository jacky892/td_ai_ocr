import json
import os
from collections import defaultdict

# --- Configuration ---
# Define the files to compare
files_to_compare = [
    ("gemini-2.5-pro", "gemini-2.5-pro/RB单世华走货报关单(2025.05.08).pdf.declaration.gemini.json"),
    ("gemini-2.5-flash", "gemini-2.5-flash/RB单世华走货报关单(2025.05.08).pdf.declaration.gemini.json"),
    ("qwen3-vl_235b-cloud", "qwen3-vl_235b-cloud/RB单世华走货报关单(2025.05.08).pdf.declaration.ollama.json"),
    ("mistral-small3.2_latest", "mistral-small3.2_latest/RB单世华走货报关单(2025.05.08).pdf.declaration.ollama.json"),
    ("qwen3-vl_32b", "qwen3-vl_32b/RB单世华走货报关单(2025.05.08).pdf.declaration.ollama.json")
]

# Define a common set of fields and their paths in the JSON, with optional mappings for different models
# The format is: (Display Name, Default JSON Path, {model_name: model_specific_path})
FIELDS_MAPPING = [
    ("Customs Declaration No.", "document_info.customs_declaration_no", {
        "mistral-small3.2_latest": "customs_declaration_number",
        "qwen3-vl_32b": "DeclarationNo"
    }),
    ("Consignor Name", "parties.consignor.name", {
        "mistral-small3.2_latest": "declaration_company", # This is a guess based on the data
        "qwen3-vl_32b": "ConsignorName"
    }),
    ("Consignee Name", "parties.consignee", {
        "mistral-small3.2_latest": "consignee",
        "qwen3-vl_32b": "ConsigneeName"
    }),
    ("Trade Mode", "coded_attributes.trade_mode", {
        "mistral-small3.2_latest": None, # Not directly available
        "qwen3-vl_32b": "TradeTerms" # Assuming TradeTerms is similar to Trade Mode
    }),
    ("Customs Office", "coded_attributes.customs_office", {
        "mistral-small3.2_latest": "declaration_port", # This is a guess
        "qwen3-vl_32b": "CustomsName"
    }),
    ("Product Name (CN)", "items.0.product_name_cn", {
        "mistral-small3.2_latest": "goods_description",
        "qwen3-vl_32b": "CommodityName"
    }),
    ("Specification", "items.0.specification", {
        "mistral-small3.2_latest": None, # No direct equivalent
        "qwen3-vl_32b": "MarkingAndNumbering" # Closest equivalent
    }),
    ("Net Weight (kg)", "summary.net_weight_kg", {
        "mistral-small3.2_latest": "total_weight",
        "qwen3-vl_32b": "NetWeight"
    }),
    ("Gross Weight (kg)", "summary.gross_weight_kg", {
        "mistral-small3.2_latest": "total_weight", # Mistral only has one weight field
        "qwen3-vl_32b": "GrossWeight"
    }),
    ("Quantity", "items.0.quantity", {
        "mistral-small3.2_latest": "quantity",
        "qwen3-vl_32b": "Quantity"
    }),
    ("Unit Price", "items.0.unit_price", {
        "mistral-small3.2_latest": "unit_price",
        "qwen3-vl_32b": "UnitPrice"
    })
]

def get_nested_value(data, path):
    """Safely retrieves a nested value from a dictionary or list."""
    keys = path.split('.')
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        elif isinstance(data, list) and key.isdigit() and len(data) > int(key):
            data = data[int(key)]
        else:
            return None # Path not found
    return data

def main():
    extracted_data = defaultdict(dict) # {field_display_name: {model_name: value}}

    # Read data from each model's output file
    for model_name, file_path in files_to_compare:
        if not os.path.exists(file_path):
            print(f"Warning: File not found for {model_name}: {file_path}", file=os.stderr)
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for display_name, default_path, model_specific_paths in FIELDS_MAPPING:
                # Determine the path for the current model
                path_to_use = model_specific_paths.get(model_name, default_path)
                
                if path_to_use is not None: # If path is explicitly set to None, skip
                    value = get_nested_value(data, path_to_use)
                    # Handle specific formatting for some fields if necessary
                    if display_name == "Customs Declaration No." and model_name == "gemini-2.5-flash":
                        value = value # No specific formatting needed, just keep original
                    extracted_data[display_name][model_name] = value if value is not None else "N/A"
                else:
                    extracted_data[display_name][model_name] = "N/A"

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_path}: {e}", file=os.stderr)
        except IOError as e:
            print(f"Error reading file {file_path}: {e}", file=os.stderr)

    # Generate the Markdown table
    model_names = [name for name, _ in files_to_compare]
    
    header = "| Field | " + " | ".join(model_names) + " |\n"
    separator = "|---| " + " | ".join(["---"] * len(model_names)) + " |\n"
    
    table_rows = []
    for display_name, model_values in extracted_data.items():
        row_values = [str(model_values.get(name, "N/A")) for name in model_names]
        table_rows.append(f"| {display_name} | " + " | ".join(row_values) + " |")

    print(header + separator + "\n".join(table_rows))

if __name__ == "__main__":
    main()
