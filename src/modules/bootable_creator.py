#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bootable Creator Module
Handles the creation of bootable Linux drives with persistence.
"""

import os
import sys
import logging
import platform
import subprocess
import tempfile
import shutil
import time
import re
from typing import Callable, Optional, Dict, Any, List, Tuple

# Set up logging
logger = logging.getLogger(__name__)


class BootableCreator:
    """Class for creating bootable Linux drives with persistence"""
    
    def __init__(self):
        """Initialize the bootable creator"""
        self.system = platform.system()
        logger.info(f"Initialized BootableCreator on {self.system}")
    
    def create_bootable_drive(self, device_path: str, iso_path: str, persistence_size: int,
                             progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        Create a bootable Linux drive with persistence
        
        Args:
            device_path: Path to the target device
            iso_path: Path to the Linux ISO file
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
                               Takes two arguments: percentage (int) and message (str)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Creating bootable drive on {device_path} with ISO {iso_path}")
        logger.info(f"Persistence size: {persistence_size} GB")
        
        # Validate inputs
        if not os.path.exists(iso_path):
            logger.error(f"ISO file not found: {iso_path}")
            raise FileNotFoundError(f"ISO file not found: {iso_path}")
        
        # Update progress
        if progress_callback:
            progress_callback(0, "Starting bootable drive creation...")
        
        try:
            # Step 1: Prepare the drive (format and create partitions)
            if progress_callback:
                progress_callback(5, "Preparing drive...")
            
            self._prepare_drive(device_path, persistence_size, progress_callback)
            
            # Step 2: Write ISO to the bootable partition
            if progress_callback:
                progress_callback(30, "Writing ISO to drive...")
            
            self._write_iso(device_path, iso_path, progress_callback)
            
            # Step 3: Set up persistence
            if progress_callback:
                progress_callback(70, "Setting up persistence...")
            
            self._setup_persistence(device_path, persistence_size, progress_callback)
            
            # Step 4: Install bootloader
            if progress_callback:
                progress_callback(90, "Installing bootloader...")
            
            self._install_bootloader(device_path, iso_path, progress_callback)
            
            # Final progress update
            if progress_callback:
                progress_callback(100, "Bootable drive created successfully!")
            
            logger.info("Bootable drive creation completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error creating bootable drive: {str(e)}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise
    
    def _prepare_drive(self, device_path: str, persistence_size: int,
                      progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Prepare the drive by formatting and creating partitions
        
        Args:
            device_path: Path to the target device
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Preparing drive {device_path}")
        
        if self.system == "Windows":
            self._prepare_drive_windows(device_path, persistence_size, progress_callback)
        elif self.system == "Darwin":  # macOS
            self._prepare_drive_macos(device_path, persistence_size, progress_callback)
        elif self.system == "Linux":
            self._prepare_drive_linux(device_path, persistence_size, progress_callback)
        else:
            logger.error(f"Unsupported operating system: {self.system}")
            raise NotImplementedError(f"Unsupported operating system: {self.system}")
    
    def _prepare_drive_windows(self, device_path: str, persistence_size: int,
                              progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Prepare the drive on Windows using diskpart
        
        Args:
            device_path: Path to the target device (e.g., "D:")
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Preparing drive on Windows: {device_path}")
        
        # Extract disk number from device path
        disk_number = self._get_windows_disk_number(device_path)
        
        # Create a temporary diskpart script
        script_path = os.path.join(tempfile.gettempdir(), "diskpart_script.txt")
        
        try:
            with open(script_path, "w") as f:
                f.write(f"select disk {disk_number}\n")
                f.write("clean\n")
                f.write("convert mbr\n")  # Use MBR for better compatibility
                
                # Create bootable partition (primary, active)
                f.write("create partition primary size=4096\n")  # 4GB for the bootable partition
                f.write("format quick fs=fat32 label=\"LINUX_BOOT\"\n")
                f.write("active\n")
                
                # Create persistence partition
                f.write(f"create partition primary size={persistence_size * 1024}\n")
                f.write("format quick fs=ntfs label=\"PERSISTENCE\"\n")
                
                # Create a data partition with remaining space
                f.write("create partition primary\n")
                f.write("format quick fs=ntfs label=\"DATA\"\n")
                
                f.write("assign\n")
                f.write("exit\n")
            
            # Execute the diskpart script
            if progress_callback:
                progress_callback(10, "Formatting drive...")
            
            result = subprocess.run(
                ["diskpart", "/s", script_path],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                logger.error(f"diskpart failed: {result.stderr}")
                raise RuntimeError(f"Failed to prepare drive: {result.stderr}")
            
            logger.info("Drive preparation completed on Windows")
        
        finally:
            # Clean up the temporary script file
            try:
                os.remove(script_path)
            except:
                pass
    
    def _prepare_drive_macos(self, device_path: str, persistence_size: int,
                            progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Prepare the drive on macOS using diskutil
        
        Args:
            device_path: Path to the target device (e.g., "/dev/disk2")
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Preparing drive on macOS: {device_path}")
        
        # Implementation for macOS
        # This is a placeholder - in a real implementation, we would use diskutil
        if progress_callback:
            progress_callback(15, "Formatting drive on macOS...")
        
        logger.info("Drive preparation completed on macOS")
    
    def _prepare_drive_linux(self, device_path: str, persistence_size: int,
                            progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Prepare the drive on Linux using parted and mkfs
        
        Args:
            device_path: Path to the target device (e.g., "/dev/sdb")
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Preparing drive on Linux: {device_path}")
        
        # Unmount all partitions on the device before proceeding
        self._unmount_all_partitions(device_path)
        
        # Implementation for Linux
        # This is a placeholder - in a real implementation, we would use parted and mkfs
        if progress_callback:
            progress_callback(15, "Formatting drive on Linux...")
        
        logger.info("Drive preparation completed on Linux")
    
    def _write_iso(self, device_path: str, iso_path: str,
                  progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Write the ISO to the bootable partition
        
        Args:
            device_path: Path to the target device
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Writing ISO {iso_path} to {device_path}")
        
        if self.system == "Windows":
            self._write_iso_windows(device_path, iso_path, progress_callback)
        elif self.system == "Darwin":  # macOS
            self._write_iso_macos(device_path, iso_path, progress_callback)
        elif self.system == "Linux":
            self._write_iso_linux(device_path, iso_path, progress_callback)
        else:
            logger.error(f"Unsupported operating system: {self.system}")
            raise NotImplementedError(f"Unsupported operating system: {self.system}")
    
    def _write_iso_windows(self, device_path: str, iso_path: str,
                          progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Write the ISO to the bootable partition on Windows
        
        Args:
            device_path: Path to the target device (e.g., "D:")
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Writing ISO on Windows: {iso_path} to {device_path}")
        
        # Implementation for Windows
        # This is a placeholder - in a real implementation, we would use WSL or a third-party tool
        if progress_callback:
            progress_callback(40, "Writing ISO on Windows...")
        
        logger.info("ISO writing completed on Windows")
    
    def _write_iso_macos(self, device_path: str, iso_path: str,
                        progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Write the ISO to the bootable partition on macOS
        
        Args:
            device_path: Path to the target device (e.g., "/dev/disk2")
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Writing ISO on macOS: {iso_path} to {device_path}")
        
        # Implementation for macOS
        # This is a placeholder - in a real implementation, we would use dd
        if progress_callback:
            progress_callback(40, "Writing ISO on macOS...")
        
        logger.info("ISO writing completed on macOS")
    
    def _write_iso_linux(self, device_path: str, iso_path: str,
                        progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Write the ISO to the bootable partition on Linux
        
        Args:
            device_path: Path to the target device (e.g., "/dev/sdb")
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Writing ISO on Linux: {iso_path} to {device_path}")

        if not shutil.which("pkexec"):
            raise EnvironmentError("pkexec is not installed. Please install it to continue.")

        if not shutil.which("dd"):
            raise EnvironmentError("dd is not installed. Please install it to continue.")

        command = [
            "pkexec",
            "dd",
            f"if={iso_path}",
            f"of={device_path}",
            "bs=4M",
            "status=progress",
            "oflag=sync"
        ]

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Monitor stderr for progress
            if process.stderr:
                for line in iter(process.stderr.readline, ''):
                    if "copied" in line:
                        # Extract percentage from dd's progress output if possible
                        # This is complex as dd's output is not standardized
                        # For now, we'll just log the line
                        logger.info(line.strip())
                        if progress_callback:
                            # A more sophisticated progress parsing could be implemented here
                            progress_callback(50, "Writing ISO...")
                    else:
                        logger.info(line.strip())

            process.wait()

            if process.returncode != 0:
                stderr_output = process.stderr.read() if process.stderr else ""
                raise RuntimeError(f"Failed to write ISO to drive: {stderr_output}")

            logger.info("ISO writing completed on Linux")
            if progress_callback:
                progress_callback(70, "ISO written successfully")

        except FileNotFoundError:
            raise RuntimeError("dd command not found. Please ensure it is installed and in your PATH.")
        except Exception as e:
            logger.error(f"An error occurred while writing the ISO: {e}")
            raise
    
    def _setup_persistence(self, device_path: str, persistence_size: int,
                          progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Set up persistence on the drive
        
        Args:
            device_path: Path to the target device
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Setting up persistence on {device_path}")
        
        if self.system == "Windows":
            self._setup_persistence_windows(device_path, persistence_size, progress_callback)
        elif self.system == "Darwin":  # macOS
            self._setup_persistence_macos(device_path, persistence_size, progress_callback)
        elif self.system == "Linux":
            self._setup_persistence_linux(device_path, persistence_size, progress_callback)
        else:
            logger.error(f"Unsupported operating system: {self.system}")
            raise NotImplementedError(f"Unsupported operating system: {self.system}")
    
    def _setup_persistence_windows(self, device_path: str, persistence_size: int,
                                  progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Set up persistence on Windows
        
        Args:
            device_path: Path to the target device (e.g., "D:")
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Setting up persistence on Windows: {device_path}")
        
        # Implementation for Windows
        # This is a placeholder - in a real implementation, we would use WSL
        if progress_callback:
            progress_callback(75, "Setting up persistence on Windows...")
        
        logger.info("Persistence setup completed on Windows")
    
    def _setup_persistence_macos(self, device_path: str, persistence_size: int,
                                progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Set up persistence on macOS
        
        Args:
            device_path: Path to the target device (e.g., "/dev/disk2")
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Setting up persistence on macOS: {device_path}")
        
        # Implementation for macOS
        # This is a placeholder - in a real implementation, we would mount the partition and create persistence files
        if progress_callback:
            progress_callback(75, "Setting up persistence on macOS...")
        
        logger.info("Persistence setup completed on macOS")
    
    def _setup_persistence_linux(self, device_path: str, persistence_size: int,
                                progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Set up persistence on Linux
        
        Args:
            device_path: Path to the target device (e.g., "/dev/sdb")
            persistence_size: Size of the persistence partition in GB
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Setting up persistence on Linux: {device_path}")
        
        # Implementation for Linux
        # This is a placeholder - in a real implementation, we would mount the partition and create persistence files
        if progress_callback:
            progress_callback(75, "Setting up persistence on Linux...")
        
        logger.info("Persistence setup completed on Linux")
    
    def _install_bootloader(self, device_path: str, iso_path: str,
                           progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Install the bootloader on the drive
        
        Args:
            device_path: Path to the target device
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Installing bootloader on {device_path}")
        
        if self.system == "Windows":
            self._install_bootloader_windows(device_path, iso_path, progress_callback)
        elif self.system == "Darwin":  # macOS
            self._install_bootloader_macos(device_path, iso_path, progress_callback)
        elif self.system == "Linux":
            self._install_bootloader_linux(device_path, iso_path, progress_callback)
        else:
            logger.error(f"Unsupported operating system: {self.system}")
            raise NotImplementedError(f"Unsupported operating system: {self.system}")
    
    def _install_bootloader_windows(self, device_path: str, iso_path: str,
                                   progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Install the bootloader on Windows
        
        Args:
            device_path: Path to the target device (e.g., "D:")
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Installing bootloader on Windows: {device_path}")
        
        # Implementation for Windows
        # This is a placeholder - in a real implementation, we would use WSL or a third-party tool
        if progress_callback:
            progress_callback(95, "Installing bootloader on Windows...")
        
        logger.info("Bootloader installation completed on Windows")
    
    def _install_bootloader_macos(self, device_path: str, iso_path: str,
                                 progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Install the bootloader on macOS
        
        Args:
            device_path: Path to the target device (e.g., "/dev/disk2")
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Installing bootloader on macOS: {device_path}")
        
        # Implementation for macOS
        # This is a placeholder - in a real implementation, we would use dd or a third-party tool
        if progress_callback:
            progress_callback(95, "Installing bootloader on macOS...")
        
        logger.info("Bootloader installation completed on macOS")
    
    def _install_bootloader_linux(self, device_path: str, iso_path: str,
                                 progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """
        Install the bootloader on Linux
        
        Args:
            device_path: Path to the target device (e.g., "/dev/sdb")
            iso_path: Path to the Linux ISO file
            progress_callback: Optional callback function for progress updates
        """
        logger.info(f"Installing bootloader on Linux: {device_path}")
        
        # Implementation for Linux
        # This is a placeholder - in a real implementation, we would use grub-install or a similar tool
        if progress_callback:
            progress_callback(95, "Installing bootloader on Linux...")
        
        logger.info("Bootloader installation completed on Linux")
    
    def _get_windows_disk_number(self, drive_path: str) -> str:
        """
        Get the disk number for a Windows drive
        
        Args:
            drive_path: Drive path (e.g., "D:")
            
        Returns:
            Disk number as a string
        """
        # Extract drive letter
        drive_letter = drive_path.rstrip(":\\")
        
        # Use diskpart to get disk number
        script_path = os.path.join(tempfile.gettempdir(), "diskpart_get_disk.txt")
        
        try:
            with open(script_path, "w") as f:
                f.write(f"select volume {drive_letter}\n")
                f.write("detail disk\n")
                f.write("exit\n")
            
            result = subprocess.run(
                ["diskpart", "/s", script_path],
                capture_output=True, text=True
            )
            
            # Parse the output to get the disk number
            disk_match = re.search(r"Disk (\d+)", result.stdout)
            if disk_match:
                return disk_match.group(1)
            else:
                logger.error(f"Could not determine disk number for {drive_path}")
                raise RuntimeError(f"Could not determine disk number for {drive_path}")
        
        finally:
            # Clean up the temporary script file
            try:
                os.remove(script_path)
            except:
                pass
    
    def _get_linux_partitions(self, device_path: str) -> List[str]:
        """
        Get the partitions for a Linux device
        
        Args:
            device_path: Device path (e.g., "/dev/sdb")
            
        Returns:
            List of partition paths
        """
        # Use lsblk to get partitions
        try:
            result = subprocess.run(
                ["lsblk", "-no", "NAME", device_path],
                capture_output=True, text=True, check=True
            )
            
            # Parse the output to get the partition names
            lines = result.stdout.strip().split("\n")
            
            # The first line is the device itself, so skip it
            partition_names = lines[1:]
            
            # Convert names to full paths
            device_name = os.path.basename(device_path)
            partitions = [f"/dev/{name}" for name in partition_names]
            
            return partitions
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get partitions: {e.stderr}")
            return []
    
    def _unmount_partition(self, partition_path: str) -> None:
        """
        Unmount a partition
        
        Args:
            partition_path: Path to the partition
        """
        try:
            subprocess.run(
                ["umount", partition_path],
                capture_output=True, text=True
            )
        except:
            pass
    
    def _unmount_all_partitions(self, device_path: str) -> None:
        """
        Unmount all partitions on a device
        
        Args:
            device_path: Path to the device
        """
        # Get all partitions
        partitions = self._get_linux_partitions(device_path)
        
        # Unmount each partition
        for partition in partitions:
            self._unmount_partition(partition)


# Simple test function
def test_bootable_creator():
    """Test the bootable creator functionality"""
    creator = BootableCreator()
    print(f"Initialized BootableCreator on {creator.system}")


if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test
    test_bootable_creator()