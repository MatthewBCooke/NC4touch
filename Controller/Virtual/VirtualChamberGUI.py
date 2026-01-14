"""
Virtual Chamber GUI - Interactive interface for simulating chamber hardware.

Provides a visual interface to:
- View and interact with virtual touchscreens
- Simulate beam breaks
- Monitor LED states, buzzer activity, and reward dispensing
- Control all virtual hardware components for testing
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import os

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualChamberGUI:
    """
    Interactive GUI for controlling and monitoring a virtual chamber.
    """

    def __init__(self, virtual_chamber, update_interval=100):
        """
        Initialize the GUI.
        
        Args:
            virtual_chamber: VirtualChamber instance to control
            update_interval: GUI update interval in milliseconds
        """
        self.chamber = virtual_chamber
        self.update_interval = update_interval

        # Create main window
        self.root = tk.Tk()
        self.root.title(f"Virtual Chamber - {self.chamber.config['chamber_name']}")
        self.root.geometry("1200x800")

        # State tracking
        self._running = False
        
        # Image cache for PhotoImage objects
        self._image_cache = {}
        self._canvas_images = {'left': None, 'middle': None, 'right': None}

        self._create_ui()
        self._start_update_loop()

        logger.info("Virtual Chamber GUI initialized")

    def _create_ui(self):
        """Create the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="🖥️ Virtual Touchscreen Chamber",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # ===== Touchscreen Section =====
        self._create_touchscreen_section(main_frame)

        # ===== Peripherals Section =====
        self._create_peripherals_section(main_frame)

        # ===== Status Section =====
        self._create_status_section(main_frame)

    def _create_touchscreen_section(self, parent):
        """Create touchscreen control panels."""
        # Container for touchscreens
        ts_frame = ttk.LabelFrame(parent, text="Touchscreens", padding="10")
        ts_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        # Left, Middle, Right screens
        self.screen_canvases = {}
        self.screen_labels = {}
        self.screen_touch_btns = {}

        for i, (name, m0) in enumerate([
            ("Left", self.chamber.left_m0),
            ("Middle", self.chamber.middle_m0),
            ("Right", self.chamber.right_m0)
        ]):
            # Frame for each screen
            screen_frame = ttk.Frame(ts_frame)
            screen_frame.grid(row=0, column=i, padx=10)

            # Title
            ttk.Label(
                screen_frame,
                text=f"{name} Screen ({m0.id})",
                font=('Arial', 10, 'bold')
            ).pack()

            # Canvas for touchscreen (scaled down representation)
            canvas = tk.Canvas(
                screen_frame,
                width=160,
                height=240,
                bg='black',
                highlightthickness=2,
                highlightbackground='gray'
            )
            canvas.pack(pady=5)
            self.screen_canvases[name.lower()] = canvas

            # Bind click events
            canvas.bind('<Button-1>', lambda e, m=m0, n=name: self._handle_screen_click(e, m, n))

            # Status label
            status_label = ttk.Label(screen_frame, text="No image", foreground='gray')
            status_label.pack()
            self.screen_labels[name.lower()] = status_label

            # Touch button
            touch_btn = ttk.Button(
                screen_frame,
                text="Simulate Touch",
                command=lambda m=m0: self._simulate_touch(m)
            )
            touch_btn.pack(pady=5)
            self.screen_touch_btns[name.lower()] = touch_btn

    def _create_peripherals_section(self, parent):
        """Create peripheral control panels."""
        # Beam Break
        bb_frame = ttk.LabelFrame(parent, text="Beam Break Sensor", padding="10")
        bb_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)

        self.bb_status_label = ttk.Label(bb_frame, text="● Not Broken", foreground='green')
        self.bb_status_label.pack()

        ttk.Button(
            bb_frame,
            text="Break Beam",
            command=self._break_beam
        ).pack(pady=5)

        ttk.Button(
            bb_frame,
            text="Restore Beam",
            command=self._restore_beam
        ).pack()

        # LEDs
        led_frame = ttk.LabelFrame(parent, text="LEDs", padding="10")
        led_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)

        ttk.Label(led_frame, text="Reward LED:").pack()
        self.reward_led_label = ttk.Label(led_frame, text="● OFF", foreground='gray')
        self.reward_led_label.pack()

        ttk.Label(led_frame, text="Punishment LED:").pack(pady=(10, 0))
        self.punishment_led_label = ttk.Label(led_frame, text="● OFF", foreground='gray')
        self.punishment_led_label.pack()

        # Buzzer & Reward
        misc_frame = ttk.LabelFrame(parent, text="Buzzer & Reward", padding="10")
        misc_frame.grid(row=2, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)

        ttk.Label(misc_frame, text="Buzzer:").pack()
        self.buzzer_label = ttk.Label(misc_frame, text="● Silent", foreground='gray')
        self.buzzer_label.pack()

        ttk.Label(misc_frame, text="Reward Pump:").pack(pady=(10, 0))
        self.reward_label = ttk.Label(misc_frame, text="● Stopped", foreground='gray')
        self.reward_label.pack()

        self.reward_count_label = ttk.Label(misc_frame, text="Dispensed: 0")
        self.reward_count_label.pack(pady=5)

    def _create_status_section(self, parent):
        """Create status/log section."""
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding="10")
        status_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # Text widget for logs
        self.log_text = tk.Text(status_frame, height=10, width=100, state='disabled')
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(status_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Control buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Get Chamber State", command=self._print_state).pack(side=tk.LEFT, padx=5)

    def _handle_screen_click(self, event, m0_device, screen_name):
        """Handle click on touchscreen canvas."""
        # Scale coordinates (canvas is 160x240, real screen is 320x480)
        x = event.x * 2
        y = event.y * 2

        self._log(f"{screen_name} screen touched at ({x}, {y})")
        m0_device.simulate_touch(x, y, duration=0.2)

    def _simulate_touch(self, m0_device):
        """Simulate a touch at screen center."""
        m0_device.simulate_touch(160, 240, duration=0.2)
        self._log(f"{m0_device.id} touched at center")

    def _break_beam(self):
        """Simulate beam break."""
        self.chamber.beambreak.simulate_break()
        self._log("Beam broken (animal at hopper)")

    def _restore_beam(self):
        """Restore beam."""
        self.chamber.beambreak.simulate_restore()
        self._log("Beam restored (animal left hopper)")

    def _print_state(self):
        """Print current chamber state."""
        state = self.chamber.get_state()
        self._log("="*50)
        self._log("CHAMBER STATE:")
        self._log(f"  Left M0: {'TOUCHED' if state['left_m0']['is_touched'] else 'not touched'}")
        self._log(f"    Image: {state['left_m0']['current_image'] or 'none'}")
        self._log(f"  Right M0: {'TOUCHED' if state['right_m0']['is_touched'] else 'not touched'}")
        self._log(f"    Image: {state['right_m0']['current_image'] or 'none'}")
        self._log(f"  Beam: {'BROKEN' if state['beambreak']['state'] == 0 else 'intact'}")
        self._log(f"  Reward LED: {'ON' if state['reward_led']['is_on'] else 'OFF'}")
        self._log(f"  Punishment LED: {'ON' if state['punishment_led']['is_on'] else 'OFF'}")
        self._log(f"  Buzzer: {'ACTIVE' if state['buzzer']['is_active'] else 'silent'}")
        self._log(f"  Reward: {'DISPENSING' if state['reward']['is_dispensing'] else 'stopped'}")
        self._log(f"  Total rewards: {state['reward']['total_dispensed']}")
        self._log("="*50)

    def _display_image_on_canvas(self, canvas, image_path, screen_name):
        """Load and display a BMP image on a canvas."""
        try:
            # Check cache first
            if image_path not in self._image_cache:
                # Load and resize image to fit canvas (160x240)
                pil_image = Image.open(image_path)
                pil_image = pil_image.resize((160, 240), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(pil_image)
                self._image_cache[image_path] = photo
            else:
                photo = self._image_cache[image_path]
            
            # Display on canvas
            canvas.delete('all')
            self._canvas_images[screen_name] = canvas.create_image(80, 120, image=photo)
            
        except Exception as e:
            logger.warning(f"Could not load image {image_path}: {e}")
            # Fallback display
            canvas.delete('all')
            canvas.create_rectangle(10, 10, 150, 230, fill='darkgray', outline='red')
            canvas.create_text(80, 120, text="Error\nloading\nimage", fill='white', justify='center')
    
    def _update_ui(self):
        """Update UI elements based on current chamber state."""
        state = self.chamber.get_state()

        # Update touchscreen displays
        for screen_name, m0_key in [
            ('left', 'left_m0'),
            ('middle', 'middle_m0'),
            ('right', 'right_m0')
        ]:
            canvas = self.screen_canvases[screen_name]
            label = self.screen_labels[screen_name]
            m0_state = state[m0_key]

            # Update canvas color based on touch state
            if m0_state['is_touched']:
                canvas.config(highlightbackground='red', highlightthickness=4)
            else:
                canvas.config(highlightbackground='gray', highlightthickness=2)

            # Update image display and label
            img_name = m0_state['current_image']
            img_path = getattr(self.chamber.m0s[['left', 'middle', 'right'].index(screen_name)], '_current_image_path', None)
            
            if img_name:
                # Update label
                display_name = img_name if '/' not in img_name else img_name.split('/')[-1]
                label.config(text=f"Image: {display_name}", foreground='white')
                
                # Try to display actual image on canvas
                if HAS_PIL and img_path and os.path.exists(img_path):
                    self._display_image_on_canvas(canvas, img_path, screen_name)
                else:
                    # Fallback: show white rectangle to indicate image present
                    canvas.delete('all')
                    canvas.create_rectangle(10, 10, 150, 230, fill='white', outline='gray')
                    canvas.create_text(80, 120, text=display_name, fill='black', width=130)
            else:
                label.config(text="No image", foreground='gray')
                canvas.delete('all')  # Clear canvas

        # Update beam break
        if state['beambreak']['state'] == 0:
            self.bb_status_label.config(text="● BROKEN", foreground='red')
        else:
            self.bb_status_label.config(text="● Not Broken", foreground='green')

        # Update LEDs
        if state['reward_led']['is_on']:
            self.reward_led_label.config(
                text=f"● ON (brightness: {state['reward_led']['brightness']})",
                foreground='yellow'
            )
        else:
            self.reward_led_label.config(text="● OFF", foreground='gray')

        if state['punishment_led']['is_on']:
            self.punishment_led_label.config(
                text=f"● ON (brightness: {state['punishment_led']['brightness']})",
                foreground='red'
            )
        else:
            self.punishment_led_label.config(text="● OFF", foreground='gray')

        # Update buzzer
        if state['buzzer']['is_active']:
            self.buzzer_label.config(
                text=f"♪ ACTIVE ({state['buzzer']['frequency']}Hz)",
                foreground='orange'
            )
        else:
            self.buzzer_label.config(text="● Silent", foreground='gray')

        # Update reward
        if state['reward']['is_dispensing']:
            self.reward_label.config(text="● DISPENSING", foreground='blue')
        else:
            self.reward_label.config(text="● Stopped", foreground='gray')

        self.reward_count_label.config(
            text=f"Dispensed: {state['reward']['total_dispensed']}"
        )

    def _start_update_loop(self):
        """Start the GUI update loop."""
        def update():
            if self._running:
                self._update_ui()
                self.root.after(self.update_interval, update)

        self._running = True
        self.root.after(self.update_interval, update)

    def _log(self, message):
        """Add message to log window."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _clear_log(self):
        """Clear the log window."""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')

    def run(self):
        """Run the GUI (blocking)."""
        logger.info("Starting Virtual Chamber GUI...")
        self._log("Virtual Chamber GUI started")
        self._log("Click on touchscreens to simulate touches")
        self._log("Use buttons to control beam break and view state")
        self.root.mainloop()
        self._running = False

    def run_async(self):
        """Run the GUI in a separate thread (non-blocking)."""
        gui_thread = threading.Thread(target=self.run, daemon=True)
        gui_thread.start()
        logger.info("Virtual Chamber GUI started in background thread")
        return gui_thread
