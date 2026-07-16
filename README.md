# Cloud Infrastructure Auditor & Cost Optimizer (CLI)

A professional-grade command-line interface (CLI) application built for DevOps and FinOps teams to scan cloud infrastructure (AWS and GCP) for orphaned, underutilized, or misconfigured resources, generate beautiful cost-saving reports, and safely clean up resources.

## Features

- **Multi-Cloud Support:** Securely interacts with AWS and GCP.
- **Orphaned Resource Scanners:**
  - **AWS:** Unattached EBS Volumes, unassociated Elastic IPs, underutilized EC2 instances (sub-5% CPU over 14 days).
  - **GCP:** Unattached Persistent Disks, unused Static External IPs, underutilized GCE VM instances (sub-5% CPU over 14 days).
- **Aesthetic Terminal Reports:** Generates Rich-formatted tables with estimated monthly costs, potential savings, and summary statistics.
- **Multiple Export Formats:** Export reports to CSV, JSON, and YAML.
- **Safe Cleanup Engine:**
  - Dry-run by default.
  - Interactive double-confirmation before resource deletion.
  - Option to target single resources or execute in bulk from a scan report.
- **Configuration Management:** Setup scan defaults (regions, thresholds, window size) interactively.
- **Robustness:** Built-in rate limit mitigation using exponential backoff.

## Installation

### Prerequisites
- Python 3.12+
- AWS Credentials configured locally (e.g., in `~/.aws/credentials`) or environment variables.
- GCP Credentials configured locally (Application Default Credentials) or a service account key JSON file.

### Local Development Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   cd cloud_auditor
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Unix/macOS:
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

## Usage

Run the auditor using the `cloud-auditor` command or `python main.py`.

### 1. Configuration
Configure default settings (regions, thresholds, days) interactively:
```bash
cloud-auditor configure
```

### 2. Scanning Resources
Scan your AWS and GCP resources. By default, it scans both providers.

- **Scan all providers and default regions:**
  ```bash
  cloud-auditor scan
  ```

- **Scan AWS only in specific regions:**
  ```bash
  cloud-auditor scan --provider aws --regions us-east-1,us-west-2
  ```

- **Scan GCP only and export reports:**
  ```bash
  cloud-auditor scan --provider gcp --export-json report.json --export-csv report.csv
  ```

- **Scan all available AWS regions:**
  ```bash
  cloud-auditor scan --provider aws --all-regions
  ```

### 3. Cleanup Resources
Safely remove the flagged resources. By default, cleanup runs in **Dry-Run** mode.

- **Run Dry-Run cleanup from the last cached scan:**
  ```bash
  cloud-auditor cleanup
  ```

- **Run Dry-Run cleanup from an exported report file:**
  ```bash
  cloud-auditor cleanup --file report.json
  ```

- **Execute actual deletion (requires confirmation):**
  ```bash
  cloud-auditor cleanup --file report.json --execute
  ```

- **Force execute deletion (bypasses confirmation):**
  ```bash
  cloud-auditor cleanup --file report.json --execute --force
  ```

- **Directly delete a specific resource:**
  ```bash
  cloud-auditor cleanup --resource-id vol-0a1b2c3d4e5f6g7h8 --resource-type "EBS Volume" --provider aws --region us-east-1 --execute
  ```

## Development and Testing

### Run Unit Tests
We use the `moto` library to mock AWS services so tests can run locally without connecting to live AWS infrastructure.

```bash
pytest tests/
```

### Compile Standalone Executable
You can compile the CLI into a single executable binary using PyInstaller:

```bash
pyinstaller --onefile main.py --name cloud-auditor
```
The compiled binary will be located in the `dist/` directory (e.g. `dist/cloud-auditor.exe` on Windows).
