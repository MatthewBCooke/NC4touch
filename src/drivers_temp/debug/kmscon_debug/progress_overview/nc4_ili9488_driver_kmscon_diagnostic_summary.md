
# Final Document: nc4_ili9488 Driver Project

## **Abstract**
This document provides a comprehensive summary of the nc4_ili9488 driver project for dual ILI9488-based TFT LCDs on a Raspberry Pi. The project aims to eliminate dependency on kmscon, transition to software-controlled chip select (CS), and enhance the driver for seamless multi-display support. Key challenges include overlay misconfigurations, incomplete DRM/KMS pipeline setups, and framebuffer locking by kmscon. Actionable recommendations and a phased implementation plan are provided to address these issues and achieve a self-sufficient driver solution. This document consolidates findings from multiple debugging sessions and outlines a structured approach to address these challenges, including overlay validation, user-space utility testing, and phased driver enhancements.

---

## High-Level Overview

### LCD Display Driver

- The core of the project is a custom driver (`nc4_ili9488`) for two ILI9488-based SPI TFT displays on a Raspberry Pi 4 running Debian Bookworm integrated with the Direct Rendering Manager (DRM) subsystem, which will ultimaitely need to support three displays.
- The driver hooks into the DRM/KMS subsystem in Linux, which handles display output (framebuffers, modesetting, etc.).

**The `nc4_ili9488.c` Driver**
- Manages ILI9488 LCD panels via SPI on a Raspberry Pi.
- Provides a framebuffer interface (e.g., `/dev/fb0`) for applications to render content.
- Handles:
  - **Initialization Commands**: Sends required sequences to the LCDs during startup.
  - **GPIO Control**: Manages reset, data/command (DC), and backlight signals.
  - **SPI Communication**: Transfers data to the LCDs via SPI.

**The `nc4_ili9488.dts` Overlay**
- Configures hardware to enable SPI communication for the displays.
- Supports SPI0 (and potentially SPI1), mapping GPIOs for:
  - **Reset**: To reinitialize the displays.
  - **DC**: For toggling between data and command modes.
  - **Backlight**: Shared across all connected displays.
- Maps each display as a unique SPI device using separate chip selects.
- Integrates with the Linux device tree to ensure compatibility and proper hardware setup.
- Supports multiple displays with shared SPI and backlight control while maintaining unique configurations for each display.

## The Role of `kmscon`

### What `kmscon` Does
- `kmscon` is a terminal emulator that configures the DRM/KMS pipeline during boot.
- Key actions performed by `kmscon`:
  1. **Requests DRM Master Status**: Gains control over the display hardware.
  2. **Creates Dumb Buffers**: Allocates memory for the framebuffers.
  3. **Attaches Buffers to CRTCs**: Links displays (connectors) to the GPU pipeline.
  4. **Issues Page Flips**: Updates the display with active content, fully activating the hardware.

### Interaction with the `nc4_ili9488` Driver
- The `nc4_ili9488` driver implements only part of the necessary DRM/KMS steps:
  - As a result, without `kmscon`, the first LCD remains uninitialized and shows a default blank (white) screen.
- When `kmscon` is enabled:
  - It completes the missing DRM/KMS steps, enabling multi-display functionality.
  - However, it locks the framebuffers for its own console layer, preventing other applications (e.g., `fbi`) from using them.

### The Problem
- `kmscon` (a terminal emulator using the `kms++` library) is automatically performing certain DRM/KMS setup steps that the driver isn’t handling yet.
- When `kmscon` runs at boot:
  - Both displays work, but the framebuffers get locked by `kmscon`, preventing apps like `fbi` from displaying images.
- When `kmscon` is disabled (or not run at the correct time):
  - One display remains blank because the driver isn’t performing all the necessary DRM/KMS steps on its own.

### Why `kmscon` Matters
- `kmscon` performs these critical DRM/KMS steps:
  1. **Atomic Mode-Setting**: Links displays (connectors) to the GPU pipeline (CRTCs).
  2. **Framebuffer Management**: Creates and manages framebuffers using “dumb buffers” in the DRM subsystem.
  3. **Page Flips**: Issues updates to the screen with new content.
- This setup ensures that, with `kmscon` running, both displays power on and show a mirrored console login prompt. The displays work because `kmscon` properly initializes them.

### Driver vs. `kmscon`
- The driver’s initialization routines currently do not replicate all the essential DRM steps (`kmscon` does, like creating a framebuffer and performing page flips).
- As a result, if `kmscon` isn’t present, the first display stays in its default “white screen” state.

### Overlay and Other Factors
- Overlay misconfigurations and possible GPIO issues complicate early initialization:
  - Warnings related to `cs-gpios`, `reset-gpios`, or `dc-gpios` might indicate incorrect or incomplete settings.
  - These issues lead to inconsistent behavior during boot.

### SPI Bus Plans
- Moving from SPI0 to SPI1 is under consideration to improve layout and flexibility.
- However, this doesn’t solve the fundamental issue of missing DRM/KMS setup steps. The driver still needs to replicate what `kmscon` does, regardless of the SPI bus used.
- In fact, the near working version of the driver that uses SPI1 does not seem to be able to take advantage of `kmscon` like we are able to with SPI0, for reasons unknown. As a consiquence, we have been unable to get more than one display working using the SPI1 bus.

### **Hardware Overview**
The pin mapping here is what was used when these data were collected.
- **Shared Resources**:
  - Power: Pin 1/17 for 3.3V, Pin 6/9 for GND.
  - SPI Interface: MOSI (Pin 19), SCLK (Pin 23), shared backlight (Pin 12, GPIO 18).
- **LCD_0**:
  - CS: GPIO 8 (CE0), DC: GPIO 25, RES: GPIO 24.
- **LCD_1**:
  - CS: GPIO 7 (CE1), DC: GPIO 27, RES: GPIO 23.

### **Hardware Overview**
The pin mapping here represents the current configuration.
- **Shared Resources**:
  - Power: Pin 1/17 for 3.3V, Pin 6/9 for GND.
  - SPI Interface: MOSI (Pin 19), SCLK (Pin 23), shared backlight (Pin 13, GPIO 27).
- **LCD_0**:
  - CS: GPIO 8 (CE0), DC: GPIO 24, RES: GPIO 25.
- **LCD_1**:
  - CS: GPIO 7 (CE1), DC: GPIO 22, RES: GPIO 23.

**The goal in this chat was to:**
1. Transition the driver to software-controlled CS for improved flexibility and scalability.
2. Remove the dependency on kmscon, a terminal emulator currently critical for display initialization during boot.
3. Enhance the driver’s DRM/KMS pipeline setup to support seamless multi-display initialization and operation.
**Note that we reverted back to using hardware CS after this.**

### **Key Challenges**
- **kmscon Dependency**:
  kmscon performs critical DRM/KMS configurations during boot, which the driver lacks, necessitating manual overlay application post-boot.
- **Overlay and Driver Issues**:
  Warnings related to `cs-gpios` and other properties hinder consistent display initialization. Note, I believe these have largely been resolved but I am unsure.
- **Framebuffer Locking**:
  kmscon locks `/dev/fb0` and `/dev/fb1`, preventing other applications from rendering to the displays.
- **DRM/KMS Pipeline Gaps**:
  Missing steps like atomic state setup, framebuffer linking, and page flips during driver initialization.

## Project Goal: Eliminating `kmscon` Dependency

### Objective
- Remove reliance on `kmscon` for display initialization in the `nc4_ili9488` driver project.

### SPI Bus Transition and Challenges
- Transition from SPI0 to SPI1:
  - We will need to transition from SPI0 to SPI1 to support a third monitor using hardwre CS.
  - Existing delayed overlay loading workaround does not work with SPI1, as `kmscon` fails to enable multi-display support on this bus.

### Key Steps
- Replicate critical DRM/KMS pipeline setup steps directly within the driver or through a modular, testable solution:
  1. **Framebuffer Linking**: Associate buffers with CRTCs and connectors.
  2. **Atomic State Updates**: Configure and commit display settings.
  3. **Page Flips**: Refresh displays with active content.

### Approach
- Implement a simple, minimally intrusive solution.
- Ensure the driver operates independently and robustly across both SPI0 and SPI1, eliminating dependency on `kmscon`.

### Requirement
- We do not need a text-based console on the dual SPI displays.
- The goal is to ensure both displays initialize properly at boot without relying on `kmscon`.
- We are even open to not having the overlay and driver load at boot if this presents a more tractable solution.

### Current Situation
- `kmscon` provides the missing DRM/KMS steps for SPI0, enabling both displays.
- Transitioning to SPI1 is necessary for improved flexibility, but `kmscon` cannot be easily used for multi-display support on SPI1.

### Approach
- Develop a streamlined, minimally disruptive solution that is:
  - **Simple**: Straightforward to implement with minimal complexity.
  - **Non-Intrusive**: Requires minimal changes to the core driver, overlay, and source code.
  - **Efficient**: Focused on replicating only the essential DRM/KMS actions performed by `kmscon`.

- Design a self-contained implementation to:
  1. Enable both displays at boot.
  2. Assign and manage framebuffers for each display.

- Avoid incorporating unnecessary components, such as a terminal emulator or console layer.

- Prioritize maintaining robust and independent multi-display functionality, ensuring the system operates seamlessly without `kmscon`.

## **Challenges and Findings**

### **1. kmscon Dependency**

**Challenge**: The driver relies on kmscon for critical DRM/KMS configurations during boot, including atomic state setup, framebuffer linking, and page flips. Without kmscon, the displays fail to initialize fully when the overlay is applied via config.txt.

**Findings**:

- kmscon performs essential ioctl calls (`DRM_IOCTL_MODE_CREATE_DUMB`, `DRM_IOCTL_MODE_ADDFB`, and `DRM_IOCTL_MODE_PAGE_FLIP`) to complete the DRM pipeline.
- These steps link CRTCs, connectors, and framebuffers, enabling multi-display functionality.
- Framebuffer locking by kmscon (e.g., on `/dev/fb0` and `/dev/fb1`) prevents applications like `fbi` from rendering.

**Implication**: The driver must replicate kmscon’s functionality to initialize displays independently.

---

### **2. Overlay and Driver Issues**

**Challenge**: Device tree overlay warnings and misconfigurations hinder consistent GPIO setup and driver functionality during boot.

**Findings**:

- Warnings include missing or incorrect `cs-gpios`, `reset-gpios`, and `dc-gpios` properties. I am unsure if this is still an issue.
- The overlay works when applied manually post-boot but fails during boot, indicating timing or dependency conflicts.
- Driver initialization lacks steps to fully configure CRTCs, connectors, and framebuffers.

**Implication**: Addressing overlay warnings and enhancing driver setup are critical for robust display initialization.

---

### **3. Framebuffer Locking**

**Challenge**: kmscon locks framebuffers during operation, limiting their use by other applications.

**Findings**:

- The locking stems from kmscon’s terminal emulation using `agetty`.
- Without kmscon, one display remains uninitialized, highlighting gaps in the driver’s framebuffer handling.

**Implication**: The driver must avoid framebuffer conflicts while ensuring complete initialization.

---

### **4. DRM/KMS Pipeline Gaps**

**Challenge**: The driver fails to fully configure the DRM pipeline during boot, leaving key steps incomplete.

**Findings**:

- Missing functionalities include:
  - Explicitly assigning CRTCs to connectors.
  - Creating and associating dumb buffers with framebuffers.
  - Triggering display updates via page flips.
- Debugging logs confirm the driver performs some mode-setting but lacks comprehensive pipeline setup.

**Implication**: Enhancing the driver’s DRM/KMS functionality is essential to achieve independence from kmscon.

---

### **5. SPI Bus Considerations**

**Challenge**: Transitioning to SPI1 from SPI0 offers potential benefits but requires validation.

**Findings**:

- SPI1 supports three hardware CE lines, providing flexibility for additional devices.
- DRM/KMS operations are bus-agnostic, making SPI1 a feasible alternative.

**Implication**: Updating the overlay and driver for SPI1 compatibility could simplify the setup and improve scalability.

---

### **6. Debugging Insights**

**Findings**:

- DRM state and framebuffer logs confirm correct mode-setting and resource linking when the driver is manually loaded.
- GPIO state checks highlight missing configurations for specific pins (`GPIO23` and `GPIO27`) in the overlay.
- User-space utilities successfully interact with DRM devices, validating the feasibility of replicating kmscon’s DRM interactions.

---

## **Proposed Solutions and Implementation Plan**

### **1. Driver Enhancements**

**Objective**: Replicate kmscon’s critical DRM/KMS pipeline steps within the nc4_ili9488 driver.

**Steps**:

1. **DRM Master Control**:
   - Implement `DRM_IOCTL_SET_MASTER` to claim DRM master control during initialization.
   - Resolve conflicts with other DRM clients (e.g., kmscon).

2. **Atomic State Setup**:
   - Explicitly assign CRTCs to connectors.
   - Create and associate dumb buffers with framebuffers using `DRM_IOCTL_MODE_CREATE_DUMB` and `DRM_IOCTL_MODE_ADDFB`.
   - Enable planes and trigger display updates using `DRM_IOCTL_MODE_PAGE_FLIP`.

3. **Enhanced Debugging**:
   - Add runtime checks for GPIO states and SPI registration.
   - Include detailed logs for DRM/KMS pipeline actions.

---
### **2. Overlay Adjustments**

**Objective**: Address misconfigurations to ensure consistent display initialization.

**Steps**:

1. **Define GPIO Properties**:
   - Fully specify `cs-gpios`, `reset-gpios`, and `dc-gpios` for all SPI devices. I do not believe this is relivant anymore.
   - Resolve overlay warnings (e.g., `#address-cells` and `#size-cells`). Again, I am unsure if this is still an issue.

2. **Validate Timing and Dependencies**:
   - Test overlay behavior during boot to identify timing-related conflicts.
   - Ensure compatibility with both SPI0 and SPI1.

---

### **3. Transition to SPI1 in Future**
**Note**: This can be disregarded for now as testing will continue using SP0 with two displays.

**Objective**: Improve scalability by leveraging SPI1’s third hardware CS to suppot a third display.

**Steps**:

1. **Update Overlay**:
   - Modify device tree properties to reflect SPI1 settings (e.g., `/dev/spidev1.0`, `/dev/spidev1.1`).
   - Validate GPIO assignments for SPI1 CE lines.

2. **Test Driver Compatibility**:
   - Verify driver functionality with SPI1 devices.
   - Compare performance and reliability across SPI0 and SPI1.

---

### **4. User-Space Utility for Testing**

**Objective**: Develop a modular utility to validate and refine DRM/KMS pipeline interactions.

**Steps**:

1. **Expand Utility Functionality**:
   - Query CRTCs, connectors, and framebuffers.
   - Implement test cases for framebuffer linking, atomic state updates, and page flips.

2. **Incremental Driver Integration**:
   - Use the utility to test and debug functionalities before integrating them into the driver.

---

### **5. Testing and Validation**

**Objective**: Ensure robust and reliable operation across all configurations.

**Steps**:

1. **Overlay Validation**:
   - Test the updated overlay for proper GPIO setup and SPI device registration.
   - Resolve any warnings or errors during boot.

2. **Driver Testing**:
   - Verify display initialization and functionality during boot.
   - Test framebuffer updates, page flips, and multi-display support.

3. **SPI1 Transition Validation**:
   - Confirm consistent behavior and performance across SPI0 and SPI1.

---
## **Testing and Validation**

### **1. Overlay Validation**

**Objective**: Ensure the updated overlay correctly configures GPIOs and SPI devices for consistent initialization.

**Tests**:

1. **Device Tree Inspection**:
   - Verify the presence and correctness of `cs-gpios`, `reset-gpios`, and `dc-gpios` for all SPI devices in `/proc/device-tree`.
   - Confirm that overlay warnings (`#address-cells`, `#size-cells`) are resolved.

2. **Boot-Time Behavior**:
   - Apply the overlay during boot and check for successful GPIO configuration and SPI device registration.

3. **Cross-SPI Testing**:
   - Test the overlay on both SPI0 and SPI1 to ensure compatibility and consistency.

---

### **2. Driver Functionality Testing**

**Objective**: Validate the driver’s ability to initialize displays and manage the DRM/KMS pipeline independently.

**Tests**:

1. **Display Initialization**:
   - Confirm that both displays are initialized and operational during boot without kmscon.
   - Verify DRM logs for successful mode-setting, framebuffer linking, and atomic state updates.

2. **Multi-Display Support**:
   - Test simultaneous operation of LCD_0 and LCD_1.
   - Validate independent framebuffer updates and page flips for each display.

3. **Debugging Enhancements**:
   - Use runtime logs to confirm GPIO state changes, SPI transactions, and DRM pipeline actions.

---

### **3. User-Space Utility Validation**

**Objective**: Refine and validate the utility for testing DRM/KMS interactions.

**Tests**:

1. **CRTC and Connector Queries**:
   - Enumerate CRTCs and connectors associated with the driver.
   - Confirm that all resources are properly linked.

2. **Framebuffer Updates**:
   - Test framebuffer linking, atomic state updates, and page flips.
   - Compare results against kmscon’s behavior.

3. **Driver Integration**:
   - Use the utility to validate incremental enhancements in the driver.

---

### **4. SPI1 Transition Validation for Future**
**Note**: This can be disregarded for now as testing will continue using SP0 with two displays.

**Objective**: Confirm consistent driver and overlay functionality after transitioning to SPI1.

**Tests**:

1. **SPI1 GPIO Setup**:
   - Verify that SPI1 CE lines (GPIO 18, GPIO 17, GPIO 16) are correctly assigned and toggled.
   - Confirm that SPI1 devices are properly registered.

2. **Driver Compatibility**:
   - Test the driver’s functionality with SPI1-based devices.
   - Validate performance and reliability under multi-display scenarios.

3. **Cross-Bus Comparison**:
   - Compare driver and overlay behavior across SPI0 and SPI1 to identify any discrepancies.

---
## **Conclusion and Next Steps**

### **Summary of Diagnostic Context**

The nc4_ili9488 driver project is centered on supporting dual ILI9488-based TFT LCDs on a Raspberry Pi, with the overarching goal of achieving a self-sufficient driver capable of initializing and managing displays independently. The dependency on kmscon for critical DRM/KMS configurations, along with overlay misconfigurations and incomplete driver initialization during boot, emerged as key challenges.

### **Key Findings**

1. **kmscon's Role**:
   - Kmscon performs essential DRM/KMS tasks, including framebuffer linking, atomic state setup, and page flips, which the driver lacks. This dependency highlights the driver’s current limitations in managing multi-display setups autonomously.
2. **Overlay and Driver Gaps**:
   - Device tree overlays exhibit misconfigurations (`cs-gpios`, `reset-gpios`, `dc-gpios`), resulting in incomplete GPIO setup during boot. These issues exacerbate the driver’s inability to fully initialize displays.
3. **Framebuffer Locking and Multi-Display Challenges**:
   - Kmscon locks framebuffer devices during operation, preventing concurrent rendering by other applications. Without kmscon, one display remains uninitialized, underlining the gaps in the driver’s framebuffer handling.
4. **Potential for SPI1 Transition**:
   - SPI1 provides additional hardware CE lines, offering a scalable alternative to SPI0. However, validation is needed to confirm consistent functionality across SPI buses.
5. **User-Space Utility Insights**:
   - User-space testing utilities successfully interacted with DRM/KMS subsystems, demonstrating the feasibility of refining driver logic incrementally.

### **Implications and Unresolved Questions**

- **Dependency Removal**: Transitioning away from kmscon requires integrating its critical DRM/KMS pipeline steps into the driver. This includes atomic state updates, framebuffer linking, and display synchronization.
- **Overlay Refinement**: Misconfigurations in the device tree overlay must be resolved to ensure reliable initialization during boot across both SPI0 and SPI1.
- **Testing Frameworks**: The success of user-space utilities suggests a pathway for structured driver refinement, though the scope of these tools must expand to cover kmscon-equivalent functionality.

## **Recommendations and Next Steps**

1. **Overlay Refinement**:
   - Resolve all warnings and misconfigurations, including `cs-gpios`, `reset-gpios`, and `dc-gpios`.
   - Validate the overlay for compatibility with SPI0 and SPI1.

2. **Driver Enhancements**:
   - Integrate kmscon-like DRM pipeline setup steps, including framebuffer linking, atomic state initialization, and page flips.
   - Add runtime checks and enhanced debugging to monitor GPIO, SPI, and DRM states.

3. **User-Space Utility Development**:
   - Extend user-space utilities to validate advanced DRM interactions, such as framebuffer updates and atomic state management.
   - Use the utility to validate incremental driver improvements.

4. **Testing and Validation**:
   - Conduct comprehensive testing of updated drivers and overlays during boot and runtime.
   - Validate functionality and performance across SPI0 and SPI1 to ensure robust display initialization and operation.

5. **SPI1 Transition**:
   - Update the overlay and driver configurations for SPI1 and validate their compatibility.
---

## **Logging Overview**

### Comparison of `kmscon` Enabled vs. Disabled Logs
This document summarizes key differences observed in the log files when `kmscon` was **enabled** versus **disabled** during the initialization and operation of the dual ILI9488 LCD displays.

### 1. DRM Pipeline Configuration

- **Atomic State Initialization**:
  - `drm_atomic_state_init` shows variations in state allocation and clearing between the two configurations.
  - Different objects (planes, CRTCs, and connectors) are linked or released.

- **Pipeline Updates**:
  - Logs indicate differences in `drm_atomic_commit`, `drm_atomic_add_affected_connectors`, and related updates. These processes show the role of `kmscon` in enabling and setting up the DRM/KMS pipeline.

### 2. Framebuffer Activity

- **Framebuffer "Dirty" Updates**:
  - Commands like `drm_mipi_dbi18_fb_dirty` reflect variations in full-screen and partial updates for `spi0.0` and `spi0.1`.
  - `kmscon` appears to actively lock and modify framebuffer states, blocking other applications (e.g., `fbi`).

- **Buffer Conversion**:
  - `nc4_mipi_dbi18_buf_copy` highlights differences in pixel data formats and byte-order transformations during framebuffer operations.

### 3. Command Execution

- **MIPI DCS Commands**:
  - Commands (`cmd=2a`, `cmd=2b`, and `cmd=2c`) for setting window addresses and updating display memory vary between configurations.
  - Differences in data lengths and parameters suggest that `kmscon` might alter display behavior.

### 4. KMS Console Management

- **Framebuffer Locking**:
  - When `kmscon` is enabled, logs like `DRM_IOCTL_VERSION` show interactions locking framebuffers, preventing usage by other processes.

- **TTY and Display Activity**:
  - Logs from `kmscon` explicitly reference interaction with `/dev/tty1`, highlighting its role in virtual terminal management.

### Summary Table

| **Subsystem**           | **kmscon Enabled**                                 | **kmscon Disabled**                                |
|--------------------------|---------------------------------------------------|--------------------------------------------------|
| DRM Pipeline Setup       | Comprehensive `drm_atomic_commit` logs, multi-object updates | Minimal updates for `spi0.0`, less pipeline activity |
| Framebuffer Operations   | Active locking, `dirty` updates blocked for external tools | Framebuffers free, full updates for `spi0.1` only |
| Command Execution        | MIPI commands triggered, display updates for both `spi0.0` and `spi0.1` | Limited commands, `spi0.0` mostly idle |
| Virtual Terminal Mgmt    | TTY interactions and locks visible in logs        | No TTY interactions or framebuffer locks         |

### Conclusion

The logs indicate that `kmscon` actively manages the DRM pipeline and framebuffers during initialization, enabling both displays but locking them for external applications. When disabled, the framebuffers are free but initialization is incomplete, leaving `spi0.0` blank.

============================================================================================================================

# Analysis of `/dev/dri/card*` Handling by kmscon and the nc4_ili9488 Driver

## **Overview**

This document provides an analysis of how `/dev/dri/card*` (DRM device nodes) are handled by kmscon and the nc4_ili9488 driver, based on the diagnostic findings and test results. Understanding these interactions is critical to identifying and addressing gaps in the driver’s DRM/KMS pipeline setup.

---

## **kmscon’s Interaction with `/dev/dri/card*`**

1. **Opening DRM Devices**:
   - kmscon actively interacts with `/dev/dri/card0` and `/dev/dri/card1` using DRM ioctl commands such as `DRM_IOCTL_VERSION`, `DRM_IOCTL_MODE_CREATE_DUMB`, and `DRM_IOCTL_MODE_ADDFB`.
2. **Device Queries**:
   - Queries these devices to retrieve details about available CRTCs, connectors, and supported modes.
3. **Page Flip Control**:
   - Uses page flips to dynamically update displays with new framebuffers.
   - Locks `/dev/fb0` and `/dev/fb1` during operation to maintain control over framebuffer updates.

---

## **nc4_ili9488 Driver’s Interaction with `/dev/dri/card*`**

1. **Manual Initialization**:
   - When the driver is loaded manually post-boot, it:
     - Initializes both `/dev/dri/card0` and `/dev/dri/card1`.
     - Creates and links `/dev/fb0` and `/dev/fb1` to the respective cards.
2. **Incomplete Boot-Time Setup**:
   - During boot, the driver fails to:
     - Properly configure both cards.
     - Fully initialize LCD_0, leaving it unassigned or unlinked.
     - Dynamically update framebuffers or perform page flips.

---

## **Key Findings**

1. **kmscon Handles Cards Holistically**:
   - kmscon configures both `/dev/dri/card0` and `/dev/dri/card1` correctly by:
     - Assigning CRTCs and connectors.
     - Creating and linking framebuffers.
     - Managing framebuffer updates via page flips.
   - This ensures both displays initialize correctly.

2. **Driver’s Gaps**:
   - During boot, the driver does not:
     - Assign CRTCs to connectors effectively, leaving LCD_0 uninitialized.
     - Create or link framebuffers to `/dev/dri/card*`.
     - Trigger page flips to dynamically update the displays.

3. **Testing Results**:
   - **With kmscon Disabled**:
     - `/dev/dri/card0` and `/dev/dri/card1` are created, but only one display initializes, and framebuffers may remain inaccessible.
   - **With Overlay Applied Manually**:
     - The driver successfully creates `/dev/fb0` and `/dev/fb1` and links them to `/dev/dri/card0` and `/dev/dri/card1`.

---

## **Recommendations for Improvement**

1. **Driver Ownership of `/dev/dri/card*`**:
   - Fully claim `/dev/dri/card*` by assigning CRTCs, creating framebuffers, and linking them correctly during boot.
2. **Eliminate Dependency on kmscon**:
   - Replicate kmscon’s steps for initializing and managing `/dev/dri/card*`.
3. **Testing and Debugging**:
   - Conduct targeted tests to ensure `/dev/dri/card*` are initialized and linked properly during boot without kmscon.

---

This analysis highlights the gaps in how the driver interacts with `/dev/dri/card*` and provides actionable insights for achieving a fully independent driver.


============================================================================================================================

# KMSCON Explanation (Step-by-Step Comparison)

Below is a **step-by-step, narrative-style** explanation of how **kmscon** brings both displays to life compared to what your **nc4_ili9488** driver is currently *not* doing. I’ll use clunky or mixed metaphors so you have some simple mental hooks for each concept. Along the way, I’ll define the major technical terms and acronyms at an “idiot-level,” to help ensure each piece is clear.

---

## 1. DRM and KMS: The Big Show Organizer and the Stage Crew

### What is DRM?

- **DRM (Direct Rendering Manager)**: Think of DRM as the “big show organizer” for graphics in the Linux kernel. It coordinates who has the right to put images on the screen and how that process happens behind the scenes.

### What is KMS?

- **KMS (Kernel Mode Setting)**: KMS is like the “stage crew” that physically arranges and turns on the displays. It’s responsible for setting display modes (like resolution or refresh rate) and hooking up the screen to the right data pipeline inside the computer.

**Analogy**:  
Imagine you have a theater (your Raspberry Pi). The show organizer (DRM) decides who gets to perform on stage (which app or driver can write to the displays). The stage crew (KMS) picks up the sets and physically arranges them on stage (managing resolutions, hooking up the panels, etc.).

---

## 2. The Pipeline, Step by Step

To get images onto your screens, several steps must happen in the DRM/KMS pipeline. Here’s how **kmscon** handles them (and how your driver is currently coming up short):

1. **Asking for the Keys (DRM Master Status)**
   - **What kmscon does**: It walks up to the show organizer (DRM) and says, “I want to be the boss of the stage. Give me Master Status!” In code terms, it uses `DRM_IOCTL_SET_MASTER` or a similar mechanism to gain full control.
   - **Definition**:
     - **DRM Master**: The application/driver that currently has the right to change display settings.
   - **What your driver does not do**: It never formally “asks” to become the boss, so if nobody else (like kmscon) does it, the displays never get fully set up.

2. **Creating Dumb Buffers (Reserving Art Canvases)**
   - **What kmscon does**: It says, “I need a blank canvas to draw my pictures (the terminal text).” In DRM-speak, this is creating a **“dumb buffer”**—a simple chunk of memory used to store the image that goes on screen.
   - **Definition**:
     - **Dumb Buffer**: A basic piece of memory that the GPU can understand as an image. No fancy GPU acceleration—just a raw place to store pixels.
   - **Analogy**: It’s like kmscon goes to the art supply store and buys plain white poster boards so it can paint the terminal image onto them.
   - **What your driver does not do**: It doesn’t grab any blank canvases for itself, so there’s nowhere for the images to be drawn.

3. **Linking CRTCs and Connectors (Attaching the Video Pipeline to the Displays)**
   - **CRTC (Cathode Ray Tube Controller)**: In modern terms, think of a **CRTC** as the “pipeline” that fetches images from memory and sends them out to a display. You can have multiple CRTCs for multiple screens.
   - **Connector**: The physical connection (like HDMI or an SPI-attached LCD) that your monitor plugs into.
   - **What kmscon does**: It effectively says, “Hey, pipeline #1 (CRTC) should feed connector #1 (the first LCD), and pipeline #2 (CRTC) should feed connector #2 (the second LCD).”
   - **Analogy**: If the pipeline is a garden hose of images, the connector is the physical spout the water (pixels) comes out of to get to the display. kmscon sets up those hoses so each display gets the right water flow.
   - **What your driver does not do**: It never fully sets up the hoses. It partially tries, but crucial steps are missing—so the displays aren’t properly fed with image data.

4. **Attaching Buffers to the Pipeline (Putting the Canvas into the Slide Projector)**
   - **What kmscon does**: After creating the dumb buffers, kmscon says, “Okay pipeline #1, use this blank canvas I just made. That’s your piece of memory to display from now on.” This is sometimes called adding a “FB (framebuffer)” to the pipeline.
   - **Definition**:
     - **FB (Framebuffer)**: A chunk of memory that directly represents the pixels shown on screen.
   - **Analogy**: If the pipeline is a slide projector, the dumb buffer is the slide with the picture on it. kmscon inserts the slide into the projector so that the image can be shown on the wall (LCD).
   - **What your driver does not do**: It doesn’t put any “slides” into the projector. So even if the lights turn on, there’s no picture to show.

5. **Page Flips (Turning the Page to Show the Next Image)**
   - **What kmscon does**: Whenever kmscon has new terminal text to show, it issues a **page flip**. That’s a quick instruction telling the pipeline, “Now show the new buffer with the updated image.”
   - **Definition**:
     - **Page Flip**: A command that swaps the currently displayed framebuffer with a new one—like turning to a new page in a book or flipping to the next slide in a slideshow.
   - **Analogy**: You have two slides (images). You slide the old one out, slip the new one in, and the audience sees the new image with no weird flickering.
   - **What your driver does not do**: Your driver never issues that “Flip to the new image” instruction because it hasn’t created or attached the new images in the first place.

---

## 3. Framebuffers, Connectors, CRTCs, and Page Flips in Plain Language

Below is a quick cheat sheet of each object:

1. **Framebuffer (FB)**  
   - “The blank sheet of paper (or the painted sheet if you’re done drawing) where your final image lives before going to the screen.”

2. **CRTC**  
   - “The pipeline or conveyor belt that fetches the sheet of paper from memory and sends it to your display.”

3. **Connector**  
   - “The physical plug or socket that attaches the pipeline to your actual screen. It could be HDMI, DisplayPort, or in your case, a custom SPI-based LCD.”

4. **Page Flip**  
   - “The act of telling the pipeline: ‘Okay, swap the old sheet with the new one so the user sees the updated image immediately.’”

5. **Master Status**  
   - “Having the main key to the stage, letting you control all the behind-the-scenes stuff (display modes, resolution, hooking up monitors, etc.).”

---

## 4. Why kmscon Makes Both Displays Work, but Your Driver Doesn’t (Yet)

When the system boots **with kmscon**:

1. kmscon **takes Master Status**: It gets full permission to manage the displays.  
2. kmscon **creates dumb buffers** (the big blank canvases).  
3. kmscon **assigns these buffers** to each display (via CRTCs and connectors).  
4. kmscon **does a page flip**: Tells each display, “Show this new buffer!”  
5. Both displays light up, because kmscon has basically done all the building, wiring, and final ‘turn on the lights’ steps in the pipeline.

When the system boots **without kmscon**:

1. Your driver **has partial code** to talk to the displays (SPI signals, initialization commands for the ILI9488 controller, etc.).  
2. However, it **doesn’t do** the full “DRM Master → Dumb Buffer → Attach to Pipeline → Page Flip” dance.  
3. One screen remains white because it’s effectively never receiving a proper image feed. It’s like the pipeline hose never got turned on, or no “slide” was inserted into the projector.

---

## 5. Additional Bits: Overlays, GPIOs, SPI, and More

- **Overlay**: A **device tree overlay** is like a blueprint addendum that says “these pins are used for these purposes,” letting the kernel know which GPIO pins do what.
- **GPIO (General-Purpose Input/Output)**: A “simple on/off switch line” on the Raspberry Pi that can be toggled for things like Reset (RES), Data/Command (DC), or Chip Select (CS).
- **SPI (Serial Peripheral Interface)**: A “conveyor belt system” for sending data out to external devices like your ILI9488 LCD panels.

The reason you can switch from SPI0 to SPI1 or use different GPIO lines is that physically it’s just a matter of which pins you tie to your LCDs. But none of that solves the fundamental issue of the missing steps in the DRM pipeline.

---

## 6. Putting It All Together in a Simple Narrative

> **“kmscon** is like a caretaker who arrives early, sets the stage, lays down the canvases, hooks up the hoses to the right sprinklers, and then flips on the water so your garden (the displays) actually gets fed.  
> 
> Meanwhile, your **nc4_ili9488 driver** arrives but doesn’t realize it also needs to set up the stage and hook up everything. It might say ‘I can talk to the LCD over SPI, so I’ll just push some initial commands.’ But it never arranged the pipeline connection or provided the final instructions to start actually *showing* stuff on the screens.  
> 
> So if kmscon doesn’t show up at all (because you disabled it), the first display sees no pipeline or buffers, remains white, and never gets any pictures. If kmscon does show up, it sets everything up, and you see the mirrored console. But then kmscon *locks the framebuffers* and effectively says, ‘These are my paintings—other apps can’t scribble on them.’ That’s why tools like `fbi` can’t draw to the screens once kmscon is in control.”  

---

## 7. Why These Steps Are Critical

Each step in the pipeline—creating a buffer, associating that buffer with a display, flipping pages—is essential to *actually see images.* Without them, the driver might communicate over SPI to the LCD’s controller, but it never properly gives the GPU’s data to the panel. That’s the difference between “some signals exist” and “the display is actually showing content.”

By **replicating what kmscon does**—i.e., setting up **DRM Master Status**, creating **framebuffers**, linking them to **CRTCs** and **connectors**, then **page flipping**—the driver can stand on its own two feet and bring up both displays without relying on kmscon.

---

# KMSCON and Cards Explanation (Extended Metaphor)

Below is a short expansion of the metaphorical story to include **cards** (such as `/dev/dri/card1`). I’ve also sprinkled in references to a couple of other DRM/KMS “supporting cast” elements that may be helpful to keep in mind. Hopefully this clarifies how the “cards” fit into the overall narrative **without** losing our big-picture context.

---

## 1. The “Cards” in `/dev/dri/card1`: Another Way In and Out of the Theater

- **What is a “card”?**  
  In the Linux DRM subsystem, each **card** (e.g., `/dev/dri/card0`, `/dev/dri/card1`) is basically a **device node** representing a particular graphics pipeline or GPU-like hardware. Even if it’s not a typical GPU, the kernel sees it as a **“card”**.

### Metaphor  

Imagine your “DRM theater” actually has multiple **entrances** (or multiple small theater rooms) where different shows could happen. Each “door” or “room” is one of these “cards.” So if you have `/dev/dri/card0` and `/dev/dri/card1`, you have two different “rooms” or “stages” that can be used for different sets of displays (or the same displays, if the hardware is configured that way).

1. If you open the door labeled **card0**, you might find the main stage with the largest production.  
2. The door labeled **card1** could be a **second** smaller stage or an overflow area. Both are recognized by the show organizer (DRM), but they represent separate hardware paths or separate ways to schedule shows.

In practice, if you have multiple GPU-like devices, each one might appear as a separate **card**. Or if your hardware can present multiple DRM pipelines, each might appear as a card, too.

---

## 2. But Wait, Planes and Overlays?

We’ve already covered **CRTCs**, **connectors**, **framebuffers**, and **page flips**. Another piece you might see in logs or documentation is **planes** or overlays:

- **Plane**:  
  In DRM, a plane is a specific image layer. The simplest system has a **primary plane** for your main image content and possibly an **overlay plane** for layering additional content on top (like a mouse pointer or a hardware-accelerated sprite).

### Metaphor  

Picture your stage as having multiple **levels** or **platforms** that can move around. The main floor (primary plane) is always visible. But you can lower or raise a second platform in front (overlay plane) with special visuals (like a digital overlay or some flashy effect). The audience sees it all as one scene, but physically they’re separate layers that the stage crew can move independently.

---

## 3. Are “Cards” Integral to the Pipeline?

Yes! The pipeline references we described (CRTCs, connectors, framebuffers, etc.) usually **live within** a given card. Your driver or kmscon might open `/dev/dri/card0` to say, “I want to talk to the show organizer for this particular stage.” If your device (SPI displays) registers as a second DRM device, it might appear under `/dev/dri/card1`—an entirely separate door to a different stage or sub-theater. So it’s absolutely integral: without opening the correct **card** device, you’re not talking to the right stage at all.

---

## 4. Other “Supporting Cast” Elements

You asked if there are any other critical elements we might have overlooked. While we’ve hit the big highlights (CRTC, connector, FB, page flips, overlays, card device nodes), a few other cameo appearances sometimes matter:

1. **Render Nodes (`/dev/dri/renderD*`)**  
   - These are like **side entrances** for 3D rendering tasks, typically bypassing the “Master Status” requirement. They’re used for off-screen GPU work. Probably not crucial for your SPI scenario, but worth knowing.

2. **Primary vs. Secondary Nodes**  
   - DRM can create multiple device nodes for different permissions or user-space interactions. It’s a detail that can matter if you’re troubleshooting more advanced setups.

3. **Atomic vs. Legacy Mode-Setting**  
   - “Atomic” is the fancy, modern approach to flipping all the display settings at once (like a coordinated scene change in a theater), while “legacy” is older and more piecemeal. kmscon typically tries to do it the “atomic” way if the driver supports it.

However, in **your** story, it’s all about hooking up the pipeline and filling in the missing kmscon steps (buffers, flips, CRTC-connector links). Adding the concept of `/dev/dri/card1` to your mental model just means you might be going in through a **second door** to a second stage if your hardware is enumerated that way.

---

## 5. Summarizing the Extended Picture

1. **Cards (`/dev/dri/card0`, `/dev/dri/card1`)**  
   - The physical or logical GPU-like device entries. Think of them as separate entrances (theaters or rooms) in your overall venue (the Pi or Linux system).

2. **CRTCs**  
   - Inside each card (theater), the **pipelines** or show feeders that channel images from memory to displays.

3. **Connectors**  
   - The actual physical or logical outputs. Where your LCD or monitor cables plug in.

4. **Planes**  
   - The layered platforms on stage. Usually a primary plane (floor) and optional overlays (floating platforms).

5. **Framebuffers (FB)**  
   - The big canvases (slides) that hold the actual image data waiting to be displayed.

6. **Page Flips**  
   - The action of flipping to the next page of the script or next image buffer so the audience sees updated content.

7. **kmscon**  
   - The caretaker who knows how to open the right door (card device), become master of the stage, put the canvases in place, connect them to the pipelines, and flip the pages.

8. **Your nc4_ili9488 Driver**  
   - A partial actor who sets up some SPI details but forgets to ask for the stage keys, gather canvases, or do the final stage arrangement and page flips—hence the missing images unless kmscon steps in.

---

## 6. Conclusion

In short, yes—**“cards”** are integral because they’re the device nodes you actually open to talk to the DRM subsystem. You can think of them as the “entrances” to the show. Everything else (CRTCs, connectors, framebuffers, and so forth) resides behind each card’s door. If you forget to open the correct door, your show never starts.

As for whether there are other “absolutely critical” elements you might be missing, you’ve really got the main big-ticket items here:

- Card devices (the main entry points to the DRM show)
- Master status
- Buffers
- Framebuffers
- Pipeline components (CRTCs, connectors, planes)
- Page flips

That’s the heart of it!
