import os
import yaml
from jinja2 import Template

class PromptManager:
    def __init__(self, prompts_file="prompts/prompts.yaml", config_file="config/agent_config.yaml"):
        # Cerca il file prompts.yaml in diverse posizioni possibili
        search_paths = [
            prompts_file,
            os.path.join(os.getcwd(), prompts_file),
            os.path.join(os.path.dirname(__file__), "..", prompts_file),
            os.path.join(os.getcwd(), "data/prompts/prompts.yaml") # Fallback per retrocompatibilità
        ]

        self.prompts = {}
        for path in search_paths:
            if os.path.exists(path):
                self.prompts = self._load_prompts(path)
                break

        if not self.prompts:
            print(f"Warning: Prompts file not found in any of {search_paths}. Using empty dict.")

        # Carica configurazione unificata
        self.config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading config from {config_file}: {e}")

    def get_config(self, path, default=None):
        """Ottiene un valore dalla configurazione dato un path (es. 'agent.max_attempts')."""
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                    break
        except (KeyError, TypeError):
            value = None

        return value if value is not None else default

    def _load_prompts(self, path):
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading prompts from {path}: {e}")
            return {}

    def get_prompt(self, path, **kwargs):
        """
        Ottiene un prompt dato un path (es. 'coder.base.system')
        e opzionalmente esegue il rendering con Jinja2.
        """
        keys = path.split('.')
        value = self.prompts
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                    break
        except (KeyError, TypeError):
            value = None

        if value is None:
            return f"Prompt not found: {path}"

        if kwargs and isinstance(value, str):
            try:
                template = Template(value)
                return template.render(**kwargs)
            except Exception as e:
                return f"Error rendering prompt {path}: {e}"

        return value

    def list_prompts(self, current_dict=None, prefix=""):
        """Ritorna una lista di tutti i path validi per i prompt."""
        if current_dict is None:
            current_dict = self.prompts

        if not isinstance(current_dict, dict):
            return []

        paths = []
        for key, value in current_dict.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                paths.extend(self.list_prompts(value, new_prefix))
            else:
                paths.append(new_prefix)
        return paths
