from typing import List, Dict, Any
import logging

class BaseScanner:
    def __init__(self, provider: str, region: str):
        self.provider = provider
        self.region = region
        self.logger = logging.getLogger(f"cloud_auditor.scanner.{provider}.{region}")

    def scan(self) -> List[Dict[str, Any]]:
        """
        Executes the scan and returns a list of identified resources.
        
        Each resource dictionary should contain:
            - 'resource_id': str (e.g. volume ID, instance ID, IP)
            - 'resource_type': str (e.g. 'EBS Volume', 'Elastic IP', 'EC2 Instance')
            - 'provider': str ('AWS' or 'GCP')
            - 'region': str (e.g. 'us-east-1')
            - 'monthly_cost': float (estimated monthly cost in USD)
            - 'potential_savings': float (estimated savings if optimized/deleted)
            - 'status': str ('orphaned', 'underutilized', 'unused')
            - 'details': str (human readable description of current state)
            - 'metadata': dict (low-level details required for deletion)
        """
        raise NotImplementedError("Scanners must implement the scan() method.")
