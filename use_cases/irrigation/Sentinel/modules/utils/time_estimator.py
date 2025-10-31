"""
Time estimation and progress tracking utilities for Sentinel-2 pipeline
"""

import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ProcessingStats:
    """Statistics for processing progress and time estimation"""
    
    # Overall pipeline stats
    total_scenes: int = 0
    completed_scenes: int = 0
    failed_scenes: int = 0
    
    # Download tracking
    total_downloads: int = 0
    completed_downloads: int = 0
    failed_downloads: int = 0
    total_download_size_mb: float = 0.0
    downloaded_size_mb: float = 0.0
    
    # Processing tracking
    total_products: int = 0
    completed_products: int = 0
    
    # Timing
    start_time: float = field(default_factory=time.time)
    download_times: List[float] = field(default_factory=list)
    processing_times: List[float] = field(default_factory=list)
    
    # Speed tracking
    avg_download_speed_mbps: float = 0.0
    avg_processing_time_per_scene: float = 0.0


class TimeEstimator:
    """
    Provides time estimation and progress tracking for the Sentinel-2 pipeline.
    
    Tracks download speeds, processing times, and provides ETA calculations.
    """
    
    def __init__(self):
        """Initialize time estimator"""
        self.stats = ProcessingStats()
        self.phase_start_time = time.time()
        self.current_phase = "initialization"
        
    def start_pipeline(self, total_scenes: int, total_downloads: int = None):
        """
        Initialize pipeline timing with total expected work.
        
        Args:
            total_scenes: Total number of scenes to process
            total_downloads: Total number of files to download (estimated)
        """
        self.stats.start_time = time.time()
        self.stats.total_scenes = total_scenes
        self.stats.total_downloads = total_downloads or (total_scenes * 5)  # Estimate 5 bands per scene
        self.current_phase = "downloading"
        
        print(f"🕐 Pipeline started at {datetime.now().strftime('%H:%M:%S')}")
        print(f"📊 Processing {total_scenes} scenes ({self.stats.total_downloads} estimated downloads)")
        
    def start_phase(self, phase_name: str):
        """Start a new processing phase"""
        self.current_phase = phase_name
        self.phase_start_time = time.time()
        
    def record_download(self, size_mb: float, duration_seconds: float, success: bool = True):
        """
        Record a completed download for speed tracking.
        
        Args:
            size_mb: Size of downloaded file in MB
            duration_seconds: Time taken to download
            success: Whether download was successful
        """
        if success:
            self.stats.completed_downloads += 1
            self.stats.downloaded_size_mb += size_mb
            self.stats.download_times.append(duration_seconds)
            
            # Update download speed (rolling average)
            if duration_seconds > 0:
                speed_mbps = size_mb / duration_seconds
                if self.stats.avg_download_speed_mbps == 0:
                    self.stats.avg_download_speed_mbps = speed_mbps
                else:
                    # Exponential moving average
                    alpha = 0.2
                    self.stats.avg_download_speed_mbps = (
                        alpha * speed_mbps + (1 - alpha) * self.stats.avg_download_speed_mbps
                    )
        else:
            self.stats.failed_downloads += 1
            
    def record_scene_completion(self, processing_time: float, products_created: int, success: bool = True):
        """
        Record completion of a scene.
        
        Args:
            processing_time: Time taken to process scene (seconds)
            products_created: Number of products created from scene
            success: Whether scene processing was successful
        """
        if success:
            self.stats.completed_scenes += 1
            self.stats.completed_products += products_created
            self.stats.processing_times.append(processing_time)
            
            # Update average processing time
            if self.stats.processing_times:
                self.stats.avg_processing_time_per_scene = sum(self.stats.processing_times) / len(self.stats.processing_times)
        else:
            self.stats.failed_scenes += 1
            
    def get_eta(self) -> Optional[Dict[str, str]]:
        """
        Calculate estimated time to completion.
        
        Returns:
            Dictionary with ETA information or None if insufficient data
        """
        if self.stats.completed_scenes == 0:
            return None
            
        elapsed_time = time.time() - self.stats.start_time
        remaining_scenes = self.stats.total_scenes - self.stats.completed_scenes
        
        if remaining_scenes <= 0:
            return {
                'eta': 'Complete',
                'elapsed': self._format_duration(elapsed_time),
                'total_estimated': self._format_duration(elapsed_time)
            }
        
        # Estimate based on average processing time per scene
        if self.stats.avg_processing_time_per_scene > 0:
            estimated_remaining_seconds = remaining_scenes * self.stats.avg_processing_time_per_scene
            total_estimated_seconds = elapsed_time + estimated_remaining_seconds
            
            eta_time = datetime.now() + timedelta(seconds=estimated_remaining_seconds)
            
            return {
                'eta': eta_time.strftime('%H:%M:%S'),
                'eta_in': self._format_duration(estimated_remaining_seconds),
                'elapsed': self._format_duration(elapsed_time),
                'total_estimated': self._format_duration(total_estimated_seconds),
                'progress_percent': (self.stats.completed_scenes / self.stats.total_scenes) * 100
            }
        
        return None
    
    def get_progress_summary(self) -> str:
        """
        Get a formatted progress summary string.
        
        Returns:
            Formatted progress summary
        """
        elapsed = time.time() - self.stats.start_time
        
        # Basic progress
        scene_progress = f"{self.stats.completed_scenes}/{self.stats.total_scenes}"
        if self.stats.total_scenes > 0:
            scene_percent = (self.stats.completed_scenes / self.stats.total_scenes) * 100
            scene_progress += f" ({scene_percent:.1f}%)"
        
        # Download progress
        download_progress = f"{self.stats.completed_downloads}/{self.stats.total_downloads}"
        if self.stats.total_downloads > 0:
            download_percent = (self.stats.completed_downloads / self.stats.total_downloads) * 100
            download_progress += f" ({download_percent:.1f}%)"
            
        # Speed info
        speed_info = ""
        if self.stats.avg_download_speed_mbps > 0:
            speed_info = f" • {self.stats.avg_download_speed_mbps:.1f} MB/s"
            
        # ETA info
        eta_info = ""
        eta = self.get_eta()
        if eta and 'eta_in' in eta:
            eta_info = f" • ETA: {eta['eta_in']}"
        
        summary = (
            f"📈 Progress: {scene_progress} scenes • "
            f"{download_progress} downloads{speed_info}{eta_info} • "
            f"Elapsed: {self._format_duration(elapsed)}"
        )
        
        if self.stats.failed_scenes > 0 or self.stats.failed_downloads > 0:
            summary += f" • ⚠️ Failures: {self.stats.failed_scenes} scenes, {self.stats.failed_downloads} downloads"
            
        return summary
    
    def print_progress(self):
        """Print current progress to console"""
        progress_msg = self.get_progress_summary()
        # Use stderr to avoid Dask output capture issues
        import sys
        print(f"\n{progress_msg}", file=sys.stderr)
        sys.stderr.flush()
        # Also try stdout
        print(f"\n{progress_msg}")
        sys.stdout.flush()
        
    def print_final_summary(self):
        """Print final pipeline completion summary"""
        elapsed = time.time() - self.stats.start_time
        
        print("\n" + "="*60)
        print("🎯 PIPELINE COMPLETION SUMMARY")
        print("="*60)
        print(f"⏱️  Total Time: {self._format_duration(elapsed)}")
        print(f"📊 Scenes: {self.stats.completed_scenes} completed, {self.stats.failed_scenes} failed")
        print(f"⬇️  Downloads: {self.stats.completed_downloads} completed, {self.stats.failed_downloads} failed")
        print(f"📦 Products: {self.stats.completed_products} created")
        
        if self.stats.downloaded_size_mb > 0:
            print(f"💾 Data Downloaded: {self.stats.downloaded_size_mb:.1f} MB")
            
        if self.stats.avg_download_speed_mbps > 0:
            print(f"🚀 Average Download Speed: {self.stats.avg_download_speed_mbps:.1f} MB/s")
            
        if self.stats.avg_processing_time_per_scene > 0:
            print(f"⚡ Average Processing Time: {self.stats.avg_processing_time_per_scene:.1f}s per scene")
            
        # Success rate
        if self.stats.total_scenes > 0:
            success_rate = (self.stats.completed_scenes / self.stats.total_scenes) * 100
            print(f"✅ Success Rate: {success_rate:.1f}%")
            
        print("="*60)
        
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"