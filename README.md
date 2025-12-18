# OCR-based Final Bill Itemization System

A production-ready system for processing insurance claims with OCR-based bill extraction, duplicate detection, and structured output generation using Google ADK (Agent Development Kit) architecture.

## System Overview

This system processes insurance claims by:
1. Loading claim documents from provided GCS links (gs:// or https:// format)
2. Performing OCR and structured data extraction on all documents
3. Classifying documents as BILL or SUPPORTING_DOC
4. Detecting and eliminating duplicate bills using hash-based fingerprinting
5. Selecting the best final bill based on item count
6. Generating structured JSON outputs for downstream systems

## Architecture

The system follows a modular agent-based architecture where each agent has a specific responsibility and communicates through a shared state dictionary.

### Agent Responsibilities

- **RootAgent**: Orchestrates the complete pipeline execution
- **IngestionAgent**: Loads claim documents from GCS
- **OCRAgent** (Maker): Performs OCR extraction and structured data extraction
- **ClassificationAgent**: Classifies documents as BILL vs SUPPORTING_DOC
- **DuplicateCheckerAgent** (Checker): Detects duplicate bills using hash-based fingerprinting
- **FinalBillAgent**: Selects the best bill and generates output structures
- **AuditAgent**: Maintains audit logs for traceability

### Maker-Checker Pattern

The system implements a Maker-Checker pattern for quality assurance:
- **Maker**: OCRAgent extracts and structures bill data
- **Checker**: DuplicateCheckerAgent validates results and flags duplicates

## Claim Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      RootAgent (Orchestrator)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │      IngestionAgent                    │
        │  • Load documents from GCS             │
        │  • Extract metadata                    │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │      OCRAgent (Maker)                  │
        │  • Extract text from images/PDFs       │
        │  • Parse structured bill data          │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │      ClassificationAgent               │
        │  • Classify as BILL/SUPPORTING_DOC     │
        │  • Filter documents                    │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  DuplicateCheckerAgent (Checker)       │
        │  • Compute bill fingerprints           │
        │  • Detect duplicates (hash-based)      │
        │  • Flag duplicate bills                │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │      FinalBillAgent                    │
        │  • Select best bill                    │
        │  • Generate final_bill.json            │
        │  • Generate bill_item_list.json        │
        │  • Generate supporting_doc_map.json    │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │      AuditAgent                        │
        │  • Log all events                      │
        │  • Generate audit_logs.json            │
        └────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- Google Cloud Project with GCS bucket configured
- Service account credentials with GCS read/write permissions

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd OCR_bill
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your GCS configuration
```

## Configuration

### Required: Document AI Setup

1. Enable the Document AI API in your Google Cloud project
2. Create a Document AI processor (OCR or Form Parser):
   - Go to https://console.cloud.google.com/ai/document-ai/processors
   - Create a new processor (recommended: "Document OCR" or "Invoice Parser")
   - Note the processor ID

3. Set the required environment variables:

```env
# Required: Document AI Configuration
DOCUMENT_AI_PROJECT_ID=your-gcp-project-id
DOCUMENT_AI_LOCATION=us  # or 'eu'
DOCUMENT_AI_PROCESSOR_ID=your-processor-id

# Optional: Google Cloud credentials (if not using default)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Optional: Other settings
OCR_MAX_PAGES=100
DUPLICATE_HASH_ALGORITHM=sha256
LOG_LEVEL=INFO
```

Note: GCS links are provided directly as input - no bucket configuration needed.

## Usage

### Running Locally

Process a single claim with GCS links:

```bash
python scripts/run_claim.py <claim_id> gs://bucket/path/doc1.pdf gs://bucket/path/doc2.jpg
```

Or with HTTPS links:

```bash
python scripts/run_claim.py <claim_id> https://storage.googleapis.com/bucket/path/doc1.pdf https://storage.googleapis.com/bucket/path/doc2.jpg
```

With verbose logging:

```bash
python scripts/run_claim.py <claim_id> gs://bucket/path/doc1.pdf --verbose
```

### Programmatic Usage

```python
from pipelines.claim_pipeline import ClaimPipeline

pipeline = ClaimPipeline()
gcs_links = [
    "gs://my-bucket/claims/doc1.pdf",
    "gs://my-bucket/claims/doc2.jpg",
]
result = pipeline.process_claim("CLAIM_001", gcs_links)

if result["status"] == "SUCCESS":
    print(f"Outputs: {list(result['outputs'].keys())}")
    # Access individual outputs:
    # final_bill = result['outputs']['final_bill']
    # bill_items = result['outputs']['bill_item_list']
    # etc.
```

## Output Structure

The system returns a dictionary with the following outputs:

### outputs["final_bill"]
Contains the selected final bill with metadata, summary totals, and all line items (JSON-serializable dict).

### outputs["bill_item_list"]
Structured list of bill items with quantities, prices, and totals (JSON-serializable dict).

### outputs["supporting_doc_map"]
Mapping of all supporting documents (non-bill documents) associated with the claim (JSON-serializable dict).

### outputs["audit_logs"]
Complete audit trail of all processing steps, agent executions, and events (JSON-serializable dict).

## Code Structure

```
.
├── config/           # Configuration management
├── models/           # Pydantic data models and schemas
├── agents/           # Processing agents (ADK pattern)
├── pipelines/        # Main pipeline orchestration
├── utils/            # Utility functions (OCR, hash, GCS link parsing)
└── scripts/          # Command-line scripts
```

## Implementation Notes

### OCR with Google Document AI

The system uses **Google Document AI** for OCR extraction:
- Supports PDF, PNG, JPG, TIFF, BMP, and other image formats
- Extracts text with high accuracy using ML models
- Structured data extraction uses regex patterns (for production, consider using Document AI's specialized Invoice/Receipt parsers)

### Placeholder Components

- **Document Classification** (`agents/classification_agent.py`): Uses simple heuristics
  - TODO: Implement ML-based classification model or use Document AI classifiers

### Production Considerations

1. **Error Handling**: Add retry logic and circuit breakers for external service calls
2. **Monitoring**: Integrate with logging/monitoring services (e.g., Cloud Logging, Prometheus)
3. **Scaling**: Consider async processing and message queues for high-volume scenarios
4. **Security**: Ensure service account credentials are properly secured
5. **Performance**: Add caching for frequently accessed GCS objects

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]
