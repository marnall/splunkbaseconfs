# encoding = utf-8

import json
import os
import tempfile
import time
from datetime import datetime

class CustomCheckpointManager:
    """
    Custom checkpoint manager that provides file-based checkpointing
    as a fallback when KVStore checkpointing fails in newer Splunk versions.
    """
    
    def __init__(self, app_name, checkpoint_dir=None):
        """
        Initialize the checkpoint manager.
        
        Args:
            app_name (str): Name of the app for checkpoint file naming
            checkpoint_dir (str): Directory to store checkpoint files. 
                                 If None, uses system temp directory
        """
        self.app_name = app_name
        if checkpoint_dir is None:
            # Use Splunk's var directory if available, otherwise temp
            splunk_home = os.environ.get('SPLUNK_HOME', '')
            if splunk_home:
                checkpoint_dir = os.path.join(splunk_home, 'var', 'lib', 'splunk', 'modinputs', app_name)
            else:
                checkpoint_dir = os.path.join(tempfile.gettempdir(), f'splunk_{app_name}_checkpoints')
        
        self.checkpoint_dir = checkpoint_dir
        
        # Create checkpoint directory if it doesn't exist
        if not os.path.exists(self.checkpoint_dir):
            try:
                os.makedirs(self.checkpoint_dir, mode=0o755)
            except OSError:
                # If we can't create the directory, fall back to temp
                self.checkpoint_dir = tempfile.mkdtemp(prefix=f'splunk_{app_name}_')
    
    def _get_checkpoint_file_path(self, key):
        """Get the full path for a checkpoint file."""
        filename = f"{self.app_name}_{key}.checkpoint"
        return os.path.join(self.checkpoint_dir, filename)
    
    def get_checkpoint(self, key):
        """
        Get checkpoint value for the given key.
        
        Args:
            key (str): Checkpoint key
            
        Returns:
            The checkpoint value if exists, None otherwise
        """
        checkpoint_file = self._get_checkpoint_file_path(key)
        
        if not os.path.exists(checkpoint_file):
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('value')
        except (IOError, ValueError, json.JSONDecodeError):
            # If file is corrupted or unreadable, return None
            return None
    
    def save_checkpoint(self, key, value):
        """
        Save checkpoint value for the given key.
        
        Args:
            key (str): Checkpoint key
            value: Checkpoint value (must be JSON serializable)
        """
        checkpoint_file = self._get_checkpoint_file_path(key)
        
        data = {
            'key': key,
            'value': value,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'app': self.app_name
        }
        
        try:
            # Write to a temporary file first, then rename for atomic operation
            temp_file = checkpoint_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            os.rename(temp_file, checkpoint_file)
            
        except (IOError, ValueError) as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            raise Exception(f"Failed to save checkpoint: {str(e)}")
    
    def delete_checkpoint(self, key):
        """
        Delete checkpoint for the given key.
        
        Args:
            key (str): Checkpoint key
        """
        checkpoint_file = self._get_checkpoint_file_path(key)
        
        if os.path.exists(checkpoint_file):
            try:
                os.remove(checkpoint_file)
            except OSError:
                pass
    
    def batch_save_checkpoints(self, checkpoint_dict):
        """
        Save multiple checkpoints in batch.
        
        Args:
            checkpoint_dict (dict): Dictionary with keys as checkpoint keys 
                                   and values as checkpoint values
        """
        for key, value in checkpoint_dict.items():
            self.save_checkpoint(key, value)
    
    def list_checkpoints(self):
        """
        List all available checkpoint keys.
        
        Returns:
            list: List of checkpoint keys
        """
        if not os.path.exists(self.checkpoint_dir):
            return []
        
        keys = []
        try:
            for filename in os.listdir(self.checkpoint_dir):
                if filename.endswith('.checkpoint') and filename.startswith(f"{self.app_name}_"):
                    # Extract key from filename
                    key = filename[len(f"{self.app_name}_"):-len('.checkpoint')]
                    keys.append(key)
        except OSError:
            pass
        
        return keys


class FallbackCheckpointHelper:
    """
    A helper class that tries the original Splunk helper checkpoint methods first,
    and falls back to file-based checkpointing if they fail.
    """
    
    def __init__(self, original_helper, app_name="TA-assetnote"):
        """
        Initialize the fallback checkpoint helper.
        
        Args:
            original_helper: The original Splunk helper object
            app_name (str): Name of the app
        """
        self.original_helper = original_helper
        self.custom_manager = CustomCheckpointManager(app_name)
        self.use_fallback = False
        
    def get_check_point(self, key):
        """
        Get checkpoint, trying original method first, then falling back to file-based.
        
        Args:
            key (str): Checkpoint key
            
        Returns:
            The checkpoint value if exists, None otherwise
        """
        if not self.use_fallback:
            try:
                # Try the original method first
                return self.original_helper.get_check_point(key)
            except Exception:
                # If original method fails, switch to fallback mode
                self.use_fallback = True
                # Log the switch (you can uncomment this if needed)
                # print(f"Switching to file-based checkpointing due to KVStore error")
        
        # Use file-based fallback
        return self.custom_manager.get_checkpoint(key)
    
    def save_check_point(self, key, value):
        """
        Save checkpoint, trying original method first, then falling back to file-based.
        
        Args:
            key (str): Checkpoint key
            value: Checkpoint value
        """
        if not self.use_fallback:
            try:
                # Try the original method first
                self.original_helper.save_check_point(key, value)
                return
            except Exception:
                # If original method fails, switch to fallback mode
                self.use_fallback = True
                # Log the switch (you can uncomment this if needed)
                # print(f"Switching to file-based checkpointing due to KVStore error")
        
        # Use file-based fallback
        self.custom_manager.save_checkpoint(key, value)
    
    def delete_check_point(self, key):
        """
        Delete checkpoint, trying original method first, then falling back to file-based.
        
        Args:
            key (str): Checkpoint key
        """
        if not self.use_fallback:
            try:
                # Try the original method first
                self.original_helper.delete_check_point(key)
                return
            except Exception:
                # If original method fails, switch to fallback mode
                self.use_fallback = True
        
        # Use file-based fallback
        self.custom_manager.delete_checkpoint(key)
    
    def batch_save_check_point(self, checkpoint_dict):
        """
        Batch save checkpoints, trying original method first, then falling back to file-based.
        
        Args:
            checkpoint_dict (dict): Dictionary of checkpoint key-value pairs
        """
        if not self.use_fallback:
            try:
                # Try the original method first
                self.original_helper.batch_save_check_point(checkpoint_dict)
                return
            except Exception:
                # If original method fails, switch to fallback mode
                self.use_fallback = True
        
        # Use file-based fallback
        self.custom_manager.batch_save_checkpoints(checkpoint_dict) 