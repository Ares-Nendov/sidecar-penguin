#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Device Detection Module
Handles detection of external storage devices and provides information about them.
"""

import os
import sys
import logging
import platform
import psutil
import subprocess
import re
from typing import List, Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)


class DeviceDetector:
    """Class for detecting and managing external storage devices"""
    
    def __init__(self):
        """Initialize the device detector"""
        self.system = platform.system()
        logger.info(f"Initialized DeviceDetector on {self.system}")
    
    def get_external_devices(self) -> List[Dict[str, Any]]:
        """
        Get a list of external storage devices (USB drives, external SSDs)
        
        Returns:
            List of dictionaries containing device information:
            - name: Device name/label
            - path: Device path
            - size: Human-readable size
            - size_bytes: Size in bytes
            - filesystem: Filesystem type (if available)
        """
        if self.system == "Windows":
            return self._get_windows_devices()
        elif self.system == "Darwin":  # macOS
            return self._get_macos_devices()
        elif self.system == "Linux":
            return self._get_linux_devices()
        else:
            logger.error(f"Unsupported operating system: {self.system}")
            raise NotImplementedError(f"Unsupported operating system: {self.system}")
    
    def _get_windows_devices(self) -> List[Dict[str, Any]]:
        """Get external devices on Windows"""
        devices = []
        
        try:
            # Get all disk partitions
            partitions = psutil.disk_partitions(all=True)
            
            # Filter for removable drives
            for partition in partitions:
                # Skip CD-ROM drives and network drives
                if "cdrom" in partition.opts or partition.fstype == "":
                    continue
                
                try:
                    # Get drive information
                    drive_info = self._get_windows_drive_info(partition.device)
                    
                    # Skip system drive
                    if self._is_system_drive(partition.device):
                        logger.info(f"Skipping system drive: {partition.device}")
                        continue
                    
                    # Skip non-removable drives unless they're external
                    if not drive_info.get("removable", False) and not drive_info.get("external", False):
                        continue
                    
                    # Get disk usage
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    devices.append({
                        "name": drive_info.get("label", f"Drive ({partition.device})"),
                        "path": partition.device.rstrip("\\"),
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "size_bytes": usage.total,
                        "size": self._format_size(usage.total),
                        "removable": drive_info.get("removable", False),
                        "external": drive_info.get("external", False)
                    })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"Could not access drive {partition.device}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error detecting Windows devices: {str(e)}")
            raise
        
        return devices
    
    def _get_windows_drive_info(self, drive_path: str) -> Dict[str, Any]:
        """
        Get additional information about a Windows drive
        
        Args:
            drive_path: Drive path (e.g., "C:\\")
            
        Returns:
            Dictionary with drive information
        """
        info = {}
        drive_letter = drive_path.rstrip("\\")
        
        try:
            # Use WMI to get drive information
            # This requires administrative privileges on some systems
            wmic_cmd = f'wmic logicaldisk where DeviceID="{drive_letter}" get VolumeName,Size,Description /format:list'
            result = subprocess.run(wmic_cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                output = result.stdout
                
                # Extract volume name (label)
                label_match = re.search(r"VolumeName=(.+)", output)
                if label_match and label_match.group(1).strip():
                    info["label"] = label_match.group(1).strip()
                
                # Check if it's a removable drive
                desc_match = re.search(r"Description=(.+)", output)
                if desc_match:
                    description = desc_match.group(1).strip().lower()
                    info["removable"] = "removable" in description
                    info["external"] = "external" in description or "usb" in description
            
            # If we couldn't get the label from WMI, try another method
            if "label" not in info:
                vol_cmd = f'vol {drive_letter}'
                vol_result = subprocess.run(vol_cmd, capture_output=True, text=True, shell=True)
                
                if vol_result.returncode == 0:
                    vol_output = vol_result.stdout
                    vol_match = re.search(r"Volume in drive .+ is (.+)", vol_output)
                    
                    if vol_match:
                        info["label"] = vol_match.group(1).strip()
            
            # Check if it's removable using another method if WMI failed
            if "removable" not in info:
                # Use diskpart to check if it's removable
                # Create a temporary script file
                script_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "diskpart_script.txt")
                with open(script_path, "w") as f:
                    f.write(f"select volume {drive_letter[0]}\ndetail volume\nexit")
                
                diskpart_cmd = f'diskpart /s "{script_path}"'
                diskpart_result = subprocess.run(diskpart_cmd, capture_output=True, text=True, shell=True)
                
                if diskpart_result.returncode == 0:
                    diskpart_output = diskpart_result.stdout.lower()
                    info["removable"] = "removable" in diskpart_output
                    info["external"] = "external" in diskpart_output or "usb" in diskpart_output
                
                # Clean up the temporary script file
                try:
                    os.remove(script_path)
                except:
                    pass
        
        except Exception as e:
            logger.warning(f"Error getting Windows drive info for {drive_path}: {str(e)}")
        
        return info
    
    def _get_macos_devices(self) -> List[Dict[str, Any]]:
        """Get external devices on macOS"""
        devices = []
        
        try:
            # Use diskutil to list all volumes
            result = subprocess.run(
                ["diskutil", "list", "-plist", "external"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                logger.error(f"diskutil command failed: {result.stderr}")
                return devices
            
            # Parse the output to find external disks
            disk_ids = re.findall(r"/dev/disk(\d+)", result.stdout)
            
            for disk_id in disk_ids:
                disk_path = f"/dev/disk{disk_id}"
                
                # Get detailed information about this disk
                info_result = subprocess.run(
                    ["diskutil", "info", "-plist", disk_path],
                    capture_output=True, text=True
                )
                
                if info_result.returncode != 0:
                    logger.warning(f"Could not get info for {disk_path}: {info_result.stderr}")
                    continue
                
                # Parse the plist output
                # In a real implementation, we would use plistlib to parse this properly
                # For simplicity, we'll use regex here
                
                # Get disk name/label
                name_match = re.search(r"<key>VolumeName</key>\s*<string>(.+?)</string>", info_result.stdout)
                name = name_match.group(1) if name_match else f"Disk {disk_id}"
                
                # Get disk size
                size_match = re.search(r"<key>TotalSize</key>\s*<integer>(\d+)</integer>", info_result.stdout)
                size_bytes = int(size_match.group(1)) if size_match else 0
                
                # Get filesystem
                fs_match = re.search(r"<key>FilesystemName</key>\s*<string>(.+?)</string>", info_result.stdout)
                filesystem = fs_match.group(1) if fs_match else "Unknown"
                
                # Get mount point
                mount_match = re.search(r"<key>MountPoint</key>\s*<string>(.+?)</string>", info_result.stdout)
                mountpoint = mount_match.group(1) if mount_match else ""
                
                # Skip if not mounted
                if not mountpoint:
                    continue
                
                devices.append({
                    "name": name,
                    "path": disk_path,
                    "mountpoint": mountpoint,
                    "filesystem": filesystem,
                    "size_bytes": size_bytes,
                    "size": self._format_size(size_bytes),
                    "removable": True,  # All external disks are considered removable
                    "external": True
                })
        
        except Exception as e:
            logger.error(f"Error detecting macOS devices: {str(e)}")
            raise
        
        return devices
    
    def _get_linux_devices(self) -> List[Dict[str, Any]]:
        """Get external devices on Linux"""
        devices = []
        
        try:
            # Get all block devices
            lsblk_cmd = ["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,LABEL,RM,VENDOR,MODEL", "-J"]
            result = subprocess.run(lsblk_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"lsblk command failed: {result.stderr}")
                return devices
            
            # In a real implementation, we would parse the JSON output properly
            # For simplicity, we'll use regex here
            
            # Find all disk entries
            disk_entries = re.finditer(r'"name":"([^"]+)".*?"type":"disk"', result.stdout)
            
            for disk_match in disk_entries:
                disk_name = disk_match.group(1)
                
                # Skip loop devices and internal drives
                if disk_name.startswith("loop") or self._is_linux_internal_drive(disk_name):
                    continue
                
                # Find all partitions for this disk
                partition_pattern = f'"name":"{disk_name}([^"]*)".*?"type":"part".*?"mountpoint":"([^"]*)"'
                partition_entries = re.finditer(partition_pattern, result.stdout)
                
                for part_match in partition_entries:
                    part_suffix = part_match.group(1)
                    mountpoint = part_match.group(2)
                    
                    # Skip if not mounted
                    if not mountpoint or mountpoint == "null":
                        continue
                    
                    part_name = f"{disk_name}{part_suffix}"
                    
                    # Get more details about this partition
                    part_pattern = f'"name":"{part_name}".*?"size":"([^"]+)".*?"fstype":"([^"]*)".*?"label":"([^"]*)"'
                    part_details = re.search(part_pattern, result.stdout)
                    
                    if part_details:
                        size_str = part_details.group(1)
                        fstype = part_details.group(2)
                        label = part_details.group(3)
                        
                        # Convert size string to bytes (approximate)
                        size_bytes = self._parse_size(size_str)
                        
                        devices.append({
                            "name": label if label and label != "null" else f"Disk {part_name}",
                            "path": f"/dev/{part_name}",
                            "mountpoint": mountpoint,
                            "filesystem": fstype if fstype and fstype != "null" else "Unknown",
                            "size_bytes": size_bytes,
                            "size": size_str,
                            "removable": True,  # We've already filtered for external drives
                            "external": True
                        })
        
        except Exception as e:
            logger.error(f"Error detecting Linux devices: {str(e)}")
            raise
        
        return devices
    
    def _is_system_drive(self, drive_path: str) -> bool:
        """
        Check if a drive is the system drive
        
        Args:
            drive_path: Drive path
            
        Returns:
            True if it's the system drive, False otherwise
        """
        if self.system == "Windows":
            system_drive = os.environ.get("SystemDrive", "C:") + "\\"
            return drive_path.upper() == system_drive.upper()
        elif self.system == "Darwin":  # macOS
            return drive_path == "/"
        elif self.system == "Linux":
            return drive_path == "/"
        
        return False
    
    def _is_linux_internal_drive(self, drive_name: str) -> bool:
        """
        Check if a Linux drive is internal
        
        Args:
            drive_name: Drive name (e.g., "sda")
            
        Returns:
            True if it's an internal drive, False otherwise
        """
        try:
            # Check if the drive is removable
            removable_path = f"/sys/block/{drive_name}/removable"
            if os.path.exists(removable_path):
                with open(removable_path, "r") as f:
                    removable = f.read().strip() == "1"
                    if removable:
                        return False
            
            # Check if it's on USB bus
            device_path = os.path.realpath(f"/sys/block/{drive_name}")
            return "usb" not in device_path
        
        except Exception as e:
            logger.warning(f"Error checking if {drive_name} is internal: {str(e)}")
            # If we can't determine, assume it's internal for safety
            return True
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Format size in bytes to human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Human-readable size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        
        for unit in ["KB", "MB", "GB", "TB"]:
            size_bytes /= 1024
            if size_bytes < 1024:
                break
        
        return f"{size_bytes:.2f} {unit}"
    
    def _parse_size(self, size_str: str) -> int:
        """
        Parse a size string to bytes
        
        Args:
            size_str: Size string (e.g., "1G", "500M")
            
        Returns:
            Size in bytes
        """
        size_str = size_str.strip().upper()
        
        # Extract the number and unit
        match = re.match(r"^([\d.]+)([KMGT])?", size_str)
        if not match:
            return 0
        
        value = float(match.group(1))
        unit = match.group(2) if match.group(2) else ""
        
        # Convert to bytes
        multipliers = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
        return int(value * multipliers.get(unit, 1))
    
    def eject_device(self, device_path: str) -> bool:
        """
        Safely eject a device
        
        Args:
            device_path: Device path
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Ejecting device: {device_path}")
        
        try:
            if self.system == "Windows":
                return self._eject_windows_device(device_path)
            elif self.system == "Darwin":  # macOS
                return self._eject_macos_device(device_path)
            elif self.system == "Linux":
                return self._eject_linux_device(device_path)
            else:
                logger.error(f"Unsupported operating system: {self.system}")
                raise NotImplementedError(f"Unsupported operating system: {self.system}")
        
        except Exception as e:
            logger.error(f"Error ejecting device {device_path}: {str(e)}")
            raise
    
    def _eject_windows_device(self, device_path: str) -> bool:
        """
        Eject a Windows device
        
        Args:
            device_path: Device path (e.g., "D:")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a temporary VBS script to eject the drive
            script_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "eject_drive.vbs")
            
            with open(script_path, "w") as f:
                f.write(f'''
                Set objShell = CreateObject("Shell.Application")
                Set objFolder = objShell.Namespace(17) ' 17 = ssfDRIVES
                
                For Each objItem in objFolder.Items
                    If objItem.Path = "{device_path}" Then
                        objItem.InvokeVerb("Eject")
                        Exit For
                    End If
                Next
                ''')
            
            # Execute the script
            result = subprocess.run(
                ["cscript", "//nologo", script_path],
                capture_output=True, text=True
            )
            
            # Clean up the temporary script file
            try:
                os.remove(script_path)
            except:
                pass
            
            return result.returncode == 0
        
        except Exception as e:
            logger.error(f"Error ejecting Windows device {device_path}: {str(e)}")
            return False
    
    def _eject_macos_device(self, device_path: str) -> bool:
        """
        Eject a macOS device
        
        Args:
            device_path: Device path (e.g., "/dev/disk2")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["diskutil", "eject", device_path],
                capture_output=True, text=True
            )
            
            return result.returncode == 0
        
        except Exception as e:
            logger.error(f"Error ejecting macOS device {device_path}: {str(e)}")
            return False
    
    def _eject_linux_device(self, device_path: str) -> bool:
        """
        Eject a Linux device
        
        Args:
            device_path: Device path (e.g., "/dev/sdb1")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First, unmount the device
            result = subprocess.run(
                ["umount", device_path],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to unmount {device_path}: {result.stderr}")
                return False
            
            # Then, use eject command if available
            eject_result = subprocess.run(
                ["eject", device_path],
                capture_output=True, text=True
            )
            
            return eject_result.returncode == 0
        
        except Exception as e:
            logger.error(f"Error ejecting Linux device {device_path}: {str(e)}")
            return False


# Simple test function
def test_device_detection():
    """Test the device detection functionality"""
    detector = DeviceDetector()
    devices = detector.get_external_devices()
    
    print(f"Found {len(devices)} external devices:")
    for i, device in enumerate(devices, 1):
        print(f"\nDevice {i}:")
        for key, value in device.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test
    test_device_detection()