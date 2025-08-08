#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ISO Handler Module
Handles ISO file operations including selection, downloading, and checksum verification.
"""

import os
import sys
import logging
import hashlib
import requests
from typing import Callable, Optional
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger(__name__)


class ISOHandler:
    """Class for handling ISO file operations"""
    
    def __init__(self):
        """Initialize the ISO handler"""
        logger.info("Initialized ISOHandler")
    
    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA256 checksum of a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 checksum as a hexadecimal string
        """
        logger.info(f"Calculating SHA256 checksum for {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Calculate SHA256 checksum
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read the file in chunks to avoid loading large files into memory
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            checksum = sha256_hash.hexdigest()
            logger.info(f"Checksum calculated: {checksum}")
            return checksum
        
        except Exception as e:
            logger.error(f"Error calculating checksum: {str(e)}")
            raise
    
    def verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """
        Verify that a file's checksum matches the expected value
        
        Args:
            file_path: Path to the file
            expected_checksum: Expected SHA256 checksum
            
        Returns:
            True if the checksums match, False otherwise
        """
        logger.info(f"Verifying checksum for {file_path}")
        
        # Normalize the expected checksum
        expected_checksum = expected_checksum.lower().strip()
        
        # Calculate the actual checksum
        actual_checksum = self.calculate_checksum(file_path)
        
        # Compare the checksums
        match = actual_checksum == expected_checksum
        
        if match:
            logger.info("Checksum verification successful")
        else:
            logger.warning(f"Checksum verification failed. Expected: {expected_checksum}, Actual: {actual_checksum}")
        
        return match
    
    def download_iso(self, url: str, save_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> str:
        """
        Download an ISO file from a URL
        
        Args:
            url: URL to download from
            save_path: Path to save the downloaded file
            progress_callback: Optional callback function for progress updates
                               Takes two arguments: percentage (int) and message (str)
            
        Returns:
            Path to the downloaded file
        """
        logger.info(f"Downloading ISO from {url} to {save_path}")
        
        # Validate URL
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                logger.error(f"Invalid URL: {url}")
                raise ValueError(f"Invalid URL: {url}")
        except Exception as e:
            logger.error(f"Error parsing URL: {str(e)}")
            raise ValueError(f"Invalid URL: {url}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        
        try:
            # Start the download
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get the total file size if available
            total_size = int(response.headers.get('content-length', 0))
            
            # Initialize progress variables
            downloaded = 0
            chunk_size = 1024 * 1024  # 1 MB chunks
            
            # Open the output file
            with open(save_path, 'wb') as f:
                # Download the file in chunks
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        if total_size > 0 and progress_callback:
                            percentage = int(downloaded * 100 / total_size)
                            message = f"Downloading ISO: {self._format_size(downloaded)} of {self._format_size(total_size)}"
                            progress_callback(percentage, message)
            
            # Final progress update
            if progress_callback:
                progress_callback(100, f"Download complete: {self._format_size(downloaded)}")
            
            logger.info(f"Download completed: {save_path}")
            return save_path
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading ISO: {str(e)}")
            
            # Clean up partial download
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                    logger.info(f"Removed partial download: {save_path}")
                except:
                    pass
            
            raise
    
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


# Simple test function
def test_iso_handler():
    """Test the ISO handler functionality"""
    handler = ISOHandler()
    
    # Test checksum calculation
    test_file = "test_file.txt"
    with open(test_file, "w") as f:
        f.write("Hello, world!")
    
    checksum = handler.calculate_checksum(test_file)
    print(f"Checksum of '{test_file}': {checksum}")
    
    # Expected SHA256 checksum of "Hello, world!"
    expected = "315f5bdb76d078c43b8ac0064e4a0164612b1fce77c869345bfc94c75894edd3"
    verification = handler.verify_checksum(test_file, expected)
    print(f"Checksum verification: {'Successful' if verification else 'Failed'}")
    
    # Clean up
    os.remove(test_file)


if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test
    test_iso_handler()