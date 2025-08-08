#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Linux Sidecar Creator
A cross-platform desktop application that converts external storage devices 
into persistent, bootable Linux sidecars.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QComboBox, QPushButton, 
                            QFileDialog, QProgressBar, QMessageBox, QLineEdit,
                            QTabWidget, QGroupBox, QFormLayout, QSpinBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices

# Import custom modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.modules.device_detection import DeviceDetector
from src.modules.iso_handler import ISOHandler
from src.modules.bootable_creator import BootableCreator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sidecar_creator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    """Worker thread to keep GUI responsive during operations"""
    progress_update = pyqtSignal(int, str)
    operation_complete = pyqtSignal(bool, str)
    
    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            self.operation(*self.args, **self.kwargs)
            self.operation_complete.emit(True, "Operation completed successfully")
        except Exception as e:
            logger.error(f"Error in worker thread: {str(e)}")
            self.operation_complete.emit(False, str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize modules
        self.device_detector = DeviceDetector()
        self.iso_handler = ISOHandler()
        self.bootable_creator = BootableCreator()
        
        # Set up the UI
        self.setWindowTitle("Linux Sidecar Creator")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Create main tab
        self.main_tab = QWidget()
        self.tabs.addTab(self.main_tab, "Create Bootable Drive")
        
        # Create settings tab
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Set up main tab UI
        self.setup_main_tab()
        
        # Set up settings tab UI
        self.setup_settings_tab()
        
        # Initialize UI state
        self.refresh_devices()
        
    def setup_main_tab(self):
        """Set up the main tab UI"""
        layout = QVBoxLayout(self.main_tab)
        
        # Device selection section
        device_group = QGroupBox("Select Target Device")
        device_layout = QVBoxLayout(device_group)
        
        device_form = QFormLayout()
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(400)
        device_form.addRow("Device:", self.device_combo)
        
        device_buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Devices")
        self.refresh_button.clicked.connect(self.refresh_devices)
        device_buttons.addWidget(self.refresh_button)
        device_buttons.addStretch()
        
        device_layout.addLayout(device_form)
        device_layout.addLayout(device_buttons)
        layout.addWidget(device_group)
        
        # ISO selection section
        iso_group = QGroupBox("Select Linux ISO")
        iso_layout = QVBoxLayout(iso_group)
        
        iso_form = QFormLayout()
        
        # Local file selection
        iso_file_layout = QHBoxLayout()
        self.iso_path_edit = QLineEdit()
        self.iso_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_iso)
        iso_file_layout.addWidget(self.iso_path_edit)
        iso_file_layout.addWidget(self.browse_button)
        iso_form.addRow("ISO File:", iso_file_layout)
        
        # URL input
        url_layout = QHBoxLayout()
        self.iso_url_edit = QLineEdit()
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_iso)
        url_layout.addWidget(self.iso_url_edit)
        url_layout.addWidget(self.download_button)
        iso_form.addRow("or URL:", url_layout)
        
        # Checksum verification
        checksum_layout = QHBoxLayout()
        self.checksum_edit = QLineEdit()
        self.verify_button = QPushButton("Verify")
        self.verify_button.clicked.connect(self.verify_checksum)
        checksum_layout.addWidget(self.checksum_edit)
        checksum_layout.addWidget(self.verify_button)
        iso_form.addRow("SHA256:", checksum_layout)
        
        iso_layout.addLayout(iso_form)
        layout.addWidget(iso_group)
        
        # Persistence section
        persistence_group = QGroupBox("Persistence Settings")
        persistence_layout = QFormLayout(persistence_group)
        
        self.persistence_size = QSpinBox()
        self.persistence_size.setMinimum(1)
        self.persistence_size.setMaximum(128)
        self.persistence_size.setValue(4)
        self.persistence_size.setSuffix(" GB")
        persistence_layout.addRow("Persistence Size:", self.persistence_size)
        
        layout.addWidget(persistence_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.create_button = QPushButton("Create Bootable Drive")
        self.create_button.clicked.connect(self.create_bootable_drive)
        self.create_button.setMinimumWidth(200)
        
        self.eject_button = QPushButton("Eject Drive")
        self.eject_button.clicked.connect(self.eject_drive)
        self.eject_button.setEnabled(False)
        
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.eject_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def setup_settings_tab(self):
        """Set up the settings tab UI"""
        layout = QVBoxLayout(self.settings_tab)
        
        # Default settings
        defaults_group = QGroupBox("Default Settings")
        defaults_layout = QFormLayout(defaults_group)
        
        self.default_persistence = QSpinBox()
        self.default_persistence.setMinimum(1)
        self.default_persistence.setMaximum(128)
        self.default_persistence.setValue(4)
        self.default_persistence.setSuffix(" GB")
        defaults_layout.addRow("Default Persistence Size:", self.default_persistence)
        
        layout.addWidget(defaults_group)
        
        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout(advanced_group)
        
        # Add advanced settings here
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self.save_settings)
        
        save_layout.addWidget(self.save_settings_button)
        layout.addLayout(save_layout)
    
    def refresh_devices(self):
        """Refresh the list of available devices"""
        try:
            self.status_label.setText("Detecting devices...")
            self.device_combo.clear()
            
            devices = self.device_detector.get_external_devices()
            
            if not devices:
                self.status_label.setText("No external devices found")
                return
            
            for device in devices:
                # Format: "Device Name (Size) - Path"
                display_text = f"{device['name']} ({device['size']}) - {device['path']}"
                self.device_combo.addItem(display_text, device)
            
            self.status_label.setText(f"Found {len(devices)} external devices")
        except Exception as e:
            logger.error(f"Error refreshing devices: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to detect devices: {str(e)}")
            self.status_label.setText("Error detecting devices")
    
    def browse_iso(self):
        """Open file dialog to select ISO file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Linux ISO", "", "ISO Files (*.iso);;All Files (*)"
        )
        
        if file_path:
            self.iso_path_edit.setText(file_path)
            self.iso_url_edit.clear()
            
            # Calculate and display checksum
            self.status_label.setText("Calculating checksum...")
            
            def calculate_checksum_task():
                checksum = self.iso_handler.calculate_checksum(file_path)
                return checksum
            
            worker = WorkerThread(calculate_checksum_task)
            worker.operation_complete.connect(self.handle_checksum_result)
            worker.start()
    
    def download_iso(self):
        """Download ISO from URL"""
        url = self.iso_url_edit.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a valid URL")
            return
        
        # Ask for download location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save ISO File", "", "ISO Files (*.iso);;All Files (*)"
        )
        
        if not save_path:
            return
        
        self.status_label.setText(f"Downloading ISO from {url}...")
        self.progress_bar.setValue(0)
        self.create_button.setEnabled(False)
        
        def download_task():
            self.iso_handler.download_iso(url, save_path, self.update_progress)
            return save_path
        
        worker = WorkerThread(download_task)
        worker.operation_complete.connect(self.handle_download_result)
        worker.start()
    
    def verify_checksum(self):
        """Verify the ISO checksum against user input"""
        iso_path = self.iso_path_edit.text()
        user_checksum = self.checksum_edit.text().strip().lower()
        
        if not iso_path:
            QMessageBox.warning(self, "Warning", "Please select an ISO file first")
            return
        
        if not user_checksum:
            QMessageBox.warning(self, "Warning", "Please enter a checksum to verify against")
            return
        
        self.status_label.setText("Verifying checksum...")
        
        def verify_task():
            calculated = self.iso_handler.calculate_checksum(iso_path)
            return calculated == user_checksum, calculated
        
        worker = WorkerThread(verify_task)
        worker.operation_complete.connect(self.handle_verify_result)
        worker.start()
    
    def create_bootable_drive(self):
        """Create the bootable drive with persistence"""
        # Get selected device
        if self.device_combo.count() == 0:
            QMessageBox.warning(self, "Warning", "No device selected")
            return
        
        device_data = self.device_combo.currentData()
        
        # Get ISO path
        iso_path = self.iso_path_edit.text()
        if not iso_path:
            QMessageBox.warning(self, "Warning", "Please select an ISO file")
            return
        
        # Get persistence size
        persistence_size = self.persistence_size.value()
        
        # Confirm with user
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Warning: All data on the selected device will be erased!")
        msg.setInformativeText(f"You are about to create a bootable Linux drive on:\n"
                              f"{device_data['name']} ({device_data['size']}) - {device_data['path']}\n\n"
                              f"This will ERASE ALL DATA on this device.\n"
                              f"Are you sure you want to continue?")
        msg.setWindowTitle("Confirm Drive Creation")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg.exec() == QMessageBox.StandardButton.No:
            return
        
        # Disable UI elements during operation
        self.create_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        
        self.status_label.setText("Creating bootable drive...")
        self.progress_bar.setValue(0)
        
        def create_task():
            self.bootable_creator.create_bootable_drive(
                device_path=device_data['path'],
                iso_path=iso_path,
                persistence_size=persistence_size,
                progress_callback=self.update_progress
            )
        
        worker = WorkerThread(create_task)
        worker.operation_complete.connect(self.handle_create_result)
        worker.start()
    
    def eject_drive(self):
        """Safely eject the drive"""
        if self.device_combo.count() == 0:
            return
        
        device_data = self.device_combo.currentData()
        
        try:
            self.status_label.setText(f"Ejecting {device_data['name']}...")
            self.device_detector.eject_device(device_data['path'])
            self.status_label.setText(f"Device {device_data['name']} ejected successfully")
            self.refresh_devices()
        except Exception as e:
            logger.error(f"Error ejecting device: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to eject device: {str(e)}")
            self.status_label.setText("Error ejecting device")
    
    def save_settings(self):
        """Save settings to config file"""
        # Save default persistence size
        default_persistence = self.default_persistence.value()
        
        # TODO: Implement settings saving
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully")
    
    def update_progress(self, percentage, message):
        """Update progress bar and status message"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
    
    def handle_checksum_result(self, success, result):
        """Handle checksum calculation result"""
        if success:
            self.checksum_edit.setText(result)
            self.status_label.setText("Checksum calculated successfully")
        else:
            QMessageBox.critical(self, "Error", f"Failed to calculate checksum: {result}")
            self.status_label.setText("Error calculating checksum")
    
    def handle_download_result(self, success, result):
        """Handle ISO download result"""
        self.create_button.setEnabled(True)
        
        if success:
            self.iso_path_edit.setText(result)
            self.status_label.setText("ISO downloaded successfully")
            
            # Calculate and display checksum
            def calculate_checksum_task():
                checksum = self.iso_handler.calculate_checksum(result)
                return checksum
            
            worker = WorkerThread(calculate_checksum_task)
            worker.operation_complete.connect(self.handle_checksum_result)
            worker.start()
        else:
            QMessageBox.critical(self, "Error", f"Failed to download ISO: {result}")
            self.status_label.setText("Error downloading ISO")
    
    def handle_verify_result(self, success, result):
        """Handle checksum verification result"""
        verified, calculated = result
        
        if success:
            if verified:
                QMessageBox.information(self, "Verification Successful", 
                                      "The ISO checksum matches the provided value")
                self.status_label.setText("Checksum verification successful")
            else:
                QMessageBox.warning(self, "Verification Failed", 
                                  f"Checksum mismatch!\nCalculated: {calculated}\nProvided: {self.checksum_edit.text()}")
                self.status_label.setText("Checksum verification failed")
        else:
            QMessageBox.critical(self, "Error", f"Failed to verify checksum: {result}")
            self.status_label.setText("Error verifying checksum")
    
    def handle_create_result(self, success, result):
        """Handle bootable drive creation result"""
        # Re-enable UI elements
        self.create_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        
        if success:
            self.eject_button.setEnabled(True)
            QMessageBox.information(self, "Success", 
                                  "Bootable drive created successfully!\n\n"
                                  "You can now boot from this drive to run Linux.")
            self.status_label.setText("Bootable drive created successfully")
            self.progress_bar.setValue(100)
        else:
            QMessageBox.critical(self, "Error", f"Failed to create bootable drive: {result}")
            self.status_label.setText("Error creating bootable drive")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()