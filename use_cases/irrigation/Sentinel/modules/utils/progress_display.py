"""
Real-time progress display utilities for Sentinel-2 pipeline downloads
"""

import sys
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class DownloadStatus(Enum):
    """Download status states"""
    PENDING = "pending"
    DOWNLOADING = "downloading" 
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadItem:
    """Individual download tracking item"""
    scene_id: str
    band: str
    status: DownloadStatus = DownloadStatus.PENDING
    file_size_mb: Optional[float] = None
    error_msg: Optional[str] = None
    line_number: Optional[int] = None
    
    @property
    def display_name(self) -> str:
        """Get shortened display name for the download"""
        # Extract tile from scene_id (e.g., S2B_34TEK_20250102_0_L2A -> 34TEK)
        parts = self.scene_id.split('_')
        if len(parts) >= 2:
            tile = parts[1]
            sensor = parts[0]
            return f"{sensor}_{tile}_{self.band}"
        return f"{self.scene_id[:15]}_{self.band}"
    
    def get_display_line(self) -> str:
        """Get the formatted display line for this download"""
        name = self.display_name
        
        if self.status == DownloadStatus.PENDING:
            return f"⏳ {name}"
        elif self.status == DownloadStatus.DOWNLOADING:
            return f"⬇️ {name}"
        elif self.status == DownloadStatus.COMPLETED:
            size_str = f"({self.file_size_mb:.1f}MB)" if self.file_size_mb else "(Downloaded)"
            return f"✅ {name} {size_str}"
        elif self.status == DownloadStatus.FAILED:
            error_str = f"({self.error_msg})" if self.error_msg else "(Failed)"
            return f"❌ {name} {error_str}"


class DownloadProgressTracker:
    """
    Real-time progress tracker for parallel downloads.
    
    Uses ANSI escape codes to update download status in place,
    creating a clean, monitor-friendly display.
    """
    
    def __init__(self, date_str: str, scene_info: List[str]):
        """
        Initialize progress tracker.
        
        Args:
            date_str: Date being processed (e.g., "20250102")
            scene_info: List of scene identifiers (e.g., ["S2B_34TEK", "S2B_34TFL"])
        """
        self.date_str = date_str
        self.scene_info = scene_info
        self.downloads: Dict[str, DownloadItem] = {}
        self.display_active = False
        self.header_lines = 0
        self.lock = threading.Lock()
        
        # ANSI escape codes
        self.CURSOR_UP = '\033[A'
        self.CLEAR_LINE = '\033[2K'
        self.CURSOR_TO_START = '\r'
        
    def add_download(self, scene_id: str, band: str) -> str:
        """
        Add a download to track.
        
        Args:
            scene_id: Full scene identifier
            band: Band name (e.g., "B02", "SCL")
            
        Returns:
            Unique key for this download
        """
        key = f"{scene_id}_{band}"
        with self.lock:
            self.downloads[key] = DownloadItem(scene_id, band)
        return key
    
    def start_display(self):
        """Initialize the progress display"""
        with self.lock:
            if self.display_active:
                return
                
            # Print header information
            total_downloads = len(self.downloads)
            scenes_str = ', '.join(self.scene_info)
            bands_per_scene = total_downloads // len(self.scene_info) if self.scene_info else 0
            
            print(f"📡 Downloading {total_downloads} files for {self.date_str}")
            print(f"🗺️  Scenes: {scenes_str} ({len(self.scene_info)} scenes × {bands_per_scene} bands)")
            print()  # Empty line for separation
            
            self.header_lines = 3
            
            # Print initial status for all downloads
            line_number = 0
            for key, download in self.downloads.items():
                download.line_number = line_number
                print(download.get_display_line())
                line_number += 1
            
            # Print summary line
            print()  # Empty line
            print(self._get_summary_line())
            
            self.display_active = True
            sys.stdout.flush()
    
    def update_status(self, key: str, status: DownloadStatus, 
                     file_size_mb: Optional[float] = None, 
                     error_msg: Optional[str] = None):
        """
        Update download status and refresh display.
        
        Args:
            key: Download key returned from add_download()
            status: New status
            file_size_mb: File size if completed
            error_msg: Error message if failed
        """
        with self.lock:
            if key not in self.downloads:
                return
                
            download = self.downloads[key]
            download.status = status
            download.file_size_mb = file_size_mb
            download.error_msg = error_msg
            
            if self.display_active and download.line_number is not None:
                self._update_display_line(download)
                self._update_summary_line()
    
    def _update_display_line(self, download: DownloadItem):
        """Update a specific line in the display"""
        if download.line_number is None:
            return
            
        # Calculate how many lines to move up
        # We need to go past the summary (2 lines) plus all downloads after this one
        total_downloads = len(self.downloads)
        lines_to_move_up = (total_downloads - download.line_number) + 1  # +1 for summary
        
        # Move cursor up, clear line, print new content, move back down
        sys.stdout.write(self.CURSOR_UP * lines_to_move_up)
        sys.stdout.write(self.CLEAR_LINE)
        sys.stdout.write(download.get_display_line() + '\n')
        
        # Move cursor back to bottom
        sys.stdout.write(self.CURSOR_UP * lines_to_move_up)
        for _ in range(lines_to_move_up):
            sys.stdout.write('\n')
        
        sys.stdout.flush()
    
    def _update_summary_line(self):
        """Update the summary line at the bottom"""
        # Move cursor up to summary line
        sys.stdout.write(self.CURSOR_UP)
        sys.stdout.write(self.CLEAR_LINE)
        sys.stdout.write(self._get_summary_line())
        sys.stdout.write('\n')
        sys.stdout.flush()
    
    def _get_summary_line(self) -> str:
        """Generate summary line showing overall progress"""
        completed = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.COMPLETED)
        failed = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.FAILED)
        total = len(self.downloads)
        downloading = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.DOWNLOADING)
        
        progress_pct = (completed / total * 100) if total > 0 else 0
        
        status_parts = [f"{completed}/{total} completed ({progress_pct:.1f}%)"]
        if downloading > 0:
            status_parts.append(f"{downloading} active")
        if failed > 0:
            status_parts.append(f"{failed} failed")
            
        return f"📊 Progress: {' • '.join(status_parts)}"
    
    def finish_display(self):
        """Finalize the display and show final summary"""
        with self.lock:
            if not self.display_active:
                return
                
            # Final summary
            completed = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.COMPLETED)
            failed = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.FAILED)
            total = len(self.downloads)
            
            # Move to summary line and update final status
            sys.stdout.write(self.CURSOR_UP)
            sys.stdout.write(self.CLEAR_LINE)
            
            if failed == 0:
                print(f"✅ All downloads complete: {completed}/{total} successful")
            else:
                print(f"⚠️  Downloads finished: {completed}/{total} successful, {failed} failed")
                
            # Add final spacing
            print()
            
            self.display_active = False
            sys.stdout.flush()
    
    def get_successful_downloads(self) -> List[Tuple[str, str]]:
        """
        Get list of successfully completed downloads.
        
        Returns:
            List of (scene_id, band) tuples for completed downloads
        """
        with self.lock:
            return [
                (download.scene_id, download.band) 
                for download in self.downloads.values() 
                if download.status == DownloadStatus.COMPLETED
            ]
    
    def get_download_stats(self) -> Dict[str, int]:
        """Get download statistics"""
        with self.lock:
            stats = {
                'total': len(self.downloads),
                'completed': sum(1 for d in self.downloads.values() if d.status == DownloadStatus.COMPLETED),
                'failed': sum(1 for d in self.downloads.values() if d.status == DownloadStatus.FAILED),
                'pending': sum(1 for d in self.downloads.values() if d.status == DownloadStatus.PENDING),
                'downloading': sum(1 for d in self.downloads.values() if d.status == DownloadStatus.DOWNLOADING)
            }
            return stats


def create_progress_tracker(date_str: str, items_for_date: List, bands: List[str]) -> DownloadProgressTracker:
    """
    Create and initialize a progress tracker for a date's downloads.
    
    Args:
        date_str: Date string (e.g., "20250102")
        items_for_date: List of STAC items for the date
        bands: List of bands to download
        
    Returns:
        Initialized DownloadProgressTracker
    """
    # Extract scene information
    scene_info = []
    for item in items_for_date:
        scene_parts = item.id.split('_')
        if len(scene_parts) >= 2:
            tile_id = scene_parts[1]  # Extract tile (e.g., 34TEK)
            sensor = scene_parts[0]   # Extract sensor (e.g., S2A)
            scene_info.append(f"{sensor}_{tile_id}")
        else:
            scene_info.append(item.id[:20])  # Fallback
    
    # Create tracker
    tracker = DownloadProgressTracker(date_str, scene_info)
    
    # Add all expected downloads
    for item in items_for_date:
        for band in bands:
            tracker.add_download(item.id, band)
    
    return tracker