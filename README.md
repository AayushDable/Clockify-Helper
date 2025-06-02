# Clockify Helper - Background Time Tracking Assistant

A Python application that runs in the background and periodically asks "What are you working on?" to help employees track their time without constantly interrupting their workflow.

## Overview

This application addresses the problem many employees face with Clockify and similar time tracking tools, where they need to constantly switch context to log their tasks. Instead, this helper:

1. Runs quietly in the background and displays a popup reminder at configurable intervals
2. Allows employees to quickly log what they're working on
3. Provides break time functionality to pause reminders
4. Saves all entries to a log file that can be easily imported into Clockify later

## Features

- **Periodic Reminders**: Get a popup asking "What are you doing?" at configurable intervals
- **Break Time Management**: Set break durations (5 min, 15 min, 30 min, 1 hour, or indefinite) during which no popups will appear
- **Activity History**: Quickly select from previous activities using autocomplete
- **CSV Logging**: All activities are logged with timestamps in a CSV file for easy import into Clockify
- **System Tray Integration**: Access the application from your system tray
- **Work Hours Settings**: Configure the application to only remind you during work hours
- **Snooze Option**: Postpone reminders when you're in the middle of something important
- **Export Function**: Export your logs with timestamps for backup or reporting
- **Customizable Settings**: Adjust reminder intervals and work hours to fit your preferences

## Installation

### Prerequisites

- Python 3.6 or higher
- Required packages: `tkinter`, `pystray`, `pillow`

### Setup

1. Install required Python packages:
   ```
   pip install pystray pillow
   ```

2. Download the `clockify_helper.py` file and an app icon (e.g., `app_icon.png`)

3. Run the application:
   ```
   python clockify_helper.py
   ```

## Usage

### Basic Usage

Once launched, the application runs in the background with an icon in your system tray. Every N hours (configurable), it will show a popup asking "What are you doing?"

- Type your current task or select from previous entries
- Click "Submit" to log the activity
- The popup automatically closes after 5 minutes if you don't respond

### Managing Breaks

You can start a break in several ways:
1. Click "Start Break" in the popup dialog
2. Right-click the system tray icon and select "Start Break"
3. Open the main window and click "Start Break"

During breaks, no popups will appear. When a timed break ends, the application automatically resumes normal operation.

### Main Interface

To open the main interface:
- Right-click the system tray icon and select "Show Window"

The main window shows:
- Your current activity
- Break status
- Time until next reminder
- List of recent activities

### Settings

Access settings through the main window or system tray icon:

- **Reminder Interval**: How often to show the "What are you doing?" popup (in hours)
- **Work Hours Only**: Enable to only receive reminders during specified work hours
- **Work Start/End Time**: Set your working hours (only relevant if "Work Hours Only" is enabled)

### Log File

Your activities are logged to `time_tracking_log.csv` with these columns:
- Timestamp
- Activity
- Type (Work/Break)
- Duration (in minutes)

This file can be used for Clockify or other time tracking systems.

## License

This software is released under the MIT License.

---

This application aims to reduce the mental overhead of time tracking while still providing accurate data for reporting purposes. By using this helper, employees can stay focused on their work while maintaining detailed activity logs.
