#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/mman.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include <xf86drm.h>
#include <xf86drmMode.h>
#include <syslog.h>

// Debugging macro for consistent logging
#define DRM_DEBUG_KMS(fmt, ...) syslog(LOG_INFO, "nc4_ili9488: [nc4_drm_init_util] " fmt, ##__VA_ARGS__)

/***************************************************************************
 * nc4_drm_init_util.c
 *
 * Utility to initialize DRM pipeline for a single display panel.
 *
 * This program:
 * - Opens a DRM device (e.g., /dev/dri/card1).
 * - Fetches DRM resources and identifies a connected display.
 * - Creates a dumb framebuffer and sets a mode for the display.
 * - Fills the framebuffer with a solid color (white) for testing.
 *
 * Designed for use as part of the nc4_ili9488 project.
 *
 * Limitations:
 * - Configures only a single connector.
 * - Designed for static modesetting (320x480 resolution).
 * - No timeout or retry logic for unavailable resources.
 *
 * Future Considerations:
 * - Multi-display support.
 * - Improved error handling and resource availability checks.
 * - Support for dynamic resolutions or configurations.
 *
 * Author: <Your Name>
 ******************************************************************************/

int main()
{
    /***************************************************************************
     * Open DRM Device
     *
     * Opens the DRM device file (e.g., /dev/dri/card1) to access display hardware.
     * - Ensures read/write access to the DRM subsystem.
     * - Exits with an error if the device is unavailable.
     **************************************************************************/
    int drm_fd = open("/dev/dri/card1", O_RDWR | 0);  
    if (drm_fd < 0)
    {
        DRM_DEBUG_KMS("Failed to open DRM device: %s\n", strerror(errno));
        return 1;
    }
    DRM_DEBUG_KMS("Opened DRM device successfully\n");

    /***************************************************************************
     * Fetch DRM Resources
     *
     * Queries the DRM device for resources, including connectors, CRTCs, and
     * framebuffers. These are necessary to configure the display pipeline.
     *
     * Exits if resources cannot be fetched.
     **************************************************************************/
    drmModeRes *resources = drmModeGetResources(drm_fd);
    if (!resources)
    {
        DRM_DEBUG_KMS("Failed to get DRM resources: %s\n", strerror(errno));
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Fetched DRM resources successfully\n");

    /***************************************************************************
     * Find Connected Display Connector
     *
     * Identifies the first connected display connector and retrieves its mode
     * (resolution, refresh rate). This is essential for setting up the pipeline.
     *
     * Exits if no connected connector is found.
     **************************************************************************/
    drmModeConnector *connector = NULL;
    drmModeModeInfo mode;
    int connector_id = -1;

    for (int i = 0; i < resources->count_connectors; i++)
    {
        connector = drmModeGetConnector(drm_fd, resources->connectors[i]);
        if (connector && connector->connection == DRM_MODE_CONNECTED && connector->count_modes > 0)
        {
            mode = connector->modes[0]; // Select the first mode (e.g., 320x480)
            connector_id = connector->connector_id;
            DRM_DEBUG_KMS("Connector %d is connected with mode %ux%u\n", connector_id, mode.hdisplay, mode.vdisplay);
            break;
        }
        drmModeFreeConnector(connector);
    }

    if (connector_id < 0)
    {
        DRM_DEBUG_KMS("No connected connector found\n");
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }

    /***************************************************************************
     * Create Dumb Buffer
     *
     * Allocates a simple framebuffer in DRM memory for storing pixel data.
     * - Sets dimensions (width, height) and format (bits per pixel).
     * - Logs details such as handle, pitch, and size.
     *
     * Exits if the buffer cannot be created.
     **************************************************************************/
    struct drm_mode_create_dumb create = {0};

    create.width = mode.hdisplay;  // Set buffer width to match display resolution.
    create.height = mode.vdisplay; // Set buffer height to match display resolution.
    create.bpp = 32;               // Bits per pixel (supports 24-bit color with alpha).

    if (drmIoctl(drm_fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0)
    {
        DRM_DEBUG_KMS("Failed to create dumb buffer: %s\n", strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Dumb buffer created: handle=%u, pitch=%u, size=%llu\n", create.handle, create.pitch, create.size);

    /***************************************************************************
     * Add Framebuffer
     *
     * Registers the dumb buffer as a framebuffer with the DRM subsystem.
     * - This step associates the buffer with the display pipeline.
     *
     * Exits if framebuffer registration fails.
     **************************************************************************/
    uint32_t fb_id;
    if (drmModeAddFB(drm_fd, create.width, create.height, 24, 32, create.pitch, create.handle, &fb_id))
    {
        DRM_DEBUG_KMS("Failed to add framebuffer: %s\n", strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Framebuffer added with ID=%u\n", fb_id);

    /***************************************************************************
     * Map Dumb Buffer
     *
     * Maps the dumb buffer into user-space memory for direct access.
     * - This allows the utility to fill the buffer with pixel data.
     *
     * Exits if the mapping fails.
     **************************************************************************/
    struct drm_mode_map_dumb map = {0};
    map.handle = create.handle;

    if (drmIoctl(drm_fd, DRM_IOCTL_MODE_MAP_DUMB, &map) < 0)
    {
        DRM_DEBUG_KMS("Failed to map dumb buffer: %s\n", strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Dumb buffer mapped at offset=%llu\n", map.offset);

    void *fb = mmap(0, create.size, PROT_READ | PROT_WRITE, MAP_SHARED, drm_fd, map.offset);
    if (fb == MAP_FAILED)
    {
        DRM_DEBUG_KMS("Failed to mmap framebuffer: %s\n", strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }

    // Fill the buffer with a solid color (white)
    memset(fb, 0xFF, create.size);
    DRM_DEBUG_KMS("Framebuffer filled with white color\n");

    /***************************************************************************
     * Set Display Mode
     *
     * Configures the CRTC (display controller) with the selected mode and
     * framebuffer. This step activates the display.
     *
     * Logs an error if the mode cannot be set but continues to allow debugging.
     **************************************************************************/
    int crtc_id = resources->crtcs[0];
    if (drmModeSetCrtc(drm_fd, crtc_id, fb_id, 0, 0, &connector_id, 1, &mode))
    {
        DRM_DEBUG_KMS("Failed to set CRTC: %s\n", strerror(errno));
    }
    else
    {
        DRM_DEBUG_KMS("CRTC set successfully for mode %ux%u on connector %d\n", mode.hdisplay, mode.vdisplay, connector_id);
    }

    getchar(); // Keep the display on until user input

    /***************************************************************************
     * Cleanup and Exit
     *
     * Releases resources allocated during initialization.
     **************************************************************************/
    drmModeFreeResources(resources);
    close(drm_fd);
    return 0;
}
