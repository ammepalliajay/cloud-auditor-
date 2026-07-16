from setuptools import setup, find_packages

setup(
    name="cloud-auditor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]>=0.9.0",
        "rich>=13.0.0",
        "boto3>=1.34.0",
        "google-cloud-compute>=1.15.0",
        "google-cloud-monitoring>=2.19.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "cloud-auditor=cloud_auditor.cli:app",
        ],
    },
)
