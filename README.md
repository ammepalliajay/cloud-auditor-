# Cloud Infrastructure Auditor & Cost Optimizer CLI

A comprehensive Python application for auditing cloud infrastructure, analyzing cost patterns, and optimizing cloud resource allocation. This project provides a modular architecture with database connectivity, REST API endpoints, and comprehensive testing.

## 📋 Project Overview

This project is designed to help organizations:
- Audit their cloud infrastructure across multiple cloud providers
- Analyze and optimize cloud costs
- Generate detailed reports on resource usage
- Track and monitor infrastructure changes over time
- Provide actionable insights for cost reduction

## 🚀 Features

- **Database Management** - Robust data persistence with configuration management
- **API Framework** - RESTful API endpoints for infrastructure queries and cost analysis
- **Data Models** - Structured data models for cloud resources and cost metrics
- **Utility Functions** - Helper functions for common operations
- **Unit Tests** - Comprehensive test suite for quality assurance
- **Modular Architecture** - Well-organized code structure for scalability
- **Configuration Management** - Flexible configuration system for different environments

## 📁 Project Structure

```
Project---/
├── main.py              # Main entry point for the CLI application
├── api.py               # API endpoint definitions and handlers
├── config.py            # Configuration management module
├── database.py          # Database connectivity and operations
├── models.py            # Data models for cloud resources
├── utils.py             # Utility functions and helpers
├── requirements.txt     # Project dependencies
├── setup.py             # Package setup and installation configuration
├── tests.py             # Unit tests for core modules
├── tests/               # Additional test directory
├── cloud_auditor/       # Main package directory
├── .github/             # GitHub Actions workflow directory
└── .gitignore           # Git ignore rules
```

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/ammepalliajay/Project---.git
cd Project---
```

2. **Create a virtual environment (recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install the project in development mode**
```bash
python setup.py develop
```

## 💻 Usage

### Running the Main Application

```bash
python main.py
```

This will initialize the project and start the main application.

### Using the API Framework

The `APIHandler` class provides a flexible API endpoint registration system:

```python
from api import APIHandler

# Create an API handler instance
handler = APIHandler()

# Register an endpoint
def get_resources():
    return {"status": "success", "resources": []}

handler.register_endpoint('/api/resources', get_resources)

# Handle incoming requests
response = handler.handle_request('/api/resources')
```

### Working with Configuration

The `config.py` module provides configuration management:

```python
from config import load_config
config = load_config()
```

### Database Operations

Access the database module for data persistence:

```python
from database import DatabaseManager
db = DatabaseManager()
db.connect()
db.execute_query("SELECT * FROM resources")
```

### Using Data Models

Define and work with cloud resource data:

```python
from models import Resource, CostMetric

# Create a resource instance
resource = Resource(
    name="ec2-instance",
    provider="aws",
    resource_type="compute"
)
```

## 🧪 Testing

Run the test suite to ensure everything is working correctly:

```bash
python -m pytest tests.py -v
```

Or run tests using the built-in test module:

```bash
python tests.py
```

## 📦 Dependencies

- **python >= 3.8** - Core requirement

Additional dependencies can be added to `requirements.txt` as needed.

## 🔧 Configuration

Create a configuration file or environment variables to customize:
- Database connection settings
- API server port and host
- Cloud provider credentials
- Logging levels
- Report output formats

## 📊 Key Modules

### `main.py`
Entry point for the CLI application. Initializes and starts the application.

### `api.py`
Defines the `APIHandler` class for managing REST API endpoints with dynamic registration and request handling.

### `config.py`
Configuration management for different environments and settings.

### `database.py`
Database connectivity layer for data persistence and query execution.

### `models.py`
Data model definitions for cloud resources, costs, and metrics.

### `utils.py`
Utility functions for logging, data processing, and common operations.

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Submit a pull request

## 📝 Development Workflow

1. Make changes to the code
2. Run tests to ensure nothing breaks
3. Update documentation if needed
4. Commit with clear messages
5. Push to your fork and create a PR

## 🚢 Deployment

The project includes GitHub Actions workflows for automated builds and releases. Check `.github/workflows/` for CI/CD configuration.

## 📞 Support & Contact

For questions or issues:
- Open a GitHub issue
- Contact: ammepalliajaykumar@gmail.com

## 📄 License

This project is open source and available under the MIT License.

## 🎯 Roadmap

- [ ] Multi-cloud provider support (AWS, Azure, GCP)
- [ ] Advanced cost prediction algorithms
- [ ] Real-time alerting system
- [ ] Custom report generation
- [ ] Mobile app integration
- [ ] Enhanced data visualization

## 📚 Additional Resources

- [Python Documentation](https://docs.python.org/)
- [REST API Best Practices](https://restfulapi.net/)
- [Database Design Patterns](https://www.postgresql.org/)

---

**Last Updated:** July 17, 2026

