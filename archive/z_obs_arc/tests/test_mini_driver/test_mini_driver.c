// SPDX-License-Identifier: GPL-2.0+
/*
 * test_mini_driver.c
 * A minimal "Hello World" SPI driver for demonstration.
 *
 * Note: On some newer kernels, .remove is defined as 'void remove(...)'
 *       rather than 'int remove(...)'. If your kernel expects the older
 *       signature, change it back to 'static int test_mini_remove(...).'
 */

#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/of.h>

/*
 * Match table for of_platform binding. This recognizes "test_mini"
 * from the Device Tree (overlay).
 */
static const struct of_device_id test_mini_of_match[] = {
    {.compatible = "test_mini"},
    {/* sentinel */}};
MODULE_DEVICE_TABLE(of, test_mini_of_match);

/*
 * The spi_device_id table ensures an alias "test_mini" is exported.
 * That way, the kernel can auto-load this driver if it sees a device
 * with 'modalias=spi:test_mini'.
 */
static const struct spi_device_id test_mini_id[] = {
    {"test_mini", 0},
    {/* sentinel */}};
MODULE_DEVICE_TABLE(spi, test_mini_id);

/*
 * Minimal probe function: logs a message upon driver binding to the SPI device.
 */
static int test_mini_probe(struct spi_device *spi)
{
    dev_info(&spi->dev, "test_mini_driver: Probed! (dev=%s)\n",
             dev_name(&spi->dev));
    return 0; /* success */
}

/*
 * For newer kernels, the 'remove' callback often expects 'void remove(...)'.
 * If your kernel complains about "void (*)(...)" vs. "int (*)(...)",
 * switch to this version.
 */
static void test_mini_remove(struct spi_device *spi)
{
    dev_info(&spi->dev, "test_mini_driver: Removed! (dev=%s)\n",
             dev_name(&spi->dev));
}

/* SPI driver struct */
static struct spi_driver test_mini_spi_driver = {
    .driver = {
        .name = "test_mini",
        .owner = THIS_MODULE,
        .of_match_table = test_mini_of_match,
    },
    .probe = test_mini_probe,
    .remove = test_mini_remove,

    /*
     * Using 'id_table' here means the kernel will automatically
     * load this module if it sees a device with 'spi:test_mini'
     * in the modalias.
     */
    .id_table = test_mini_id,
};

/*
 * Registers test_mini_spi_driver with the SPI subsystem at load time,
 * and unregisters at unload time.
 */
module_spi_driver(test_mini_spi_driver);

/* Required for the kernel build system to accept the module. */
MODULE_LICENSE("GPL");
MODULE_AUTHOR("YourNameHere");
MODULE_DESCRIPTION("Minimal SPI driver to test overlay loading");
