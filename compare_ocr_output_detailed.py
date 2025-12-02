import json
import os
from collections import defaultdict
import sys

import csv
import argparse

# --- Configuration ---
# A more detailed field mapping based on the provided JSON structure
FIELDS_MAPPING = {
    "document_info": {
        "document_type": ("Document Type", {"mistral-small3.2_latest": "document_type", "qwen3-vl_32b": "document_type"}),
        "customs_declaration_no": ("Customs Declaration No.", {"mistral-small3.2_latest": "customs_declaration_number", "qwen3-vl_32b": "DeclarationNo"}),
        "declaration_date": ("Declaration Date", {"mistral-small3.2_latest": "declaration_date", "qwen3-vl_32b": "DateOfDeclaration"}),
        "export_date": ("Export Date", {"mistral-small3.2_latest": "declaration_date", "qwen3-vl_32b": "DateOfEntry"}),
    },
    "parties": {
        "consignor.name": ("Consignor Name", {"mistral-small3.2_latest": "declaration_company", "qwen3-vl_32b": "ConsignorName"}),
        "consignor.code": ("Consignor Code", {"mistral-small3.2_latest": "declaration_company_address", "qwen3-vl_32b": "ConsignorNo"}),
        "consignee": ("Consignee", {"mistral-small3.2_latest": "consignee", "qwen3-vl_32b": "ConsigneeName"}),
        "declaring_agent": ("Declaring Agent", {"mistral-small3.2_latest": "declarant", "qwen3-vl_32b": "Declarant"}),
    },
    "coded_attributes": {
        "trade_mode": ("Trade Mode", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "TradeTerms"}),
        "trade_mode_id": ("Trade Mode ID", {}),
        "levy_nature": ("Levy Nature", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "ExemptionType"}),
        "levy_nature_id": ("Levy Nature ID", {}),
        "customs_office": ("Customs Office", {"mistral-small3.2_latest": "declaration_port", "qwen3-vl_32b": "CustomsName"}),
        "customs_office_id": ("Customs Office ID", {}),
        "exit_port": ("Exit Port", {"mistral-small3.2_latest": "declaration_port", "qwen3-vl_32b": "PortOfLoading"}),
        "exit_port_id": ("Exit Port ID", {}),
        "transaction_mode": ("Transaction Mode", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "TradeTerms"}),
        "transaction_mode_id": ("Transaction Mode ID", {}),
        "transport_mode": ("Transport Mode", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "ModeOfTransport"}),
        "transport_mode_id": ("Transport Mode ID", {}),
        "domestic_source_place": ("Domestic Source Place", {"mistral-small3.2_latest": "origin_country", "qwen3-vl_32b": "CountryOfOrigin"}),
        "domestic_source_place_id": ("Domestic Source Place ID", {}),
        "wrapping_type": ("Wrapping Type", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "PackingType"}),
        "wrapping_type_id": ("Wrapping Type ID", {}),
    },
    "logistics": {
        "trading_country": ("Trading Country", {"mistral-small3.2_latest": "origin_country", "qwen3-vl_32b": "CountryOfOrigin"}),
        "trading_country_id": ("Trading Country ID", {}),
        "destination_country": ("Destination Country", {"mistral-small3.2_latest": "destination_country", "qwen3-vl_32b": "CountryOfDestination"}),
        "destination_country_id": ("Destination Country ID", {}),
        "destination_port": ("Destination Port", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "PortOfDischarge"}),
        "destination_port_id": ("Destination Port ID", {}),
        "transport_tool_id": ("Transport Tool ID", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "TransportNo"}),
        "bill_of_lading_no": ("Bill of Lading No.", {"mistral-small3.2_latest": None, "qwen3-vl_32b": None}),
    },
    "items": { # Special handling for list of items
        "line_no": ("Line No.", {"qwen3-vl_32b": None}),
        "hs_code": ("HS Code", {"mistral-small3.2_latest": "goods_code", "qwen3-vl_32b": "CommodityCode"}),
        "product_name_cn": ("Product Name (CN)", {"mistral-small3.2_latest": "goods_description", "qwen3-vl_32b": "CommodityName"}),
        "specification": ("Specification", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "MarkingAndNumbering"}),
        "quantity": ("Quantity", {"mistral-small3.2_latest": "quantity", "qwen3-vl_32b": "Quantity"}),
        "unit": ("Unit", {"mistral-small3.2_latest": None, "qwen3-vl_32b": None}),
        "unit_price": ("Unit Price", {"mistral-small3.2_latest": "unit_price", "qwen3-vl_32b": "UnitPrice"}),
        "total_price": ("Total Price", {"mistral-small3.2_latest": "total_price", "qwen3-vl_32b": "TotalPrice"}),
        "net_weight_kg": ("Net Weight (kg)", {"mistral-small3.2_latest": "total_weight", "qwen3-vl_32b": "NetWeight"}),
        "origin_country": ("Origin Country", {"mistral-small3.2_latest": "origin_country", "qwen3-vl_32b": "CountryOfOrigin"}),
        "origin_country_id": ("Origin Country ID", {}),
        "final_destination_country": ("Final Destination Country", {}),
        "final_destination_country_id": ("Final Destination Country ID", {}),
        "domestic_source_place": ("Domestic Source Place", {}),
        "domestic_source_place_id": ("Domestic Source Place ID", {}),
        "tax_mode": ("Tax Mode", {}),
        "tax_mode_id": ("Tax Mode ID", {}),
    },
    "summary": {
        "total_packages": ("Total Packages", {"mistral-small3.2_latest": None, "qwen3-vl_32b": "ContainerNo", "qwen3-vl_235b-cloud": "total_packages"}),
        "gross_weight_kg": ("Gross Weight (kg)", {"mistral-small3.2_latest": "total_weight", "qwen3-vl_32b": "GrossWeight", "qwen3-vl_235b-cloud": "gross_weight_kg"}),
        "net_weight_kg": ("Net Weight (kg)", {"mistral-small3.2_latest": "total_weight", "qwen3-vl_32b": "NetWeight", "qwen3-vl_235b-cloud": "net_weight_kg"}),
    }
}


def get_nested_value(data, path):
    """Safely retrieves a nested value from a dictionary or list."""
    if path is None:
        return None
    keys = path.split('.')
    for key in keys:
        if isinstance(data, dict):
            if key in data:
                data = data[key]
            else:
                return None
        elif isinstance(data, list):
            if key.isdigit() and len(data) > int(key):
                data = data[int(key)]
            else:
                return None
        else:
            return None # Path not found
    return data

def parse_arguments():
    parser = argparse.ArgumentParser(description="Compare OCR outputs from different models.")
    parser.add_argument(
        "--output-dir",
        default="_multi_model_output",
        help="Root directory containing the model outputs (default: _multi_model_output)"
    )
    parser.add_argument(
        "--format",
        choices=["md", "csv"],
        default="md",
        help="Output format: 'md' (Markdown table) or 'csv' (Comma Separated Values). Default: md"
    )
    return parser.parse_args()

def discover_processed_files(output_dir):
    """
    Scans the output directory for processed JSON files.
    Returns a dict: {pdf_filename: {model_name: full_path}}
    """
    discovered = defaultdict(dict)
    
    if not os.path.exists(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist.", file=sys.stderr)
        return discovered

    # Iterate over subdirectories (assumed to be model names)
    for model_name in os.listdir(output_dir):
        model_dir = os.path.join(output_dir, model_name)
        if not os.path.isdir(model_dir):
            continue

        # Scan for .declaration.*.json files
        for filename in os.listdir(model_dir):
            if ".declaration." in filename and filename.endswith(".json"):
                # Extract original PDF filename (everything before .declaration)
                pdf_filename = filename.split(".declaration.")[0]
                full_path = os.path.join(model_dir, filename)
                discovered[pdf_filename][model_name] = full_path
    
    return discovered

def main():
    args = parse_arguments()
    output_dir = args.output_dir
    output_format = args.format
    
    discovered_files = discover_processed_files(output_dir)
    
    if not discovered_files:
        print(f"No processed files found in '{output_dir}'.", file=sys.stderr)
        return

    # Collect all unique model names across all files to ensure consistent columns
    all_model_names = set()
    for model_map in discovered_files.values():
        all_model_names.update(model_map.keys())
    sorted_model_names = sorted(list(all_model_names))

    # Prepare for CSV output if requested
    csv_writer = None
    if output_format == "csv":
        csv_writer = csv.writer(sys.stdout)
        # Header: Filename, Field Group, Field, Model1, Model2, ...
        header = ["Filename", "Field Group", "Field"] + sorted_model_names
        csv_writer.writerow(header)

    for pdf_filename, model_map in discovered_files.items():
        if output_format == "md":
            print(f"\n### Comparison for: {pdf_filename}\n")

        model_data = {}
        for model_name in sorted_model_names:
            file_path = model_map.get(model_name)
            if not file_path:
                model_data[model_name] = {}
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    model_data[model_name] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading or parsing {file_path}: {e}", file=sys.stderr)
                model_data[model_name] = {}

        table_rows = []
        
        if output_format == "md":
            # Generate headers
            header = "| Field Group | Field | " + " | ".join(sorted_model_names) + " |\n"
            separator = "|---|---| " + " | ".join(["---"] * len(sorted_model_names)) + " |\n"
            table_rows.append(header + separator)

        for group_name, fields in FIELDS_MAPPING.items():
            if group_name == "items":
                continue # Handle items separately

            for field_path, (display_name, model_specific_paths) in fields.items():
                row_values = []
                for model_name in sorted_model_names:
                    data = model_data.get(model_name, {})
                    # Use group_name.field_path as default if not overridden
                    default_path = f"{group_name}.{field_path}"
                    path_to_use = model_specific_paths.get(model_name, default_path)
                    value = get_nested_value(data, path_to_use)
                    row_values.append(str(value) if value is not None else "N/A")

                if output_format == "md":
                    table_rows.append(f"| **{group_name}** | {display_name} | " + " | ".join(row_values) + " |\n")
                elif output_format == "csv":
                    csv_writer.writerow([pdf_filename, group_name, display_name] + row_values)

        # Handle items
        max_items = 0
        for model_name in sorted_model_names:
            data = model_data.get(model_name, {})
            items = get_nested_value(data, "items")
            if isinstance(items, list):
                max_items = max(max_items, len(items))

        if max_items > 0:
             for i in range(max_items):
                for item_field_path, (display_name, model_specific_paths) in FIELDS_MAPPING["items"].items():
                    row_values = []
                    for model_name in sorted_model_names:
                        data = model_data.get(model_name, {})
                        base_path = f"items.{i}" if get_nested_value(data, "items") else ""
                        path_to_use = model_specific_paths.get(model_name)
                        
                        # For models with flat structure, we only show the first item's data
                        if model_name in ["mistral-small3.2_latest", "qwen3-vl_32b"] and i > 0:
                            value = "N/A (flat structure)"
                        elif path_to_use:
                            value = get_nested_value(data, path_to_use)
                        else: # structured models
                             value = get_nested_value(data, f"items.{i}.{item_field_path}")

                        row_values.append(str(value) if value is not None else "N/A")
                    
                    if output_format == "md":
                        table_rows.append(f"| **items[{i}]** | {display_name} | " + " | ".join(row_values) + " |\n")
                    elif output_format == "csv":
                        csv_writer.writerow([pdf_filename, f"items[{i}]", display_name] + row_values)

        if output_format == "md":
            print("".join(table_rows))


if __name__ == "__main__":
    main()
