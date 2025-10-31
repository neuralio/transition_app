"""
Index registry for managing available vegetation indices
"""

from typing import Dict, Type, List
from .base_index import BaseIndex


class IndexRegistry:
    """
    Registry for managing available vegetation indices.
    
    Provides a centralized way to register, discover, and instantiate
    vegetation indices for the Sentinel-2 processing pipeline.
    """
    
    def __init__(self):
        """Initialize empty registry"""
        self._indices: Dict[str, Type[BaseIndex]] = {}
    
    def register(self, name: str, index_class: Type[BaseIndex]) -> None:
        """
        Register a new index class.
        
        Args:
            name: Name of the index (e.g., 'NDVI')
            index_class: Index class that inherits from BaseIndex
        """
        if not issubclass(index_class, BaseIndex):
            raise ValueError(f"Index class {index_class} must inherit from BaseIndex")
        
        self._indices[name.upper()] = index_class
        print(f"Registered index: {name.upper()}")
    
    def get_index(self, name: str, **kwargs) -> BaseIndex:
        """
        Get an instance of a registered index.
        
        Args:
            name: Name of the index
            **kwargs: Additional arguments to pass to index constructor
            
        Returns:
            Instance of the requested index
            
        Raises:
            KeyError: If index is not registered
        """
        name_upper = name.upper()
        if name_upper not in self._indices:
            raise KeyError(f"Index '{name}' not found. Available indices: {self.list_indices()}")
        
        return self._indices[name_upper](**kwargs)
    
    def list_indices(self) -> List[str]:
        """
        Get list of all registered index names.
        
        Returns:
            List of registered index names
        """
        return list(self._indices.keys())
    
    def is_registered(self, name: str) -> bool:
        """
        Check if an index is registered.
        
        Args:
            name: Name of the index
            
        Returns:
            True if index is registered
        """
        return name.upper() in self._indices
    
    def get_required_bands(self, index_names: List[str]) -> List[str]:
        """
        Get all unique bands required by a list of indices.
        
        Args:
            index_names: List of index names
            
        Returns:
            List of unique required bands
        """
        all_bands = set()
        
        for name in index_names:
            index = self.get_index(name)
            all_bands.update(index.required_bands)
        
        return sorted(list(all_bands))
    
    def calculate_indices(self, ds, index_names: List[str], **kwargs) -> Dict[str, any]:
        """
        Calculate multiple indices from a dataset.
        
        Args:
            ds: xarray Dataset containing Sentinel-2 bands
            index_names: List of index names to calculate
            **kwargs: Additional arguments to pass to specific indices
            
        Returns:
            Dictionary mapping index names to calculated DataArrays
        """
        results = {}
        
        for name in index_names:
            try:
                # Get index-specific kwargs if provided
                index_kwargs = kwargs.get(name.lower(), {})
                index = self.get_index(name, **index_kwargs)
                
                print(f"    Calculating {name}...")
                results[name] = index(ds)
                
            except Exception as e:
                print(f"    ✗ Failed to calculate {name}: {e}")
                results[name] = None
        
        return results