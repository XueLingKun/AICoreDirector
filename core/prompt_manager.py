import os
import configparser
import yaml
import json

class PromptManager:
    def __init__(self, prompt_dir="config_prompts"):
        self.prompts = {}
        if not os.path.exists(prompt_dir):
            return
        for fname in os.listdir(prompt_dir):
            fpath = os.path.join(prompt_dir, fname)
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                with open(fpath, "r", encoding="utf-8") as f:
                    self.prompts[fname[:-5]] = yaml.safe_load(f)
            elif fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8") as f:
                    self.prompts[fname[:-5]] = json.load(f)
            elif fname.endswith(".ini"):
                cp = configparser.ConfigParser()
                cp.read(fpath, encoding="utf-8")
                self.prompts[fname[:-4]] = {s: dict(cp.items(s)) for s in cp.sections()}
    def get_prompt(self, plugin, template="default"):
        # plugin: 文件名（不含扩展名），template: section/key
        p = self.prompts.get(plugin, {})
        if isinstance(p, dict):
            return p.get(template, "")
        return p 