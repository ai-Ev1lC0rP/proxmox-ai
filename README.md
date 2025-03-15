# Proxmox AI Manager 

A powerful AI-driven system for managing Proxmox Virtual Environment (PVE) infrastructure, leveraging LLMs for intelligent automation and management assistance.

## Features 

### 1. Proxmox API Integration 

- Complete Proxmox API client using proxmoxer
- Token-based authentication for secure access
- VM and container management capabilities
- Storage and resource monitoring
- Cluster status and task tracking

### 2. Intelligent AI Agents 

- **VM Management Agent**: Create, modify, delete, and control virtual machines
- **Container Management Agent**: Manage LXC containers with best practices
- **Storage Management Agent**: Optimize and monitor storage solutions
- **Cluster Management Agent**: Configure and maintain Proxmox clusters
- **API Assistant Agent**: Help construct and understand Proxmox API calls
- **Performance Analysis Agent**: Monitor and optimize system performance

### 3. Advanced LLM Integration 

- Connect to local Ollama server for LLM capabilities
- Streaming responses in real-time
- Adjustable model parameters (temperature, top_p, max_tokens)
- Natural language processing of management requests
- Intelligent parsing of Proxmox documentation

### 4. User-Friendly Interfaces 

- Command-line interface for quick management tasks
- Connection to multiple Proxmox hosts
- Secure credential handling via environment variables
- Interactive mode for conversational management

### 5. Containerized Deployment 

- Docker and Docker Compose support
- Integrated Ollama container for LLM capabilities
- Secure environment variable management
- GPU passthrough for optimal LLM performance

### 6. Ansible Integration 

- Ansible integration for configuration management
- Available playbooks for VM, container, and cluster management
- Accessible through command-line interface, natural language commands, and programmatic API

## Ansible Integration 

The Proxmox AI assistant includes full Ansible integration for managing Proxmox infrastructure as code:

### Available Playbooks

- **proxmox_vm_manager.yml**: Create, start, stop, restart, and delete VMs
- **proxmox_container_manager.yml**: Create, start, stop, restart, and delete LXC containers 
- **proxmox_cluster_manager.yml**: Manage Proxmox clusters, including creation, joining, and HA configuration

### Using Ansible Integration

The Ansible integration can be accessed through:

1. Command-line interface:
```bash
python -m proxmox_helpers.ansible_manager --playbook proxmox_vm_manager --operation create --vm-name test-vm
```

2. Natural language commands:
```
run ansible playbook proxmox_vm_manager with vars {"vm_name": "test-vm", "vm_memory": 4096}
manage vm with ansible create vm 101 on node pve
manage container with ansible start ct 102 on node pve
manage cluster with ansible status on node pve
```

3. Programmatic API:
```python
from proxmox_helpers.ansible_manager import AnsibleManager

ansible = AnsibleManager()
success, output = ansible.run_vm_management(
    operation='create',
    vm_name='test-vm',
    vm_memory=4096
)
```

### Adding Custom Playbooks

Place your custom Ansible playbooks in the `ansible_integration/playbooks` directory. They will be automatically discovered and made available through the API and CLI.

## Quick Start 

### Prerequisites

1. Python 3.8+ for local development
2. [Ollama](https://ollama.ai/) installed or Docker for containerized deployment
3. Proxmox VE environment with API access

### Environment Setup 

1. Create a `.env` file in the project root based on the provided `.env.example`:

```env
# Proxmox connection details
PROXMOX_HOST=your-proxmox-host.example.com
PROXMOX_PORT=8006
PROXMOX_USER=root@pam
PROXMOX_TOKEN_ID=your-token-id
PROXMOX_SECRET=your-token-secret
PROXMOX_VERIFY_SSL=false

# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2:latest

# Database settings
PROXMOX_DB_URL=postgresql://postgres:postgres@localhost:5432/proxmox_ai
```

2. Alternatively, export environment variables directly in your shell:

```bash
export PROXMOX_HOST=your-proxmox-host.example.com
export PROXMOX_PORT=8006
export PROXMOX_USER=root@pam
export PROXMOX_TOKEN_ID=your-token-id
export PROXMOX_SECRET=your-token-secret
```

### Running with Docker 

1. Start the containerized application:

```bash
docker compose up -d
```

This will start both the Proxmox AI application and an Ollama instance for LLM support.

### Running Locally 

1. Ensure Ollama is running:

```bash
ollama serve
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the application:

```bash
python proxmox_ai.py
```

## Docker Support 

### Quick Start with Docker

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

## Database Support 

The application uses PostgreSQL with pgvector for storing:

1. Proxmox node and resource information
2. Command history with vector embeddings
3. Script templates and metadata

### Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables for Proxmox AI
CREATE TABLE IF NOT EXISTS proxmox_nodes (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    cpu FLOAT,
    memory BIGINT,
    uptime BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proxmox_vms (
    id SERIAL PRIMARY KEY,
    vmid INTEGER NOT NULL,
    name VARCHAR(255),
    node_id VARCHAR(255) REFERENCES proxmox_nodes(node_id),
    status VARCHAR(50),
    cpu FLOAT,
    memory BIGINT,
    disk BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vmid, node_id)
);

CREATE TABLE IF NOT EXISTS command_logs (
    id SERIAL PRIMARY KEY,
    command TEXT NOT NULL,
    command_embedding vector(384),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result JSON
);

CREATE TABLE IF NOT EXISTS script_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    script_path VARCHAR(255) NOT NULL,
    parameters JSON,
    script_embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Command Line Interface 

Proxmox AI includes a command-line interface to interact with your Proxmox environment:

```bash
# Execute a direct command
python cli.py "your command here"

# Examples
python cli.py "list all vms"
python cli.py "show node status"
python cli.py "start vm 100"
```

## Environment Variables 

| Variable | Description | Default |
|----------|-------------|---------|
| PROXMOX_HOST | Proxmox host address | None |
| PROXMOX_PORT | Proxmox API port | 8006 |
| PROXMOX_USER | Proxmox username | None |
| PROXMOX_TOKEN_ID | Proxmox API token ID | None |
| PROXMOX_SECRET | Proxmox API token secret | None |
| PROXMOX_VERIFY_SSL | Verify SSL certificates | false |
| OLLAMA_BASE_URL | URL for Ollama API | http://localhost:11434/v1 |
| OLLAMA_MODEL | Model to use for LLM | llama3.2:latest |
| PROXMOX_DB_URL | PostgreSQL connection URL | postgresql://postgres:postgres@localhost:5432/proxmox_ai |
| PROXMOX_SCRIPTS_PATH | Path to ProxmoxVE scripts | ./ProxmoxVE |
| DEBUG | Enable debug mode | false |
| MODE | Operation mode | query |
| QUERY | Query to execute | None |
| EXECUTE | Whether to execute commands | false |

## Changelog 

### 2023-06-20

- Added PostgreSQL database with pgvector support for embeddings
- Integrated command handler with semantic search
- Added script manager for ProxmoxVE helper scripts
- Updated Docker Compose for PostgreSQL integration
- Added comprehensive test suite for components
- Developed CLI interface for command execution

### 2023-03-15

- Updated UI theme from "News Assistant" to "Proxmox Server Whisperer" with fun, magical server management language
- Changed mode labels to match the new theme:
  - "News Search" → "Server Whisperer"
  - "News Source Comparison" → "Solution Comparison"
  - "Web Search" → "Mystical Web Search"
  - "Research" → "Deep Thought"
- Updated system prompts to use mystical/magical terminology for a more engaging user experience

### 2023-07-01

- Added Ansible integration for configuration management
- Available playbooks for VM, container, and cluster management
- Accessible through command-line interface, natural language commands, and programmatic API

## Troubleshooting 

### Docker Issues

- **Container exits immediately**: Make sure you're running in server mode or providing the necessary environment variables for direct queries.
- **Can't connect to Proxmox**: Verify your Proxmox host is reachable and credentials are correct.
- **Ollama connection errors**: These are expected if you're not running Ollama. You can connect to an external Ollama instance by setting the `OLLAMA_BASE_URL` environment variable.

## Usage 

### Command Line Interface

```bash
# Basic usage
python cli.py "your command here"

# Examples
python cli.py "list all vms"
python cli.py "show node status"
python cli.py "start vm 100"
```

### Natural Language Examples

Proxmox AI supports natural language queries including:

- "Show me all running virtual machines"
- "What's the status of node1?"
- "Start the container with ID 101"
- "How much disk space is available on all nodes?"
- "Create a backup of all VMs on node1"
- "Show me the resource usage of the cluster"

## Development Roadmap 

1. Proxmox API client integration 
2. AI agent framework development 
3. Docker containerization 
4. PostgreSQL database integration 
5. Vector embeddings for semantic search 
6. ProxmoxVE script integration 
7. Command handler with natural language processing 
8. Ansible integration for configuration management
9. Scheduled task management

## Test Results 

The following tests are currently passing:

### Test Database Manager

```bash
pytest -xvs tests/test_database_manager.py
```

### Test Command Handler

```bash
pytest -xvs tests/test_command_handler.py
```

### Test Script Manager

```bash
pytest -xvs tests/test_script_manager.py
```

### Docker Compose Up

```bash
docker compose up -d
```

### CLI List VMs

```bash
python cli.py "list all vms"
```

### Database Setup

```bash
python database/setup.py
```

### CLI List Containers

```bash
python cli.py "list containers on node1"
```

### CLI System Status

```bash
python cli.py "show system status"
```

## Completed Features 

- Proxmox API client for VM, container, and node management
- PostgreSQL database with pgvector for embeddings and semantic search
- Command handler for natural language processing of Proxmox commands
- Script manager for utilizing ProxmoxVE helper scripts
- Vector-based semantic search for commands and scripts
- Docker and Docker Compose support for containerized deployment
- CLI interface for executing commands against Proxmox VE
- Ansible integration for configuration management

## Next Steps 

- Terraform module integration for infrastructure as code
- Ansible playbook integration for configuration management
- Web dashboard for visualizing Proxmox resources
- Notification system for alerts and events
- Enhanced security features for credential management
- Performance analytics dashboard
- Advanced agent specializations for different management tasks

## License 

MIT License

## Acknowledgments 🙏

This project was inspired by and builds upon several excellent open-source projects:

- [Proxmoxer](https://github.com/proxmoxer/proxmoxer) - Python client for Proxmox API
- [Ansible](https://github.com/ansible/ansible) - IT automation platform
- [Ollama](https://github.com/ollama/ollama) - Run LLMs locally
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers) - For vector embeddings
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) - Python SQL toolkit and ORM
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search for PostgreSQL

Special thanks to all the contributors and maintainers of these projects for making this work possible!
