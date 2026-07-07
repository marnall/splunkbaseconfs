import json
import os
 
class CybleConfig:
    def __init__(self, logger, file_name="cyble_config.json"):
        self.logger = logger

        # Resolve absolute path inside app/local/
        app_home = os.path.dirname(os.path.dirname(__file__))  # go up from bin/ → app root
        local_dir = os.path.join(app_home, "local")
 
        self.file_path = os.path.join(local_dir, file_name)
 
    def read_all(self) -> dict:
        """Read entire config file, return dict. Creates file if missing."""
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
 
        except Exception as e:
            self.logger.info(f"[CYBLE CONFIG] Failed to read config: {str(e)}")
            return {}
 
    def get(self, key):
        self.logger.info(f"[CYBLE CONFIG] Getting config value for key: {key}")
        return self.read_all().get(key)
 
    def set(self, key, value):
        self.logger.info(f"[CYBLE CONFIG] Setting config value for key: {key}, value: {value}")
        config = self.read_all()
        config[key] = value
        try:
            with open(self.file_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"[CYBLE CONFIG] Failed to write config: {str(e)}")
            raise