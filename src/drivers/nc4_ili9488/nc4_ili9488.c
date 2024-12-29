// SPDX-License-Identifier: GPL-2.0+
/*******************************************************************************
 * nc4_ili9488.c
 *
 * DRM driver for Ilitek ILI9488-based TFT LCD panels (320x480, SPI)
 * Modified to support multiple displays on the same SPI bus (up to 2 or 3).
 *
 * - Renamed and adapted from the original ili9488.c driver.
 * - Maintains extensive debugging output.
 * - Each panel (per SPI device) is initialized with the same known-good
 *   command sequence.
 *
 * Author: IHOR NEPOMNIASHCHYI
 * Adaptations by: <Your Name or Company>
 ******************************************************************************/

#include <linux/backlight.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/module.h>
#include <linux/property.h>
#include <linux/spi/spi.h>

/* -----------------------------------------------------------------------------
 * ADD THESE HEADERS to fix "undefined struct drm_framebuffer" errors
 * -----------------------------------------------------------------------------
 */
#include <drm/drm_framebuffer.h> /* For struct drm_framebuffer, fb->format */
#include <drm/drm_fourcc.h>		 /* For more format definitions (if needed) */
/* -----------------------------------------------------------------------------
 * END OF NEW HEADERS
 * -----------------------------------------------------------------------------
 */

#include <drm/drm_atomic_helper.h>
#include <drm/drm_damage_helper.h>
#include <drm/drm_drv.h>
#include <drm/drm_fbdev_generic.h>
#include <drm/drm_format_helper.h>
#include <drm/drm_gem_atomic_helper.h>
#include <drm/drm_gem_dma_helper.h>
#include <drm/drm_gem_framebuffer_helper.h>
#include <drm/drm_managed.h>
#include <drm/drm_mipi_dbi.h>
#include <drm/drm_modeset_helper.h>
#include <video/mipi_display.h>

/* Driver version string */
#define NC4_ILI9488_DRIVER_VERSION "v2.2"

/* ILI9488 command definitions */
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

/* MADCTL bits */
#define ILI9488_MADCTL_BGR BIT(3)
#define ILI9488_MADCTL_MV BIT(5)
#define ILI9488_MADCTL_MX BIT(6)
#define ILI9488_MADCTL_MY BIT(7)

/* Supported DRM formats for this driver: RGB565 or XRGB8888 (converted to 18-bit) */
static const uint32_t mipi_dbi_formats[] = {
	DRM_FORMAT_RGB565,
	DRM_FORMAT_XRGB8888,
};

/*******************************************************************************
 * Forward declarations of custom functions
 ******************************************************************************/
static void nc4_mipi_dbi18_fb_dirty(struct drm_framebuffer *fb, struct drm_rect *rect);
static int nc4_mipi_dbi18_buf_copy(void *dst, struct drm_framebuffer *fb,
								   struct drm_rect *clip, bool swap);

/*******************************************************************************
 * Helper function: Debug wrapper for sending commands
 *
 * Logs every command sent to the panel for easier traceability.
 ******************************************************************************/
static inline int nc4_ili9488_send_cmd(struct mipi_dbi *dbi,
									   const char *cmd_name,
									   u8 cmd_code,
									   int num_args,
									   ...)
{
	va_list args;
	u8 data[16]; /* Sufficient for known sequences */
	int i, ret;

	/* ADDED FOR DEBUG */
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_send_cmd] SPI dev=%s cs=%d -> cmd=%s(0x%02X), num_args=%d\n",
				  dev_name(dbi->spi->dev.parent),
				  to_spi_device(dbi->spi->dev.parent)->chip_select,
				  cmd_name, cmd_code, num_args);

	if (num_args > 16)
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_send_cmd] Command %s(0x%02X) has too many args: %d\n",
					  cmd_name, cmd_code, num_args);
		return -EINVAL;
	}

	va_start(args, num_args);
	for (i = 0; i < num_args; i++)
		data[i] = (u8)va_arg(args, int);
	va_end(args);

	/* Log debug details */
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_send_cmd] CMD:%s(0x%02X), args(%d):", cmd_name, cmd_code, num_args);
	for (i = 0; i < num_args; i++)
	{
		DRM_DEBUG_KMS("  0x%02X", data[i]);
	}
	DRM_DEBUG_KMS("\n");

	/* Send the command via MIPI-DBI */
	ret = mipi_dbi_command(dbi, cmd_code,
						   data[0], data[1], data[2], data[3],
						   data[4], data[5], data[6], data[7],
						   data[8], data[9], data[10], data[11],
						   data[12], data[13], data[14], data[15]);

	return ret;
}

/*******************************************************************************
 * Helper function: Set window address for partial updates
 ******************************************************************************/
static void nc4_mipi_dbi_set_window_address(struct mipi_dbi_dev *dbidev,
											unsigned int xs, unsigned int xe,
											unsigned int ys, unsigned int ye)
{
	struct mipi_dbi *dbi = &dbidev->dbi;

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi_set_window_address] dev=%s cs=%d xs=%u xe=%u ys=%u ye=%u\n",
				  dev_name(dbi->spi->dev.parent),
				  to_spi_device(dbi->spi->dev.parent)->chip_select,
				  xs, xe, ys, ye);

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

/*******************************************************************************
 * nc4_mipi_dbi18_buf_copy
 *
 * Copies the framebuffer data into an intermediate buffer if needed (e.g.
 * converting XRGB8888 to 18-bit or performing partial updates).
 ******************************************************************************/
static int nc4_mipi_dbi18_buf_copy(void *dst, struct drm_framebuffer *fb,
								   struct drm_rect *clip, bool swap)
{
	struct drm_gem_object *gem = drm_gem_fb_get_obj(fb, 0);
	struct iosys_map map[DRM_FORMAT_MAX_PLANES];
	struct iosys_map data[DRM_FORMAT_MAX_PLANES];
	struct iosys_map dst_map = IOSYS_MAP_INIT_VADDR(dst);
	int ret;

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_buf_copy] format=%p4cc swap=%d "
				  "clip=(%d,%d)-(%d,%d)\n",
				  &fb->format->format, (int)swap,
				  clip->x1, clip->y1, clip->x2, clip->y2);

	ret = drm_gem_fb_begin_cpu_access(fb, DMA_FROM_DEVICE);
	if (ret)
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_buf_copy] begin_cpu_access failed: %d\n", ret);
		return ret;
	}

	ret = drm_gem_fb_vmap(fb, map, data);
	if (ret)
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_buf_copy] fb_vmap failed: %d\n", ret);
		goto out_end_access;
	}

	switch (fb->format->format)
	{
	case DRM_FORMAT_RGB565:
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_buf_copy] Converting from RGB565%s\n",
					  swap ? " with byte-swap" : "");
		if (swap)
			drm_fb_swab(&dst_map, NULL, data, fb, clip, !gem->import_attach);
		else
			drm_fb_memcpy(&dst_map, NULL, data, fb, clip);
		break;
	case DRM_FORMAT_XRGB8888:
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_buf_copy] Converting from XRGB8888 to 18-bit\n");
		drm_fb_xrgb8888_to_rgb888(&dst_map, NULL, data, fb, clip);
		break;
	default:
		drm_err_once(fb->dev, "nc4_ili9488: [nc4_mipi_dbi18_buf_copy] Unsupported format: %p4cc\n",
					 &fb->format->format);
		ret = -EINVAL;
	}

	drm_gem_fb_vunmap(fb, map);

out_end_access:
	drm_gem_fb_end_cpu_access(fb, DMA_FROM_DEVICE);
	return ret;
}

/*******************************************************************************
 * nc4_mipi_dbi18_fb_dirty
 *
 * Performs a partial (or full) update of the panel memory from the fb data.
 ******************************************************************************/
static void nc4_mipi_dbi18_fb_dirty(struct drm_framebuffer *fb, struct drm_rect *rect)
{
	struct mipi_dbi_dev *dbidev = drm_to_mipi_dbi_dev(fb->dev);
	struct mipi_dbi *dbi = &dbidev->dbi;
	unsigned int width = rect->x2 - rect->x1;
	unsigned int height = rect->y2 - rect->y1;
	bool swap = dbi->swap_bytes;
	int ret;
	void *tr;

	if (!fb)
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_fb_dirty] Skipping update, framebuffer is null.\n");
		return;
	}

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_fb_dirty] Dirty framebuffer update: dev=%s cs=%d rect=(%u,%u)-(%u,%u)\n",
				  dev_name(fb->dev->dev),
				  to_spi_device(fb->dev->dev)->chip_select,
				  rect->x1, rect->y1, rect->x2, rect->y2);

	/* Determine if a full update is required */
	if (width == fb->width && height == fb->height)
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_fb_dirty] Full framebuffer update detected.\n");

	/* Use intermediate buffer if necessary */
	tr = dbidev->tx_buf;
	ret = nc4_mipi_dbi18_buf_copy(tr, fb, rect, swap);
	if (ret)
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_fb_dirty] Failed to copy framebuffer data, error: %d\n", ret);
		return;
	}

	/* Set the window address and write data */
	nc4_mipi_dbi_set_window_address(dbidev, rect->x1, rect->x2 - 1, rect->y1, rect->y2 - 1);
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_fb_dirty] Writing memory data to device.\n");
	mipi_dbi_command_buf(dbi, MIPI_DCS_WRITE_MEMORY_START, tr, width * height * 3);
}

/*******************************************************************************
 * nc4_mipi_dbi18_pipe_update
 *
 * Called by the DRM pipeline when there's damage to the plane state.
 ******************************************************************************/
void nc4_mipi_dbi18_pipe_update(struct drm_simple_display_pipe *pipe,
								struct drm_plane_state *old_state)
{
	struct drm_plane_state *state = pipe->plane.state;
	struct drm_rect rect;

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_pipe_update] pipe_update called\n");

	if (!pipe->crtc.state->active)
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_pipe_update] pipe_update aborted: crtc not active\n");
		return;
	}

	if (drm_atomic_helper_damage_merged(old_state, state, &rect))
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_pipe_update] merged damage rect=(" DRM_RECT_FMT ")\n",
					  DRM_RECT_ARG(&rect));
		nc4_mipi_dbi18_fb_dirty(state->fb, &rect);
	}
	else
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_pipe_update] no damage to update\n");
	}

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_pipe_update] pipe_update done for dev=%s cs=%d\n",
				  dev_name(pipe->crtc.dev->dev),
				  to_spi_device(pipe->crtc.dev->dev)->chip_select);
}

/*******************************************************************************
 * nc4_mipi_dbi18_enable_flush
 *
 * Performs a full-screen update when the display is first enabled,
 * and then enables the backlight.
 ******************************************************************************/
void nc4_mipi_dbi18_enable_flush(struct mipi_dbi_dev *dbidev,
								 struct drm_crtc_state *crtc_state,
								 struct drm_plane_state *plane_state)
{
	struct drm_framebuffer *fb = plane_state->fb;
	struct drm_rect rect = {
		.x1 = 0,
		.y1 = 0,
		.x2 = fb->width,
		.y2 = fb->height,
	};
	int idx;

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_enable_flush] enable_flush - full screen\n");

	if (!drm_dev_enter(&dbidev->drm, &idx))
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_enable_flush] enable_flush -> drm_dev_enter failed. dev=%s cs=%d\n",
					  dev_name(dbidev->dbi.spi->dev.parent),
					  to_spi_device(dbidev->dbi.spi->dev.parent)->chip_select);
		return;
	}

	nc4_mipi_dbi18_fb_dirty(fb, &rect);

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_enable_flush] after fb_dirty in enable_flush dev=%s cs=%d\n",
				  dev_name(dbidev->dbi.spi->dev.parent),
				  to_spi_device(dbidev->dbi.spi->dev.parent)->chip_select);

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_enable_flush] enabling backlight\n");
	backlight_enable(dbidev->backlight);

	drm_dev_exit(idx);
}

/*******************************************************************************
 * nc4_mipi_dbi18_dev_init
 *
 * Prepares the mipi_dbi_dev structure with the supported formats and a chosen
 * DRM display mode (320x480 by default).
 ******************************************************************************/
int nc4_mipi_dbi18_dev_init(struct mipi_dbi_dev *dbidev,
							const struct drm_simple_display_pipe_funcs *funcs,
							const struct drm_display_mode *mode,
							unsigned int rotation)
{
	size_t bufsize = mode->vdisplay * mode->hdisplay * sizeof(u32);

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_mipi_dbi18_dev_init] dev_init mode=%dx%d rotation=%u\n",
				  mode->hdisplay, mode->vdisplay, rotation);

	dbidev->drm.mode_config.preferred_depth = 32;

	return mipi_dbi_dev_init_with_formats(dbidev, funcs,
										  mipi_dbi_formats,
										  ARRAY_SIZE(mipi_dbi_formats),
										  mode, rotation, bufsize);
}

/*******************************************************************************
 * nc4_ili9488_enable
 *
 * Function that powers on and initializes the ILI9488 panel with known commands.
 ******************************************************************************/
static void nc4_ili9488_enable(struct drm_simple_display_pipe *pipe,
							   struct drm_crtc_state *crtc_state,
							   struct drm_plane_state *plane_state)
{
	struct mipi_dbi_dev *dbidev = drm_to_mipi_dbi_dev(pipe->crtc.dev);
	struct mipi_dbi *dbi = &dbidev->dbi;
	u8 addr_mode;
	int ret, idx;

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_enable] ***BEGIN enable*** dev=%s cs=%d\n",
				  dev_name(pipe->crtc.dev->dev),
				  to_spi_device(pipe->crtc.dev->dev)->chip_select);

	if (!drm_dev_enter(pipe->crtc.dev, &idx))
	{
		DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_enable] Failed to enter DRM device dev=%s cs=%d\n",
					  dev_name(pipe->crtc.dev->dev),
					  to_spi_device(pipe->crtc.dev->dev)->chip_select);
		return;
	}

	/* Power on and reset the panel */
	ret = mipi_dbi_poweron_conditional_reset(dbidev);
	if (ret < 0)
	{
		drm_err_once(pipe->crtc.dev, "nc4_ili9488: Power-on reset failed: %d\n", ret);
		goto out_exit;
	}
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_enable] Power-on reset completed, return code=%d (0=ok,1=skip)\n", ret);

	/* Optional explicit hardware reset */
	if (dbi->reset)
	{
		gpiod_set_value_cansleep(dbi->reset, 0);
		msleep(20); /* Low for 20ms */
		gpiod_set_value_cansleep(dbi->reset, 1);
		msleep(120); /* High for 120ms */
		DRM_DEBUG_KMS("nc4_ili9488: Explicit hardware reset completed.\n");
	}

	/* Initialize panel commands */
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_enable] Sending initialization commands.\n");
	nc4_ili9488_send_cmd(dbi, "SW_RESET", ILI9488_CMD_SOFTWARE_RESET, 0);
	msleep(120);

	nc4_ili9488_send_cmd(dbi, "DISPLAY_OFF", ILI9488_CMD_DISPLAY_OFF, 0);
	nc4_ili9488_send_cmd(dbi, "POS_GAMMA", ILI9488_CMD_POSITIVE_GAMMA_CORRECTION, 15,
						 0x00, 0x03, 0x09, 0x08, 0x16, 0x0a, 0x3f, 0x78, 0x4c,
						 0x09, 0x0a, 0x08, 0x16, 0x1a, 0x0f);
	nc4_ili9488_send_cmd(dbi, "NEG_GAMMA", ILI9488_CMD_NEGATIVE_GAMMA_CORRECTION, 15,
						 0x00, 0x16, 0x19, 0x03, 0x0f, 0x05, 0x32, 0x45, 0x46,
						 0x04, 0x0e, 0x0d, 0x35, 0x37, 0x0f);

	/* Additional configuration */
	nc4_ili9488_send_cmd(dbi, "MEM_ACCESS_CTRL", ILI9488_CMD_MEMORY_ACCESS_CONTROL, 1, 0x48);
	nc4_ili9488_send_cmd(dbi, "PIXEL_FORMAT", ILI9488_CMD_COLMOD_PIXEL_FORMAT_SET, 1,
						 (MIPI_DCS_PIXEL_FMT_18BIT << 1) | MIPI_DCS_PIXEL_FMT_18BIT);

	/* Turn the display on */
	nc4_ili9488_send_cmd(dbi, "SLEEP_OUT", ILI9488_CMD_SLEEP_OUT, 0);
	msleep(120);
	nc4_ili9488_send_cmd(dbi, "DISPLAY_ON", ILI9488_CMD_DISPLAY_ON, 0);
	msleep(100);

	/* Configure rotation */
	addr_mode = ILI9488_MADCTL_MX; /* Default */
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_enable] Address mode set to 0x%02X.\n", addr_mode);
	mipi_dbi_command(dbi, ILI9488_CMD_SET_ADDRESS_MODE, addr_mode);

	/* Perform a full-screen flush to initialize framebuffer */
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_enable] Performing initial full-screen flush.\n");
	nc4_mipi_dbi18_enable_flush(dbidev, crtc_state, plane_state);

	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_enable] ***END enable*** dev=%s cs=%d\n",
				  dev_name(pipe->crtc.dev->dev),
				  to_spi_device(pipe->crtc.dev->dev)->chip_select);

out_exit:
	drm_dev_exit(idx);
}

/*******************************************************************************
 * drm_simple_display_pipe_funcs for nc4_ili9488
 ******************************************************************************/
static const struct drm_simple_display_pipe_funcs nc4_ili9488_pipe_funcs = {
	.mode_valid = mipi_dbi_pipe_mode_valid,
	.enable = nc4_ili9488_enable,
	.disable = mipi_dbi_pipe_disable,
	.update = nc4_mipi_dbi18_pipe_update,
};

/*******************************************************************************
 * Default 320x480 mode for ILI9488
 ******************************************************************************/
static const struct drm_display_mode nc4_sx035hv006_mode = {
	DRM_SIMPLE_MODE(320, 480, 49, 73),
};

/*******************************************************************************
 * File operations for DRM
 ******************************************************************************/
static const struct file_operations nc4_ili9488_fops = {
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

/*******************************************************************************
 * DRM driver definition
 ******************************************************************************/
static struct drm_driver nc4_ili9488_driver = {
	.driver_features = DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC,
	.fops = &nc4_ili9488_fops,
	DRM_GEM_DMA_DRIVER_OPS_VMAP, /* Macro for GEM DMA ops */
	.debugfs_init = mipi_dbi_debugfs_init,
	.name = "nc4_ili9488",
	.desc = "nc4 ILI9488",
	.date = "20241227",
	.major = 1,
	.minor = 0,
};

/*******************************************************************************
 * Compatible strings for Device Tree
 ******************************************************************************/
static const struct of_device_id nc4_ili9488_of_match[] = {
	{.compatible = "ili9488"},
	{/* sentinel */}};
MODULE_DEVICE_TABLE(of, nc4_ili9488_of_match);

static const struct spi_device_id nc4_ili9488_id[] = {
	{"ili9488", 0},
	{/* sentinel */}};
MODULE_DEVICE_TABLE(spi, nc4_ili9488_id);

/*******************************************************************************
 * nc4_ili9488_probe
 *
 * Called when the SPI device for this driver is registered.
 ******************************************************************************/
static int nc4_ili9488_probe(struct spi_device *spi)
{
	struct device *dev = &spi->dev;
	struct mipi_dbi_dev *dbidev;
	struct drm_device *drm;
	struct mipi_dbi *dbi;
	struct gpio_desc *dc;
	u32 rotation = 0;
	int ret;

	/* Probe start */
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_probe] Starting probe for device dev=%s cs=%d\n",
				  dev_name(dev), spi->chip_select);
	dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] Loading nc4_ili9488 driver version: %s\n", NC4_ILI9488_DRIVER_VERSION);

	/* Allocate the DRM device */
	dbidev = devm_drm_dev_alloc(dev, &nc4_ili9488_driver,
								struct mipi_dbi_dev, drm);
	if (IS_ERR(dbidev))
	{
		dev_err(dev, "nc4_ili9488: [nc4_ili9488_probe] Failed to allocate DRM device.\n");
		return PTR_ERR(dbidev);
	}

	dbi = &dbidev->dbi;
	drm = &dbidev->drm;

	/* Retrieve and log reset GPIO state */
	dbi->reset = devm_gpiod_get_optional(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(dbi->reset))
	{
		dev_err_probe(dev, PTR_ERR(dbi->reset), "nc4_ili9488: Failed to get 'reset' GPIO\n");
		return PTR_ERR(dbi->reset);
	}
	else if (dbi->reset)
	{
		dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] Reset GPIO acquired.\n");
	}
	else
	{
		dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] No reset GPIO defined.\n");
	}

	/* Retrieve and log DC GPIO state */
	dc = devm_gpiod_get_optional(dev, "dc", GPIOD_OUT_LOW);
	if (IS_ERR(dc))
	{
		dev_err_probe(dev, PTR_ERR(dc), "nc4_ili9488: Failed to get 'dc' GPIO\n");
		return PTR_ERR(dc);
	}
	else if (dc)
	{
		dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] DC GPIO acquired.\n");
	}
	else
	{
		dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] No DC GPIO defined.\n");
	}

	/* Retrieve the shared backlight */
	dbidev->backlight = devm_of_find_backlight(dev);
	if (IS_ERR(dbidev->backlight))
	{
		dev_err(dev, "nc4_ili9488: [nc4_ili9488_probe] Failed to find backlight.\n");
		return PTR_ERR(dbidev->backlight);
	}
	dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] Backlight found and initialized.\n");

	/* Retrieve rotation property */
	device_property_read_u32(dev, "rotation", &rotation);
	DRM_DEBUG_KMS("nc4_ili9488: [nc4_ili9488_probe] Rotation property=%u\n", rotation);

	/* Initialize the SPI interface */
	ret = mipi_dbi_spi_init(spi, dbi, dc);
	if (ret)
	{
		dev_err(dev, "nc4_ili9488: [nc4_ili9488_probe] SPI initialization failed: %d\n", ret);
		return ret;
	}
	dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] SPI initialized successfully (mode=0x%X, max_speed_hz=%u).\n",
			 spi->mode, spi->max_speed_hz);

	/* Initialize the MIPI-DBI device */
	ret = nc4_mipi_dbi18_dev_init(dbidev, &nc4_ili9488_pipe_funcs,
								  &nc4_sx035hv006_mode, rotation);
	if (ret)
	{
		dev_err(dev, "nc4_ili9488: [nc4_ili9488_probe] MIPI-DBI device initialization failed: %d\n", ret);
		return ret;
	}
	dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] MIPI-DBI device initialized.\n");

	/* Reset DRM mode configuration */
	drm_mode_config_reset(drm);

	/* Register the DRM device */
	ret = drm_dev_register(drm, 0);
	if (ret)
	{
		dev_err(dev, "nc4_ili9488: [nc4_ili9488_probe] DRM device registration failed: %d\n", ret);
		return ret;
	}
	dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] DRM device registered successfully.\n");

	/* Store driver data and set up framebuffer */
	spi_set_drvdata(spi, drm);
	drm_fbdev_generic_setup(drm, 0);

	dev_info(dev, "nc4_ili9488: [nc4_ili9488_probe] Probe completed successfully for dev=%s cs=%d\n",
			 dev_name(dev), spi->chip_select);

	return 0;
}

/*******************************************************************************
 * nc4_ili9488_remove
 ******************************************************************************/
static void nc4_ili9488_remove(struct spi_device *spi)
{
	struct drm_device *drm = spi_get_drvdata(spi);

	dev_info(&spi->dev, "nc4_ili9488: [nc4_ili9488_remove] Removing dev=%s cs=%d\n",
			 dev_name(&spi->dev), spi->chip_select);

	drm_dev_unplug(drm);
	drm_atomic_helper_shutdown(drm);
}

/*******************************************************************************
 * nc4_ili9488_shutdown
 ******************************************************************************/
static void nc4_ili9488_shutdown(struct spi_device *spi)
{
	dev_info(&spi->dev, "nc4_ili9488: [nc4_ili9488_shutdown] Shutdown dev=%s cs=%d\n",
			 dev_name(&spi->dev), spi->chip_select);
	drm_atomic_helper_shutdown(spi_get_drvdata(spi));
}

/*******************************************************************************
 * SPI driver structure
 ******************************************************************************/
static struct spi_driver nc4_ili9488_spi_driver = {
	.driver = {
		.name = "nc4_ili9488",
		.of_match_table = nc4_ili9488_of_match,
	},
	.id_table = nc4_ili9488_id,
	.probe = nc4_ili9488_probe,
	.remove = nc4_ili9488_remove,
	.shutdown = nc4_ili9488_shutdown,
};
module_spi_driver(nc4_ili9488_spi_driver);

MODULE_DESCRIPTION("nc4 Ilitek ILI9488 DRM driver with debugging");
MODULE_AUTHOR("IHOR NEPOMNIASHCHYI, <Your Name>");
MODULE_LICENSE("GPL");
