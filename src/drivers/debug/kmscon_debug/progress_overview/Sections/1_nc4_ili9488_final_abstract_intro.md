
# Final Document: nc4_ili9488 Driver Project

## **Abstract**
This document provides a comprehensive summary of the nc4_ili9488 driver project for dual ILI9488-based TFT LCDs on a Raspberry Pi. The project aims to eliminate dependency on kmscon, transition to software-controlled chip select (CS), and enhance the driver for seamless multi-display support. Key challenges include overlay misconfigurations, incomplete DRM/KMS pipeline setups, and framebuffer locking by kmscon. Actionable recommendations and a phased implementation plan are provided to address these issues and achieve a self-sufficient driver solution.

---

## **Introduction**
The nc4_ili9488 driver project is designed to support two ILI9488-based TFT LCD modules on a Raspberry Pi 4 running Debian Bookworm. Both displays are connected via SPI0 and managed using a custom driver integrated with the Direct Rendering Manager (DRM) subsystem. The primary objectives of this project are to:

1. Transition the driver to software-controlled CS for improved flexibility and scalability.
2. Remove the dependency on kmscon, a terminal emulator currently critical for display initialization during boot.
3. Enhance the driver’s DRM/KMS pipeline setup to support seamless multi-display initialization and operation.

### **Hardware Overview**
- **Shared Resources**:
  - Power: Pin 1/17 for 3.3V, Pin 6/9 for GND.
  - SPI Interface: MOSI (Pin 19), SCLK (Pin 23), shared backlight (Pin 12, GPIO 18).
- **LCD_0**:
  - CS: GPIO 8 (CE0), DC: GPIO 25, RES: GPIO 24.
- **LCD_1**:
  - CS: GPIO 7 (CE1), DC: GPIO 27, RES: GPIO 23.

### **Key Challenges**
- **kmscon Dependency**:
  kmscon performs critical DRM/KMS configurations during boot, which the driver lacks, necessitating manual overlay application post-boot.
- **Overlay and Driver Issues**:
  Warnings related to `cs-gpios` and other properties hinder consistent display initialization.
- **Framebuffer Locking**:
  kmscon locks `/dev/fb0` and `/dev/fb1`, preventing other applications from rendering to the displays.
- **DRM/KMS Pipeline Gaps**:
  Missing steps like atomic state setup, framebuffer linking, and page flips during driver initialization.

This document consolidates findings from multiple debugging sessions and outlines a structured approach to address these challenges, including overlay validation, user-space utility testing, and phased driver enhancements.

---

This completes the Abstract and Introduction sections. The next steps will focus on detailing the challenges and findings.
