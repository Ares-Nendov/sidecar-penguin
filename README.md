# Linux Sidecar Creator

A cross-platform desktop application that converts external storage devices into persistent, bootable Linux sidecars.

## Features

- **Device Detection**: Automatically detects and lists external storage devices (USB drives, external SSDs)
- **ISO Handling**: Select a Linux ISO file from your local machine or download from a URL
- **Checksum Verification**: Verify ISO integrity with SHA256 checksum
- **Persistence**: Create a persistent storage partition to save files and settings across reboots
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **User-Friendly**: Simple and intuitive GUI with progress tracking

## Requirements

- Python 3.6 or higher
- PyQt6
- Other dependencies listed in `requirements.txt`

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/linux-sidecar-creator.git
   cd linux-sidecar-creator
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running from Source

Run the application directly from source:

```
python src/main.py
```

### Building an Executable

Build a standalone executable using PyInstaller:

```
pyinstaller pyinstaller.spec
```

The executable will be created in the `dist` directory.

## How to Use

1. **Select Target Device**: Choose the external storage device you want to convert into a Linux sidecar.
2. **Select Linux ISO**: Either browse for a local ISO file or enter a URL to download.
3. **Verify Checksum** (Optional): Enter the SHA256 checksum to verify the ISO integrity.
4. **Set Persistence Size**: Choose how much space to allocate for persistent storage.
5. **Create Bootable Drive**: Click the "Create Bootable Drive" button to start the process.
6. **Wait for Completion**: The application will format the drive, write the ISO, and set up persistence.
7. **Eject Drive**: Once completed, you can safely eject the drive using the "Eject Drive" button.

## Warning

**This application will erase all data on the selected device!** Make sure to back up any important data before using this tool.

## Permissions

This application requires administrative privileges to perform disk operations. On Linux and macOS, you may be prompted for your password. On Windows, you may need to run the application as administrator.

## Troubleshooting

- **Device Not Detected**: Make sure the device is properly connected and not in use by another application.
- **ISO Write Failed**: Check if the ISO file is valid and not corrupted.
- **Permission Denied**: Run the application with administrative privileges.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework
- [psutil](https://github.com/giampaolo/psutil) for system utilities
- [requests](https://requests.readthedocs.io/) for HTTP requests