import json
from pathlib import Path
from typing import Dict, Optional

from ffmwr.utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)

_name_mapping_cache: Optional[Dict[str, str]] = None


def load_name_mapping(root_dir: Path = None) -> Dict[str, str]:
    """Load name mapping from resources/files/name_mapping.json.
    
    Args:
        root_dir: Root directory of the project. If None, uses current working directory.
        
    Returns:
        Dictionary mapping manager names to nicknames. Empty dict if file not found or invalid.
    """
    global _name_mapping_cache
    
    if _name_mapping_cache is not None:
        return _name_mapping_cache
    
    if root_dir is None:
        root_dir = Path.cwd()
    
    name_mapping_file = root_dir / "resources" / "files" / "name_mapping.json"
    
    try:
        if name_mapping_file.exists():
            with open(name_mapping_file, "r", encoding="utf-8") as f:
                _name_mapping_cache = json.load(f)
                logger.debug(f"Loaded name mapping with {len(_name_mapping_cache)} entries")
        else:
            logger.debug("name_mapping.json not found, using original names")
            _name_mapping_cache = {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load name_mapping.json: {e}. Using original names.")
        _name_mapping_cache = {}
    
    return _name_mapping_cache


def get_nickname(manager_name: str, root_dir: Path = None) -> str:
    """Get nickname for a manager name, or return original name if no mapping exists.
    
    Args:
        manager_name: The original manager name
        root_dir: Root directory of the project
        
    Returns:
        Nickname if found in mapping, otherwise the original manager name
    """
    name_mapping = load_name_mapping(root_dir)
    return name_mapping.get(manager_name, manager_name)


def apply_nickname_mapping(manager_str: str, root_dir: Path = None) -> str:
    """Apply nickname mapping to a manager string (which may contain multiple names).
    
    Args:
        manager_str: Manager string (e.g., "John Barnes, Jane Smith")
        root_dir: Root directory of the project
        
    Returns:
        Manager string with nicknames applied where available
    """
    if not manager_str:
        return manager_str
    
    # Split by comma, apply mapping to each name, then rejoin
    names = [name.strip() for name in manager_str.split(",")]
    name_mapping = load_name_mapping(root_dir)
    
    # Debug logging to help identify what names need mapping
    logger.debug(f"Applying nickname mapping to: '{manager_str}'")
    logger.debug(f"Individual names: {names}")
    logger.debug(f"Available mappings: {list(name_mapping.keys())}")
    
    mapped_names = [get_nickname(name, root_dir) for name in names]
    result = ", ".join(mapped_names)
    
    if result != manager_str:
        logger.debug(f"Mapped '{manager_str}' to '{result}'")
    else:
        logger.debug(f"No mapping applied for '{manager_str}'")
    
    return result