import csv
import json
import yaml
from typing import List, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

def format_currency(value: float) -> str:
    return f"${value:,.2f}"

def display_report(resources: List[Dict[str, Any]]) -> None:
    """
    Displays scan results in a Rich table.
    """
    if not resources:
        console.print(Panel(Text("No idle or orphaned resources identified! Your infrastructure looks clean.", style="green"), title="Scan Complete"))
        return

    table = Table(title="Cloud Cost Optimization Scan Report", header_style="bold magenta")
    table.add_column("Provider", justify="center")
    table.add_column("Region/Zone", justify="left")
    table.add_column("Resource ID", justify="left", style="cyan")
    table.add_column("Type", justify="left")
    table.add_column("Status", justify="center")
    table.add_column("Monthly Cost", justify="right", style="red")
    table.add_column("Potential Savings", justify="right", style="bold green")
    table.add_column("Details", justify="left")

    total_cost = 0.0
    total_savings = 0.0

    for res in resources:
        cost = res.get("monthly_cost", 0.0)
        savings = res.get("potential_savings", 0.0)
        total_cost += cost
        total_savings += savings

        status_style = "yellow"
        if res.get("status") == "orphaned":
            status_style = "bold red"
        elif res.get("status") == "unused":
            status_style = "orange3"
        elif res.get("status") == "underutilized":
            status_style = "blue"

        table.add_row(
            res.get("provider", ""),
            res.get("region", ""),
            res.get("resource_id", ""),
            res.get("resource_type", ""),
            Text(res.get("status", ""), style=status_style),
            format_currency(cost),
            format_currency(savings),
            res.get("details", "")
        )

    console.print(table)
    
    # Print Summary Box
    summary_text = (
        f"Total Resources Flagged: [bold cyan]{len(resources)}[/bold cyan]\n"
        f"Estimated Total Monthly Cost: [bold red]{format_currency(total_cost)}[/bold red]\n"
        f"Estimated Total Monthly Savings: [bold green]{format_currency(total_savings)}[/bold green]\n"
        f"Estimated Annual Savings: [bold green]{format_currency(total_savings * 12)}[/bold green]"
    )
    console.print(Panel(summary_text, title="Financial Summary", border_style="bold green", expand=False))

def export_report(resources: List[Dict[str, Any]], export_path: str, format_type: str) -> None:
    """
    Exports the scan report to a specified file format (json, csv, yaml).
    """
    path = Path(export_path)
    # Ensure parent directories exist
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if format_type == "json":
        with open(path, "w") as f:
            json.dump(resources, f, indent=2)
        console.print(f"[green]Successfully exported scan results to JSON file: {path}[/green]")
    elif format_type == "yaml":
        with open(path, "w") as f:
            yaml.safe_dump(resources, f, default_flow_style=False)
        console.print(f"[green]Successfully exported scan results to YAML file: {path}[/green]")
    elif format_type == "csv":
        if not resources:
            headers = ["provider", "region", "resource_id", "resource_type", "status", "monthly_cost", "potential_savings", "details"]
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            console.print(f"[green]Successfully exported scan results (empty) to CSV file: {path}[/green]")
            return
            
        headers = list(resources[0].keys())
        # Filter metadata since it's a dict and CSVs are flat
        flat_headers = [h for h in headers if h != "metadata"]
        
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=flat_headers)
            writer.writeheader()
            for res in resources:
                row = {k: v for k, v in res.items() if k != "metadata"}
                writer.writerow(row)
        console.print(f"[green]Successfully exported scan results to CSV file: {path}[/green]")
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
