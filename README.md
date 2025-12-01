# Trade Document OCR Extractor

This script, `tradedec_notes_ocr_v6.py`, uses AI vision models (like Google Gemini or local Ollama models) to extract structured JSON data from PDF trade documents such as customs declarations and release notifications.

It supports processing single files or batch processing an entire directory of PDFs.

## Usage

### Basic Command Structure
```bash
python tradedec_notes_ocr_v6.py <input_path> --page <page_number> --type <document_type> [options]
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
python tradedec_notes_ocr_v6.py "rb_and_sg/RB单世华走货报关单(2025.05.08).pdf" --page 1 --type declaration --provider gemini
```

### Batch Processing a Directory
This command processes page 1 of all PDF files found in the `rb_and_sg/` directory.
```bash
python tradedec_notes_ocr_v6.py rb_and_sg --page 1 --type declaration --provider gemini
```

To force re-processing of files that already have an output JSON, use the `--overwrite` flag:
```bash
python tradedec_notes_ocr_v6.py rb_and_sg --page 1 --type declaration --provider gemini --overwrite
```

### Comparing Model Outputs
Use the `--compare` argument to compare the current run's outputs against previously generated JSON files from another model or run. This feature requires the `jsondiff` Python library (`pip install jsondiff`).

```bash
python tradedec_notes_ocr_v6.py rb_and_sg --page 1 --type declaration --provider gemini --model gemini-2.5-flash --compare gemini-2.5-pro
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

The script expects a specific directory structure to discover the model outputs. The `tradedec_notes_ocr_v6.py` script can generate this structure automatically. A root directory (e.g., `_multi_model_output/`) should contain subdirectories, where each subdirectory is named after the model that generated the outputs within it.

```
_multi_model_output/
├───gemini-2.5-flash/
│   ├───RB单世华走货报关单(2025.05.08).pdf.declaration.gemini.json
│   └───RB单世华走货报关单(2025.05.20).pdf.declaration.gemini.json
├───gemini-2.5-pro/
│   ├───RB单世华走货报关单(2025.05.08).pdf.declaration.gemini.json
│   └───RB单世华走货报关单(2025.05.20).pdf.declaration.gemini.json
└───qwen3-vl_32b/
    └───RB单世华走货报关单(2025.05.08).pdf.declaration.ollama.json
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
### Comparison for: SG单世华走货报关单(2025.05.28).pdf

| Field Group | Field | gemini-2.5-flash | gemini-2.5-pro | qwen3-vl_235b-cloud | qwen3-vl_32b |
|---|---| --- | --- | --- | --- |
| **document_info** | Document Type | Customs Export Declaration | 中华人民共和国海关出口货物报关单 | N/A | N/A |
| **document_info** | Customs Declaration No. | 531620250161406906 | 531620250161406906 | N/A | N/A |
| **document_info** | Declaration Date | 2025-05-28 | 2025-05-28 | N/A | N/A |
| **parties** | Consignor Name | 开平市世纪华元经贸有限公司 | 开平市世纪华纪元经贸有限公司 | N/A | N/A |
| **parties** | Consignee | RETAIL HOLDINGS PTY LIMITED (AUS) | RETAIL HOLDINGS PTY LIMITED | N/A | N/A |
...
```
