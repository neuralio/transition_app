"""
Processing Tracker for Sentinel-2 Pipeline

Provides JSON-based tracking of downloads, products, and processing state
to enable resume functionality and avoid duplicate work.
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, date
import os
import logging


class ProcessingTracker:
    """
    Tracks processing state using JSON metadata files.
    
    Manages download history, product generation, and enables resume functionality
    by maintaining persistent state across pipeline runs.
    """
    
    def __init__(self, metadata_dir: Union[str, Path], logger: Optional[logging.Logger] = None):
        """
        Initialize processing tracker.
        
        Args:
            metadata_dir: Directory to store metadata JSON files
            logger: Optional logger instance
        """
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        
        # Define metadata file paths
        self.download_history_file = self.metadata_dir / "download_history.json"
        self.product_history_file = self.metadata_dir / "product_history.json"
        self.processing_config_file = self.metadata_dir / "processing_config.json"
        self.session_history_file = self.metadata_dir / "session_history.json"
        
        # Load existing metadata
        self.download_history = self._load_json(self.download_history_file, {})
        self.product_history = self._load_json(self.product_history_file, {
            "daily_products": {},
            "temporal_composites": {}
        })
        self.processing_config = self._load_json(self.processing_config_file, {})
        self.session_history = self._load_json(self.session_history_file, [])
        
        self.logger.info(f"ProcessingTracker initialized with metadata dir: {metadata_dir}")
    
    def _load_json(self, file_path: Path, default: Any) -> Any:
        """Load JSON file with fallback to default value"""
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Could not load {file_path}: {e}, using defaults")
        return default
    
    def _save_json(self, data: Any, file_path: Path) -> bool:
        """Save data to JSON file with error handling"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save {file_path}: {e}")
            return False
    
    def _get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get file information for tracking"""
        file_path = Path(file_path)
        try:
            stat = file_path.stat()
            return {
                "exists": True,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(file_path)
            }
        except (OSError, FileNotFoundError):
            return {
                "exists": False,
                "size_mb": 0,
                "modified_time": None,
                "path": str(file_path)
            }
    
    # ==================== DOWNLOAD TRACKING ====================
    
    def is_scene_downloaded(self, scene_id: str, band: str) -> bool:
        """
        Check if a specific band of a scene has been downloaded.
        
        Args:
            scene_id: Sentinel-2 scene identifier (e.g., S2A_34TEK_20250102_0_L2A)
            band: Band name (e.g., B02, B03, SCL)
            
        Returns:
            True if band is downloaded and file exists
        """
        if scene_id not in self.download_history:
            return False
        
        scene_data = self.download_history[scene_id]
        if band not in scene_data.get("bands", {}):
            return False
        
        # Check if marked as complete and file still exists
        if scene_data["bands"][band].get("status") != "complete":
            return False
        
        file_path = scene_data["bands"][band].get("file_path")
        if file_path and Path(file_path).exists():
            return True
        
        # File was marked complete but doesn't exist - mark for re-download
        self.logger.warning(f"Downloaded file missing: {file_path}, marking for re-download")
        scene_data["bands"][band]["status"] = "missing"
        self._save_json(self.download_history, self.download_history_file)
        return False
    
    def mark_download_complete(self, scene_id: str, band: str, file_path: Union[str, Path], 
                             download_time: Optional[datetime] = None) -> None:
        """
        Mark a band download as complete.
        
        Args:
            scene_id: Scene identifier
            band: Band name
            file_path: Path to downloaded file
            download_time: When download completed (defaults to now)
        """
        if scene_id not in self.download_history:
            # Extract metadata from scene_id
            parts = scene_id.split('_')
            self.download_history[scene_id] = {
                "tile": parts[1] if len(parts) > 1 else "unknown",
                "date": parts[2] if len(parts) > 2 else "unknown",
                "sensor": parts[0] if len(parts) > 0 else "unknown",
                "bands": {},
                "processing_level": parts[4] if len(parts) > 4 else "L2A"
            }
        
        file_info = self._get_file_info(file_path)
        
        self.download_history[scene_id]["bands"][band] = {
            "status": "complete",
            "download_time": (download_time or datetime.now()).isoformat(),
            "file_path": str(file_path),
            "file_size_mb": file_info["size_mb"],
            "file_exists": file_info["exists"]
        }
        
        self._save_json(self.download_history, self.download_history_file)
        self.logger.debug(f"Marked download complete: {scene_id}/{band}")
    
    def mark_download_failed(self, scene_id: str, band: str, error: str) -> None:
        """Mark a band download as failed"""
        if scene_id not in self.download_history:
            self.download_history[scene_id] = {"bands": {}}
        
        self.download_history[scene_id]["bands"][band] = {
            "status": "failed",
            "error": error,
            "failed_time": datetime.now().isoformat(),
            "retry_count": self.download_history[scene_id]["bands"].get(band, {}).get("retry_count", 0) + 1
        }
        
        self._save_json(self.download_history, self.download_history_file)
        self.logger.warning(f"Marked download failed: {scene_id}/{band} - {error}")
    
    # ==================== PRODUCT TRACKING ====================
    
    def is_product_complete(self, date: str, product_type: str, index_name: Optional[str] = None) -> bool:
        """
        Check if a product has been generated for a specific date.
        
        Args:
            date: Date string (YYYYMMDD format)
            product_type: Type of product ('mosaic', 'rgb', 'indices', 'cloud_free')
            index_name: For indices, specify which index (NDVI, EVI, SAVI)
            
        Returns:
            True if product exists and file is valid
        """
        if date not in self.product_history["daily_products"]:
            return False
        
        date_products = self.product_history["daily_products"][date]
        
        if product_type == "indices" and index_name:
            product_data = date_products.get("indices", {}).get(index_name, {})
        else:
            product_data = date_products.get(product_type, {})
        
        if not isinstance(product_data, dict) or product_data.get("status") != "complete":
            return False
        
        # Validate file still exists
        file_path = product_data.get("file_path")
        if file_path and Path(file_path).exists():
            return True
        
        # File was marked complete but doesn't exist - mark for re-generation
        self.logger.warning(f"Product file missing: {file_path}, marking for re-generation")
        if product_type == "indices" and index_name:
            date_products.setdefault("indices", {})[index_name] = {"status": "missing"}
        else:
            date_products[product_type] = {"status": "missing"}
        
        self._save_json(self.product_history, self.product_history_file)
        return False
    
    def mark_product_complete(self, date: str, product_type: str, file_path: Union[str, Path],
                            index_name: Optional[str] = None, generation_time: Optional[datetime] = None) -> None:
        """
        Mark a product as complete.
        
        Args:
            date: Date string (YYYYMMDD)
            product_type: Product type
            file_path: Path to generated file
            index_name: Index name for indices
            generation_time: When product was generated
        """
        if date not in self.product_history["daily_products"]:
            self.product_history["daily_products"][date] = {}
        
        date_products = self.product_history["daily_products"][date]
        file_info = self._get_file_info(file_path)
        
        product_data = {
            "status": "complete",
            "generation_time": (generation_time or datetime.now()).isoformat(),
            "file_path": str(file_path),
            "file_size_mb": file_info["size_mb"],
            "file_exists": file_info["exists"]
        }
        
        if product_type == "indices" and index_name:
            if "indices" not in date_products:
                date_products["indices"] = {}
            date_products["indices"][index_name] = product_data
        else:
            date_products[product_type] = product_data
        
        self._save_json(self.product_history, self.product_history_file)
        self.logger.debug(f"Marked product complete: {date}/{product_type}" + 
                         (f"/{index_name}" if index_name else ""))
    
    # ==================== TEMPORAL COMPOSITE TRACKING ====================
    
    def is_temporal_composite_complete(self, index_name: str, rule: str, reducer: str,
                                     start_date: str, end_date: str) -> bool:
        """
        Check if a temporal composite has been generated.
        
        Args:
            index_name: Index name (NDVI, EVI, SAVI)
            rule: Temporal rule (10D, 16D)
            reducer: Reduction method (max, median, mean)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            
        Returns:
            True if composite exists and is valid
        """
        composite_key = f"{index_name}_{rule}_{reducer}_{start_date}_{end_date}"
        
        if composite_key not in self.product_history["temporal_composites"]:
            return False
        
        composite_data = self.product_history["temporal_composites"][composite_key]
        
        if composite_data.get("status") != "complete":
            return False
        
        # Validate file exists
        file_path = composite_data.get("file_path")
        if file_path and Path(file_path).exists():
            return True
        
        # Mark for re-generation
        self.logger.warning(f"Composite file missing: {file_path}, marking for re-generation")
        composite_data["status"] = "missing"
        self._save_json(self.product_history, self.product_history_file)
        return False
    
    def mark_temporal_composite_complete(self, index_name: str, rule: str, reducer: str,
                                       start_date: str, end_date: str, file_path: Union[str, Path],
                                       generation_time: Optional[datetime] = None) -> None:
        """Mark a temporal composite as complete"""
        composite_key = f"{index_name}_{rule}_{reducer}_{start_date}_{end_date}"
        file_info = self._get_file_info(file_path)
        
        self.product_history["temporal_composites"][composite_key] = {
            "status": "complete",
            "index_name": index_name,
            "rule": rule,
            "reducer": reducer,
            "start_date": start_date,
            "end_date": end_date,
            "generation_time": (generation_time or datetime.now()).isoformat(),
            "file_path": str(file_path),
            "file_size_mb": file_info["size_mb"],
            "file_exists": file_info["exists"]
        }
        
        self._save_json(self.product_history, self.product_history_file)
        self.logger.debug(f"Marked temporal composite complete: {composite_key}")
    
    # ==================== VALIDATION AND RESUME LOGIC ====================
    
    def validate_existing_files(self, output_dir: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate existing files against metadata and scan for untracked files.
        
        Args:
            output_dir: Base output directory to scan
            
        Returns:
            Validation report with statistics and issues found
        """
        output_dir = Path(output_dir)
        report = {
            "scanned_time": datetime.now().isoformat(),
            "total_tracked_downloads": 0,
            "valid_downloads": 0,
            "missing_downloads": 0,
            "total_tracked_products": 0,
            "valid_products": 0,
            "missing_products": 0,
            "untracked_files": [],
            "issues": []
        }
        
        # Validate downloads
        for scene_id, scene_data in self.download_history.items():
            for band, band_data in scene_data.get("bands", {}).items():
                report["total_tracked_downloads"] += 1
                
                if band_data.get("status") == "complete":
                    file_path = band_data.get("file_path")
                    if file_path and Path(file_path).exists():
                        report["valid_downloads"] += 1
                    else:
                        report["missing_downloads"] += 1
                        report["issues"].append(f"Missing download: {scene_id}/{band} at {file_path}")
        
        # Validate daily products
        for date, date_products in self.product_history["daily_products"].items():
            for product_type, product_data in date_products.items():
                if product_type == "indices":
                    for index_name, index_data in product_data.items():
                        report["total_tracked_products"] += 1
                        self._validate_product_file(index_data, f"{date}/{product_type}/{index_name}", report)
                else:
                    report["total_tracked_products"] += 1
                    self._validate_product_file(product_data, f"{date}/{product_type}", report)
        
        # Validate temporal composites
        for composite_key, composite_data in self.product_history["temporal_composites"].items():
            report["total_tracked_products"] += 1
            self._validate_product_file(composite_data, f"composite/{composite_key}", report)
        
        self.logger.info(f"Validation complete: {report['valid_downloads']}/{report['total_tracked_downloads']} downloads valid, "
                        f"{report['valid_products']}/{report['total_tracked_products']} products valid")
        
        return report
    
    def _validate_product_file(self, product_data: Dict, product_id: str, report: Dict) -> None:
        """Helper to validate a single product file"""
        if not isinstance(product_data, dict):
            return
            
        if product_data.get("status") == "complete":
            file_path = product_data.get("file_path")
            if file_path and Path(file_path).exists():
                report["valid_products"] += 1
            else:
                report["missing_products"] += 1
                report["issues"].append(f"Missing product: {product_id} at {file_path}")
    
    def get_resume_summary(self, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate a summary of what can be resumed vs what needs processing.
        
        Args:
            config: Current processing configuration for comparison
            
        Returns:
            Resume summary with statistics and recommendations
        """
        summary = {
            "generated_time": datetime.now().isoformat(),
            "downloads": {
                "total_scenes": len(self.download_history),
                "complete_scenes": 0,
                "partial_scenes": 0,
                "failed_scenes": 0,
                "total_bands": 0,
                "complete_bands": 0
            },
            "products": {
                "total_dates": len(self.product_history["daily_products"]),
                "complete_dates": 0,
                "partial_dates": 0,
                "total_products": 0,
                "complete_products": 0
            },
            "temporal_composites": {
                "total_composites": len(self.product_history["temporal_composites"]),
                "complete_composites": 0
            },
            "estimated_time_savings": "Unknown",
            "config_drift": False,
            "recommendations": []
        }
        
        # Analyze downloads
        for scene_id, scene_data in self.download_history.items():
            bands = scene_data.get("bands", {})
            complete_bands = sum(1 for b in bands.values() if b.get("status") == "complete")
            failed_bands = sum(1 for b in bands.values() if b.get("status") == "failed")
            
            summary["downloads"]["total_bands"] += len(bands)
            summary["downloads"]["complete_bands"] += complete_bands
            
            if complete_bands == len(bands) and len(bands) > 0:
                summary["downloads"]["complete_scenes"] += 1
            elif complete_bands > 0:
                summary["downloads"]["partial_scenes"] += 1
            elif failed_bands > 0:
                summary["downloads"]["failed_scenes"] += 1
        
        # Analyze products
        for date, date_products in self.product_history["daily_products"].items():
            total_products = 0
            complete_products = 0
            
            for product_type, product_data in date_products.items():
                if product_type == "indices":
                    for index_data in product_data.values():
                        total_products += 1
                        if isinstance(index_data, dict) and index_data.get("status") == "complete":
                            complete_products += 1
                else:
                    total_products += 1
                    if isinstance(product_data, dict) and product_data.get("status") == "complete":
                        complete_products += 1
            
            summary["products"]["total_products"] += total_products
            summary["products"]["complete_products"] += complete_products
            
            if total_products > 0:
                if complete_products == total_products:
                    summary["products"]["complete_dates"] += 1
                elif complete_products > 0:
                    summary["products"]["partial_dates"] += 1
        
        # Analyze temporal composites
        summary["temporal_composites"]["complete_composites"] = sum(
            1 for comp in self.product_history["temporal_composites"].values()
            if isinstance(comp, dict) and comp.get("status") == "complete"
        )
        
        # Check for configuration drift
        if config and self.processing_config:
            if self._has_config_drift(config):
                summary["config_drift"] = True
                summary["recommendations"].append("Configuration has changed - some products may need regeneration")
        
        # Generate recommendations
        if summary["downloads"]["failed_scenes"] > 0:
            summary["recommendations"].append(f"Retry {summary['downloads']['failed_scenes']} failed scene downloads")
        
        skip_ratio = (summary["products"]["complete_products"] / 
                     max(summary["products"]["total_products"], 1))
        if skip_ratio > 0.5:
            summary["recommendations"].append(f"Significant progress exists ({skip_ratio:.1%} products complete)")
            summary["estimated_time_savings"] = f"{skip_ratio:.1%} processing time saved"
        
        return summary
    
    def _has_config_drift(self, current_config: Dict) -> bool:
        """Check if configuration has changed significantly"""
        if not self.processing_config:
            return False
        
        # Check important parameters that would require re-processing
        important_keys = [
            "indices_to_calculate", "temporal_rule", "temporal_reducer",
            "create_rgb", "create_cloud_masked_products", "target_crs"
        ]
        
        for key in important_keys:
            if current_config.get(key) != self.processing_config.get(key):
                self.logger.warning(f"Config drift detected: {key} changed from "
                                  f"{self.processing_config.get(key)} to {current_config.get(key)}")
                return True
        
        return False
    
    # ==================== SESSION MANAGEMENT ====================
    
    def start_processing_session(self, config: Dict) -> str:
        """
        Start a new processing session.
        
        Args:
            config: Processing configuration
            
        Returns:
            Session ID
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        session_data = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "config": config,
            "initial_state": {
                "total_downloads": len(self.download_history),
                "total_daily_products": len(self.product_history["daily_products"]),
                "total_composites": len(self.product_history["temporal_composites"])
            }
        }
        
        self.session_history.append(session_data)
        
        # Update processing config
        self.processing_config = config.copy()
        self._save_json(self.processing_config, self.processing_config_file)
        
        self.logger.info(f"Started processing session: {session_id}")
        return session_id
    
    def end_processing_session(self, session_id: str, success: bool = True, error: Optional[str] = None) -> None:
        """End a processing session"""
        for session in reversed(self.session_history):
            if session.get("session_id") == session_id:
                session["end_time"] = datetime.now().isoformat()
                session["success"] = success
                session["final_state"] = {
                    "total_downloads": len(self.download_history),
                    "total_daily_products": len(self.product_history["daily_products"]),
                    "total_composites": len(self.product_history["temporal_composites"])
                }
                if error:
                    session["error"] = error
                break
        
        self._save_json(self.session_history, self.session_history_file)
        self.logger.info(f"Ended processing session: {session_id} (success: {success})")
    
    # ==================== UTILITIES ====================
    
    def cleanup_metadata(self, keep_sessions: int = 10) -> None:
        """Clean up old metadata to keep files manageable"""
        # Keep only recent sessions
        if len(self.session_history) > keep_sessions:
            self.session_history = self.session_history[-keep_sessions:]
            self._save_json(self.session_history, self.session_history_file)
        
        # Remove failed/incomplete entries older than 7 days
        cutoff_time = datetime.now().timestamp() - (7 * 24 * 3600)  # 7 days ago
        
        # Clean download history
        to_remove = []
        for scene_id, scene_data in self.download_history.items():
            bands_to_remove = []
            for band, band_data in scene_data.get("bands", {}).items():
                if band_data.get("status") in ["failed", "missing"]:
                    try:
                        failed_time = datetime.fromisoformat(band_data.get("failed_time", "")).timestamp()
                        if failed_time < cutoff_time:
                            bands_to_remove.append(band)
                    except (ValueError, TypeError):
                        bands_to_remove.append(band)  # Remove invalid entries
            
            for band in bands_to_remove:
                del scene_data["bands"][band]
            
            if not scene_data.get("bands"):
                to_remove.append(scene_id)
        
        for scene_id in to_remove:
            del self.download_history[scene_id]
        
        if to_remove or any(scene_data.get("bands") for scene_data in self.download_history.values()):
            self._save_json(self.download_history, self.download_history_file)
        
        self.logger.info(f"Metadata cleanup completed: removed {len(to_remove)} old entries")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about tracked processing"""
        stats = {
            "metadata_files": {
                "download_history_size": self.download_history_file.stat().st_size if self.download_history_file.exists() else 0,
                "product_history_size": self.product_history_file.stat().st_size if self.product_history_file.exists() else 0,
                "session_count": len(self.session_history)
            },
            "downloads": {
                "total_scenes": len(self.download_history),
                "total_band_downloads": sum(len(scene.get("bands", {})) for scene in self.download_history.values()),
                "successful_downloads": sum(
                    sum(1 for band in scene.get("bands", {}).values() if band.get("status") == "complete")
                    for scene in self.download_history.values()
                ),
                "failed_downloads": sum(
                    sum(1 for band in scene.get("bands", {}).values() if band.get("status") == "failed")
                    for scene in self.download_history.values()
                )
            },
            "products": {
                "daily_dates": len(self.product_history["daily_products"]),
                "temporal_composites": len(self.product_history["temporal_composites"]),
                "total_products": (
                    sum(
                        len(date_prods.get("indices", {})) + 
                        sum(1 for k, v in date_prods.items() if k != "indices" and isinstance(v, dict))
                        for date_prods in self.product_history["daily_products"].values()
                    ) + len(self.product_history["temporal_composites"])
                )
            }
        }
        
        return stats