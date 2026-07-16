from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from cloud_auditor.scanners.base import BaseScanner
from cloud_auditor.config import retry_on_rate_limit

# Basic EC2 monthly cost estimates (On-Demand, Linux, average across regions)
EC2_COSTS = {
    "t2.nano": 4.2, "t2.micro": 8.5, "t2.small": 17.0, "t2.medium": 34.0, "t2.large": 68.0,
    "t3.nano": 3.8, "t3.micro": 7.6, "t3.small": 15.2, "t3.medium": 30.4, "t3.large": 60.8, "t3.xlarge": 121.6, "t3.2xlarge": 243.2,
    "t4g.nano": 3.1, "t4g.micro": 6.1, "t4g.small": 12.3, "t4g.medium": 24.5, "t4g.large": 49.0, "t4g.xlarge": 98.0, "t4g.2xlarge": 196.0,
    "m5.large": 70.0, "m5.xlarge": 140.0, "m5.2xlarge": 280.0, "m5.4xlarge": 560.0,
    "c5.large": 62.0, "c5.xlarge": 124.0, "c5.2xlarge": 248.0, "c5.4xlarge": 496.0,
    "r5.large": 92.0, "r5.xlarge": 184.0, "r5.2xlarge": 368.0, "r5.4xlarge": 736.0,
}

def estimate_ec2_cost(instance_type: str) -> float:
    if instance_type in EC2_COSTS:
        return EC2_COSTS[instance_type]
    
    if "nano" in instance_type:
        return 4.0
    elif "micro" in instance_type:
        return 8.0
    elif "small" in instance_type:
        return 16.0
    elif "medium" in instance_type:
        return 32.0
    elif "large" in instance_type:
        if "2xl" in instance_type:
            return 250.0
        elif "4xl" in instance_type:
            return 500.0
        elif "8xl" in instance_type:
            return 1000.0
        elif "12xl" in instance_type:
            return 1500.0
        elif "16xl" in instance_type:
            return 2000.0
        elif "24xl" in instance_type:
            return 3000.0
        elif "xl" in instance_type:
            return 120.0
        else:
            return 65.0
    return 50.0

def estimate_ebs_cost(volume_type: str, size_gb: int) -> float:
    rates = {
        "gp2": 0.10,
        "gp3": 0.08,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.025,
        "standard": 0.05
    }
    rate = rates.get(volume_type, 0.08)
    return size_gb * rate

class EbsVolumeScanner(BaseScanner):
    def __init__(self, session, region: str):
        super().__init__("AWS", region)
        self.ec2 = session.client("ec2", region_name=region)

    @retry_on_rate_limit()
    def scan(self) -> List[Dict[str, Any]]:
        self.logger.info(f"Scanning unattached EBS volumes in {self.region}...")
        resources = []
        try:
            response = self.ec2.describe_volumes(
                Filters=[{'Name': 'status', 'Values': ['available']}]
            )
            for vol in response.get("Volumes", []):
                vol_id = vol["VolumeId"]
                size = vol["Size"]
                vol_type = vol["VolumeType"]
                cost = estimate_ebs_cost(vol_type, size)
                created_at_str = vol.get('CreateTime').strftime('%Y-%m-%d') if vol.get('CreateTime') else 'unknown'
                resources.append({
                    "resource_id": vol_id,
                    "resource_type": "EBS Volume",
                    "provider": self.provider,
                    "region": self.region,
                    "monthly_cost": cost,
                    "potential_savings": cost,
                    "status": "orphaned",
                    "details": f"Unattached (Created: {created_at_str}, Size: {size} GB, Type: {vol_type})",
                    "metadata": {
                        "VolumeId": vol_id,
                        "Size": size,
                        "VolumeType": vol_type
                    }
                })
        except Exception as e:
            self.logger.error(f"Error scanning EBS volumes in {self.region}: {e}")
        return resources

class EipScanner(BaseScanner):
    def __init__(self, session, region: str):
        super().__init__("AWS", region)
        self.ec2 = session.client("ec2", region_name=region)

    @retry_on_rate_limit()
    def scan(self) -> List[Dict[str, Any]]:
        self.logger.info(f"Scanning unassociated Elastic IPs in {self.region}...")
        resources = []
        try:
            response = self.ec2.describe_addresses()
            for addr in response.get("Addresses", []):
                if "AssociationId" not in addr:
                    public_ip = addr.get("PublicIp", "")
                    allocation_id = addr.get("AllocationId", "")
                    cost = 3.65  # $0.005/hr * 730 hrs
                    resources.append({
                        "resource_id": public_ip,
                        "resource_type": "Elastic IP",
                        "provider": self.provider,
                        "region": self.region,
                        "monthly_cost": cost,
                        "potential_savings": cost,
                        "status": "unused",
                        "details": f"Unassociated Elastic IP (Allocation ID: {allocation_id})",
                        "metadata": {
                            "AllocationId": allocation_id,
                            "PublicIp": public_ip
                        }
                    })
        except Exception as e:
            self.logger.error(f"Error scanning EIPs in {self.region}: {e}")
        return resources

class Ec2InstanceScanner(BaseScanner):
    def __init__(self, session, region: str, cpu_threshold: float = 5.0, days_threshold: int = 14):
        super().__init__("AWS", region)
        self.ec2 = session.client("ec2", region_name=region)
        self.cloudwatch = session.client("cloudwatch", region_name=region)
        self.cpu_threshold = cpu_threshold
        self.days_threshold = days_threshold

    @retry_on_rate_limit()
    def scan(self) -> List[Dict[str, Any]]:
        self.logger.info(f"Scanning underutilized EC2 instances in {self.region}...")
        resources = []
        try:
            response = self.ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=self.days_threshold)
            
            for reservation in response.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    instance_id = inst["InstanceId"]
                    inst_type = inst["InstanceType"]
                    
                    metric_response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,
                        Statistics=['Average']
                    )
                    
                    datapoints = metric_response.get("Datapoints", [])
                    if not datapoints:
                        continue
                    
                    avg_cpu = sum(dp["Average"] for dp in datapoints) / len(datapoints)
                    
                    if avg_cpu < self.cpu_threshold:
                        cost = estimate_ec2_cost(inst_type)
                        resources.append({
                            "resource_id": instance_id,
                            "resource_type": "EC2 Instance",
                            "provider": self.provider,
                            "region": self.region,
                            "monthly_cost": cost,
                            "potential_savings": cost,
                            "status": "underutilized",
                            "details": f"Avg CPU: {avg_cpu:.2f}% (Threshold: {self.cpu_threshold}%, over {self.days_threshold} days)",
                            "metadata": {
                                "InstanceId": instance_id,
                                "InstanceType": inst_type
                            }
                        })
        except Exception as e:
            self.logger.error(f"Error scanning EC2 instances in {self.region}: {e}")
        return resources
