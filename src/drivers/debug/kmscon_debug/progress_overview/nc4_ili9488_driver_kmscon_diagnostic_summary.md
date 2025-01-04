
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
