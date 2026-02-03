#include <linux/module.h>
#include <linux/init.h>
#include <drm/drm_print.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Test Author");
MODULE_DESCRIPTION("Minimal DRM Test Driver");

static int __init test_driver_init(void)
{
    DRM_INFO("Test Driver: Initialized successfully.\n");
    return 0;
}

static void __exit test_driver_exit(void)
{
    DRM_INFO("Test Driver: Exiting successfully.\n");
}

module_init(test_driver_init);
module_exit(test_driver_exit);
