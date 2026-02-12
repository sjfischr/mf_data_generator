# Synthetic Multifamily Appraisal Generator

A fully automated system that generates synthetic multifamily loan appraisal packages using AI. Enter a property address and basic details, and the system produces a complete appraisal report (DOCX), rent rolls, and T-12 operating statements.

## Architecture

```
Frontend (React/Vercel)
    │
    ▼
API Gateway ──► Input Validator Lambda
                    │
                    ▼
              Step Functions Orchestrator
                    │
                    ▼
              Crosswalk Generator (Haiku)
              ─── generates master data schema ───
                    │
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
  Section 1-12   T-12/Rent Roll   Image Gen
  (Haiku/Sonnet/  (Sonnet +       (Haiku +
   Opus)          openpyxl)       Replicate)
        └───────────┼───────────────┘
                    ▼
              QC Validator (Sonnet)
                    │
                    ▼
              Document Assembler (Pandoc)
                    │
                    ▼
              S3 ──► Presigned Download URLs
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS (Vercel) |
| API | AWS API Gateway (REST) |
| Orchestration | AWS Step Functions |
| Compute | AWS Lambda (Python 3.11) |
| AI Models | AWS Bedrock (Claude Haiku, Sonnet 4.5, Opus 4.6) |
| Images | Replicate API (z-image-turbo) |
| Storage | Amazon S3 |
| Notifications | Amazon SNS |
| IaC | AWS CDK v2 (Python) |
| Documents | Pandoc, python-docx, openpyxl |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS CLI configured with appropriate credentials
- AWS CDK CLI (`npm install -g aws-cdk`)
- Pandoc installed
- Replicate API token

### Setup

```bash
# Clone and install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your values
```

### Deploy Backend

```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cdk deploy --all
```

### Deploy Frontend

```bash
cd frontend
cp .env.example .env.local
# Set VITE_API_URL to your API Gateway URL
npm run build
vercel --prod
```

## Project Structure

```
mf_data_gen/
├── cdk/                          # AWS CDK infrastructure
│   ├── app.py                    # CDK app entry point
│   └── stacks/
│       ├── storage_stack.py      # S3, SNS
│       ├── lambda_stack.py       # All Lambda functions
│       ├── stepfunctions_stack.py # Step Functions state machine
│       └── api_stack.py          # API Gateway
├── lambdas/
│   ├── shared/                   # Shared utilities
│   │   ├── models.py             # Pydantic crosswalk schema
│   │   ├── bedrock_client.py     # Bedrock API client
│   │   ├── s3_utils.py           # S3 read/write helpers
│   │   └── section_generator.py  # Base class for sections
│   ├── input_validator/          # Validates user input
│   ├── crosswalk_generator/      # Generates master data (CRITICAL)
│   ├── section_generators/       # 12 appraisal sections
│   │   ├── section_01/ (Haiku)   # Introduction
│   │   ├── section_02/ (Sonnet)  # Property Description
│   │   ├── section_03/ (Sonnet)  # Market Analysis
│   │   ├── section_04/ (Haiku)   # Highest and Best Use
│   │   ├── section_05/ (Haiku)   # Valuation Methodology
│   │   ├── section_06/ (Opus)    # Sales Comparison
│   │   ├── section_07/ (Opus)    # Income Approach
│   │   ├── section_08/ (Haiku)   # Cost Approach
│   │   ├── section_09/ (Opus)    # Reconciliation
│   │   ├── section_10/ (Haiku)   # Assumptions
│   │   ├── section_11/ (Haiku)   # Certification
│   │   └── section_12/ (Haiku)   # Addenda
│   ├── image_generator/          # Replicate image generation
│   ├── t12_generator/            # Excel T-12 and rent roll
│   ├── qc_validator/             # Data consistency checks
│   ├── assembler/                # DOCX assembly + ZIP
│   ├── status_checker/           # Job status API
│   └── download_handler/         # Presigned URL API
├── frontend/                     # React SPA
├── templates/                    # Markdown templates
├── tests/                        # pytest test suite
├── scripts/                      # Deploy scripts
└── docs/                         # Documentation
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/generate` | Start appraisal generation |
| GET | `/api/status/{job_id}` | Check generation progress |
| GET | `/api/download/{job_id}` | Get download URLs |

## Configuration

| Variable | Description |
|----------|-------------|
| `AWS_ACCOUNT_ID` | AWS account ID |
| `AWS_REGION` | AWS region (default: us-east-1) |
| `REPLICATE_API_TOKEN` | Replicate API key for image generation |
| `S3_BUCKET` | S3 bucket name |

## Testing

```bash
pytest tests/ -v
```
