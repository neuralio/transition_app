"""
Configuration management for Sentinel-2 processing pipeline
"""

from typing import Dict, Any, List, Union, Optional
from pathlib import Path
import json
import yaml
from dataclasses import dataclass, asdict
from datetime import date


@dataclass
class ProcessingConfig:
    """Configuration class for Sentinel-2 processing parameters"""
    
    # Spatial parameters
    bbox: List[float]  # [minx, miny, maxx, maxy] 
    target_crs: str = "EPSG:4326"
    aoi: Optional[str] = None  # Path to AOI file (GeoJSON/Shapefile)
    
    # Temporal parameters
    start_date: str = "2024-01-01"
    end_date: Optional[str] = None  # None means use today's date
    max_scenes: int = 50
    
    # Processing parameters
    cloud_cover_threshold: float = 80.0
    ignore_cloud_filter: bool = True
    
    # Output parameters
    output_dir: str = "data"
    compress: str = "lzw"
    
    # STAC Configuration
    stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    
    # Index parameters
    indices_to_calculate: List[str] = None
    temporal_compositing: bool = True
    temporal_rule: str = "10D"  # 10-day dekadal
    temporal_reducer: str = "max"
    
    # Processing options
    create_rgb: bool = True
    create_cloud_masked_products: bool = True
    save_individual_bands: bool = False
    
    def __post_init__(self):
        """Initialize default values after instantiation"""
        if self.indices_to_calculate is None:
            self.indices_to_calculate = ["NDVI", "EVI", "SAVI"]
        
        # Set end_date to today if None
        if self.end_date is None:
            self.end_date = date.today().strftime('%Y-%m-%d')


class ConfigManager:
    """
    Configuration manager for Sentinel-2 processing pipeline.
    
    Handles loading, saving, and validating configuration parameters
    from various sources (JSON, YAML, environment variables).
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (JSON or YAML)
        """
        self.config_file = Path(config_file) if config_file else None
        self.config = ProcessingConfig(bbox=[22.0, 40.5, 22.8, 40.9])  # Default Neuralio bbox
        
        if self.config_file and self.config_file.exists():
            self.load_config()
    
    def load_config(self, config_file: Optional[Union[str, Path]] = None) -> ProcessingConfig:
        """
        Load configuration from file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Loaded configuration
        """
        if config_file:
            self.config_file = Path(config_file)
        
        if not self.config_file or not self.config_file.exists():
            print(f"Configuration file not found: {self.config_file}")
            return self.config
        
        try:
            with open(self.config_file, 'r') as f:
                if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                    config_dict = yaml.safe_load(f)
                else:
                    config_dict = json.load(f)
            
            # Handle None values in config (especially for end_date)
            if config_dict.get('end_date') is None:
                config_dict['end_date'] = None  # Ensure it's explicitly None
            
            # Update configuration with loaded values
            self.update_config(config_dict)
            print(f"Configuration loaded from {self.config_file}")
            
            # Apply post-init logic after loading to handle None end_date
            self.config.__post_init__()
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
        
        return self.config
    
    def save_config(self, config_file: Optional[Union[str, Path]] = None, 
                   format: str = 'json') -> bool:
        """
        Save configuration to file.
        
        Args:
            config_file: Path to save configuration
            format: File format ('json' or 'yaml')
            
        Returns:
            True if successful
        """
        if config_file:
            self.config_file = Path(config_file)
        elif not self.config_file:
            self.config_file = Path(f"s2_config.{format}")
        
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_dict, f, indent=2)
            
            print(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values, handling parameter aliases.
        
        Args:
            updates: Dictionary of configuration updates
        """
        # Handle parameter aliases for backward compatibility
        parameter_aliases = {
            'date_start': 'start_date',
            'cloud_pct': 'cloud_cover_threshold', 
            'outdir': 'output_dir',
            'indices': 'indices_to_calculate',
            'temporal': 'temporal_compositing',
            'interval': 'temporal_rule',
            'reducer': 'temporal_reducer'
        }
        
        for key, value in updates.items():
            # Use alias if it exists, otherwise use original key
            config_key = parameter_aliases.get(key, key)
            
            if hasattr(self.config, config_key):
                setattr(self.config, config_key, value)
            else:
                print(f"Warning: Unknown configuration parameter: {key} (mapped to {config_key})")
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration parameters.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate bbox
        if len(self.config.bbox) != 4:
            errors.append("bbox must have exactly 4 values [minx, miny, maxx, maxy]")
        elif self.config.bbox[0] >= self.config.bbox[2] or self.config.bbox[1] >= self.config.bbox[3]:
            errors.append("Invalid bbox: min values must be less than max values")
        
        # Validate dates
        try:
            from datetime import datetime
            datetime.strptime(self.config.start_date, '%Y-%m-%d')
            datetime.strptime(self.config.end_date, '%Y-%m-%d')
        except ValueError:
            errors.append("Dates must be in YYYY-MM-DD format")
        
        # Validate numeric ranges
        if not 0 <= self.config.cloud_cover_threshold <= 100:
            errors.append("cloud_cover_threshold must be between 0 and 100")
        
        if self.config.max_scenes < 0:
            errors.append("max_scenes must be non-negative (0 = all scenes)")
        
        # Validate temporal parameters
        if self.config.temporal_rule not in ['10D', '16D']:
            errors.append("temporal_rule must be '10D' or '16D'")
        
        if self.config.temporal_reducer not in ['max', 'mean', 'median']:
            errors.append("temporal_reducer must be 'max', 'mean', or 'median'")
        
        # Validate indices
        valid_indices = ['NDVI', 'EVI', 'SAVI', 'NDWI']
        for index in self.config.indices_to_calculate:
            if index not in valid_indices:
                errors.append(f"Unknown index: {index}. Valid indices: {valid_indices}")
        
        return errors
    
    def get_bbox_wkt(self) -> str:
        """
        Get bounding box as WKT POLYGON.
        
        Returns:
            WKT polygon string
        """
        minx, miny, maxx, maxy = self.config.bbox
        return f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
    
    def get_output_paths(self) -> Dict[str, Path]:
        """
        Get standardized output paths with separate directories per product type.
        
        Returns:
            Dictionary of output paths
        """
        base_dir = Path(self.config.output_dir)
        
        paths = {
            'base': base_dir,
            'products': base_dir / 'products',
            'intermediate': base_dir / 'intermediate',
            'raw': base_dir / 'raw',
            'metadata': base_dir / 'metadata',
            'logs': base_dir / 'logs',
            
            # RGB products
            'rgb_daily': base_dir / 'products' / 'rgb' / 'daily',
            
            # Each index gets its own directory
            'ndvi_daily': base_dir / 'products' / 'ndvi' / 'daily',
            'evi_daily': base_dir / 'products' / 'evi' / 'daily',
            'savi_daily': base_dir / 'products' / 'savi' / 'daily',
            'ndwi_daily': base_dir / 'products' / 'ndwi' / 'daily',
            
            # Unified temporal composites for all indices
            'indices_dekadal': base_dir / 'products' / 'indices' / 'dekadal',
            
            # Cloud-free products
            'cloud_free_daily': base_dir / 'products' / 'cloud_free' / 'daily',
            
            # Individual bands (if enabled)
            'bands': base_dir / 'products' / 'bands' / 'daily' if self.config.save_individual_bands else None,
            
            # Mosaics moved to products folder
            'mosaics_daily': base_dir / 'products' / 'mosaics' / 'daily'
        }
        
        return paths
    
    def create_output_directories(self) -> Dict[str, Path]:
        """
        Create all required output directories with separate structure per product type.
        
        Returns:
            Dictionary of created directory paths
        """
        paths = self.get_output_paths()
        
        # Create all directories (skip None paths)
        for key, path in paths.items():
            if path is not None:
                path.mkdir(parents=True, exist_ok=True)
        
        print(f"Created product-specific directory structure in {paths['base']}")
        print(f"  - RGB daily: {paths['rgb_daily']}")
        print(f"  - NDVI daily: {paths['ndvi_daily']}")
        print(f"  - EVI daily: {paths['evi_daily']}")
        print(f"  - SAVI daily: {paths['savi_daily']}")
        print(f"  - NDWI daily: {paths['ndwi_daily']}")
        print(f"  - Indices temporal dekadal: {paths['indices_dekadal']}")
        print(f"  - Cloud-free daily: {paths['cloud_free_daily']}")
        print(f"  - Mosaics daily: {paths['mosaics_daily']}")
        if paths['bands']:
            print(f"  - Individual bands: {paths['bands']}")
        
        return paths
    
    def print_config(self) -> None:
        """Print current configuration in a readable format"""
        print("\n=== Sentinel-2 Processing Configuration ===")
        print(f"Bounding Box: {self.config.bbox}")
        print(f"Date Range: {self.config.start_date} to {self.config.end_date}")
        print(f"Max Scenes: {self.config.max_scenes}")
        print(f"Cloud Cover Threshold: {self.config.cloud_cover_threshold}%")
        print(f"Ignore Cloud Filter: {self.config.ignore_cloud_filter}")
        print(f"Output Directory: {self.config.output_dir}")
        print(f"Indices: {', '.join(self.config.indices_to_calculate)}")
        print(f"Temporal Compositing: {self.config.temporal_compositing} ({self.config.temporal_rule} {self.config.temporal_reducer})")
        print(f"Create RGB: {self.config.create_rgb}")
        print(f"Create Cloud-Masked Products: {self.config.create_cloud_masked_products}")
        print(f"Save Individual Bands: {self.config.save_individual_bands}")
        print("=" * 45)