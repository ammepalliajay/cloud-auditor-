"""
Cloud Auditor - Data Models Module
Defines all data structures and models for cloud resource auditing.
"""

class CloudResource:
    """Represents a cloud resource (VM, Storage, etc.)"""
    def __init__(self, name, provider, resource_type):
        self.name = name
        self.provider = provider  # aws, gcp, azure
        self.resource_type = resource_type  # compute, storage, network
        self.created_at = None
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'name': self.name,
            'provider': self.provider,
            'resource_type': self.resource_type,
            'created_at': self.created_at
        }

class CostMetric:
    """Represents cost data for resources"""
    def __init__(self, resource_id, cost, currency="USD"):
        self.resource_id = resource_id
        self.cost = cost
        self.currency = currency
        self.timestamp = None
    
    def to_dict(self):
        """Convert cost metric to dictionary."""
        return {
            'resource_id': self.resource_id,
            'cost': self.cost,
            'currency': self.currency,
            'timestamp': self.timestamp
        }
