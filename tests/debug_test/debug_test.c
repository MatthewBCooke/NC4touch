#include <linux/module.h>
#include <linux/init.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Test Author");
MODULE_DESCRIPTION("Debugging Test Module");

/* Module initialization */
static int __init debug_test_init(void)
{
    pr_info("debug_test: Initializing test module\n");
    pr_debug("debug_test: Debug message during initialization\n");
    pr_err("debug_test: Error message for testing\n");
    return 0;
}

/* Module cleanup */
static void __exit debug_test_exit(void)
{
    pr_info("debug_test: Exiting test module\n");
    pr_debug("debug_test: Debug message during cleanup\n");
    pr_err("debug_test: Error message during cleanup\n");
}

module_init(debug_test_init);
module_exit(debug_test_exit);
