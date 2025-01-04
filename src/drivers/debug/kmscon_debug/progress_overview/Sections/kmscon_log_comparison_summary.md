
# Comparison of `kmscon` Enabled vs. Disabled Logs

This document summarizes key differences observed in the log files when `kmscon` was **enabled** versus **disabled** during the initialization and operation of the dual ILI9488 LCD displays.

## 1. DRM Pipeline Configuration
- **Atomic State Initialization**:
  - `drm_atomic_state_init` shows variations in state allocation and clearing between the two configurations.
  - Different objects (planes, CRTCs, and connectors) are linked or released.

- **Pipeline Updates**:
  - Logs indicate differences in `drm_atomic_commit`, `drm_atomic_add_affected_connectors`, and related updates. These processes show the role of `kmscon` in enabling and setting up the DRM/KMS pipeline.

## 2. Framebuffer Activity
- **Framebuffer "Dirty" Updates**:
  - Commands like `drm_mipi_dbi18_fb_dirty` reflect variations in full-screen and partial updates for `spi0.0` and `spi0.1`.
  - `kmscon` appears to actively lock and modify framebuffer states, blocking other applications (e.g., `fbi`).

- **Buffer Conversion**:
  - `nc4_mipi_dbi18_buf_copy` highlights differences in pixel data formats and byte-order transformations during framebuffer operations.

## 3. Command Execution
- **MIPI DCS Commands**:
  - Commands (`cmd=2a`, `cmd=2b`, and `cmd=2c`) for setting window addresses and updating display memory vary between configurations.
  - Differences in data lengths and parameters suggest that `kmscon` might alter display behavior.

## 4. KMS Console Management
- **Framebuffer Locking**:
  - When `kmscon` is enabled, logs like `DRM_IOCTL_VERSION` show interactions locking framebuffers, preventing usage by other processes.

- **TTY and Display Activity**:
  - Logs from `kmscon` explicitly reference interaction with `/dev/tty1`, highlighting its role in virtual terminal management.

## Summary Table

| **Subsystem**           | **kmscon Enabled**                                 | **kmscon Disabled**                                |
|--------------------------|---------------------------------------------------|--------------------------------------------------|
| DRM Pipeline Setup       | Comprehensive `drm_atomic_commit` logs, multi-object updates | Minimal updates for `spi0.0`, less pipeline activity |
| Framebuffer Operations   | Active locking, `dirty` updates blocked for external tools | Framebuffers free, full updates for `spi0.1` only |
| Command Execution        | MIPI commands triggered, display updates for both `spi0.0` and `spi0.1` | Limited commands, `spi0.0` mostly idle |
| Virtual Terminal Mgmt    | TTY interactions and locks visible in logs        | No TTY interactions or framebuffer locks         |

## Conclusion
The logs indicate that `kmscon` actively manages the DRM pipeline and framebuffers during initialization, enabling both displays but locking them for external applications. When disabled, the framebuffers are free but initialization is incomplete, leaving `spi0.0` blank.
