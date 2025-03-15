# 🚀 Proxmox AI Manager

An AI-powered assistant for managing Proxmox VE environments using natural language processing and machine learning.

## 📋 Features

- **Natural Language Interface**: Manage your Proxmox environment with conversational commands
- **Ansible Integration**: Execute Ansible playbooks through simple language commands
- **VM & Container Management**: Create, configure, and manage VMs and containers
- **Backup Management**: Schedule, create, list, and restore backups with ease
- **Cluster Operations**: Manage Proxmox clusters efficiently
- **Vector Database**: Store and retrieve information using vector embeddings for improved semantic search

## 🛠️ Technologies Used

- **Python**: Core programming language
- **Proxmoxer**: Python client for Proxmox API
- **Ansible**: For configuration management and automation
- **SQLAlchemy**: For ORM and database interactions
- **PostgreSQL**: For data storage with pgvector extension
- **Sentence Transformers**: For creating vector embeddings
- **Ollama**: For the LLM interface

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Access to a Proxmox VE environment
- PostgreSQL with pgvector extension
- Ansible (for configuration management features)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/proxmox-ai.git
cd proxmox-ai
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
python app.py
```

## 🧩 Project Structure

- **proxmox_ai.py**: Main AI assistant
- **proxmox_client.py**: Client for Proxmox API
- **proxmox_agents.py**: Different AI agents for various tasks
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

## 📚 Usage Examples

### Managing VMs

```
> Create a new VM with 4GB RAM and 2 cores on node pve1
> List all running VMs on the cluster
> Stop VM 101
```

### Managing Backups

```
> List all backups for VM 101
> Create a backup of VM 101 on storage local
> Schedule daily backups for VM 101 at 2 AM
```

### Ansible Integration

```
> Run the security_hardening playbook on all nodes
> Create a new container using Ansible
```

## 🙏 Acknowledgments

This project uses and references code from the following open-source projects:

- [Proxmoxer](https://github.com/proxmoxer/proxmoxer)
- [Ansible](https://github.com/ansible/ansible)
- [Ollama](https://github.com/ollama/ollama)
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers)
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy)
- [pgvector](https://github.com/pgvector/pgvector)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.