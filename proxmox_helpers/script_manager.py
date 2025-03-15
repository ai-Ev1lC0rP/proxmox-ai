"""
Script manager for ProxmoxVE helper scripts

This module provides functionality for discovering, indexing,
and executing the ProxmoxVE helper scripts for VM and container creation.
"""
from typing import Dict, List, Optional, Any, Tuple, Union
import os
import json
import logging
import subprocess
import glob
import re
from pathlib import Path

from database.manager import DatabaseManager
from database.schema import ScriptTemplate

logger = logging.getLogger(__name__)

class ProxmoxScriptManager:
    """
    Manager for ProxmoxVE helper scripts
    
    This class indexes and provides a way to execute the helper 
    scripts from the ProxmoxVE collection.
    """
    
    def __init__(self, 
                 proxmox_scripts_path: str = None, 
                 db_manager: DatabaseManager = None):
        """
        Initialize the script manager
        
        Args:
            proxmox_scripts_path: Path to the ProxmoxVE scripts directory
            db_manager: Database manager instance
        """
        # Default to the ProxmoxVE directory in the project
        if proxmox_scripts_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            proxmox_scripts_path = os.path.join(base_dir, 'ProxmoxVE')
        
        self.proxmox_scripts_path = proxmox_scripts_path
        self.db_manager = db_manager or DatabaseManager()
        
        # Paths to script directories
        self.vm_scripts_path = os.path.join(proxmox_scripts_path, 'vm')
        self.ct_scripts_path = os.path.join(proxmox_scripts_path, 'ct')
        self.json_templates_path = os.path.join(proxmox_scripts_path, 'json')
    
    def index_all_scripts(self) -> None:
        """
        Index all available scripts and store in the database
        """
        # Index VM scripts
        self._index_scripts_in_directory(
            self.vm_scripts_path, 'vm', '*.sh'
        )
        
        # Index container scripts
        self._index_scripts_in_directory(
            self.ct_scripts_path, 'ct', '*.sh'
        )
        
        # Index JSON templates
        self._index_scripts_in_directory(
            self.json_templates_path, 'json', '*.json'
        )
        
        logger.info("Completed indexing all ProxmoxVE scripts")
    
    def _index_scripts_in_directory(self, 
                                  directory: str, 
                                  script_type: str, 
                                  pattern: str) -> None:
        """
        Index scripts in a directory
        
        Args:
            directory: Directory to search
            script_type: Type of script ('vm', 'ct', 'json')
            pattern: Glob pattern to match files
        """
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return
        
        script_files = glob.glob(os.path.join(directory, pattern))
        
        for script_file in script_files:
            try:
                script_name = os.path.basename(script_file)
                
                # Parse script to extract information
                if script_file.endswith('.sh'):
                    description, parameters = self._parse_bash_script(script_file)
                elif script_file.endswith('.json'):
                    description, parameters = self._parse_json_template(script_file)
                else:
                    continue
                
                # Create relative path from proxmox_scripts_path
                rel_path = os.path.relpath(script_file, self.proxmox_scripts_path)
                
                # Create syntax example
                if script_type == 'vm':
                    syntax_example = f"bash -c \"$(wget -qLO - https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/{rel_path})\""
                elif script_type == 'ct':
                    syntax_example = f"bash -c \"$(wget -qLO - https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/{rel_path})\""
                else:
                    syntax_example = f"Import JSON template from: {rel_path}"
                
                # Store in database with embedding
                self._store_script_template(
                    name=script_name,
                    script_type=script_type,
                    description=description,
                    template_path=rel_path,
                    parameters=parameters,
                    syntax_example=syntax_example
                )
                
                logger.info(f"Indexed script: {script_name}")
            except Exception as e:
                logger.error(f"Error indexing script {script_file}: {e}")
    
    def _parse_bash_script(self, script_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse a bash script to extract description and parameters
        
        Args:
            script_path: Path to the bash script
            
        Returns:
            Tuple of (description, parameters)
        """
        description = ""
        parameters = {}
        
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Extract description from comments
            desc_match = re.search(r'#\s+(.*?)\n', content)
            if desc_match:
                description = desc_match.group(1)
            
            # Extract common variables that might be parameters
            var_matches = re.findall(r'var_(\w+)="([^"]*)"', content)
            for var_name, default_value in var_matches:
                parameters[var_name] = {
                    "default": default_value,
                    "type": "string"
                }
            
            # Look for advanced_settings function which often contains parameters
            advanced_match = re.search(r'function\s+advanced_settings\s*\{\s*(.*?)\s*\}', 
                                      content, re.DOTALL)
            if advanced_match:
                advanced_content = advanced_match.group(1)
                
                # Extract parameters from whiptail dialogs
                whiptail_matches = re.findall(
                    r'whiptail\s+--inputbox\s+"([^"]+)"\s+\d+\s+\d+\s+"?([^"]*)"?', 
                    advanced_content
                )
                
                for prompt, default in whiptail_matches:
                    # Create a parameter name from the prompt
                    param_name = re.sub(r'[^a-zA-Z0-9]', '_', prompt.lower())
                    param_name = re.sub(r'_+', '_', param_name)
                    param_name = param_name.strip('_')
                    
                    parameters[param_name] = {
                        "description": prompt,
                        "default": default,
                        "type": "string"
                    }
            
            return description, parameters
        except Exception as e:
            logger.error(f"Error parsing bash script {script_path}: {e}")
            return f"Script: {os.path.basename(script_path)}", {}
    
    def _parse_json_template(self, json_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse a JSON template to extract description and parameters
        
        Args:
            json_path: Path to the JSON template
            
        Returns:
            Tuple of (description, parameters)
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            description = data.get('description', f"Template: {os.path.basename(json_path)}")
            
            # Extract parameters from the JSON structure
            parameters = {}
            for key, value in data.items():
                if key != 'description' and not key.startswith('_'):
                    param_type = "string"
                    if isinstance(value, bool):
                        param_type = "boolean"
                    elif isinstance(value, int):
                        param_type = "integer"
                    elif isinstance(value, float):
                        param_type = "float"
                    
                    parameters[key] = {
                        "default": value,
                        "type": param_type
                    }
            
            return description, parameters
        except Exception as e:
            logger.error(f"Error parsing JSON template {json_path}: {e}")
            return f"Template: {os.path.basename(json_path)}", {}
    
    def _store_script_template(self, 
                              name: str, 
                              script_type: str, 
                              description: str, 
                              template_path: str, 
                              parameters: Dict[str, Any],
                              syntax_example: str) -> None:
        """
        Store a script template in the database with vector embedding
        
        Args:
            name: Script name
            script_type: Type of script
            description: Script description
            template_path: Path to the template
            parameters: Dictionary of parameters
            syntax_example: Example command syntax
        """
        try:
            session = self.db_manager.Session()
            
            # Check if template already exists
            template = session.query(ScriptTemplate).filter_by(
                name=name, 
                script_type=script_type
            ).first()
            
            # Create embedding for description for semantic search
            embedding = self.db_manager.create_text_embedding(
                f"{name} {description} {script_type}"
            )
            embedding_str = self.db_manager.vector_to_pg_array(embedding)
            
            if template:
                # Update existing template
                template.description = description
                template.template_path = template_path
                template.parameters = parameters
                template.syntax_example = syntax_example
                template.embedded_description = embedding_str
            else:
                # Create new template
                template = ScriptTemplate(
                    name=name,
                    script_type=script_type,
                    description=description,
                    template_path=template_path,
                    parameters=parameters,
                    syntax_example=syntax_example,
                    embedded_description=embedding_str
                )
                session.add(template)
            
            session.commit()
        except Exception as e:
            logger.error(f"Error storing script template: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_script_templates(self, script_type: str = None) -> List[Dict[str, Any]]:
        """
        Get all script templates
        
        Args:
            script_type: Optional filter by script type ('vm', 'ct', 'json')
            
        Returns:
            List of script template dictionaries
        """
        templates = self.db_manager.get_script_templates(script_type)
        return [
            {
                "id": t.id,
                "name": t.name,
                "script_type": t.script_type,
                "description": t.description,
                "template_path": t.template_path,
                "parameters": t.parameters,
                "syntax_example": t.syntax_example
            }
            for t in templates
        ]
    
    def search_script_templates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for script templates by description
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching script template dictionaries
        """
        templates = self.db_manager.search_script_templates(query, limit)
        return [
            {
                "id": t.id,
                "name": t.name,
                "script_type": t.script_type,
                "description": t.description,
                "template_path": t.template_path,
                "parameters": t.parameters,
                "syntax_example": t.syntax_example
            }
            for t in templates
        ]
    
    def execute_script(self, 
                      script_path: str, 
                      script_type: str,
                      parameters: Dict[str, str] = None) -> Tuple[bool, str]:
        """
        Execute a ProxmoxVE script
        
        Args:
            script_path: Path to the script (relative to proxmox_scripts_path)
            script_type: Type of script ('vm', 'ct')
            parameters: Optional parameters to pass to the script
            
        Returns:
            Tuple of (success, output/error)
        """
        if parameters is None:
            parameters = {}
        
        # Construct full path
        full_path = os.path.join(self.proxmox_scripts_path, script_path)
        
        if not os.path.exists(full_path):
            return False, f"Script not found: {full_path}"
        
        try:
            # For VM and container scripts, we need to run them with bash
            if script_type in ('vm', 'ct'):
                # Set environment variables for parameters
                env = os.environ.copy()
                for key, value in parameters.items():
                    env[key] = str(value)
                
                # Execute with bash
                process = subprocess.Popen(
                    ['bash', full_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                
                stdout, stderr = process.communicate()
                success = process.returncode == 0
                
                output = stdout.decode('utf-8')
                if not success:
                    output = stderr.decode('utf-8')
                
                return success, output
            
            # For JSON templates, just read and return the content
            elif script_type == 'json':
                with open(full_path, 'r') as f:
                    content = f.read()
                return True, content
            
            else:
                return False, f"Unsupported script type: {script_type}"
        
        except Exception as e:
            logger.error(f"Error executing script {full_path}: {e}")
            return False, f"Error executing script: {str(e)}"
