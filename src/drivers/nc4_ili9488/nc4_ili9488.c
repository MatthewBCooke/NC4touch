// nc4_ili9488.c
// A simple fbdev driver for ILI9488 panels connected to SPI on a Raspberry Pi.
// Supports multiple panels (initially two), easy to extend to a third.
// Name: nc4_ili9488
// License: GPL

#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
#include <linux/fb.h>
#include <linux/vmalloc.h>
#include <linux/uaccess.h>
#include <linux/of.h>
#include <linux/of_gpio.h>

/* Driver version for reference in logs */
#define ILI9488_DRIVER_VERSION "v1.0.2-debug"

#define NC4_ILI9488_NAME "nc4_ili9488"
#define LCD_WIDTH   320
#define LCD_HEIGHT  480
// We will use 24-bit color in FB, and send RGB888. Display uses 18-bit but we discard LSBs.

struct nc4_ili9488_panel {
	struct spi_device *spi;
	struct fb_info *info;
	u8 *buffer; // Framebuffer RAM
	size_t buffer_size;

	struct gpio_desc *reset_gpio;
	struct gpio_desc *dc_gpio;
	struct gpio_desc *bl_gpio;

	bool backlight_enabled;

	u32 bus_speed_hz;

	// For easy extension if adding more panels:
	u16 width;
	u16 height;
};

// We can store per-panel data in driver data
static int nc4_ili9488_init_panel(struct nc4_ili9488_panel *panel);
static int nc4_ili9488_update_display(struct nc4_ili9488_panel *panel);

// Send command (DC = low)
static int nc4_ili9488_write_cmd(struct nc4_ili9488_panel *panel, u8 cmd)
{
	gpiod_set_value_cansleep(panel->dc_gpio, 0);
	return spi_write(panel->spi, &cmd, 1);
}

// Send data (DC = high)
static int nc4_ili9488_write_data(struct nc4_ili9488_panel *panel, const u8 *data, size_t len)
{
	gpiod_set_value_cansleep(panel->dc_gpio, 1);
	return spi_write(panel->spi, data, len);
}

// Helper to write a single data byte
static int nc4_ili9488_write_data_byte(struct nc4_ili9488_panel *panel, u8 val)
{
	return nc4_ili9488_write_data(panel, &val, 1);
}

// Panel initialization sequence
static int nc4_ili9488_init_panel(struct nc4_ili9488_panel *panel)
{
	int ret;

	dev_info(&panel->spi->dev, "Resetting panel for ILI9488 driver %s\n", ILI9488_DRIVER_VERSION);
	// Hardware Reset
	gpiod_set_value_cansleep(panel->reset_gpio, 1);
	mdelay(5);
	gpiod_set_value_cansleep(panel->reset_gpio, 0);
	mdelay(20);
	gpiod_set_value_cansleep(panel->reset_gpio, 1);
	mdelay(120);

	// Sleep Out (0x11)
	ret = nc4_ili9488_write_cmd(panel, 0x11);
	if (ret)
		goto err;
	mdelay(120);

	// Pixel Format Set (0x3A) - Set to 0x66 for 18-bit
	ret = nc4_ili9488_write_cmd(panel, 0x3A);
	if (ret)
		goto err;
	ret = nc4_ili9488_write_data_byte(panel, 0x66);
	if (ret)
		goto err;

	// Memory Access Control (0x36) - for portrait (example: 0x48)
	ret = nc4_ili9488_write_cmd(panel, 0x36);
	if (ret)
		goto err;
	ret = nc4_ili9488_write_data_byte(panel, 0x48);
	if (ret)
		goto err;

	// Display On (0x29)
	ret = nc4_ili9488_write_cmd(panel, 0x29);
	if (ret)
		goto err;

	mdelay(20);
	dev_info(&panel->spi->dev, "Panel initialized successfully\n");
	return 0;
err:
	dev_err(&panel->spi->dev, "Failed during panel init\n");
	return ret;
}

static int nc4_ili9488_set_window(struct nc4_ili9488_panel *panel, u16 x1, u16 y1, u16 x2, u16 y2)
{
	u8 buf[4];
	int ret;

	// Column Address Set (0x2A)
	ret = nc4_ili9488_write_cmd(panel, 0x2A);
	if (ret)
		return ret;
	buf[0] = (x1 >> 8) & 0xFF;
	buf[1] = x1 & 0xFF;
	buf[2] = (x2 >> 8) & 0xFF;
	buf[3] = x2 & 0xFF;
	ret = nc4_ili9488_write_data(panel, buf, 4);
	if (ret)
		return ret;

	// Page Address Set (0x2B)
	ret = nc4_ili9488_write_cmd(panel, 0x2B);
	if (ret)
		return ret;
	buf[0] = (y1 >> 8) & 0xFF;
	buf[1] = y1 & 0xFF;
	buf[2] = (y2 >> 8) & 0xFF;
	buf[3] = y2 & 0xFF;
	ret = nc4_ili9488_write_data(panel, buf, 4);
	if (ret)
		return ret;

	// Memory Write (0x2C)
	ret = nc4_ili9488_write_cmd(panel, 0x2C);
	return ret;
}

// Update the entire display from the framebuffer
static int nc4_ili9488_update_display(struct nc4_ili9488_panel *panel)
{
	int ret;
	// Full window update
	ret = nc4_ili9488_set_window(panel, 0, 0, panel->width - 1, panel->height - 1);
	if (ret) {
		dev_err(&panel->spi->dev, "Failed to set window\n");
		return ret;
	}

	// Send all pixels
	gpiod_set_value_cansleep(panel->dc_gpio, 1);
	ret = spi_write(panel->spi, panel->buffer, panel->buffer_size);
	if (ret)
		dev_err(&panel->spi->dev, "Failed to write framebuffer to panel\n");
	return ret;
}

static int nc4_ili9488_blank(int blank, struct fb_info *info)
{
	struct nc4_ili9488_panel *panel = info->par;
	if (!panel->bl_gpio)
		return 0;

	if (blank) {
		// Turn backlight off
		gpiod_set_value_cansleep(panel->bl_gpio, 0);
		panel->backlight_enabled = false;
		dev_info(&panel->spi->dev, "Backlight off\n");
	} else {
		// Turn backlight on
		gpiod_set_value_cansleep(panel->bl_gpio, 1);
		panel->backlight_enabled = true;
		dev_info(&panel->spi->dev, "Backlight on\n");
	}
	return 0;
}

static struct fb_ops nc4_ili9488_fbops = {
	.owner = THIS_MODULE,
	.fb_read = fb_sys_read,
	.fb_write = fb_sys_write,
	.fb_fillrect = sys_fillrect,
	.fb_copyarea = sys_copyarea,
	.fb_imageblit = sys_imageblit,
	.fb_blank = nc4_ili9488_blank,
};

// After any write, we call full update (for simplicity)
static void nc4_ili9488_flush(struct fb_info *info)
{
	struct nc4_ili9488_panel *panel = info->par;
	nc4_ili9488_update_display(panel);
}

static int nc4_ili9488_probe(struct spi_device *spi)
{
	struct device *dev = &spi->dev;
	struct nc4_ili9488_panel *panel;
	struct fb_info *info;
	int ret;

	dev_info(dev, "Probing nc4_ili9488 panel\n");

	panel = devm_kzalloc(dev, sizeof(*panel), GFP_KERNEL);
	if (!panel)
		return -ENOMEM;

	panel->spi = spi;

	// Parse device tree
	panel->dc_gpio = devm_gpiod_get(dev, "dc", GPIOD_OUT_LOW);
	if (IS_ERR(panel->dc_gpio)) {
		dev_err(dev, "Failed to get DC GPIO\n");
		return PTR_ERR(panel->dc_gpio);
	}

	panel->reset_gpio = devm_gpiod_get(dev, "reset", GPIOD_OUT_LOW);
	if (IS_ERR(panel->reset_gpio)) {
		dev_err(dev, "Failed to get RESET GPIO\n");
		return PTR_ERR(panel->reset_gpio);
	}

	// Backlight may be shared, but we just request it for each panel
	// (If it's truly shared, just provide same GPIO and it's harmless)
	panel->bl_gpio = devm_gpiod_get_optional(dev, "backlight", GPIOD_OUT_LOW);
	if (IS_ERR(panel->bl_gpio)) {
		dev_err(dev, "Failed to get Backlight GPIO\n");
		return PTR_ERR(panel->bl_gpio);
	}

	// Set SPI mode and speed
	spi->mode = SPI_MODE_0;
	spi->bits_per_word = 8;
	if (device_property_read_u32(dev, "spi-max-frequency", &panel->bus_speed_hz))
		panel->bus_speed_hz = 4000000; // default if not found

	spi->max_speed_hz = panel->bus_speed_hz;

	ret = spi_setup(spi);
	if (ret) {
		dev_err(dev, "Failed to setup SPI\n");
		return ret;
	}

	panel->width = LCD_WIDTH;
	panel->height = LCD_HEIGHT;
	panel->buffer_size = panel->width * panel->height * 3; // RGB888 (3 bytes/pixel)

	// Allocate framebuffer
	info = framebuffer_alloc(0, dev);
	if (!info)
		return -ENOMEM;

	panel->info = info;
	info->screen_size = panel->buffer_size;
	info->fix.type = FB_TYPE_PACKED_PIXELS;
	info->fix.visual = FB_VISUAL_TRUECOLOR;
	info->fix.line_length = panel->width * 3;
	strcpy(info->fix.id, "nc4_ili9488");

	info->var.xres = panel->width;
	info->var.yres = panel->height;
	info->var.xres_virtual = panel->width;
	info->var.yres_virtual = panel->height;
	info->var.bits_per_pixel = 24;
	info->var.red.offset = 16;  info->var.red.length = 8;
	info->var.green.offset = 8; info->var.green.length = 8;
	info->var.blue.offset = 0;  info->var.blue.length = 8;

	info->fbops = &nc4_ili9488_fbops;
	info->par = panel;

	panel->buffer = vmalloc(panel->buffer_size);
	if (!panel->buffer) {
		framebuffer_release(info);
		return -ENOMEM;
	}
	memset(panel->buffer, 0xFF, panel->buffer_size); // White screen initially
	info->screen_base = (char __iomem *)panel->buffer;

	ret = register_framebuffer(info);
	if (ret) {
		vfree(panel->buffer);
		framebuffer_release(info);
		return ret;
	}

	spi_set_drvdata(spi, panel);

	ret = nc4_ili9488_init_panel(panel);
	if (ret) {
		unregister_framebuffer(info);
		vfree(panel->buffer);
		framebuffer_release(info);
		return ret;
	}

	// Turn backlight on
	nc4_ili9488_blank(FB_BLANK_UNBLANK, info);

	// Initial update
	nc4_ili9488_flush(info);

	dev_info(dev, "nc4_ili9488 panel registered at /dev/fb%d\n", info->node);
	return 0;
}

static void nc4_ili9488_remove(struct spi_device *spi)
{
	struct nc4_ili9488_panel *panel = spi_get_drvdata(spi);
	if (panel) {
		if (panel->info) {
			unregister_framebuffer(panel->info);
			vfree(panel->buffer);
			framebuffer_release(panel->info);
		}
	}
}

static const struct of_device_id nc4_ili9488_of_match[] = {
	{ .compatible = "nc4_ili9488", },
	{}
};
MODULE_DEVICE_TABLE(of, nc4_ili9488_of_match);

static const struct spi_device_id nc4_ili9488_id[] = {
    { "nc4_ili9488", 0 },
    {}
};
MODULE_DEVICE_TABLE(spi, nc4_ili9488_id);

static struct spi_driver nc4_ili9488_driver = {
	.driver = {
		.name = NC4_ILI9488_NAME,
		.of_match_table = of_match_ptr(nc4_ili9488_of_match),
	},
	.probe = nc4_ili9488_probe,
	.remove = nc4_ili9488_remove,
	.id_table = nc4_ili9488_id,
};

module_spi_driver(nc4_ili9488_driver);

MODULE_DESCRIPTION("nc4_ili9488 fbdev driver for ILI9488 LCD panels " ILI9488_DRIVER_VERSION);
MODULE_AUTHOR("YourNameHere");
MODULE_LICENSE("GPL");



