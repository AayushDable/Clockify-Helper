import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import threading
import time
import csv
import json
import os
from datetime import datetime, timedelta
import configparser
import sys
import webbrowser
import pystray
from PIL import Image, ImageDraw

class ClockifyHelper:
    def __init__(self):
        """Initialize the application"""
        self.config_file = "clockify_helper_config.ini"
        self.log_file = "time_tracking_log.csv"
        self.load_config()
        self.setup_logging()
        self.running = True
        self.in_break = False
        self.break_end_time = None
        self.last_activity = ""
        self.activity_history = []
        self.reminder_popup_active = False

        # Load activity history if it exists
        self.load_activity_history()
        
        # Start background thread
        self.background_thread = threading.Thread(target=self.background_worker, daemon=True)
        self.background_thread.start()
        
        # Setup UI
        self.setup_ui()

    def _on_tray_notify(self, icon, item):
        if item == pystray.MouseEventType.DOUBLE_CLICK:
            self.root.after(0, self.show_window)

    def create_tray_icon(self):
        # Create a simple icon dynamically
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill="dodgerblue")
        draw.rectangle((28, 28, 36, 48), fill="white")
        draw.rectangle((26, 42, 38, 52), fill="grey")
        self.systray_icon = pystray.Icon(
            "clockify_helper",
            image,
            "Clockify Helper",
            menu=pystray.Menu(
                pystray.MenuItem("Show Clockify Helper", self.on_tray_show),
                pystray.MenuItem("Exit", self.on_tray_exit)
            )
        )
        self.systray_icon._icon._on_notify = self._on_tray_notify

        # Start tray icon on another thread so it doesn't block Tk
        threading.Thread(target=self.systray_icon.run, daemon=True).start()

    def on_tray_show(self, icon, item):
        self.root.after(0, self.show_window)

    def on_tray_exit(self, icon, item):
        self.running = False
        icon.stop()
        self.quit_app()


    def load_config(self):
        """Load configuration from INI file or create default"""
        self.config = configparser.ConfigParser()
        
        # Default configuration
        default_config = {
            'SETTINGS': {
                'reminder_interval_hours': '2',
                'enable_system_tray': 'True',
                'auto_start': 'False',
                'work_hours_start': '09:00',
                'work_hours_end': '17:00',
                'enable_work_hours_only': 'True',
                'snooze_duration_minutes': '15'
            }
        }
        
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Create default config file
            for section, options in default_config.items():
                self.config.add_section(section)
                for key, value in options.items():
                    self.config.set(section, key, value)
            
            with open(self.config_file, 'w') as f:
                self.config.write(f)
    
    def setup_logging(self):
        """Setup CSV logging with headers if file doesn't exist"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Activity', 'Type', 'Duration_Minutes'])
    
    def load_activity_history(self):
        """Load previous activities for autocomplete"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    activities = set()
                    for row in reader:
                        if row['Activity'] and row['Activity'] != 'Break':
                            activities.add(row['Activity'])
                    self.activity_history = list(activities)
            except Exception as e:
                print(f"Error loading activity history: {e}")
                self.activity_history = []

    def on_minimize(self, event):
        # If the user minimized (iconified), withdraw and show tray
        if self.root.state() == 'iconic':
            self.root.after(200, self.hide_window)  # Give Tk time to finish minimizing

    def setup_ui(self):
        """Setup the main UI window (hidden by default)"""
        self.root = tk.Tk()
        self.root.title("Clockify Helper")
        self.root.geometry("400x350")
        self.root.withdraw()  # Hide initially
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.bind('<Unmap>', self.on_minimize)

        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Make the frame expandable
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # App title
        title_label = ttk.Label(main_frame, text="Clockify Helper", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Application is running in the background")
        self.status_label.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Create a separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Current activity
        ttk.Label(main_frame, text="Current Activity:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.current_activity_var = tk.StringVar()
        self.current_activity_label = ttk.Label(main_frame, textvariable=self.current_activity_var)
        self.current_activity_label.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # Break status
        ttk.Label(main_frame, text="Break Status:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.break_status_var = tk.StringVar(value="Not in break")
        self.break_status_label = ttk.Label(main_frame, textvariable=self.break_status_var)
        self.break_status_label.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Next reminder
        ttk.Label(main_frame, text="Next Reminder:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.next_reminder_var = tk.StringVar()
        self.next_reminder_label = ttk.Label(main_frame, textvariable=self.next_reminder_var)
        self.next_reminder_label.grid(row=5, column=1, sticky=tk.W, pady=2)
        
        # Create a separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=6, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame, text="Log Activity Now", command=self.show_activity_popup).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Start Break", command=self.show_break_popup).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="End Break", command=self.end_break).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Settings", command=self.show_settings).pack(side=tk.LEFT, padx=5)
        
        # Recent activities listbox with label
        activities_frame = ttk.LabelFrame(main_frame, text="Recent Activities")
        activities_frame.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(8, weight=1)
        
        self.activities_listbox = tk.Listbox(activities_frame, height=6)
        self.activities_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(self.activities_listbox, orient=tk.VERTICAL, command=self.activities_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.activities_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Footer with export button and help link
        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(footer_frame, text="Export Log", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        
        help_link = ttk.Label(footer_frame, text="Help", foreground="blue", cursor="hand2")
        help_link.pack(side=tk.RIGHT, padx=5)
        help_link.bind("<Button-1>", lambda e: messagebox.showinfo("Help", "For help, check the documentation or contact support."))
        
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Load recent activities
        self.refresh_activities_list()
        self.create_tray_icon()

    def refresh_activities_list(self):
        """Refresh the activities listbox with recent entries"""
        self.activities_listbox.delete(0, tk.END)
        
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    activities = list(reader)
                    # Show last 10 activities
                    for activity in activities[-10:]:
                        timestamp = activity['Timestamp']
                        activity_name = activity['Activity']
                        activity_type = activity['Type']
                        self.activities_listbox.insert(0, f"{timestamp} - {activity_name} ({activity_type})")
        except Exception as e:
            print(f"Error refreshing activities: {e}")
    
    def background_worker(self):
        """Background thread that handles periodic reminders"""
        reminder_interval = float(self.config.get('SETTINGS', 'reminder_interval_hours')) * 3600  # Convert to seconds
        
        while self.running:
            time.sleep(5)  # Check every minute
            
            # Check if we should show reminder
            current_time = datetime.now()
            
            # Check work hours if enabled
            if self.config.getboolean('SETTINGS', 'enable_work_hours_only'):
                work_start = datetime.strptime(self.config.get('SETTINGS', 'work_hours_start'), '%H:%M').time()
                work_end = datetime.strptime(self.config.get('SETTINGS', 'work_hours_end'), '%H:%M').time()
                current_time_only = current_time.time()
                
                if not (work_start <= current_time_only <= work_end):
                    continue  # Skip if outside work hours
            
            # Check if in break
            if self.in_break:
                if self.break_end_time and current_time >= self.break_end_time:
                    self.end_break()
                else:
                    continue  # Skip reminder during break
            
            # Show reminder based on interval
            if not hasattr(self, 'last_reminder_time'):
                self.last_reminder_time = current_time
                self.root.after(0, self.show_activity_popup)

            elif (current_time - self.last_reminder_time).total_seconds() >= reminder_interval:
                if not self.reminder_popup_active:
                    self.root.after(0, self.show_activity_popup)

    def update_ui_status(self):
        """Update UI status information"""
        self.current_activity_var.set(self.last_activity if self.last_activity else "None")
        
        if self.in_break:
            if self.break_end_time:
                remaining = self.break_end_time - datetime.now()
                if remaining.total_seconds() > 0:
                    minutes_left = int(remaining.total_seconds() / 60)
                    self.break_status_var.set(f"In break ({minutes_left} min left)")
                else:
                    self.break_status_var.set("Break ending...")
            else:
                self.break_status_var.set("In break (indefinite)")
        else:
            self.break_status_var.set("Not in break")
        
        # Improved next reminder display
        if hasattr(self, 'last_reminder_time'):
            interval_seconds = float(self.config.get('SETTINGS', 'reminder_interval_hours')) * 3600
            next_reminder = self.last_reminder_time + timedelta(seconds=interval_seconds)
            remaining = next_reminder - datetime.now()
            if remaining.total_seconds() > 0:
                h, rem = divmod(int(remaining.total_seconds()), 3600)
                m, s = divmod(rem, 60)
                if h > 0:
                    self.next_reminder_var.set(f"{h:02}:{m:02}:{s:02} left")
                else:
                    self.next_reminder_var.set(f"{m:02}:{s:02} left")
            else:
                self.next_reminder_var.set("Due now!")
        else:
            self.next_reminder_var.set("Soon")
        
        # Schedule next update for live countdown
        self.root.after(1000, self.update_ui_status)

        
    def show_activity_popup(self):
        if self.in_break or self.reminder_popup_active:
            return
        self.reminder_popup_active = True

        # Create a temporary window to ensure dialogs appear on top
        temp_root = tk.Tk()
        temp_root.withdraw()  # Hide the temporary window
        temp_root.attributes('-topmost', True)  # Make it topmost
        temp_root.lift()
        temp_root.focus_force()

        try:
            # If already working on a task, confirm with the user
            if self.last_activity:
                still_working = messagebox.askyesno(
                    "Activity Tracker",
                    f"Still working on \"{self.last_activity}\"?",
                    parent=temp_root  # Use temp window as parent
                )
                if still_working:
                    # Just reset the reminder time; do not log again
                    self.last_reminder_time = datetime.now()
                    self.reminder_popup_active = False
                    return
                # else, fall through to ask for new task

            # Either no last activity, or user said 'no'
            activity = simpledialog.askstring(
                "Activity Tracker", 
                "What are you currently working on?",
                initialvalue=self.last_activity if self.last_activity else "",
                parent=temp_root  # Use temp window as parent
            )

            if activity:
                self.log_activity(activity.strip(), "Work")
                self.last_activity = activity.strip()
                self.last_reminder_time = datetime.now()
                if activity.strip() not in self.activity_history:
                    self.activity_history.append(activity.strip())
                self.refresh_activities_list()
                self.reminder_popup_active = False
            else:
                # User cancelled - snooze for default time
                snooze_minutes = int(self.config.get('SETTINGS', 'snooze_duration_minutes'))
                self.last_reminder_time = datetime.now() + timedelta(minutes=snooze_minutes)
                self.reminder_popup_active = False
        
        finally:
            # Always destroy the temporary window
            temp_root.destroy()


    
    def show_break_popup(self):
        """Show break duration selection popup"""
        popup = tk.Toplevel()
        popup.title("Break Time")
        popup.geometry("300x200")
        popup.transient(self.root)
        popup.grab_set()
        
        # Center the popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
        y = (popup.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(popup, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(main_frame, text="How long is your break?", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=5)
        
        # Break duration options
        break_options = [
            ("5 minutes", 5),
            ("15 minutes", 15),
            ("30 minutes", 30),
            ("1 hour", 60),
            ("Indefinite", None)
        ]
        
        for i, (text, minutes) in enumerate(break_options):
            ttk.Button(main_frame, text=text, 
                      command=lambda p=popup, m=minutes: self.start_break_with_duration(p, m)).grid(row=i+1, column=0, columnspan=2, pady=2, sticky=(tk.W, tk.E))
    
    def start_break_with_duration(self, popup, duration_minutes):
        """Start break with specified duration"""
        popup.destroy()
        self.start_break(duration_minutes)
        self.log_activity("Break", "Break")
    
    def snooze_reminder(self, popup, minutes):
        """Snooze reminder for specified minutes"""
        popup.destroy()
        self.last_reminder_time = datetime.now() + timedelta(minutes=minutes)
    
    def start_break(self, duration_minutes=None):
        """Start a break period"""
        self.in_break = True
        if duration_minutes:
            self.break_end_time = datetime.now() + timedelta(minutes=duration_minutes)
        else:
            self.break_end_time = None
        
        # Reset reminder timer when break starts
        self.last_reminder_time = datetime.now()
        self.update_ui_status()
    
    def end_break(self):
        """End the current break"""
        self.in_break = False
        self.break_end_time = None
        # Reset reminder timer when break ends
        self.last_reminder_time = datetime.now()
        self.update_ui_status()
    
    def log_activity(self, activity, activity_type="Work"):
        """Log activity to CSV file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate duration if there was a previous activity
        duration = ""
        if hasattr(self, 'last_log_time') and self.last_log_time:
            duration_delta = datetime.now() - self.last_log_time
            duration = str(int(duration_delta.total_seconds() / 60))  # Duration in minutes
        
        self.last_log_time = datetime.now()
        
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, activity, activity_type, duration])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to log activity: {e}")
    
    def show_settings(self):
        """Show settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.transient(self.root)
        
        main_frame = ttk.Frame(settings_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Reminder interval
        ttk.Label(main_frame, text="Reminder Interval (hours):").grid(row=0, column=0, sticky=tk.W, pady=2)
        interval_var = tk.StringVar(value=self.config.get('SETTINGS', 'reminder_interval_hours'))
        ttk.Entry(main_frame, textvariable=interval_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Snooze duration
        ttk.Label(main_frame, text="Snooze Duration (minutes):").grid(row=1, column=0, sticky=tk.W, pady=2)
        snooze_var = tk.StringVar(value=self.config.get('SETTINGS', 'snooze_duration_minutes'))
        ttk.Entry(main_frame, textvariable=snooze_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Work hours
        ttk.Label(main_frame, text="Enable Work Hours Only:").grid(row=2, column=0, sticky=tk.W, pady=2)
        work_hours_var = tk.BooleanVar(value=self.config.getboolean('SETTINGS', 'enable_work_hours_only'))
        ttk.Checkbutton(main_frame, variable=work_hours_var).grid(row=2, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(main_frame, text="Work Start Time (HH:MM):").grid(row=3, column=0, sticky=tk.W, pady=2)
        start_time_var = tk.StringVar(value=self.config.get('SETTINGS', 'work_hours_start'))
        ttk.Entry(main_frame, textvariable=start_time_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(main_frame, text="Work End Time (HH:MM):").grid(row=4, column=0, sticky=tk.W, pady=2)
        end_time_var = tk.StringVar(value=self.config.get('SETTINGS', 'work_hours_end'))
        ttk.Entry(main_frame, textvariable=end_time_var, width=10).grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Log file location
        ttk.Label(main_frame, text="Log File:").grid(row=5, column=0, sticky=tk.W, pady=2)
        ttk.Label(main_frame, text=os.path.abspath(self.log_file)).grid(row=5, column=1, columnspan=2, sticky=tk.W, pady=2)
        
        def save_settings():
            try:
                # Validate inputs
                try:
                    interval = float(interval_var.get())
                    if interval <= 0:
                        raise ValueError("Reminder interval must be positive")
                except ValueError:
                    messagebox.showerror("Error", "Invalid reminder interval value")
                    return
                
                try:
                    snooze = int(snooze_var.get())
                    if snooze <= 0:
                        raise ValueError("Snooze duration must be positive")
                except ValueError:
                    messagebox.showerror("Error", "Invalid snooze duration value")
                    return
                
                # Validate time format
                try:
                    datetime.strptime(start_time_var.get(), '%H:%M')
                    datetime.strptime(end_time_var.get(), '%H:%M')
                except ValueError:
                    messagebox.showerror("Error", "Invalid time format. Please use HH:MM")
                    return
                
                self.config.set('SETTINGS', 'reminder_interval_hours', interval_var.get())
                self.config.set('SETTINGS', 'snooze_duration_minutes', snooze_var.get())
                self.config.set('SETTINGS', 'enable_work_hours_only', str(work_hours_var.get()))
                self.config.set('SETTINGS', 'work_hours_start', start_time_var.get())
                self.config.set('SETTINGS', 'work_hours_end', end_time_var.get())
                
                with open(self.config_file, 'w') as f:
                    self.config.write(f)
                
                messagebox.showinfo("Success", "Settings saved successfully!")
                settings_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {e}")
        
        # Save and cancel buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def export_csv(self):
        """Export log to a new CSV file with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"clockify_export_{timestamp}.csv"
        
        try:
            import shutil
            shutil.copy2(self.log_file, export_filename)
            messagebox.showinfo("Success", f"Log exported to {export_filename}")
            return export_filename
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
            return None
    
    def show_about(self):
        """Show about dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About Clockify Helper")
        about_window.geometry("400x250")
        about_window.transient(self.root)
        about_window.grab_set()
        
        main_frame = ttk.Frame(about_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # App title and version
        ttk.Label(main_frame, text="Clockify Helper", font=("Arial", 16, "bold")).grid(row=0, column=0, pady=5)
        ttk.Label(main_frame, text="Version 1.0.0").grid(row=1, column=0, pady=5)
        
        # Description
        description = """A background application that helps you track your time 
without constantly interrupting your workflow. It periodically 
asks what you're working on and logs your activities."""
        ttk.Label(main_frame, text=description, wraplength=380).grid(row=2, column=0, pady=10)
        
        # Close button
        ttk.Button(main_frame, text="Close", command=about_window.destroy).grid(row=3, column=0, pady=10)
    
    def hide_window(self):
        """Hide the main window"""
        self.root.withdraw()
    
    def show_window(self):
        self.root.deiconify()
        self.root.state('normal')  # Ensure not minimized
        self.root.lift()
        self.refresh_activities_list()
        self.update_ui_status()
    
    def quit_app(self):
        """Quit the application"""
        self.running = False
        self.root.quit()
        sys.exit()

def main():
    """Main application entry point"""
    print("Clockify Helper Application")
    print("==========================")
    print("Starting application...")
    
    app = ClockifyHelper()
    app.show_window()  # Show the main window
    
    print("Application started successfully!")
    print("The application is running.")
    
    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down...")
        app.quit_app()

if __name__ == "__main__":
    main()