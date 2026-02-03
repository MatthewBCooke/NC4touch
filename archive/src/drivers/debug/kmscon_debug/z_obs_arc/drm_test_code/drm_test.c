#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <drm/drm.h> // Corrected include path
#include <unistd.h>  // Added for close()
#include <errno.h>
#include <string.h>
#include <ctype.h> // For isprint()

#define DRM_CARD_PATH "/dev/dri/card0"

int main()
{
    int fd;
    struct drm_version version;

    // Open DRM device
    fd = open(DRM_CARD_PATH, O_RDWR | O_CLOEXEC);
    if (fd < 0)
    {
        perror("Failed to open DRM device");
        return 1;
    }

    printf("Opened DRM device: %s\n", DRM_CARD_PATH);

    // Clear the version structure
    memset(&version, 0, sizeof(version));

    // Allocate larger buffers for version strings
    char name[256] = {0}; // Increased size and initialized to zero
    char desc[1024] = {0};
    char date[256] = {0};

    version.name = name;
    version.name_len = sizeof(name) - 1; // Reserve space for null-termination
    version.desc = desc;
    version.desc_len = sizeof(desc) - 1;
    version.date = date;
    version.date_len = sizeof(date) - 1;

    // Query DRM version
    if (ioctl(fd, DRM_IOCTL_VERSION, &version) < 0)
    {
        perror("Failed to get DRM version");
        close(fd);
        return 1;
    }

    // Log raw buffer contents for debugging
    printf("Raw Driver Name: ");
    for (size_t i = 0; i < version.name_len; i++)
    {
        printf("%02x ", (unsigned char)name[i]);
    }
    printf("\n");

    printf("Raw Description: ");
    for (size_t i = 0; i < version.desc_len; i++)
    {
        printf("%02x ", (unsigned char)desc[i]);
    }
    printf("\n");

    printf("Raw Date: ");
    for (size_t i = 0; i < version.date_len; i++)
    {
        printf("%02x ", (unsigned char)date[i]);
    }
    printf("\n");

    // Ensure null-termination for safety and remove non-printable characters
    for (size_t i = 0; i < sizeof(name); i++)
    {
        if (!isprint(name[i]))
            name[i] = '\0';
    }
    for (size_t i = 0; i < sizeof(desc); i++)
    {
        if (!isprint(desc[i]))
            desc[i] = '\0';
    }
    for (size_t i = 0; i < sizeof(date); i++)
    {
        if (!isprint(date[i]))
            date[i] = '\0';
    }

    // Print results
    printf("DRM Version: %d.%d.%d\n", version.version_major, version.version_minor, version.version_patchlevel);
    printf("Driver Name: %s\n", version.name);
    printf("Description: %s\n", version.desc);
    printf("Date: %s\n", version.date);

    // Close the DRM device
    close(fd);
    printf("Closed DRM device.\n");

    return 0;
}
