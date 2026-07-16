import typer
import yaml
import json
import logging
from typing import List, Optional
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from cloud_auditor import __version__
from cloud_auditor.config import load_config, save_config, DEFAULT_CONFIG, CONFIG_PATH
from cloud_auditor.auth import get_aws_session, get_gcp_credentials
from cloud_auditor.scanners.aws_scanners import EbsVolumeScanner, EipScanner, Ec2InstanceScanner
from cloud_auditor.scanners.gcp_scanners import GcpDiskScanner, GcpIpScanner, GcpVmScanner
from cloud_auditor.reporter import display_report, export_report
from cloud_auditor.cleanup import cleanup_resources

# Setup logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cloud_auditor")

app = typer.Typer(help="Cloud Infrastructure Auditor & Cost Optimizer CLI")
console = Console()

LAST_SCAN_PATH = Path.home() / ".cloud_auditor_last_scan.json"

@app.command()
def scan(
    provider: str = typer.Option("all", "--provider", "-p", help="Cloud provider to scan: aws, gcp, all"),
    regions: Optional[str] = typer.Option(None, "--regions", "-r", help="Comma-separated list of regions/zones to scan"),
    all_regions: bool = typer.Option(False, "--all-regions", help="Scan all available regions (can be slow)"),
    aws_profile: Optional[str] = typer.Option(None, "--aws-profile", help="AWS CLI profile to use"),
    aws_role_arn: Optional[str] = typer.Option(None, "--aws-role-arn", help="AWS IAM Role ARN to assume"),
    gcp_key: Optional[str] = typer.Option(None, "--gcp-key", help="Path to GCP service account key JSON"),
    cpu_threshold: float = typer.Option(5.0, "--cpu-threshold", help="Average CPU utilization percentage threshold for underutilized VMs"),
    days: int = typer.Option(14, "--days", "-d", help="Number of days to analyze CPU utilization"),
    export_json: Optional[str] = typer.Option(None, "--export-json", help="Path to export results as JSON"),
    export_csv: Optional[str] = typer.Option(None, "--export-csv", help="Path to export results as CSV"),
    export_yaml: Optional[str] = typer.Option(None, "--export-yaml", help="Path to export results as YAML"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose debugging logs"),
):
    """
    Scan cloud infrastructure for orphaned, underutilized, or unused resources.
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    config = load_config()
    resources = []

    providers = ["aws", "gcp"] if provider.lower() == "all" else [provider.lower()]

    for prov in providers:
        if prov == "aws":
            console.print("[bold blue]Starting AWS Scan...[/bold blue]")
            try:
                session = get_aws_session(profile_name=aws_profile, role_arn=aws_role_arn)
                
                aws_regions = []
                if regions and provider.lower() == "aws":
                    aws_regions = [reg.strip() for reg in regions.split(",")]
                elif all_regions:
                    ec2_client = session.client("ec2")
                    describe_regions = ec2_client.describe_regions()
                    aws_regions = [r["RegionName"] for r in describe_regions["Regions"]]
                else:
                    aws_regions = config.get("aws", {}).get("regions", DEFAULT_CONFIG["aws"]["regions"])
                
                console.print(f"Scanning AWS regions: [cyan]{', '.join(aws_regions)}[/cyan]")
                
                for reg in aws_regions:
                    # EBS Volumes
                    ebs_scanner = EbsVolumeScanner(session, reg)
                    resources.extend(ebs_scanner.scan())
                    
                    # Elastic IPs
                    eip_scanner = EipScanner(session, reg)
                    resources.extend(eip_scanner.scan())
                    
                    # EC2 instances
                    ec2_scanner = Ec2InstanceScanner(session, reg, cpu_threshold=cpu_threshold, days_threshold=days)
                    resources.extend(ec2_scanner.scan())
                    
            except Exception as e:
                console.print(f"[bold red]AWS Scan failed: {e}[/bold red]")
                
        elif prov == "gcp":
            console.print("[bold green]Starting GCP Scan...[/bold green]")
            try:
                creds, project_id = get_gcp_credentials(key_path=gcp_key)
                if not project_id:
                    raise ValueError("GCP Project ID not found. Ensure Application Default Credentials or key file are correctly set.")
                
                console.print(f"GCP Project: [cyan]{project_id}[/cyan]")
                
                gcp_regions = []
                if regions and provider.lower() == "gcp":
                    gcp_regions = [reg.strip() for reg in regions.split(",")]
                else:
                    gcp_regions = config.get("gcp", {}).get("regions", DEFAULT_CONFIG["gcp"]["regions"])
                
                gcp_zones = []
                for r in gcp_regions:
                    if r.endswith("1") or r.endswith("2") or r.endswith("3") or r.endswith("4"):
                        gcp_zones.extend([f"{r}-a", f"{r}-b"])
                    else:
                        gcp_zones.append(r)
                
                unique_regions = list(set([z.rsplit("-", 1)[0] for z in gcp_zones]))
                
                console.print(f"Scanning GCP Regions: [cyan]{', '.join(unique_regions)}[/cyan]")
                console.print(f"Scanning GCP Zones: [cyan]{', '.join(gcp_zones)}[/cyan]")
                
                # Scan Static IPs (Regional)
                for reg in unique_regions:
                    ip_scanner = GcpIpScanner(creds, project_id, reg)
                    resources.extend(ip_scanner.scan())
                
                # Scan Disks and VMs (Zonal)
                for zone in gcp_zones:
                    disk_scanner = GcpDiskScanner(creds, project_id, zone)
                    resources.extend(disk_scanner.scan())
                    
                    vm_scanner = GcpVmScanner(creds, project_id, zone, cpu_threshold=cpu_threshold, days_threshold=days)
                    resources.extend(vm_scanner.scan())
                    
            except Exception as e:
                console.print(f"[bold red]GCP Scan failed: {e}[/bold red]")

    display_report(resources)

    # Save to last scan file for easy cleanup
    try:
        LAST_SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_SCAN_PATH, "w") as f:
            json.dump(resources, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to cache scan results: {e}")

    # Exports
    if export_json:
        export_report(resources, export_json, "json")
    if export_csv:
        export_report(resources, export_csv, "csv")
    if export_yaml:
        export_report(resources, export_yaml, "yaml")

@app.command()
def cleanup(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to a JSON report from a previous scan"),
    resource_id: Optional[str] = typer.Option(None, "--resource-id", help="Directly cleanup a specific resource by ID"),
    resource_type: Optional[str] = typer.Option(None, "--resource-type", help="Directly cleanup a specific resource type"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Directly cleanup a specific provider (AWS/GCP)"),
    region: Optional[str] = typer.Option(None, "--region", help="Region/Zone of the resource to cleanup"),
    execute: bool = typer.Option(False, "--execute", help="Execute the deletion (defaults to dry-run)"),
    force: bool = typer.Option(False, "--force", help="Bypass confirmation prompt"),
    aws_profile: Optional[str] = typer.Option(None, "--aws-profile", help="AWS CLI profile to use"),
    gcp_key: Optional[str] = typer.Option(None, "--gcp-key", help="Path to GCP service account key JSON"),
):
    """
    Clean up identified idle or orphaned resources.
    Defaults to a safe dry-run mode. Use --execute to actually run deletions.
    """
    resources = []
    
    if resource_id:
        if not resource_type or not provider or not region:
            console.print("[bold red]Error: Direct resource cleanup requires --resource-type, --provider, and --region.[/bold red]")
            raise typer.Exit(1)
        
        resources = [{
            "resource_id": resource_id,
            "resource_type": resource_type,
            "provider": provider.upper(),
            "region": region,
            "metadata": {}
        }]
    else:
        path_to_load = Path(file) if file else LAST_SCAN_PATH
        if not path_to_load.exists():
            console.print(f"[bold red]No scan data found at '{path_to_load}'. Please run a scan first: 'scan'[/bold red]")
            raise typer.Exit(1)
            
        try:
            with open(path_to_load, "r") as f:
                resources = json.load(f)
        except Exception as e:
            console.print(f"[bold red]Failed to read scan data: {e}[/bold red]")
            raise typer.Exit(1)

    if not resources:
        console.print("[yellow]No resources found for cleanup.[/yellow]")
        return

    console.print(f"[bold red]Found {len(resources)} resource(s) targeted for cleanup.[/bold red]")
    for r in resources:
        console.print(f" - [bold]{r['provider']}[/bold] {r['resource_type']} [cyan]{r['resource_id']}[/cyan] ({r['region']})")

    dry_run = not execute
    if not dry_run and not force:
        confirm = Confirm.ask("[bold red]Are you absolutely sure you want to DELETE these resource(s)?[/bold red]")
        if not confirm:
            console.print("[yellow]Cleanup aborted.[/yellow]")
            raise typer.Exit(0)

    cleanup_resources(resources, dry_run=dry_run, aws_profile=aws_profile, gcp_key=gcp_key)

@app.command()
def configure():
    """
    Configure default settings for AWS and GCP scans.
    """
    config = load_config()
    
    console.print("[bold magenta]Configure Cloud Infrastructure Auditor Defaults[/bold magenta]")
    
    aws_reg_str = console.input(f"AWS Default Regions (comma-separated) [{','.join(config['aws']['regions'])}]: ").strip()
    if aws_reg_str:
        config["aws"]["regions"] = [r.strip() for r in aws_reg_str.split(",")]
        
    aws_cpu = console.input(f"AWS EC2 CPU Threshold % [{config['aws']['cpu_threshold']}]: ").strip()
    if aws_cpu:
        config["aws"]["cpu_threshold"] = float(aws_cpu)
        
    aws_days = console.input(f"AWS CloudWatch Metric Analyze Days [{config['aws']['days_threshold']}]: ").strip()
    if aws_days:
        config["aws"]["days_threshold"] = int(aws_days)
        
    gcp_reg_str = console.input(f"GCP Default Regions (comma-separated) [{','.join(config['gcp']['regions'])}]: ").strip()
    if gcp_reg_str:
        config["gcp"]["regions"] = [r.strip() for r in gcp_reg_str.split(",")]
        
    gcp_cpu = console.input(f"GCP GCE CPU Threshold % [{config['gcp']['cpu_threshold']}]: ").strip()
    if gcp_cpu:
        config["gcp"]["cpu_threshold"] = float(gcp_cpu)
        
    gcp_days = console.input(f"GCP Monitoring Metric Analyze Days [{config['gcp']['days_threshold']}]: ").strip()
    if gcp_days:
        config["gcp"]["days_threshold"] = int(gcp_days)

    save_config(config)
    console.print(f"[green]Successfully saved configuration to {CONFIG_PATH}[/green]")

def version_callback(value: bool):
    if value:
        console.print(f"Cloud Infrastructure Auditor CLI Version: {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show application version and exit"),
):
    pass
