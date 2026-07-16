import boto3
from datetime import datetime, timedelta, timezone
from moto import mock_aws
from cloud_auditor.scanners.aws_scanners import EbsVolumeScanner, EipScanner, Ec2InstanceScanner

@mock_aws
def test_ebs_volume_scanner():
    session = boto3.Session()
    ec2_client = session.client("ec2", region_name="us-east-1")
    
    vol = ec2_client.create_volume(
        AvailabilityZone="us-east-1a",
        Size=10,
        VolumeType="gp3"
    )
    vol_id = vol["VolumeId"]
    
    scanner = EbsVolumeScanner(session, "us-east-1")
    results = scanner.scan()
    
    assert len(results) == 1
    assert results[0]["resource_id"] == vol_id
    assert results[0]["resource_type"] == "EBS Volume"
    assert results[0]["monthly_cost"] == 10 * 0.08
    assert results[0]["status"] == "orphaned"

@mock_aws
def test_eip_scanner():
    session = boto3.Session()
    ec2_client = session.client("ec2", region_name="us-east-1")
    
    allocation = ec2_client.allocate_address(Domain="vpc")
    public_ip = allocation["PublicIp"]
    allocation_id = allocation["AllocationId"]
    
    scanner = EipScanner(session, "us-east-1")
    results = scanner.scan()
    
    assert len(results) == 1
    assert results[0]["resource_id"] == public_ip
    assert results[0]["resource_type"] == "Elastic IP"
    assert results[0]["metadata"]["AllocationId"] == allocation_id

@mock_aws
def test_ec2_instance_scanner_underutilized():
    session = boto3.Session()
    ec2_client = session.client("ec2", region_name="us-east-1")
    cw_client = session.client("cloudwatch", region_name="us-east-1")
    
    run_response = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t3.micro"
    )
    instance_id = run_response["Instances"][0]["InstanceId"]
    
    now = datetime.now(timezone.utc)
    for i in range(14):
        time_point = now - timedelta(days=i)
        cw_client.put_metric_data(
            Namespace="AWS/EC2",
            MetricData=[
                {
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                    "Timestamp": time_point,
                    "Value": 2.5,
                    "Unit": "Percent"
                }
            ]
        )
        
    scanner = Ec2InstanceScanner(session, "us-east-1", cpu_threshold=5.0, days_threshold=14)
    results = scanner.scan()
    
    assert len(results) == 1
    assert results[0]["resource_id"] == instance_id
    assert results[0]["resource_type"] == "EC2 Instance"
    assert results[0]["status"] == "underutilized"
