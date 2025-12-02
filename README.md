# Trade Document OCR Extractor

This script, `tradedec_notes_ocr_v7.py`, uses AI vision models (like Google Gemini or local Ollama models) to extract structured JSON data from PDF trade documents such as customs declarations and release notifications.

It supports processing single files or batch processing an entire directory of PDFs.

## Usage

### Basic Command Structure
```bash
python tradedec_notes_ocr_v7.py <input_path> --page <page_number> --type <document_type> [options]
```

### Key Arguments
-   `input_path`: Path to a single PDF file or a directory containing multiple PDF files.
-   `--page`: The page number within the PDF to process (1-based).
-   `--type`: The type of document. Choices: `declaration`, `notification`, `packing`.

### AI Provider Options
-   `--provider`: Choose the AI provider. Choices: `gemini`, `ollama`.
-   `--model`: (Optional) Specify a model name. If not provided, a default model for the selected provider will be used.
-   `--api-key`: Required for some providers like Gemini. Can also be set via the `GOOGLE_API_KEY` environment variable.

## Examples

### Processing a Single File
This command processes page 1 of a single PDF file using the default `gemini` model. Note that you may need to escape special characters like parentheses in your shell.
```bash
python tradedec_notes_ocr_v7.py "rb_and_sg/RB单世华走货报关单(2025.05.08).pdf" --page 1 --type declaration --provider gemini
```

### Batch Processing a Directory
This command processes page 1 of all PDF files found in the `rb_and_sg/` directory.
```bash
python tradedec_notes_ocr_v7.py rb_and_sg --page 1 --type declaration --provider gemini
```

To force re-processing of files that already have an output JSON, use the `--overwrite` flag:
```bash
python tradedec_notes_ocr_v7.py rb_and_sg --page 1 --type declaration --provider gemini --overwrite
```

### Comparing Model Outputs
Use the `--compare` argument to compare the current run's outputs against previously generated JSON files from another model or run. This feature requires the `jsondiff` Python library (`pip install jsondiff`).

```bash
python tradedec_notes_ocr_v7.py rb_and_sg --page 1 --type declaration --provider gemini --model gemini-2.5-flash --compare gemini-2.5-pro
```

In this example:
1.  The script will process files using the `gemini-2.5-flash` model and save results to the `gemini-2.5-flash/` directory.
2.  For each file, it will then look inside the `gemini-2.5-pro/` directory for the corresponding JSON from a previous run.
3.  If a corresponding file is found and differences are detected by `jsondiff`, these differences will be aggregated.
4.  After all files are processed, an aggregate diff report named `gemini-2.5-flash_vs_gemini-2.5-pro.diff.json` will be saved inside the `gemini-2.5-pro/` comparison directory. This report will detail all detected differences across the batch.

## Output Files

The script saves extracted data into a directory named after the model used (e.g., `gemini-2.5-pro/`). This keeps results from different models organized.

The output JSON filename is based on the input PDF's name, with the document type and provider appended for clarity.

-   **Input:** `rb_and_sg/SG单世华走货报关单(2025.06.19).pdf`
-   **Model:** `gemini-2.5-pro` (this is an example)
-   **Output Path:** `gemini-2.5-pro/SG单世华走货报关单(2025.06.19).pdf.declaration.gemini.json`

## Detailed Comparison of All Model Outputs

The `compare_ocr_output_detailed.py` script provides a way to generate a detailed, side-by-side comparison of the JSON outputs from multiple OCR models for each processed document.

### File and Directory Structure

The script expects a specific directory structure to discover the model outputs. The `tradedec_notes_ocr_v7.py` script can generate this structure automatically. A root directory (e.g., `_multi_model_output/`) should contain subdirectories, where each subdirectory is named after the model that generated the outputs within it.

```
_multi_model_output/
├───gemini-2.5-pro/
│   └───...
├───mistral-small3.2_latest/
│   └───...
├───qwen3-vl_235b-cloud/
│   └───...
└───qwen3-vl_32b/
    └───...
```

### Usage

Run the script from the command line, specifying the output directory and desired format.

```bash
python compare_ocr_output_detailed.py --output-dir _multi_model_output --format md
```

-   `--output-dir`: The root directory containing the model output subdirectories. Defaults to `_multi_model_output`.
-   `--format`: The output format. `md` for a Markdown table (default), or `csv` for a CSV file printed to standard output.

### Example Markdown Output

The script will print a comparison table for each source PDF file it finds across the model directories.

```markdown
### Comparison for: sample_declaration.pdf

| Field Group | Field | gemini-2.5-pro | mistral-small3.2_latest | qwen3-vl_235b-cloud | qwen3-vl_32b |
|---|---| --- | --- | --- | --- |
| **document_info** | Document Type | Customs Export Declaration | N/A | Customs Export Declaration | N/A |
| **document_info** | Customs Declaration No. | 530420250040970934 | N/A | 530420250040970934 | N/A |
| **document_info** | Declaration Date | 2025-06-19 | N/A | 2025-06-19 | N/A |
| **document_info** | Export Date | N/A | N/A |  | N/A |
| **parties** | Consignor Name | 开平市世华纪元经贸有限公司 | N/A | 开平市世华纪元经贸有限公司 | N/A |
| **parties** | Consignor Code | 91440783714753661E | N/A | 91440783714753661E | N/A |
| **parties** | Consignee | RETAIL HOLDINGS PTY LIMITED | N/A | RETAIL HOLDINGS PTY LIMITED | N/A |
| **parties** | Declaring Agent | 深圳市东运货运有限公司 (91440300MA5FC50094) | N/A | 深圳市东运货运有限公司 (91440300MA5FC50094) | N/A |
| **coded_attributes** | Trade Mode | 一般贸易 | N/A | 一般贸易 | N/A |
| **coded_attributes** | Trade Mode ID | 0110 | 0110 | 0110 | 0110 |
| **coded_attributes** | Levy Nature | 一般征税 | N/A | 一般征税 | N/A |
| **coded_attributes** | Levy Nature ID | 101 | 101 | 101 | 101 |
| **coded_attributes** | Customs Office | N/A | N/A |  | N/A |
| **coded_attributes** | Customs Office ID | N/A |  |  | 5304 |
| **coded_attributes** | Exit Port | 蛇口海关 | N/A | 蛇口海关 | N/A |
| **coded_attributes** | Exit Port ID | 5304 | 5304 | 5304 | 5304 |
| **coded_attributes** | Transaction Mode | FOB | N/A | FOB | N/A |
| **coded_attributes** | Transaction Mode ID | 3 | 3 | 3 | 3 |
| **coded_attributes** | Transport Mode | 水路运输 | N/A | 水路运输 | N/A |
| **coded_attributes** | Transport Mode ID | 2 | 2 | 2 | 2 |
| **coded_attributes** | Domestic Source Place | N/A | N/A |  | N/A |
| **coded_attributes** | Domestic Source Place ID | N/A | 44079 |  | 44079 |
| **coded_attributes** | Wrapping Type | 纸制或纤维板制盒/箱 | N/A | 纸制或纤维板制盒/箱 | N/A |
| **coded_attributes** | Wrapping Type ID | 22 | 22 | 22 | 22 |
| **logistics** | Trading Country | 澳大利亚 | N/A | 澳大利亚 | N/A |
| **logistics** | Trading Country ID | AUS | AUS | AUS | AUS |
| **logistics** | Destination Country | 澳大利亚 | N/A | 澳大利亚 | N/A |
| **logistics** | Destination Country ID | AUS000 | AUS | AUS000 | AUS000 |
| **logistics** | Destination Port | 蛇口 | N/A | 蛇口 | N/A |
| **logistics** | Destination Port ID | 470101 | AUS000 | 470101 | 470101 |
| **logistics** | Transport Tool ID | UN9367205/146S | N/A | UN9367205/146S | N/A |
| **logistics** | Bill of Lading No. | ES32506191389 | N/A | ES32506191389 | N/A |
| **summary** | Total Packages | 352 | N/A | N/A | N/A |
| **summary** | Gross Weight (kg) | 3936 | N/A | N/A | N/A |
| **summary** | Net Weight (kg) | 3584 | N/A | N/A | N/A |
| **items[0]** | Line No. | 1 | 1 | 1 | 1 |
| **items[0]** | HS Code | 6204620000 | N/A | 6204620000 | N/A |
| **items[0]** | Product Name (CN) | 棉梭织女装短裤 | N/A | 棉梭织女装短裤 | N/A |
| **items[0]** | Specification | 3|1|梭织|短裤|女式|100%棉|Sportsgirl牌|货号: 080412 | 311梭织|短裤|女式|100%棉|Sportsgirl牌|货号:080412 | 3|1|梭织|短裤|女式|100%棉|Sportsgirl牌|货号: 080412 | N/A |
| **items[0]** | Quantity | 1825 | N/A | 1825 | N/A |
| **items[0]** | Unit | 条 | 件 | 条 | 条 |
| **items[0]** | Unit Price | 9.0 | N/A | 9.0000 | N/A |
| **items[0]** | Total Price | 16425.0 | N/A | 16425.00 | N/A |
| **items[0]** | Net Weight (kg) | 655 | N/A | 655 | N/A |
| **items[0]** | Origin Country | 中国 | N/A | 中国 | N/A |
| **items[0]** | Origin Country ID | CHN | CHN | CHN | CHN |
| **items[0]** | Final Destination Country | 澳大利亚 | 澳大利亚 | 澳大利亚 | 澳大利亚 |
| **items[0]** | Final Destination Country ID | AUS | AUS | AUS | AUS |
| **items[0]** | Domestic Source Place | 江门 | 江门 | 江门 | 江门 |
| **items[0]** | Domestic Source Place ID | 44079 | 44079 | 44079 | 44079 |
| **items[0]** | Tax Mode | 照章征税 | 征税 | 照章征税 | 照章征税 |
| **items[0]** | Tax Mode ID | 1 | 1 | 1 | 1 |
| **items[1]** | Line No. | 2 | N/A (flat structure) | 2 | N/A (flat structure) |
| **items[1]** | HS Code | 6204620000 | N/A (flat structure) | 6204620000 | N/A (flat structure) |
| **items[1]** | Product Name (CN) | 棉梭织女装牛仔短裤 | N/A (flat structure) | 棉梭织女装牛仔短裤 | N/A (flat structure) |
| **items[1]** | Specification | 3|1|梭织|短裤|女式|100%棉|Sportsgirl牌|货号: 079769 | N/A (flat structure) | 3|1|梭织|短裤|女式|100%棉|Sportsgirl牌|货号: 079769 | N/A (flat structure) |
| **items[1]** | Quantity | 4063 | N/A (flat structure) | 4063 | N/A (flat structure) |
| **items[1]** | Unit | 条 | N/A (flat structure) | 条 | N/A (flat structure) |
| **items[1]** | Unit Price | 9.0 | N/A (flat structure) | 9.0000 | N/A (flat structure) |
| **items[1]** | Total Price | 36567.0 | N/A (flat structure) | 36567.00 | N/A (flat structure) |
| **items[1]** | Net Weight (kg) | 1542 | N/A (flat structure) | 1542 | N/A (flat structure) |
| **items[1]** | Origin Country | 中国 | N/A (flat structure) | 中国 | N/A (flat structure) |
| **items[1]** | Origin Country ID | CHN | N/A (flat structure) | CHN | N/A (flat structure) |
| **items[1]** | Final Destination Country | 澳大利亚 | N/A (flat structure) | 澳大利亚 | N/A (flat structure) |
| **items[1]** | Final Destination Country ID | AUS | N/A (flat structure) | AUS | N/A (flat structure) |
| **items[1]** | Domestic Source Place | 江门 | N/A (flat structure) | 江门 | N/A (flat structure) |
| **items[1]** | Domestic Source Place ID | 44079 | N/A (flat structure) | 44079 | N/A (flat structure) |
| **items[1]** | Tax Mode | 照章征税 | N/A (flat structure) | 照章征税 | N/A (flat structure) |
| **items[1]** | Tax Mode ID | 1 | N/A (flat structure) | 1 | N/A (flat structure) |
| **items[2]** | Line No. | 3 | N/A (flat structure) | 3 | N/A (flat structure) |
| **items[2]** | HS Code | 6204620000 | N/A (flat structure) | 6204620000 | N/A (flat structure) |
| **items[2]** | Product Name (CN) | 棉梭织女装牛仔长裤 | N/A (flat structure) | 棉梭织女装牛仔长裤 | N/A (flat structure) |
| **items[2]** | Specification | 3|1|梭织|长裤|女式|100%棉|Sportsgirl牌|货号: 081112 | N/A (flat structure) | 3|1|梭织|长裤|女式|100%棉|Sportsgirl牌|货号: 081112 | N/A (flat structure) |
| **items[2]** | Quantity | 2005 | N/A (flat structure) | 2005 | N/A (flat structure) |
| **items[2]** | Unit | 条 | N/A (flat structure) | 条 | N/A (flat structure) |
| **items[2]** | Unit Price | 11.5 | N/A (flat structure) | 11.5000 | N/A (flat structure) |
| **items[2]** | Total Price | 23057.5 | N/A (flat structure) | 23057.50 | N/A (flat structure) |
| **items[2]** | Net Weight (kg) | 1387 | N/A (flat structure) | 1387 | N/A (flat structure) |
| **items[2]** | Origin Country | 中国 | N/A (flat structure) | 中国 | N/A (flat structure) |
| **items[2]** | Origin Country ID | CHN | N/A (flat structure) | CHN | N/A (flat structure) |
| **items[2]** | Final Destination Country | 澳大利亚 | N/A (flat structure) | 澳大利亚 | N/A (flat structure) |
| **items[2]** | Final Destination Country ID | AUS | N/A (flat structure) | AUS | N/A (flat structure) |
| **items[2]** | Domestic Source Place | 江门 | N/A (flat structure) | 江门 | N/A (flat structure) |
| **items[2]** | Domestic Source Place ID | 44079 | N/A (flat structure) | 44079 | N/A (flat structure) |
| **items[2]** | Tax Mode | 照章征税 | N/A (flat structure) | 照章征税 | N/A (flat structure) |
| **items[2]** | Tax Mode ID | 1 | N/A (flat structure) | 1 | N/A (flat structure) |
```
