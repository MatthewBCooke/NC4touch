// SPDX-License-Identifier: GPL-2.0+
/*
 * DRM driver for Ilitek ILI9488 panels
 *
 * Copyright 2024 IHOR NEPOMNIASHCHYI <nepomniashchyi.igor@gmail.com>
 *
 * Based on mi0283qt.c, ili9488.c from other contributors:
 * Copyright 2016 Noralf Trønnes
 * Copyright 2019 Bird Techstep
 * Copyright 2023 Vasily Kapustin
 *
 * This driver uses the mipi_dbi interface to set up and control ILI9488-based
 * LCD panels over SPI. The panel is exposed as a DRM device, allowing the
 * creation of framebuffers and updates via /dev/fbX or DRM APIs.
 *
 * This version has been further refined with added debugging and is prepared
 * for multi-display support. Each ILI9488 node in the device tree will create
 * a separate instance of this driver, resulting in multiple DRM devices (e.g.,
 * /dev/fb0, /dev/fb1, etc.).
 *
 * Since all displays share a common backlight line in this configuration, they
 * will all enable or disable together. This is a design choice; if you want
 * separate backlight control per panel later, you can add more overlays and
 * logic.
 *
 * To filter driver logs, use:
 *   dmesg | grep -i 'ili9488'
 */

#include <linux/backlight.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/module.h>
#include <linux/property.h>
#include <linux/spi/spi.h>

#include <drm/drm_atomic_helper.h>
#include <drm/drm_damage_helper.h>
#include <drm/drm_drv.h>
#include <drm/drm_fbdev_generic.h>
#include <drm/drm_framebuffer.h>
#include <drm/drm_format_helper.h>
#include <drm/drm_gem_framebuffer_helper.h>
#include <drm/drm_fb_helper.h>
#include <drm/drm_gem_atomic_helper.h>
#include <drm/drm_gem_dma_helper.h>
#include <drm/drm_managed.h>
#include <drm/drm_mipi_dbi.h>
#include <drm/drm_modeset_helper.h>
#include <video/mipi_display.h>

/* AWL: Track the version for debugging */
#define ILI9488_DRIVER_VERSION "v2.0"

/* Display-specific commands from the ILI9488 datasheet */
#define ILI9488_CMD_NOP 0x00
#define ILI9488_CMD_SOFTWARE_RESET 0x01
#define ILI9488_CMD_READ_DISP_ID 0x04
#define ILI9488_CMD_READ_DISP_STATUS 0x09
#define ILI9488_CMD_SLEEP_OUT 0x11
#define ILI9488_CMD_DISPLAY_OFF 0x28
#define ILI9488_CMD_DISPLAY_ON 0x29
#define ILI9488_CMD_MEMORY_WRITE 0x2C
#define ILI9488_CMD_MEMORY_ACCESS_CONTROL 0x36
#define ILI9488_CMD_SET_ADDRESS_MODE 0x36
#define ILI9488_CMD_POSITIVE_GAMMA_CORRECTION 0xE0
#define ILI9488_CMD_NEGATIVE_GAMMA_CORRECTION 0xE1
#define ILI9488_CMD_POWER_CONTROL_1 0xC0
#define ILI9488_CMD_POWER_CONTROL_2 0xC1
#define ILI9488_CMD_VCOM_CONTROL_1 0xC5
#define ILI9488_CMD_FRAME_RATE_CONTROL_NORMAL 0xB1
#define ILI9488_CMD_DISPLAY_INVERSION_CONTROL 0xB4
#define ILI9488_CMD_DISPLAY_FUNCTION_CONTROL 0xB6
#define ILI9488_CMD_ENTRY_MODE_SET 0xB7
#define ILI9488_CMD_INTERFACE_MODE_CONTROL 0xB0
#define ILI9488_CMD_ADJUST_CONTROL_3 0xF7
#define ILI9488_CMD_NORMAL_DISP_MODE_ON 0x13
#define ILI9488_CMD_COLMOD_PIXEL_FORMAT_SET 0x3A

/* Memory Access Control bits */
#define ILI9488_MADCTL_BGR BIT(3)
#define ILI9488_MADCTL_MV BIT(5)
#define ILI9488_MADCTL_MX BIT(6)
#define ILI9488_MADCTL_MY BIT(7)

/* Supported DRM formats */
static const uint32_t mipi_dbi_formats[] = {
	DRM_FORMAT_RGB565,
	DRM_FORMAT_XRGB8888};

static void mipi_dbi18_fb_dirty(struct drm_framebuffer *fb, struct drm_rect *rect);
static int mipi_dbi18_buf_copy(void *dst, struct drm_framebuffer *fb,
							   struct drm_rect *clip, bool swap);

/*
 * Helper to set the updated window address region for subsequent memory writes.
 * Ensures that subsequent pixels written will land in the correct part of the panel.
 */
static void mipi_dbi_set_window_address(struct mipi_dbi_dev *dbidev,
										unsigned int xs, unsigned int xe,
										unsigned int ys, unsigned int ye)
{
	struct mipi_dbi *dbi = &dbidev->dbi;

	xs += dbidev->left_offset;
	xe += dbidev->left_offset;
	ys += dbidev->top_offset;
	ye += dbidev->top_offset;

	mipi_dbi_command(dbi, MIPI_DCS_SET_COLUMN_ADDRESS,
					 (xs >> 8) & 0xff, xs & 0xff,
					 (xe >> 8) & 0xff, xe & 0xff);

	mipi_dbi_command(dbi, MIPI_DCS_SET_PAGE_ADDRESS,
					 (ys >> 8) & 0xff, ys & 0xff,
					 (ye >> 8) & 0xff, ye & 0xff);
}

/*
 * mipi_dbi18_buf_copy:
 * Converts framebuffer formats and copies data into a buffer suitable
 * for the ILI9488. Handles endianness and pixel format transformations.
 */
int mipi_dbi18_buf_copy(void *dst, struct drm_framebuffer *fb,
						struct drm_rect *clip, bool swap)
{
	struct drm_gem_object *gem = drm_gem_fb_get_obj(fb, 0);
	struct iosys_map map[DRM_FORMAT_MAX_PLANES];
	struct iosys_map data[DRM_FORMAT_MAX_PLANES];
	struct iosys_map dst_map = IOSYS_MAP_INIT_VADDR(dst);
	int ret;

	ret = drm_gem_fb_begin_cpu_access(fb, DMA_FROM_DEVICE);
	if (ret)
		return ret;

	ret = drm_gem_fb_vmap(fb, map, data);
	if (ret)
		goto out_drm_gem_fb_end_cpu_access;

	switch (fb->format->format)
	{
	case DRM_FORMAT_RGB565:
		if (swap)
			drm_fb_swab(&dst_map, NULL, data, fb, clip, !gem->import_attach);
		else
			drm_fb_memcpy(&dst_map, NULL, data, fb, clip);
		break;
	case DRM_FORMAT_XRGB8888:
		drm_fb_xrgb8888_to_rgb888(&dst_map, NULL, data, fb, clip);
		break;
	default:
		drm_err_once(fb->dev, "ili9488: Unsupported format: %p4cc\n",
					 &fb->format->format);
		ret = -EINVAL;
	}

	drm_gem_fb_vunmap(fb, map);

out_drm_gem_fb_end_cpu_access:
	drm_gem_fb_end_cpu_access(fb, DMA_FROM_DEVICE);
	return ret;
}

/*
 * mipi_dbi18_fb_dirty:
 * Called when framebuffer changes occur. Copies the dirty region to the panel
 * via SPI.
 */
static void mipi_dbi18_fb_dirty(struct drm_framebuffer *fb, struct drm_rect *rect)
{
	struct iosys_map map[DRM_FORMAT_MAX_PLANES];
	struct iosys_map data[DRM_FORMAT_MAX_PLANES];
	struct mipi_dbi_dev *dbidev = drm_to_mipi_dbi_dev(fb->dev);
	struct mipi_dbi *dbi = &dbidev->dbi;
	unsigned int height = rect->y2 - rect->y1;
	unsigned int width = rect->x2 - rect->x1;
	bool swap = dbi->swap_bytes;
	int idx, ret = 0;
	bool full;
	void *tr;

	if (WARN_ON(!fb))
		return;

	if (!drm_dev_enter(fb->dev, &idx))
		return;

	ret = drm_gem_fb_vmap(fb, map, data);
	if (ret)
	{
		drm_dev_exit(idx);
		return;
	}

	full = (width == fb->width && height == fb->height);

	DRM_DEBUG_KMS("ili9488: Flushing [FB:%d] " DRM_RECT_FMT " dev_name=%s spi_cs=%d\n",
				  fb->base.id, DRM_RECT_ARG(rect),
				  dev_name(fb->dev->dev),
				  to_spi_device(fb->dev->dev)->chip_select);

	/*
	 * If full-screen updates and suitable format are present, we can write directly.
	 * Otherwise, we copy through dbidev->tx_buf.
	 */
	if (!dbi->dc || !full || swap ||
		fb->format->format == DRM_FORMAT_XRGB8888)
	{
		tr = dbidev->tx_buf;
		ret = mipi_dbi18_buf_copy(dbidev->tx_buf, fb, rect, swap);
		if (ret)
		{
			drm_err_once(fb->dev, "ili9488: Failed to copy buffer for update: %d\n", ret);
			goto err_msg;
		}
	}
	else
	{
		tr = data[0].vaddr;
	}

	mipi_dbi_set_window_address(dbidev,
								rect->x1, rect->x2 - 1,
								rect->y1, rect->y2 - 1);

	ret = mipi_dbi_command_buf(dbi, MIPI_DCS_WRITE_MEMORY_START, tr, width * height * 3);
err_msg:
	if (ret)
		drm_err_once(fb->dev, "ili9488: Failed to update display memory: %d\n", ret);

	drm_gem_fb_vunmap(fb, map);
	drm_dev_exit(idx);
}

/*
 * mipi_dbi18_pipe_update:
 * During atomic commits, updates any changed areas of the framebuffer.
 */
void mipi_dbi18_pipe_update(struct drm_simple_display_pipe *pipe,
							struct drm_plane_state *old_state)
{
	struct drm_plane_state *state = pipe->plane.state;
	struct drm_rect rect;

	if (!pipe->crtc.state->active)
		return;

	if (drm_atomic_helper_damage_merged(old_state, state, &rect))
		mipi_dbi18_fb_dirty(state->fb, &rect);
}

/*
 * mipi_dbi18_enable_flush:
 * On initial enable, do a full-screen update and turn on backlight.
 */
void mipi_dbi18_enable_flush(struct mipi_dbi_dev *dbidev,
							 struct drm_crtc_state *crtc_state,
							 struct drm_plane_state *plane_state)
{
	struct drm_framebuffer *fb = plane_state->fb;
	struct drm_rect rect = {
		.x1 = 0,
		.x2 = fb->width,
		.y1 = 0,
		.y2 = fb->height,
	};
	int idx;

	if (!drm_dev_enter(&dbidev->drm, &idx))
		return;

	mipi_dbi18_fb_dirty(fb, &rect);
	backlight_enable(dbidev->backlight);

	drm_dev_exit(idx);
}

/*
 * mipi_dbi18_dev_init:
 * Initializes the device with specific formats and a given mode.
 * Prepares the mipi_dbi_dev structure for use.
 */
int mipi_dbi18_dev_init(struct mipi_dbi_dev *dbidev,
						const struct drm_simple_display_pipe_funcs *funcs,
						const struct drm_display_mode *mode, unsigned int rotation)
{
	size_t bufsize = mode->vdisplay * mode->hdisplay * sizeof(u32);

	dbidev->drm.mode_config.preferred_depth = 32;

	return mipi_dbi_dev_init_with_formats(dbidev, funcs, mipi_dbi_formats,
										  ARRAY_SIZE(mipi_dbi_formats),
										  mode, rotation, bufsize);
}

/*
 * sx035hv006_enable:
 * Initializes the panel: sets power, gamma, inversion, pixel format, and finally turns it on.
 * This sequence is panel-specific based on ILI9488 documentation.
 */
static void sx035hv006_enable(struct drm_simple_display_pipe *pipe,
							  struct drm_crtc_state *crtc_state,
							  struct drm_plane_state *plane_state)
{
	struct mipi_dbi_dev *dbidev = drm_to_mipi_dbi_dev(pipe->crtc.dev);
	struct mipi_dbi *dbi = &dbidev->dbi;
	u8 addr_mode;
	int ret, idx;

	if (!drm_dev_enter(pipe->crtc.dev, &idx))
		return;

	DRM_DEBUG_KMS("ili9488: Enabling display (dev=%s cs=%d)\n",
				  dev_name(pipe->crtc.dev->dev),
				  to_spi_device(pipe->crtc.dev->dev)->chip_select);

	ret = mipi_dbi_poweron_conditional_reset(dbidev);
	if (ret < 0)
	{
		drm_err_once(pipe->crtc.dev, "ili9488: Power on/reset failed: %d\n", ret);
		goto out_exit;
	}
	if (ret == 1)
		goto out_enable;

	mipi_dbi_command(dbi, ILI9488_CMD_DISPLAY_OFF);

	/* Positive Gamma Control */
	mipi_dbi_command(dbi, ILI9488_CMD_POSITIVE_GAMMA_CORRECTION,
					 0x00, 0x03, 0x09, 0x08, 0x16,
					 0x0a, 0x3f, 0x78, 0x4c, 0x09,
					 0x0a, 0x08, 0x16, 0x1a, 0x0f);

	/* Negative Gamma Control */
	mipi_dbi_command(dbi, ILI9488_CMD_NEGATIVE_GAMMA_CORRECTION,
					 0x00, 0x16, 0x19, 0x03, 0x0f,
					 0x05, 0x32, 0x45, 0x46, 0x04,
					 0x0e, 0x0d, 0x35, 0x37, 0x0f);

	/* Power Controls */
	mipi_dbi_command(dbi, ILI9488_CMD_POWER_CONTROL_1, 0x17, 0x15);
	mipi_dbi_command(dbi, ILI9488_CMD_POWER_CONTROL_2, 0x41);

	/* VCOM Control */
	mipi_dbi_command(dbi, ILI9488_CMD_VCOM_CONTROL_1, 0x00, 0x12, 0x80);

	/* Memory Access Control (rotation/orientation) */
	mipi_dbi_command(dbi, ILI9488_CMD_MEMORY_ACCESS_CONTROL, 0x48);

	/* Pixel Format: 18-bit (configured for RGB666) */
	mipi_dbi_command(dbi, ILI9488_CMD_COLMOD_PIXEL_FORMAT_SET,
					 MIPI_DCS_PIXEL_FMT_18BIT << 1 | MIPI_DCS_PIXEL_FMT_18BIT);

	mipi_dbi_command(dbi, ILI9488_CMD_INTERFACE_MODE_CONTROL, 0x00);

	/* Frame Rate Control */
	mipi_dbi_command(dbi, ILI9488_CMD_FRAME_RATE_CONTROL_NORMAL, 0xA0);

	/* Display Inversion Control: 2-dot inversion */
	mipi_dbi_command(dbi, ILI9488_CMD_DISPLAY_INVERSION_CONTROL, 0x02);

	/* Display Function Control */
	mipi_dbi_command(dbi, ILI9488_CMD_DISPLAY_FUNCTION_CONTROL, 0x02, 0x02, 0x3B);

	/* Entry Mode Set */
	mipi_dbi_command(dbi, ILI9488_CMD_ENTRY_MODE_SET, 0xC6);

	/* Adjust Control 3 */
	mipi_dbi_command(dbi, ILI9488_CMD_ADJUST_CONTROL_3, 0xa9, 0x51, 0x2c, 0x82);

	/* Exit Sleep */
	mipi_dbi_command(dbi, ILI9488_CMD_SLEEP_OUT);
	msleep(120);

	mipi_dbi_command(dbi, ILI9488_CMD_NORMAL_DISP_MODE_ON);
	mipi_dbi_command(dbi, ILI9488_CMD_DISPLAY_ON);
	msleep(100);

out_enable:
	/* Set address mode based on rotation */
	switch (dbidev->rotation)
	{
	default:
		addr_mode = ILI9488_MADCTL_MX;
		break;
	case 90:
		addr_mode = ILI9488_MADCTL_MV;
		break;
	case 180:
		addr_mode = ILI9488_MADCTL_MY;
		break;
	case 270:
		addr_mode = ILI9488_MADCTL_MV | ILI9488_MADCTL_MY | ILI9488_MADCTL_MX;
		break;
	}

	mipi_dbi_command(dbi, ILI9488_CMD_SET_ADDRESS_MODE, addr_mode);

	/* Initial full flush and enable backlight */
	mipi_dbi18_enable_flush(dbidev, crtc_state, plane_state);

	DRM_DEBUG_KMS("ili9488: Display enabled (dev=%s cs=%d)\n",
				  dev_name(pipe->crtc.dev->dev),
				  to_spi_device(pipe->crtc.dev->dev)->chip_select);

out_exit:
	drm_dev_exit(idx);
}

/* Pipeline functions for our DRM setup */
static const struct drm_simple_display_pipe_funcs ili9488_pipe_funcs = {
	.mode_valid = mipi_dbi_pipe_mode_valid,
	.enable = sx035hv006_enable,
	.disable = mipi_dbi_pipe_disable,
	.update = mipi_dbi18_pipe_update,
};

/* Default mode for 320x480 display */
static const struct drm_display_mode sx035hv006_mode = {
	DRM_SIMPLE_MODE(320, 480, 49, 73),
};

/* File operations */
static const struct file_operations ili9488_fops = {
	.owner = THIS_MODULE,
	.open = drm_open,
	.release = drm_release,
	.unlocked_ioctl = drm_ioctl,
	.compat_ioctl = drm_compat_ioctl,
	.poll = drm_poll,
	.read = drm_read,
	.llseek = noop_llseek,
	.mmap = drm_gem_mmap,
	DRM_GEM_DMA_UNMAPPED_AREA_FOPS};

/* DRM driver description */
static struct drm_driver ili9488_driver = {
	.driver_features = DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC,
	.fops = &ili9488_fops,
	DRM_GEM_DMA_DRIVER_OPS_VMAP,
	.debugfs_init = mipi_dbi_debugfs_init,
	.name = "ili9488",
	.desc = "Ilitek ILI9488",
	.date = "20230414",
	.major = 1,
	.minor = 0,
};

static const struct of_device_id ili9488_of_match[] = {
	{.compatible = "ilitek,ili9488"},
	{}};
MODULE_DEVICE_TABLE(of, ili9488_of_match);

static const struct spi_device_id ili9488_id[] = {
	{"ili9488", 0},
	{}};
MODULE_DEVICE_TABLE(spi, ili9488_id);

/*
 * ili9488_probe:
 * Creates a mipi_dbi_dev per SPI device node. Each node from the DT overlay
 * (like pitft@0 and pitft@1) results in one call to probe, giving multiple
 * instances of this driver and multiple displays.
 */
static int ili9488_probe(struct spi_device *spi)
{
	struct device *dev = &spi->dev;
	struct mipi_dbi_dev *dbidev;
	struct drm_device *drm;
	struct mipi_dbi *dbi;
	struct gpio_desc *dc;
	u32 rotation = 0;
	int ret;

	dev_info(dev, "Loading ILI9488 driver %s\n", ILI9488_DRIVER_VERSION);
	dev_info(dev, "ili9488: Probing device (dev=%s cs=%d)\n", dev_name(dev), spi->chip_select);

	/* Allocate a new DRM device instance */
	dbidev = devm_drm_dev_alloc(dev, &ili9488_driver,
								struct mipi_dbi_dev, drm);
	if (IS_ERR(dbidev))
	{
		dev_err(dev, "ili9488: Failed to allocate drm device\n");
		return PTR_ERR(dbidev);
	}

	dbi = &dbidev->dbi;
	drm = &dbidev->drm;

	dbi->reset = devm_gpiod_get_optional(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(dbi->reset))
	{
		dev_err_probe(dev, PTR_ERR(dbi->reset), "ili9488: Failed to get 'reset' GPIO\n");
		return PTR_ERR(dbi->reset);
	}

	dc = devm_gpiod_get_optional(dev, "dc", GPIOD_OUT_LOW);
	if (IS_ERR(dc))
	{
		dev_err_probe(dev, PTR_ERR(dc), "ili9488: Failed to get 'dc' GPIO\n");
		return PTR_ERR(dc);
	}

	/* Retrieve the shared backlight device */
	dbidev->backlight = devm_of_find_backlight(dev);
	if (IS_ERR(dbidev->backlight))
	{
		dev_err(dev, "ili9488: Failed to find backlight\n");
		return PTR_ERR(dbidev->backlight);
	}

	device_property_read_u32(dev, "rotation", &rotation);
	dev_info(dev, "ili9488: Rotation property: %u (dev=%s cs=%d)\n",
			 rotation, dev_name(dev), spi->chip_select);

	/* SPI initialization with the DC pin if present */
	ret = mipi_dbi_spi_init(spi, dbi, dc);
	if (ret)
	{
		dev_err(dev, "ili9488: SPI init failed: %d\n", ret);
		return ret;
	}

	/* Initialize the DRM device with the pipeline functions and mode */
	ret = mipi_dbi18_dev_init(dbidev, &ili9488_pipe_funcs, &sx035hv006_mode, rotation);
	if (ret)
	{
		dev_err(dev, "ili9488: mipi_dbi device init failed: %d\n", ret);
		return ret;
	}

	drm_mode_config_reset(drm);

	/* Register the device: this creates a new DRM device for each panel */
	ret = drm_dev_register(drm, 0);
	if (ret)
	{
		dev_err(dev, "ili9488: DRM device registration failed: %d\n", ret);
		return ret;
	}

	spi_set_drvdata(spi, drm);

	/*
	 * Create a framebuffer device interface for fbdev clients.
	 * With multiple displays, you'll see fb0, fb1, etc.
	 */
	drm_fbdev_generic_setup(drm, 0);

	dev_info(dev, "ili9488: Probe successful (dev=%s cs=%d), device ready\n",
			 dev_name(dev), spi->chip_select);

	return 0;
}

/*
 * ili9488_remove:
 * Cleanup when the device is removed.
 */
static void ili9488_remove(struct spi_device *spi)
{
	struct drm_device *drm = spi_get_drvdata(spi);

	dev_info(&spi->dev, "ili9488: Removing device (dev=%s cs=%d)\n",
			 dev_name(&spi->dev), spi->chip_select);

	drm_dev_unplug(drm);
	drm_atomic_helper_shutdown(drm);
}

/*
 * ili9488_shutdown:
 * Cleanup on shutdown.
 */
static void ili9488_shutdown(struct spi_device *spi)
{
	dev_info(&spi->dev, "ili9488: Shutdown called (dev=%s cs=%d)\n",
			 dev_name(&spi->dev), spi->chip_select);
	drm_atomic_helper_shutdown(spi_get_drvdata(spi));
}

static struct spi_driver ili9488_spi_driver = {
	.driver = {
		.name = "ili9488",
		.of_match_table = ili9488_of_match,
	},
	.id_table = ili9488_id,
	.probe = ili9488_probe,
	.remove = ili9488_remove,
	.shutdown = ili9488_shutdown,
};
module_spi_driver(ili9488_spi_driver);

MODULE_DESCRIPTION("Ilitek ILI9488 DRM driver (prepared for multiple panels)");
MODULE_AUTHOR("IHOR NEPOMNIASHCHYI <nepomniashchyi.igor@gmail.com>");
MODULE_LICENSE("GPL");
