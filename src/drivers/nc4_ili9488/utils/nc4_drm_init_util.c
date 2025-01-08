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

#define DRM_DEBUG_KMS(fmt, ...) syslog(LOG_INFO, "nc4_ili9488: [nc4_drm_init_util] " fmt, ##__VA_ARGS__)

// Helper to log connector details
void log_connector_details(drmModeConnector *connector)
{
    DRM_DEBUG_KMS("Connector %d: connection=%d, count_modes=%d, type=%d, type_id=%d\n",
                  connector->connector_id, connector->connection, connector->count_modes,
                  connector->connector_type, connector->connector_type_id);
    for (int i = 0; i < connector->count_modes; i++)
    {
        drmModeModeInfo mode = connector->modes[i];
        DRM_DEBUG_KMS("Mode %d: %ux%u @ %uHz\n", i, mode.hdisplay, mode.vdisplay, mode.vrefresh);
    }
}

// Helper to log CRTC details
void log_crtc_details(drmModeRes *resources)
{
    DRM_DEBUG_KMS("CRTCs available: %d\n", resources->count_crtcs);
    for (int i = 0; i < resources->count_crtcs; i++)
    {
        DRM_DEBUG_KMS("CRTC %d: ID=%d\n", i, resources->crtcs[i]);
    }
}

// Helper to log framebuffer details
void log_framebuffer_details(int fb_num)
{
    char fb_path[50];
    snprintf(fb_path, sizeof(fb_path), "/sys/class/graphics/fb%d", fb_num);
    if (access(fb_path, F_OK) == 0)
    {
        DRM_DEBUG_KMS("Framebuffer %d is present at %s\n", fb_num, fb_path);
    }
    else
    {
        DRM_DEBUG_KMS("Framebuffer %d is missing or inaccessible at %s\n", fb_num, fb_path);
    }
}

// Main initialization function for a single card
int initialize_display(int card_num, int fb_num)
{
    char device_path[20];
    snprintf(device_path, sizeof(device_path), "/dev/dri/card%d", card_num);

    // Open DRM Device
    int drm_fd = open(device_path, O_RDWR | 0);
    if (drm_fd < 0)
    {
        DRM_DEBUG_KMS("Failed to open DRM device %s: %s\n", device_path, strerror(errno));
        return 1;
    }
    DRM_DEBUG_KMS("Opened DRM device %s successfully\n", device_path);

    // Fetch DRM Resources
    drmModeRes *resources = drmModeGetResources(drm_fd);
    if (!resources)
    {
        DRM_DEBUG_KMS("Failed to get DRM resources for %s: %s\n", device_path, strerror(errno));
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Fetched DRM resources for %s successfully\n", device_path);

    // Log CRTC details
    log_crtc_details(resources);

    // Find Connected Display Connector
    drmModeConnector *connector = NULL;
    drmModeModeInfo mode;
    int connector_id = -1;

    for (int i = 0; i < resources->count_connectors; i++)
    {
        connector = drmModeGetConnector(drm_fd, resources->connectors[i]);
        if (connector)
        {
            log_connector_details(connector);
            if (connector->connection == DRM_MODE_CONNECTED && connector->count_modes > 0)
            {
                mode = connector->modes[0]; // Use the first mode (e.g., 320x480)
                connector_id = connector->connector_id;
                DRM_DEBUG_KMS("Selected connector %d for %s with mode %ux%u\n",
                              connector_id, device_path, mode.hdisplay, mode.vdisplay);
                break;
            }
            drmModeFreeConnector(connector);
        }
    }

    if (connector_id < 0)
    {
        DRM_DEBUG_KMS("No connected connector found for %s\n", device_path);
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }

    // Allocate a unique CRTC for the display
    int crtc_id = -1;
    for (int i = 0; i < resources->count_crtcs; i++)
    {
        if (!(resources->crtcs[i] & (1 << i)))
        { // Check availability
            crtc_id = resources->crtcs[i];
            DRM_DEBUG_KMS("Assigned CRTC %d to %s\n", crtc_id, device_path);
            break;
        }
    }
    if (crtc_id == -1)
    {
        DRM_DEBUG_KMS("No available CRTC for %s\n", device_path);
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }

    // Create Dumb Buffer
    struct drm_mode_create_dumb create = {0};
    create.width = mode.hdisplay;
    create.height = mode.vdisplay;
    create.bpp = 32;

    if (drmIoctl(drm_fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0)
    {
        DRM_DEBUG_KMS("Failed to create dumb buffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Dumb buffer created: handle=%u, pitch=%u, size=%llu\n",
                  create.handle, create.pitch, create.size);

    // Add Framebuffer
    uint32_t fb_id;
    if (drmModeAddFB(drm_fd, create.width, create.height, 24, 32, create.pitch, create.handle, &fb_id))
    {
        DRM_DEBUG_KMS("Failed to add framebuffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Framebuffer added with ID=%u for %s\n", fb_id, device_path);

    // Map Dumb Buffer
    struct drm_mode_map_dumb map = {0};
    map.handle = create.handle;

    if (drmIoctl(drm_fd, DRM_IOCTL_MODE_MAP_DUMB, &map) < 0)
    {
        DRM_DEBUG_KMS("Failed to map dumb buffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Dumb buffer mapped at offset=%llu\n", map.offset);

    void *fb = mmap(0, create.size, PROT_READ | PROT_WRITE, MAP_SHARED, drm_fd, map.offset);
    if (fb == MAP_FAILED)
    {
        DRM_DEBUG_KMS("Failed to mmap framebuffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }

    // memset(fb, 0xFF, create.size); // Fill the buffer with white for testing
    // DRM_DEBUG_KMS("Framebuffer filled with white color for %s\n", device_path);

    // Set Display Mode
    if (drmModeSetCrtc(drm_fd, crtc_id, fb_id, 0, 0, &connector_id, 1, &mode))
    {
        DRM_DEBUG_KMS("Failed to set CRTC %d for %s: %s\n", crtc_id, device_path, strerror(errno));
    }
    else
    {
        DRM_DEBUG_KMS("CRTC %d set successfully for %s with mode %ux%u on connector %d\n",
                      crtc_id, device_path, mode.hdisplay, mode.vdisplay, connector_id);
    }

    // Log framebuffer details
    log_framebuffer_details(fb_num);

    drmModeFreeResources(resources);
    close(drm_fd);
    return 0;
}

int main()
{
    for (int card_num = 0; card_num < 2; card_num++)
    {
        DRM_DEBUG_KMS("Initializing display for card%d\n", card_num);
        if (initialize_display(card_num, card_num + 2) != 0)
        {
            DRM_DEBUG_KMS("Failed to initialize card%d\n", card_num);
        }
    }
    return 0;
}
