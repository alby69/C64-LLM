import os
import yaml
from jinja2 import Template

class PromptManager:
    def __init__(self, prompts_file="data/prompts/prompts.yaml"):
        self.prompts_file = prompts_file
        self.prompts = self._load_prompts()

    def _load_prompts(self):
        if not os.path.exists(self.prompts_file):
            return {}
        with open(self.prompts_file, 'r') as f:
            return yaml.safe_load(f)

    def get_prompt(self, path, **kwargs):
        """
        Ottiene un prompt dato un path (es. 'coder.base.system')
        e opzionalmente esegue il rendering con Jinja2.
        """
        keys = path.split('.')
        value = self.prompts
        try:
            for key in keys:
                value = value[key]
        except (KeyError, TypeError):
            return f"Prompt not found: {path}"

        if kwargs:
            template = Template(value)
            return template.render(**kwargs)

        return value

    def list_prompts(self, current_dict=None, prefix=""):
        """Ritorna una lista di tutti i path validi per i prompt (es. 'coder.base.system')."""
        if current_dict is None:
            current_dict = self.prompts

        paths = []
        for key, value in current_dict.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                paths.extend(self.list_prompts(value, new_prefix))
            else:
                paths.append(new_prefix)
        return paths
