"""
Logging configuration for Sentinel-2 processing pipeline
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union
from datetime import datetime


class PipelineLogger:
    """
    Centralized logging configuration for the Sentinel-2 processing pipeline.
    
    Provides structured logging with file and console outputs,
    progress tracking, and error reporting.
    """
    
    def __init__(self, name: str = "s2_pipeline", log_dir: Optional[Union[str, Path]] = None,
                 level: str = "INFO", console_output: bool = True):
        """
        Initialize pipeline logger.
        
        Args:
            name: Logger name
            log_dir: Directory for log files (if None, only console logging)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to output to console
        """
        self.name = name
        self.log_dir = Path(log_dir) if log_dir else None
        self.level = getattr(logging, level.upper())
        self.console_output = console_output
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Setup handlers
        self._setup_handlers()
        
        self.logger.info(f"Pipeline logger initialized: {name}")
    
    def _setup_handlers(self):
        """Setup logging handlers for file and console output"""
        
        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            
            # Console formatter (simpler format)
            console_format = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
        
        # File handler
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Main log file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = self.log_dir / f"{self.name}_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(self.level)
            
            # File formatter (detailed format)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
            
            # Error log file (only warnings and errors)
            error_file = self.log_dir / f"{self.name}_errors_{timestamp}.log"
            error_handler = logging.FileHandler(error_file)
            error_handler.setLevel(logging.WARNING)
            error_handler.setFormatter(file_format)
            self.logger.addHandler(error_handler)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message)
    
    def log_scene_processing(self, scene_id: str, status: str, details: str = ""):
        """Log scene processing status"""
        message = f"Scene {scene_id}: {status}"
        if details:
            message += f" - {details}"
        
        if status.lower() in ['error', 'failed']:
            self.error(message)
        elif status.lower() in ['warning', 'partial']:
            self.warning(message)
        else:
            self.info(message)
    
    def log_index_calculation(self, index_name: str, scene_id: str, 
                            success: bool, details: str = ""):
        """Log index calculation results"""
        status = "SUCCESS" if success else "FAILED"
        message = f"{index_name} calculation for {scene_id}: {status}"
        if details:
            message += f" - {details}"
        
        if success:
            self.info(message)
        else:
            self.error(message)
    
    def log_temporal_composite(self, index_name: str, period: str, 
                             scenes_count: int, success: bool):
        """Log temporal composite creation"""
        status = "SUCCESS" if success else "FAILED"
        message = f"Temporal composite {index_name} {period}: {status} ({scenes_count} scenes)"
        
        if success:
            self.info(message)
        else:
            self.error(message)
    
    def log_file_operation(self, operation: str, file_path: Union[str, Path], 
                          success: bool, details: str = ""):
        """Log file operations (save, load, etc.)"""
        status = "SUCCESS" if success else "FAILED"
        message = f"File {operation} {file_path}: {status}"
        if details:
            message += f" - {details}"
        
        if success:
            self.debug(message)  # File ops are usually debug level
        else:
            self.error(message)
    
    def log_processing_summary(self, total_scenes: int, successful_scenes: int, 
                             indices_calculated: list, composites_created: int):
        """Log processing session summary"""
        self.info("=== Processing Summary ===")
        self.info(f"Total scenes processed: {successful_scenes}/{total_scenes}")
        self.info(f"Indices calculated: {', '.join(indices_calculated)}")
        self.info(f"Temporal composites created: {composites_created}")
        
        if successful_scenes < total_scenes:
            failed_scenes = total_scenes - successful_scenes
            self.warning(f"{failed_scenes} scenes failed processing")
        
        self.info("=== End Summary ===")
    
    def create_processing_context(self, scene_id: str):
        """Create a context manager for scene processing logging"""
        return ProcessingContext(self, scene_id)


class ProcessingContext:
    """Context manager for logging scene processing operations"""
    
    def __init__(self, logger: PipelineLogger, scene_id: str):
        self.logger = logger
        self.scene_id = scene_id
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting processing: {self.scene_id}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.now() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed processing: {self.scene_id} "
                           f"(Duration: {duration.total_seconds():.1f}s)")
        else:
            self.logger.error(f"Failed processing: {self.scene_id} "
                            f"(Duration: {duration.total_seconds():.1f}s) "
                            f"- Error: {exc_val}")
        
        return False  # Don't suppress exceptions


def setup_pipeline_logging(log_dir: Optional[Union[str, Path]] = None, 
                          level: str = "INFO") -> PipelineLogger:
    """
    Setup standard pipeline logging configuration.
    
    Args:
        log_dir: Directory for log files
        level: Logging level
        
    Returns:
        Configured PipelineLogger instance
    """
    return PipelineLogger(
        name="s2_pipeline",
        log_dir=log_dir,
        level=level,
        console_output=True
    )