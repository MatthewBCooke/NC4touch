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

#define DRM_DEBUG_KMS(fmt, ...) syslog(LOG_INFO, "nc4_ili9488: [drm_init_utility] " fmt, ##__VA_ARGS__)

int main()
{
    int drm_fd = open("/dev/dri/card1", O_RDWR | 0);
    if (drm_fd < 0)
    {
        DRM_DEBUG_KMS("Failed to open DRM device: %s\n", strerror(errno));
        return 1;
    }
    DRM_DEBUG_KMS("Opened DRM device successfully\n");

    drmModeRes *resources = drmModeGetResources(drm_fd);
    if (!resources)
    {
        DRM_DEBUG_KMS("Failed to get DRM resources: %s\n", strerror(errno));
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Fetched DRM resources successfully\n");

    drmModeConnector *connector = NULL;
    drmModeModeInfo mode;
    int connector_id = -1;

    // Find the connected connector
    for (int i = 0; i < resources->count_connectors; i++)
    {
        connector = drmModeGetConnector(drm_fd, resources->connectors[i]);
        if (connector && connector->connection == DRM_MODE_CONNECTED && connector->count_modes > 0)
        {
            mode = connector->modes[0]; // Select the first mode (320x480 expected)
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

    // Create a dumb buffer
    struct drm_mode_create_dumb create = {0};
    create.width = mode.hdisplay;
    create.height = mode.vdisplay;
    create.bpp = 32;

    if (drmIoctl(drm_fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0)
    {
        DRM_DEBUG_KMS("Failed to create dumb buffer: %s\n", strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Dumb buffer created: handle=%u, pitch=%u, size=%llu\n", create.handle, create.pitch, create.size);

    uint32_t fb_id;
    if (drmModeAddFB(drm_fd, create.width, create.height, 24, 32, create.pitch, create.handle, &fb_id))
    {
        DRM_DEBUG_KMS("Failed to add framebuffer: %s\n", strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Framebuffer added with ID=%u\n", fb_id);

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

    // Fill the buffer with a solid color (e.g., white)
    memset(fb, 0xFF, create.size);
    DRM_DEBUG_KMS("Framebuffer filled with white color\n");

    // Set the mode
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

    // Cleanup (close DRM resources and device)
    drmModeFreeResources(resources);
    close(drm_fd);
    return 0;
}
