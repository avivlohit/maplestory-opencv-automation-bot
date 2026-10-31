from pathlib import Path
import yaml
'''
Configuration Loader
'''
class ConfigLoader():
    _instance = None
    _config = {} # Pre-initialize empty dict for .update merging to avoid errors

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_yaml_config()
        return cls._instance
    
    def _load_yaml_config(self):
        root_dir = Path(__file__).resolve().parent
        '''Configuration file list'''
        config_files = ["config_default.yaml", "config_data.yaml", "config_log.yaml","config_method.yaml"]

        for file_name in config_files:
            config_path = root_dir / file_name

            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
                
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._config.update(data)

    def get(self, key_path, default=None):
        """
        Get method supporting dot notation
        Example: config.get("database.connection.host")
        """
        # Split incoming string by dot into list. E.g. "database.host" -> ["database", "host"]
        keys = key_path.split(".")
        value = self._config
        
        # Traverse layer by layer
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default  # Return default value if not found, preventing crashes
                
        return value

config = ConfigLoader()
