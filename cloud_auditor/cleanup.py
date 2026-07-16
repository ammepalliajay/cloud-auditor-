import logging
from typing import List, Dict, Any
from rich.console import Console
from cloud_auditor.auth import get_aws_session, get_gcp_credentials

try:
    from google.cloud import compute_v1
except ImportError:
    compute_v1 = None

console = Console()
logger = logging.getLogger("cloud_auditor")

def cleanup_resources(resources: List[Dict[str, Any]], dry_run: bool = True, aws_profile: str = None, gcp_key: str = None) -> List[Dict[str, Any]]:
    """
    Cleans up the provided list of resources by terminating/deleting/releasing them.
    Supports dry-run logic by default.
    """
    results = []
    
    # Cache SDK clients to avoid recreating them for every resource
    aws_clients = {}
    gcp_clients = {}
    
    # Initialize credentials/sessions if resources are present
    gcp_creds = None
    if any(r["provider"] == "GCP" for r in resources):
        try:
            gcp_creds, _ = get_gcp_credentials(gcp_key)
        except Exception as e:
            console.print(f"[bold red]Failed to load GCP credentials: {e}[/bold red]")
            
    aws_session = None
    if any(r["provider"] == "AWS" for r in resources):
        try:
            aws_session = get_aws_session(profile_name=aws_profile)
        except Exception as e:
            console.print(f"[bold red]Failed to load AWS session: {e}[/bold red]")

    for res in resources:
        prov = res["provider"]
        res_type = res["resource_type"]
        res_id = res["resource_id"]
        region = res["region"]
        metadata = res.get("metadata", {})
        
        prefix = "[Dry Run] " if dry_run else ""
        action_desc = f"{prefix}Deleting {res_type} {res_id} in {region}"
        console.print(f"[yellow]{action_desc}...[/yellow]")
        
        if dry_run:
            results.append({"resource_id": res_id, "status": "success", "message": "Dry run - no action taken"})
            continue
            
        success = False
        err_msg = ""
        
        try:
            if prov == "AWS":
                if not aws_session:
                    raise ValueError("AWS session is not initialized")
                
                if region not in aws_clients:
                    aws_clients[region] = aws_session.client("ec2", region_name=region)
                ec2_client = aws_clients[region]
                
                if res_type == "EBS Volume":
                    vol_id = metadata.get("VolumeId", res_id)
                    ec2_client.delete_volume(VolumeId=vol_id)
                    success = True
                elif res_type == "Elastic IP":
                    alloc_id = metadata.get("AllocationId")
                    if alloc_id:
                        ec2_client.release_address(AllocationId=alloc_id)
                    else:
                        ec2_client.release_address(PublicIp=res_id)
                    success = True
                elif res_type == "EC2 Instance":
                    inst_id = metadata.get("InstanceId", res_id)
                    ec2_client.terminate_instances(InstanceIds=[inst_id])
                    success = True
                else:
                    raise ValueError(f"Unknown AWS resource type: {res_type}")
                    
            elif prov == "GCP":
                if not gcp_creds:
                    raise ValueError("GCP credentials are not initialized")
                if not compute_v1:
                    raise ValueError("google-cloud-compute is not installed")
                
                project = metadata.get("Project")
                
                if res_type == "Persistent Disk":
                    disk_name = metadata.get("DiskName", res_id)
                    zone = metadata.get("Zone", region)
                    
                    if "disks" not in gcp_clients:
                        gcp_clients["disks"] = compute_v1.DisksClient(credentials=gcp_creds)
                    
                    # Triggers the deletion asynchronously in GCP GCE
                    gcp_clients["disks"].delete(project=project, zone=zone, disk=disk_name)
                    success = True
                elif res_type == "Static IP":
                    ip_name = metadata.get("AddressName", res_id)
                    ip_region = metadata.get("Region", region)
                    
                    if "addresses" not in gcp_clients:
                        gcp_clients["addresses"] = compute_v1.AddressesClient(credentials=gcp_creds)
                        
                    gcp_clients["addresses"].delete(project=project, region=ip_region, address=ip_name)
                    success = True
                elif res_type == "GCE VM":
                    inst_name = metadata.get("InstanceName", res_id)
                    zone = metadata.get("Zone", region)
                    
                    if "instances" not in gcp_clients:
                        gcp_clients["instances"] = compute_v1.InstancesClient(credentials=gcp_creds)
                        
                    gcp_clients["instances"].delete(project=project, zone=zone, instance=inst_name)
                    success = True
                else:
                    raise ValueError(f"Unknown GCP resource type: {res_type}")
            else:
                raise ValueError(f"Unknown provider: {prov}")
                
        except Exception as e:
            err_msg = str(e)
            console.print(f"[bold red]Failed to delete {res_type} {res_id}: {err_msg}[/bold red]")
            
        if success:
            console.print(f"[green]Successfully deleted {res_type} {res_id}[/green]")
            results.append({"resource_id": res_id, "status": "success", "message": "Successfully deleted"})
        else:
            results.append({"resource_id": res_id, "status": "failed", "message": err_msg})
                
    return results
