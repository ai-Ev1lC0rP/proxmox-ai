# 🚀 Proxmox AI Manager

An AI-powered assistant for managing Proxmox VE environments using natural language processing and machine learning.

## 📋 Features

- **Natural Language Interface**: Manage your Proxmox environment with conversational commands
- **Ansible Integration**: Execute Ansible playbooks through simple language commands
- **VM & Container Management**: Create, configure, and manage VMs and containers
- **Backup Management**: Schedule, create, list, and restore backups with ease
- **Cluster Operations**: Manage Proxmox clusters efficiently
- **Vector Database**: Store and retrieve information using vector embeddings for improved semantic search
- **Performance Monitoring**: Track resource usage and performance metrics for VMs, containers, and nodes
- **User & Permissions Management**: Manage access control with comprehensive user management
- **Firewall Configuration**: Configure firewall rules for VMs and containers
- **Enhanced Visualization**: Rich, interactive charts and metrics dashboards using Plotly
- **Theming Support**: Choose between light and dark themes to match your preferences
- **Authentication System**: Secure your Proxmox AI interface with user authentication

## 🛠️ Technologies Used

- **Python**: Core programming language
- **Proxmoxer**: Python client for Proxmox API
- **Ansible**: For configuration management and automation
- **SQLAlchemy**: For ORM and database interactions
- **PostgreSQL**: For data storage with pgvector extension
- **Sentence Transformers**: For creating vector embeddings
- **Ollama**: For the LLM interface
- **Streamlit**: For web-based user interface
- **Plotly**: For interactive data visualizations
- **Pandas**: For data manipulation and analysis

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Access to a Proxmox VE environment
- PostgreSQL with pgvector extension
- Ansible (for configuration management features)
- Ollama for local LLM capabilities

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/proxmox-ai.git
   cd proxmox-ai
   ```

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

1. Set up the environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

1. Run the application:

   ```bash
   # Option 1: Run with Chainlit UI
   chainlit run ui.py

   # Option 2: Run with Streamlit UI (more stable)
   ./run_streamlit.sh
   ```

### Authentication Configuration

To enable authentication for the web interface, set the following environment variables:

```bash
# In your .env file
AUTH_ENABLED=true
AUTH_USERNAME=your_username
AUTH_PASSWORD_HASH=your_password_hash
```

Generate a password hash using:

```python
import hashlib
hashlib.sha256("your_password".encode()).hexdigest()
```

## 🧩 Project Structure

- **proxmox_ai.py**: Main AI assistant
- **proxmox_client.py**: Client for Proxmox API
- **proxmox_agents.py**: Different AI agents for various tasks
- **ui.py**: Chainlit-based user interface
- **streamlit_ui.py**: Streamlit-based alternative user interface
- **proxmox_helpers/**: Helper modules
  - **ansible_manager.py**: Ansible integration
  - **ansible_cli.py**: Command-line interface for Ansible
- **ansible_integration/**: Ansible playbooks and templates
- **database/**: Database models and connections
- **tests/**: Test suite

## 📊 Testing

Run the test suite with:

```bash
pytest
```

## 🧪 Test Results

- ✅ VM Management
- ✅ Container Management
- ✅ Cluster Operations
- ✅ Backup Management
- ✅ Ansible Integration
- ✅ Database Operations
- ✅ Performance Monitoring
- ✅ User Management
- ✅ Firewall Configuration
- ✅ UI Authentication
- ✅ Error Handling
- ✅ Visualization Components

## 📚 Usage Examples

### Managing VMs

```bash
> Create a new VM with 4GB RAM and 2 cores on node pve1
> List all running VMs on the cluster
> Stop VM 101
```

### Managing Backups

```bash
> List all backups for VM 101
> Create a backup of VM 101 on storage local
> Schedule daily backups for VM 101 at 2 AM
```

### Performance Monitoring

```bash
> Show CPU usage for VM 101 over the last hour
> Get memory usage trends for container 102
> Display network traffic for node pve1
```

### User Management

```bash
> List all users with access to the cluster
> Create a new user john with admin privileges
> Show permissions for user sarah
```

## 🐳 Docker Setup

The project is fully containerized using Docker Compose with the following services:

- **proxmox-ai**: The main application service
- **postgres**: Database with pgvector extension for vector storage
- **ollama**: LLM service using Ollama

To start all services:

```bash
# Start all services
docker-compose up -d

# Run the UI locally (recommended for development)
./run_streamlit.sh
```

Make sure to configure your environment variables in the `.env` file before starting the containers.

## 🚀 Recent Updates

- Implemented authentication system for the web interface with secure password handling
- Added comprehensive error handling throughout the application with informative error messages
- Enhanced the monitoring dashboard with interactive visualizations using Plotly
  - Added CPU, memory, and storage usage gauges
  - Implemented network and disk I/O bar charts
  - Created resource distribution visualizations
- Added theme customization with light and dark mode support
- Implemented auto-refresh functionality for monitoring data
- Enhanced the sidebar with connection status indicators and quick settings access
- Enhanced Streamlit UI with tabbed interface for improved user experience
  - Added dedicated tabs for VM & Container management
  - Implemented VM to Container conversion interface
  - Created backup management interface with create and restore options
  - Added comprehensive monitoring dashboard for nodes, VMs, and containers
- Improved client-server architecture with dedicated API endpoints
- Enhanced vector store capabilities with semantic search and chat history tracking
- Integrated dedicated agents for backup management, monitoring, and VM-to-container conversion
- Updated Docker configuration with proper service dependencies and healthchecks
- Added database initialization command to main application

## 📋 Todo List

- [x] Add more comprehensive error handling in the Streamlit UI
- [x] Implement authentication for the web interface
- [x] Add more visualization options for Proxmox metrics
- [ ] Expand test coverage for the UI components
- [ ] Implement API documentation with OpenAPI/Swagger
- [ ] Add role-based access control for the web interface
- [x] Create more detailed metrics visualizations for the monitoring dashboard
- [ ] Implement scheduling capabilities for VM-to-container conversions
- [ ] Add more advanced filtering options for VM, container, and backup listings
- [ ] Implement real-time alerts for critical Proxmox events
- [ ] Add support for custom dashboard layouts

## 🙏 Acknowledgments

This project uses and references code from the following open-source projects:

- [Proxmoxer](https://github.com/proxmoxer/proxmoxer)
- [Ansible](https://github.com/ansible/ansible)
- [Ollama](https://github.com/ollama/ollama)
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers)
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy)
- [pgvector](https://github.com/pgvector/pgvector)
- [Streamlit](https://github.com/streamlit/streamlit)
- [Plotly](https://github.com/plotly/plotly.py)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
