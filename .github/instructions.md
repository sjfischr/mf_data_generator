# Deployment Instructions for AI Coding Agents

## ⚠️ CRITICAL: Deployment Policy

**NEVER** attempt to deploy or build infrastructure locally. All deployments are automated through GitHub Actions and Vercel.

### ❌ DO NOT DO THESE:
- ❌ Do NOT run `cdk deploy` locally
- ❌ Do NOT run `cdk synth` locally (except for testing)
- ❌ Do NOT use AWS SAM (`sam build`, `sam deploy`)
- ❌ Do NOT run `vercel deploy` locally
- ❌ Do NOT manually upload Lambda code to AWS
- ❌ Do NOT try to configure AWS credentials in development

### ✅ ALWAYS DO THIS:
- ✅ Make your code changes
- ✅ Commit and push to GitHub
- ✅ Let GitHub Actions handle all deployments automatically

---

## Architecture Overview

This project generates synthetic multifamily appraisal packages using AI:

**Frontend**: React 18 + TypeScript + Tailwind CSS → Deployed to Vercel
**Backend**: AWS CDK → Lambda + Step Functions + API Gateway + S3 → Deployed via GitHub Actions

### Infrastructure Stacks (CDK)
1. **StorageStack** - S3 bucket and SNS topic
2. **LambdaStack** - All Lambda functions (20+ functions)
3. **StepFunctionsStack** - Orchestration state machine
4. **ApiStack** - API Gateway with REST endpoints

### Key Lambda Functions
- `input_validator` - Validates user input from frontend
- `crosswalk_generator` - Creates master data schema (CRITICAL)
- `section_generators` (01-12) - Generate appraisal sections using Claude
- `image_generator` - Generates property images via Replicate API
- `t12_generator` - Creates Excel files (T-12, rent rolls)
- `qc_validator` - Validates data consistency
- `assembler` - Assembles final DOCX + ZIP package
- `status_checker` - API endpoint for job status
- `download_handler` - API endpoint for download URLs
- `lucky_generator` - Quick generation API endpoint

---

## Automated Deployment Workflows

### Backend Deployment (GitHub Actions)

**File**: `.github/workflows/deploy-backend.yml`

**Triggers automatically when you push changes to**:
- `cdk/**` - Infrastructure code
- `lambdas/**` - Lambda function code
- `templates/**` - Markdown templates for AI prompts
- `requirements.txt` - Python dependencies
- The workflow file itself

**What it does**:
1. Sets up Python 3.11 and Node 18
2. Installs Python dependencies
3. Installs AWS CDK CLI
4. Authenticates with AWS using GitHub Secrets
5. Runs `cdk synth` to validate CloudFormation templates
6. Runs `cdk deploy --all` to deploy all 4 stacks

**Required GitHub Secrets**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `REPLICATE_API_TOKEN`

### Frontend Deployment (Vercel)

**File**: `.github/workflows/deploy-frontend.yml`

**Triggers automatically when you push changes to**:
- `frontend/**` - Frontend code
- The workflow file itself

**What it does**:
1. Sets up Node 18
2. Installs frontend dependencies
3. Builds React app with `npm run build`
4. Deploys to Vercel production

**Required GitHub Secrets**:
- `VITE_API_URL` - API Gateway URL from backend
- `VERCEL_TOKEN` - Vercel deployment token
- `VERCEL_ORG_ID` - Vercel organization ID
- `VERCEL_PROJECT_ID` - Vercel project ID

**Note**: Vercel is also configured to auto-deploy from GitHub directly. The workflow provides additional control and environment variable injection.

---

## Development Workflow

### Making Backend Changes

1. **Modify Lambda code** in `lambdas/` directory
   - Each Lambda has its own folder with `handler.py`
   - Shared utilities are in `lambdas/shared/`
   - Each Lambda can have its own `requirements.txt` for dependencies

2. **Modify infrastructure** in `cdk/stacks/` if needed
   - `storage_stack.py` - S3, SNS resources
   - `lambda_stack.py` - Lambda functions, IAM roles
   - `stepfunctions_stack.py` - Step Functions state machine
   - `api_stack.py` - API Gateway endpoints

3. **Modify AI templates** in `templates/` directory
   - `data_crosswalk.md` - Schema for crosswalk generator
   - `image_prompts.md` - Prompts for image generation

4. **Test locally** (optional):
   ```bash
   pytest tests/ -v
   ```

5. **Commit and push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```

6. **Monitor deployment**:
   - Go to GitHub → Actions tab
   - Watch "Deploy Backend (CDK)" workflow
   - Deployment takes 5-10 minutes typically

### Making Frontend Changes

1. **Modify React components** in `frontend/src/`
   - `components/` - React components
   - `services/api.ts` - API client
   - `App.tsx` - Main app component

2. **Modify styles** in Tailwind CSS (inline classes)

3. **Test locally** (optional):
   ```bash
   cd frontend
   npm run dev
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```

5. **Monitor deployment**:
   - Go to GitHub → Actions tab
   - Watch "Deploy Frontend (Vercel)" workflow
   - Deployment takes 1-2 minutes typically
   - Or check Vercel dashboard directly

---

## Project Structure (For Reference)

```
mf_data_generator/
├── .github/
│   ├── workflows/
│   │   ├── deploy-backend.yml    # Backend deployment automation
│   │   └── deploy-frontend.yml   # Frontend deployment automation
│   └── instructions.md            # THIS FILE
│
├── cdk/                           # AWS CDK Infrastructure (Python)
│   ├── app.py                     # CDK entry point
│   └── stacks/
│       ├── storage_stack.py       # S3 + SNS
│       ├── lambda_stack.py        # All Lambda functions
│       ├── stepfunctions_stack.py # State machine orchestration
│       └── api_stack.py           # API Gateway REST API
│
├── lambdas/                       # Lambda function code (Python 3.11)
│   ├── shared/                    # Shared utilities
│   │   ├── models.py              # Pydantic data models
│   │   ├── bedrock_client.py      # AWS Bedrock API client
│   │   ├── s3_utils.py            # S3 helpers
│   │   ├── section_generator.py   # Base class for sections
│   │   └── agent_tools.py         # AI agent tools
│   ├── input_validator/           # Entry point Lambda
│   ├── crosswalk_generator/       # Master data generator (CRITICAL)
│   ├── section_generators/        # 12 appraisal sections
│   │   ├── section_01/ ... section_12/
│   ├── image_generator/           # Replicate API integration
│   ├── t12_generator/             # Excel file generation
│   ├── qc_validator/              # Data validation
│   ├── assembler/                 # Document assembly (Pandoc)
│   ├── status_checker/            # Status API endpoint
│   ├── download_handler/          # Download API endpoint
│   └── lucky_generator/           # Quick generation endpoint
│
├── frontend/                      # React + TypeScript + Tailwind
│   ├── src/
│   │   ├── components/            # React components
│   │   ├── services/api.ts        # API client
│   │   └── App.tsx                # Main app
│   ├── package.json
│   └── vite.config.ts             # Vite bundler config
│
├── templates/                     # AI prompt templates
│   ├── data_crosswalk.md          # Crosswalk schema definition
│   └── image_prompts.md           # Image generation prompts
│
├── tests/                         # pytest test suite
│   └── unit/
│
└── requirements.txt               # Python dependencies for CDK
```

---

## Common Tasks

### Adding a New Lambda Function

1. Create new folder in `lambdas/my_new_lambda/`
2. Add `__init__.py` and `handler.py`
3. Add function-specific dependencies in `requirements.txt` (optional)
4. Register in `cdk/stacks/lambda_stack.py`:
   ```python
   self.my_new_lambda = l.Function(
       self, "MyNewLambda",
       runtime=l.Runtime.PYTHON_3_11,
       handler="handler.handler",
       code=l.Code.from_asset("lambdas/my_new_lambda"),
       ...
   )
   ```
5. Wire into Step Functions or API Gateway as needed
6. Push to GitHub → Auto-deploys

### Modifying Step Functions State Machine

1. Edit `cdk/stacks/stepfunctions_stack.py`
2. Update the state machine definition JSON
3. Push to GitHub → Auto-deploys

### Adding API Endpoint

1. Add Lambda handler in `lambdas/`
2. Register Lambda in `lambda_stack.py`
3. Add API route in `cdk/stacks/api_stack.py`:
   ```python
   my_endpoint = api.root.add_resource("my-endpoint")
   my_endpoint.add_method("GET", apigw.LambdaIntegration(my_lambda))
   ```
4. Update frontend `services/api.ts` to call new endpoint
5. Push to GitHub → Auto-deploys both backend and frontend

### Changing AI Models or Prompts

1. **Model changes**: Edit `lambdas/shared/bedrock_client.py` or individual Lambda handlers
2. **Prompt changes**: Edit templates in `templates/` or in-code prompts in Lambda handlers
3. Push to GitHub → Auto-deploys

### Debugging Deployment Issues

1. **Check GitHub Actions logs**:
   - Go to repository → Actions tab
   - Click on failed workflow run
   - Expand failed step to see error

2. **Common backend issues**:
   - CDK bootstrap not run (one-time per account/region)
   - Missing GitHub Secrets (AWS credentials)
   - CloudFormation stack in ROLLBACK state (delete manually)
   - Lambda dependencies missing from `requirements.txt`

3. **Common frontend issues**:
   - Missing `VITE_API_URL` secret
   - Invalid Vercel credentials
   - TypeScript compilation errors

4. **View AWS CloudWatch logs**:
   - Log into AWS Console
   - Navigate to CloudWatch → Log groups
   - Find `/aws/lambda/[function-name]`

---

## Environment Variables & Secrets

### GitHub Secrets (Repository Settings → Secrets)

**Backend**:
- `AWS_ACCESS_KEY_ID` - AWS IAM access key
- `AWS_SECRET_ACCESS_KEY` - AWS IAM secret key
- `REPLICATE_API_TOKEN` - Replicate API token injected into ImageGenerator Lambda

**Frontend**:
- `VITE_API_URL` - Full API Gateway URL (e.g., `https://abc123.execute-api.us-east-1.amazonaws.com/prod`)
- `VERCEL_TOKEN` - Vercel CLI authentication token
- `VERCEL_ORG_ID` - From Vercel project settings
- `VERCEL_PROJECT_ID` - From Vercel project settings

### Lambda Environment Variables (Set in CDK)

These are configured in `lambda_stack.py` and automatically injected:
- `BUCKET_NAME` - S3 bucket for storing generated files
- `TOPIC_ARN` - SNS topic for notifications
- `REPLICATE_API_TOKEN` - For image generation (set in CDK)

---

## Testing & Validation

### Local Testing (Optional)

**Backend**:
```bash
# Unit tests
pytest tests/ -v

# Lambda function tests (mock Bedrock/S3)
pytest tests/unit/test_crosswalk_generator.py -v
```

**Frontend**:
```bash
cd frontend
npm run dev  # Local dev server on http://localhost:5173
npm run build  # Test production build
```

**CDK Validation** (does NOT deploy):
```bash
cdk synth  # Generates CloudFormation templates
```

### Post-Deployment Testing

1. **API health check**:
   ```bash
   curl https://[API-URL]/api/status/test
   ```

2. **Frontend check**:
   - Visit Vercel URL
   - Fill out property form
   - Submit generation request
   - Monitor progress
   - Download generated package

3. **Check Lambda logs in CloudWatch**

---

## Important Notes

### Lambda Layer Dependencies

Lambda packages dependencies are deployed with the function code, not as layers. Each Lambda has:
- Its own `requirements.txt` (function-specific deps)
- Access to `lambdas/shared/` modules (shared utilities)
- CDK packages dependencies automatically using `bundling` with Docker

### State Machine Execution

The Step Functions workflow executes in this order:
1. Input Validator
2. Crosswalk Generator (creates master data schema)
3. Parallel execution:
   - 12 Section Generators
   - T-12 Generator
   - Image Generator
4. QC Validator
5. Assembler (creates final DOCX and ZIP)

### Data Flow

1. User submits form → API Gateway → Input Validator Lambda
2. Input Validator starts Step Functions execution
3. Crosswalk Generator creates `crosswalk.json` → S3
4. All generators read `crosswalk.json` and generate content → S3
5. QC Validator checks consistency
6. Assembler combines everything → Final ZIP → S3
7. Frontend polls Status Checker Lambda
8. Download Handler Lambda returns presigned S3 URLs

---

## Summary for AI Agents

**Your job is to**:
- Write or modify code in `cdk/`, `lambdas/`, or `frontend/`
- Ensure code quality and correctness
- Write clear commit messages
- Push to GitHub

**Your job is NOT to**:
- Deploy anything manually
- Configure AWS locally
- Run CDK or SAM commands (except `cdk synth` for validation)
- Worry about build processes

**The CI/CD pipeline handles**:
- Building Lambda packages with dependencies
- Deploying CDK stacks to AWS
- Building and deploying frontend to Vercel
- Managing infrastructure state
- Rolling back on failures

**When you push to main branch**, GitHub Actions automatically:
1. Detects which files changed (backend vs frontend)
2. Triggers appropriate workflow(s)
3. Builds and tests code
4. Deploys to production
5. Reports success or failure

**Trust the pipeline. Just push code.**

---

## Support & Troubleshooting

If deployments fail:
1. Check GitHub Actions logs for detailed errors
2. For backend: check CloudFormation console for stack status
3. For frontend: check Vercel dashboard for build logs
4. Review this document for required secrets and configuration
5. Verify CDK bootstrap was run once: `cdk bootstrap` (manual, one-time)

Never try to "fix" deployment issues by running commands locally. Fix in code, push again, let CI/CD retry.
