import boto3
import google.auth
from google.oauth2 import service_account
import logging

logger = logging.getLogger("cloud_auditor")

def get_aws_session(profile_name=None, role_arn=None, role_session_name="CloudAuditorSession", region_name=None):
    """
    Creates and returns a boto3.Session.
    Supports local profiles and IAM role assumption.
    """
    try:
        # Step 1: Base Session
        if profile_name:
            logger.info(f"Using AWS profile: {profile_name}")
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
        else:
            logger.info("Using default AWS credential chain")
            session = boto3.Session(region_name=region_name)
        
        # Step 2: Assume Role if specified
        if role_arn:
            logger.info(f"Assuming AWS IAM Role: {role_arn}")
            sts_client = session.client("sts")
            assumed_role = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name
            )
            credentials = assumed_role["Credentials"]
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=region_name or session.region_name
            )
            
        return session
    except Exception as e:
        logger.error(f"Failed to authenticate with AWS: {e}")
        raise e

def get_gcp_credentials(key_path=None):
    """
    Retrieves Google Cloud credentials and project ID.
    Supports explicit service account key path or ADC (Application Default Credentials).
    """
    try:
        if key_path:
            logger.info(f"Using GCP Service Account Key: {key_path}")
            credentials = service_account.Credentials.from_service_account_file(key_path)
            project_id = credentials.project_id
            return credentials, project_id
        else:
            logger.info("Using GCP Application Default Credentials (ADC)")
            credentials, project_id = google.auth.default()
            return credentials, project_id
    except Exception as e:
        logger.error(f"Failed to authenticate with GCP: {e}")
        raise e
