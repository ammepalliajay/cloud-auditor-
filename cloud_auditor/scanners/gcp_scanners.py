import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from cloud_auditor.scanners.base import BaseScanner
from cloud_auditor.config import retry_on_rate_limit

try:
    from google.cloud import compute_v1
    from google.cloud import monitoring_v3
    from google.protobuf.duration_pb2 import Duration
except ImportError:
    compute_v1 = None
    monitoring_v3 = None

logger = logging.getLogger("cloud_auditor")

GCP_VM_COSTS = {
    "f1-micro": 4.88, "g1-small": 18.52,
    "e2-micro": 6.11, "e2-small": 12.21, "e2-medium": 24.50,
    "e2-standard-2": 49.01, "e2-standard-4": 98.02,
    "n1-standard-1": 24.27, "n1-standard-2": 48.54, "n1-standard-4": 97.09,
    "n2-standard-2": 70.92, "n2-standard-4": 141.84,
}

def estimate_gcp_vm_cost(machine_type: str) -> float:
    short_name = machine_type.split("/")[-1] if "/" in machine_type else machine_type
    if short_name in GCP_VM_COSTS:
        return GCP_VM_COSTS[short_name]
    
    if "micro" in short_name:
        return 5.0
    elif "small" in short_name:
        return 12.0
    elif "medium" in short_name:
        return 24.0
    elif "standard-2" in short_name:
        return 50.0
    elif "standard-4" in short_name:
        return 100.0
    elif "standard-8" in short_name:
        return 200.0
    elif "standard-16" in short_name:
        return 400.0
    return 30.0

def estimate_gcp_disk_cost(disk_type: str, size_gb: int) -> float:
    short_type = disk_type.split("/")[-1] if "/" in disk_type else disk_type
    rates = {
        "pd-standard": 0.040,
        "pd-balanced": 0.100,
        "pd-ssd": 0.170,
        "pd-extreme": 0.240
    }
    rate = rates.get(short_type, 0.04)
    return size_gb * rate

class GcpDiskScanner(BaseScanner):
    def __init__(self, credentials, project_id: str, zone: str):
        super().__init__("GCP", zone)
        self.credentials = credentials
        self.project_id = project_id
        self.zone = zone
        self.client = compute_v1.DisksClient(credentials=self.credentials) if compute_v1 else None

    @retry_on_rate_limit()
    def scan(self) -> List[Dict[str, Any]]:
        self.logger.info(f"Scanning unattached GCP disks in zone {self.zone}...")
        resources = []
        if not self.client:
            self.logger.error("GCP Compute Engine client library is not installed or available.")
            return resources
        
        try:
            disks = self.client.list(project=self.project_id, zone=self.zone)
            for disk in disks:
                if not disk.users:
                    disk_name = disk.name
                    size_gb = disk.size_gb or 0
                    disk_type = disk.type_ or "pd-standard"
                    cost = estimate_gcp_disk_cost(disk_type, size_gb)
                    resources.append({
                        "resource_id": disk_name,
                        "resource_type": "Persistent Disk",
                        "provider": self.provider,
                        "region": self.zone,
                        "monthly_cost": cost,
                        "potential_savings": cost,
                        "status": "orphaned",
                        "details": f"Unattached Disk (Size: {size_gb} GB, Type: {disk_type.split('/')[-1]})",
                        "metadata": {
                            "DiskName": disk_name,
                            "Zone": self.zone,
                            "Project": self.project_id
                        }
                    })
        except Exception as e:
            self.logger.error(f"Error scanning GCP disks in {self.zone}: {e}")
        return resources

class GcpIpScanner(BaseScanner):
    def __init__(self, credentials, project_id: str, region: str):
        super().__init__("GCP", region)
        self.credentials = credentials
        self.project_id = project_id
        self.region_name = region
        self.client = compute_v1.AddressesClient(credentials=self.credentials) if compute_v1 else None

    @retry_on_rate_limit()
    def scan(self) -> List[Dict[str, Any]]:
        self.logger.info(f"Scanning unused GCP static IPs in region {self.region_name}...")
        resources = []
        if not self.client:
            self.logger.error("GCP Compute Engine client library is not installed or available.")
            return resources
        
        try:
            addresses = self.client.list(project=self.project_id, region=self.region_name)
            for addr in addresses:
                if addr.status == "RESERVED":
                    ip_name = addr.name
                    ip_address = addr.address
                    cost = 7.30  # $0.01/hr * 730 hrs
                    resources.append({
                        "resource_id": ip_address,
                        "resource_type": "Static IP",
                        "provider": self.provider,
                        "region": self.region_name,
                        "monthly_cost": cost,
                        "potential_savings": cost,
                        "status": "unused",
                        "details": f"Unused Static IP (Name: {ip_name})",
                        "metadata": {
                            "AddressName": ip_name,
                            "Region": self.region_name,
                            "Project": self.project_id,
                            "Address": ip_address
                        }
                    })
        except Exception as e:
            self.logger.error(f"Error scanning GCP IPs in {self.region_name}: {e}")
        return resources

class GcpVmScanner(BaseScanner):
    def __init__(self, credentials, project_id: str, zone: str, cpu_threshold: float = 5.0, days_threshold: int = 14):
        super().__init__("GCP", zone)
        self.credentials = credentials
        self.project_id = project_id
        self.zone = zone
        self.cpu_threshold = cpu_threshold
        self.days_threshold = days_threshold
        self.instances_client = compute_v1.InstancesClient(credentials=self.credentials) if compute_v1 else None
        self.metric_client = monitoring_v3.MetricServiceClient(credentials=self.credentials) if monitoring_v3 else None

    @retry_on_rate_limit()
    def scan(self) -> List[Dict[str, Any]]:
        self.logger.info(f"Scanning underutilized GCP VM instances in zone {self.zone}...")
        resources = []
        if not self.instances_client or not self.metric_client:
            self.logger.error("GCP Compute/Monitoring client libraries are not installed or available.")
            return resources
        
        try:
            instances = self.instances_client.list(project=self.project_id, zone=self.zone)
            running_instances = [inst for inst in instances if inst.status == "RUNNING"]
            
            if not running_instances:
                return resources
            
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=self.days_threshold)
            
            for inst in running_instances:
                instance_id = inst.id
                instance_name = inst.name
                machine_type = inst.machine_type
                
                project_name = f"projects/{self.project_id}"
                interval = monitoring_v3.TimeInterval(
                    start_time={"seconds": int(start_time.timestamp())},
                    end_time={"seconds": int(end_time.timestamp())}
                )
                
                aggregation = monitoring_v3.Aggregation(
                    alignment_period=Duration(seconds=86400),
                    per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN
                )
                
                results = self.metric_client.list_time_series(
                    name=project_name,
                    filter=(
                        'metric.type = "compute.googleapis.com/instance/cpu/utilization" '
                        'AND resource.type = "gce_instance" '
                        f'AND resource.labels.instance_id = "{instance_id}"'
                    ),
                    interval=interval,
                    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    aggregation=aggregation
                )
                
                datapoints = []
                for series in results:
                    for point in series.points:
                        datapoints.append(point.value.double_value)
                
                if not datapoints:
                    continue
                
                # GCP Metric yields 0.0 to 1.0. Convert to %
                avg_cpu = (sum(datapoints) / len(datapoints)) * 100.0
                
                if avg_cpu < self.cpu_threshold:
                    cost = estimate_gcp_vm_cost(machine_type)
                    resources.append({
                        "resource_id": instance_name,
                        "resource_type": "GCE VM",
                        "provider": self.provider,
                        "region": self.zone,
                        "monthly_cost": cost,
                        "potential_savings": cost,
                        "status": "underutilized",
                        "details": f"Avg CPU: {avg_cpu:.2f}% (Threshold: {self.cpu_threshold}%, over {self.days_threshold} days)",
                        "metadata": {
                            "InstanceName": instance_name,
                            "Zone": self.zone,
                            "Project": self.project_id,
                            "MachineType": machine_type.split('/')[-1]
                        }
                    })
        except Exception as e:
            self.logger.error(f"Error scanning GCP VMs in {self.zone}: {e}")
        return resources
