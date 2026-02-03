// SPDX-License-Identifier: GPL-2.0+
/*
 * DRM driver for Ilitek ILI9488 panels
 *
 * Copyright 2024 ADAM WARD LESTER (NC4 LAB)
 *
 * This driver uses the mipi_dbi interface to set up and control ILI9488-based
 * LCD panels over SPI. Each panel appears as a DRM device, enabling the creation
 * of framebuffers and updates via /dev/fbX or via standard DRM APIs.
 *
 * This version adds extensive debugging output. It logs initialization details,
 * GPIO line presence, SPI setup, rotation configuration, command sequences, and
 * framebuffer updates. The goal is to gather as much information as possible
 * to diagnose issues with multiple displays or unexpected behavior.
 *
 * Use:
 *   dmesg | grep -i 'nc4_ili9488'
 * to filter logs. If you find it difficult to enable DRM_DEBUG_KMS logs,
 * consider switching these statements to dev_dbg() or pr_debug().
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

/* ------------------------------------------------------------------------- */
/*                          Driver Version / Defines                         */
/* ------------------------------------------------------------------------- */

#define ILI9488_DRIVER_VERSION "v3.0-debug"

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

/* Mode settings for SPI */
#define NC4_ILI9488_SPI_MODE SPI_MODE_3 /* Force CPOL=1, CPHA=1 */

/* Supported DRM formats for this driver */
static const uint32_t mipi_dbi_formats[] = {
	DRM_FORMAT_RGB565,
	DRM_FORMAT_XRGB8888};

/* ------------------------------------------------------------------------- */
/*                   Forward Declarations / Local Prototypes                */
/* ------------------------------------------------------------------------- */

static void mipi_dbi18_fb_dirty(struct drm_framebuffer *fb, struct drm_rect *rect);
static int mipi_dbi18_buf_copy(void *dst, struct drm_framebuffer *fb,
							   struct drm_rect *clip, bool swap);

/* ------------------------------------------------------------------------- */
/*                    Debug Helper: Send MIPI Command                        */
/* ------------------------------------------------------------------------- */

/**
 * nc4_ili9488_send_cmd - Send an ILI9488 command with debug logging.
 * @dbi:  Pointer to the mipi_dbi structure controlling the panel.
 * @name: Descriptive name of the command for debugging (e.g. "SW_RESET").
 * @cmd:  The MIPI DCS or extended command byte (e.g. 0x01).
 * @num:  Number of parameter bytes to follow.
 * @...:  The variable argument list of parameter bytes.
 *
 * This function logs the command name, code, and parameters before sending
 * them via mipi_dbi_command(). If num > 16, it logs an error and aborts.
 */
static inline int nc4_ili9488_send_cmd(struct mipi_dbi *dbi, const char *name,
									   u8 cmd, int num, ...)
{
	va_list args;
	u8 data[16];
	int i, ret;

	if (num > 16)
	{
		DRM_DEBUG_KMS("nc4_ili9488: Command %s(0x%02X) has too many args: %d\n",
					  name, cmd, num);
		return -EINVAL;
	}

	va_start(args, num);
	for (i = 0; i < num; i++)
		data[i] = (u8)va_arg(args, int);
	va_end(args);

	DRM_DEBUG_KMS("nc4_ili9488: Sending CMD:%s(0x%02X), args(%d):",
				  name, cmd, num);
	for (i = 0; i < num; i++)
		DRM_DEBUG_KMS(" 0x%02X", data[i]);
	DRM_DEBUG_KMS("\n");

	ret = mipi_dbi_command(dbi, cmd,
						   data[0], data[1], data[2], data[3],
						   data[4], data[5], data[6], data[7],
						   data[8], data[9], data[10], data[11],
						   data[12], data[13], data[14], data[15]);
	return ret;
}

/* ------------------------------------------------------------------------- */
/*                 MIPI DBI Utility: Set Window Address Region               */
/* ------------------------------------------------------------------------- */

/**
 * mipi_dbi_set_window_address - Set the column/page address region for updates
 * @dbidev: Pointer to the MIPI DBI device wrapper.
 * @xs:     Start column (X)
 * @xe:     End column (X)
 * @ys:     Start row   (Y)
 * @ye:     End row     (Y)
 *
 * Applies dbidev->left_offset and dbidev->top_offset to account for any
 * hardware margins. Then sends MIPI_DCS_SET_COLUMN_ADDRESS and
 * MIPI_DCS_SET_PAGE_ADDRESS to define the updated region on the panel.
 */
static void mipi_dbi_set_window_address(struct mipi_dbi_dev *dbidev,
										unsigned int xs, unsigned int xe,
										unsigned int ys, unsigned int ye)
{
	struct mipi_dbi *dbi = &dbidev->dbi;

	DRM_DEBUG_KMS("nc4_ili9488: set_window_address dev=%s xs=%u xe=%u ys=%u ye=%u\n",
				  dev_name(dbi->spi->dev.parent), xs, xe, ys, ye);

	// Adjust for top/left offsets if the hardware has them
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

/* ------------------------------------------------------------------------- */
/*         mipi_dbi18_buf_copy - Convert or swab a region of framebuffer     */
/* ------------------------------------------------------------------------- */

/**
 * mipi_dbi18_buf_copy - Copy and convert a damaged region into a transmit buffer
 * @dst:  Destination buffer (3 bytes/pixel for RGB888).
 * @fb:   DRM framebuffer to read from.
 * @clip: Rectangular area of the framebuffer to copy.
 * @swap: Whether to perform byte-swap (for RGB565).
 *
 * This function maps the framebuffer for CPU access, then either:
 *   - Swaps or copies data directly for RGB565, or
 *   - Converts XRGB8888 => RGB888 for 18-bit panels.
 * Afterwards, it unmaps the framebuffer and ends CPU access.
 */
static int mipi_dbi18_buf_copy(void *dst, struct drm_framebuffer *fb,
							   struct drm_rect *clip, bool swap)
{
	struct drm_gem_object *gem = drm_gem_fb_get_obj(fb, 0);
	struct iosys_map map[DRM_FORMAT_MAX_PLANES];
	struct iosys_map data[DRM_FORMAT_MAX_PLANES];
	struct iosys_map dst_map = IOSYS_MAP_INIT_VADDR(dst);
	int ret;

	DRM_DEBUG_KMS("nc4_ili9488: mipi_dbi18_buf_copy format=%p4cc swap=%d "
				  "clip=(%d,%d)-(%d,%d)\n",
				  &fb->format->format, (int)swap,
				  clip->x1, clip->y1, clip->x2, clip->y2);

	ret = drm_gem_fb_begin_cpu_access(fb, DMA_FROM_DEVICE);
	if (ret)
	{
		DRM_DEBUG_KMS("nc4_ili9488: begin_cpu_access failed: %d\n", ret);
		return ret;
	}

	ret = drm_gem_fb_vmap(fb, map, data);
	if (ret)
	{
		DRM_DEBUG_KMS("nc4_ili9488: fb_vmap failed: %d\n", ret);
		goto out_drm_gem_fb_end_cpu_access;
	}

	switch (fb->format->format)
	{
	case DRM_FORMAT_RGB565:
		DRM_DEBUG_KMS("nc4_ili9488: Converting from RGB565%s\n",
					  swap ? " with byte-swap" : "");
		if (swap)
			drm_fb_swab(&dst_map, NULL, data, fb, clip,
						!gem->import_attach);
		else
			drm_fb_memcpy(&dst_map, NULL, data, fb, clip);
		break;

	case DRM_FORMAT_XRGB8888:
		DRM_DEBUG_KMS("nc4_ili9488: Converting from XRGB8888 to RGB888\n");
		drm_fb_xrgb8888_to_rgb888(&dst_map, NULL, data, fb, clip);
		break;

	default:
		drm_err_once(fb->dev,
					 "nc4_ili9488: Unsupported format: %p4cc\n",
					 &fb->format->format);
		ret = -EINVAL;
	}

	drm_gem_fb_vunmap(fb, map);

out_drm_gem_fb_end_cpu_access:
	drm_gem_fb_end_cpu_access(fb, DMA_FROM_DEVICE);
	return ret;
}

/* ------------------------------------------------------------------------- */
/*                 Framebuffer Dirty Handler (partial updates)              */
/* ------------------------------------------------------------------------- */

/**
 * mipi_dbi18_fb_dirty - Update the panel for a given dirty rectangle
 * @fb:   DRM framebuffer that changed.
 * @rect: The rectangle area of the framebuffer that is dirty/changed.
 *
 * Maps or copies the changed region, performs color conversion if needed,
 * and transmits it to the panel via SPI. If the update is partial, we
 * typically copy into the driver's tx_buf. For full updates (and if
 * conditions allow), we may send the mapped data directly.
 */
static void mipi_dbi18_fb_dirty(struct drm_framebuffer *fb,
								struct drm_rect *rect)
{
	struct mipi_dbi_dev *dbidev = drm_to_mipi_dbi_dev(fb->dev);
	struct mipi_dbi *dbi = &dbidev->dbi;
	unsigned int width = rect->x2 - rect->x1;
	unsigned int height = rect->y2 - rect->y1;
	bool swap = dbi->swap_bytes;
	struct iosys_map map[DRM_FORMAT_MAX_PLANES];
	struct iosys_map data[DRM_FORMAT_MAX_PLANES];
	void *tr;
	int idx, ret = 0;
	bool full;

	if (WARN_ON(!fb))
		return;

	if (!drm_dev_enter(fb->dev, &idx))
	{
		DRM_DEBUG_KMS("nc4_ili9488: drm_dev_enter failed\n");
		return;
	}

	DRM_DEBUG_KMS("nc4_ili9488: FB dirty: fb_id=%d dev=%s cs=%d "
				  "rect=(%d,%d)-(%d,%d)\n",
				  fb->base.id, dev_name(fb->dev->dev),
				  to_spi_device(fb->dev->dev)->chip_select,
				  rect->x1, rect->y1, rect->x2, rect->y2);

	ret = drm_gem_fb_vmap(fb, map, data);
	if (ret)
	{
		DRM_DEBUG_KMS("nc4_ili9488: gem_fb_vmap failed: %d\n", ret);
		drm_dev_exit(idx);
		return;
	}

	full = ((width == fb->width) && (height == fb->height));
	DRM_DEBUG_KMS("nc4_ili9488: full_update=%d fb_w=%d fb_h=%d "
				  "update_w=%d update_h=%d\n",
				  full, fb->width, fb->height, width, height);

	if (!dbi->dc || !full || swap ||
		fb->format->format == DRM_FORMAT_XRGB8888)
	{
		DRM_DEBUG_KMS("nc4_ili9488: Using tx_buf for this update\n");
		tr = dbidev->tx_buf;
		drm_gem_fb_vunmap(fb, map);
		ret = mipi_dbi18_buf_copy(dbidev->tx_buf, fb, rect, swap);
		if (ret)
		{
			drm_err_once(fb->dev,
						 "nc4_ili9488: Failed to copy buffer: %d\n",
						 ret);
			goto err_exit;
		}
	}
	else
	{
		DRM_DEBUG_KMS("nc4_ili9488: Directly using mapped fb data for update\n");
		tr = data[0].vaddr;
		drm_gem_fb_vunmap(fb, map);
	}

	mipi_dbi_set_window_address(dbidev, rect->x1, rect->x2 - 1,
								rect->y1, rect->y2 - 1);

	DRM_DEBUG_KMS("nc4_ili9488: Writing memory start cmd for region\n");
	ret = mipi_dbi_command_buf(dbi, MIPI_DCS_WRITE_MEMORY_START,
							   tr, width * height * 3);
	if (ret)
		drm_err_once(fb->dev,
					 "nc4_ili9488: Failed to update display memory: %d\n",
					 ret);

err_exit:
	drm_dev_exit(idx);
}

/* ------------------------------------------------------------------------- */
/*     mipi_dbi18_pipe_update - Called during atomic plane state changes     */
/* ------------------------------------------------------------------------- */

/**
 * mipi_dbi18_pipe_update - Simple display pipe update callback
 * @pipe:       The DRM simple display pipe associated with the panel.
 * @old_state:  The previous plane state (for damage merge).
 *
 * When the plane state changes, we compute the merged damage region and call
 * mipi_dbi18_fb_dirty() to push the updated region to the panel. If the CRTC
 * is not active, we skip the update.
 */
void mipi_dbi18_pipe_update(struct drm_simple_display_pipe *pipe,
							struct drm_plane_state *old_state)
{
	struct drm_plane_state *state = pipe->plane.state;
	struct drm_rect rect;

	DRM_DEBUG_KMS("nc4_ili9488: pipe_update called\n");

	if (!pipe->crtc.state->active)
	{
		DRM_DEBUG_KMS("nc4_ili9488: pipe_update aborted: crtc not active\n");
		return;
	}

	if (drm_atomic_helper_damage_merged(old_state, state, &rect))
	{
		DRM_DEBUG_KMS("nc4_ili9488: merged damage rect: (" DRM_RECT_FMT ")\n",
					  DRM_RECT_ARG(&rect));
		mipi_dbi18_fb_dirty(state->fb, &rect);
	}
	else
	{
		DRM_DEBUG_KMS("nc4_ili9488: no damage to update\n");
	}
}

/* ------------------------------------------------------------------------- */
/*  mipi_dbi18_enable_flush - Flush the full screen and enable backlight     */
/* ------------------------------------------------------------------------- */

/**
 * mipi_dbi18_enable_flush - Flushes the entire screen and enables backlight.
 * @dbidev:      The MIPI DBI device container.
 * @crtc_state:  Unused, but part of the DRM pipeline enable signature.
 * @plane_state: The current plane state (where we get the fb).
 *
 * This function flushes the full screen area to the panel by marking the entire
 * framebuffer as dirty, then enables the backlight. Typically called when the
 * panel is first enabled via the .enable callback in the display pipe.
 */
void mipi_dbi18_enable_flush(struct mipi_dbi_dev *dbidev,
							 struct drm_crtc_state *crtc_state,
							 struct drm_plane_state *plane_state)
{
	struct drm_framebuffer *fb = plane_state->fb;
	struct drm_rect rect = {
		.x1 = 0,		  // Starting x-coordinate for flush
		.y1 = 0,		  // Starting y-coordinate for flush
		.x2 = fb->width,  // Ending x-coordinate (full width)
		.y2 = fb->height, // Ending y-coordinate (full height)
	};
	int idx;

	DRM_DEBUG_KMS("nc4_ili9488: enable_flush (full screen)\n");

	// Attempt to enter the device context. If it fails, log and return.
	if (!drm_dev_enter(&dbidev->drm, &idx))
	{
		DRM_DEBUG_KMS("nc4_ili9488: enable_flush drm_dev_enter failed\n");
		return;
	}

	// Mark the entire framebuffer as dirty to trigger a full refresh.
	mipi_dbi18_fb_dirty(fb, &rect);

	DRM_DEBUG_KMS("nc4_ili9488: enabling backlight\n");
	backlight_enable(dbidev->backlight);

	// Exit the device context to complete the operation.
	drm_dev_exit(idx);
}

/* ------------------------------------------------------------------------- */
/*                mipi_dbi18_dev_init - DRM device initialization           */
/* ------------------------------------------------------------------------- */

/**
 * mipi_dbi18_dev_init - Initialize the MIPI DBI device with certain formats
 * @dbidev:    MIPI DBI device to initialize.
 * @funcs:     The display pipe functions (enable, disable, update, etc.).
 * @mode:      The base mode (e.g., 320x480) for this panel.
 * @rotation:  Rotation angle in degrees (0, 90, 180, 270).
 *
 * Allocates resources and sets up the device with a 32-bit preferred depth.
 * Then calls mipi_dbi_dev_init_with_formats() to register a display pipe with
 * the specified pixel formats.
 */
int mipi_dbi18_dev_init(struct mipi_dbi_dev *dbidev,
						const struct drm_simple_display_pipe_funcs *funcs,
						const struct drm_display_mode *mode,
						unsigned int rotation)
{
	size_t bufsize = mode->vdisplay * mode->hdisplay * sizeof(u32);

	DRM_DEBUG_KMS("nc4_ili9488: mipi_dbi18_dev_init: mode=%dx%d rotation=%u\n",
				  mode->hdisplay, mode->vdisplay, rotation);

	// Prefer a 32-bit depth if possible
	dbidev->drm.mode_config.preferred_depth = 32;

	return mipi_dbi_dev_init_with_formats(dbidev, funcs,
										  mipi_dbi_formats,
										  ARRAY_SIZE(mipi_dbi_formats),
										  mode, rotation, bufsize);
}

/* ------------------------------------------------------------------------- */
/*        sx035hv006_enable - Panel-specific init sequence (enable)         */
/* ------------------------------------------------------------------------- */

/**
 * sx035hv006_enable - Panel enable callback for the simple_display_pipe
 * @pipe:        The DRM simple display pipe.
 * @crtc_state:  The new CRTC state (unused).
 * @plane_state: The new plane state (has the framebuffer).
 *
 * This function:
 *   - Ensures the device is powered on (poweron_conditional_reset).
 *   - Performs a hardware reset via the GPIO if present.
 *   - Sends a series of ILI9488 initialization commands (gammas, power config, etc.).
 *   - Sets rotation bits in the MEM_ACCESS_CTRL register.
 *   - Flushes the panel and enables the backlight.
 */
static void sx035hv006_enable(struct drm_simple_display_pipe *pipe,
							  struct drm_crtc_state *crtc_state,
							  struct drm_plane_state *plane_state)
{
	struct mipi_dbi_dev *dbidev = drm_to_mipi_dbi_dev(pipe->crtc.dev);
	struct mipi_dbi *dbi = &dbidev->dbi;
	u8 addr_mode;
	int ret, idx;

	DRM_DEBUG_KMS("nc4_ili9488: sx035hv006_enable called dev=%s cs=%d\n",
				  dev_name(pipe->crtc.dev->dev),
				  to_spi_device(pipe->crtc.dev->dev)->chip_select);

	if (!drm_dev_enter(pipe->crtc.dev, &idx))
	{
		DRM_DEBUG_KMS("nc4_ili9488: sx035hv006_enable drm_dev_enter failed\n");
		return;
	}

	ret = mipi_dbi_poweron_conditional_reset(dbidev);
	if (ret < 0)
	{
		drm_err_once(pipe->crtc.dev,
					 "nc4_ili9488: poweron_reset failed: %d\n", ret);
		goto out_exit;
	}
	if (ret == 1)
		goto out_enable; // Panel was already powered, skip re-init

	// Hardware reset pulse if reset GPIO is available
	if (dbi->reset)
	{
		gpiod_set_value_cansleep(dbi->reset, 0); // Drive reset low
		msleep(20);
		gpiod_set_value_cansleep(dbi->reset, 1); // Drive reset high
		msleep(120);
	}

	// Basic init commands with delay
	nc4_ili9488_send_cmd(dbi, "SW_RESET", ILI9488_CMD_SOFTWARE_RESET, 0);
	msleep(120);

	nc4_ili9488_send_cmd(dbi, "DISPLAY_OFF", ILI9488_CMD_DISPLAY_OFF, 0);

	nc4_ili9488_send_cmd(dbi, "POS_GAMMA", ILI9488_CMD_POSITIVE_GAMMA_CORRECTION, 15,
						 0x00, 0x03, 0x09, 0x08, 0x16, 0x0a,
						 0x3f, 0x78, 0x4c, 0x09, 0x0a, 0x08,
						 0x16, 0x1a, 0x0f);
	nc4_ili9488_send_cmd(dbi, "NEG_GAMMA", ILI9488_CMD_NEGATIVE_GAMMA_CORRECTION, 15,
						 0x00, 0x16, 0x19, 0x03, 0x0f, 0x05,
						 0x32, 0x45, 0x46, 0x04, 0x0e, 0x0d,
						 0x35, 0x37, 0x0f);

	nc4_ili9488_send_cmd(dbi, "PWR_CTRL1", ILI9488_CMD_POWER_CONTROL_1, 2, 0x17, 0x15);
	nc4_ili9488_send_cmd(dbi, "PWR_CTRL2", ILI9488_CMD_POWER_CONTROL_2, 1, 0x41);
	nc4_ili9488_send_cmd(dbi, "VCOM_CTRL1", ILI9488_CMD_VCOM_CONTROL_1, 3, 0x00, 0x12, 0x80);

	nc4_ili9488_send_cmd(dbi, "MEM_ACCESS_CTRL", ILI9488_CMD_MEMORY_ACCESS_CONTROL,
						 1, 0x48);
	nc4_ili9488_send_cmd(dbi, "PIXEL_FORMAT", ILI9488_CMD_COLMOD_PIXEL_FORMAT_SET,
						 1, (MIPI_DCS_PIXEL_FMT_18BIT << 1) | MIPI_DCS_PIXEL_FMT_18BIT);

	nc4_ili9488_send_cmd(dbi, "IF_MODE_CTRL", ILI9488_CMD_INTERFACE_MODE_CONTROL, 1, 0x00);
	nc4_ili9488_send_cmd(dbi, "FRAME_RATE", ILI9488_CMD_FRAME_RATE_CONTROL_NORMAL, 1, 0xA0);
	nc4_ili9488_send_cmd(dbi, "DISP_INV_CTRL", ILI9488_CMD_DISPLAY_INVERSION_CONTROL, 1, 0x02);
	nc4_ili9488_send_cmd(dbi, "DISP_FUNC_CTRL", ILI9488_CMD_DISPLAY_FUNCTION_CONTROL, 3,
						 0x02, 0x02, 0x3B);
	nc4_ili9488_send_cmd(dbi, "ENTRY_MODE_SET", ILI9488_CMD_ENTRY_MODE_SET, 1, 0xC6);
	nc4_ili9488_send_cmd(dbi, "ADJUST_CTRL3", ILI9488_CMD_ADJUST_CONTROL_3, 4,
						 0xa9, 0x51, 0x2c, 0x82);

	nc4_ili9488_send_cmd(dbi, "SLEEP_OUT", ILI9488_CMD_SLEEP_OUT, 0);
	msleep(120);

	nc4_ili9488_send_cmd(dbi, "NORMAL_MODE_ON", ILI9488_CMD_NORMAL_DISP_MODE_ON, 0);
	nc4_ili9488_send_cmd(dbi, "DISPLAY_ON", ILI9488_CMD_DISPLAY_ON, 0);
	msleep(100);

out_enable:
	// Set rotation bits for MEM_ACCESS_CTRL (or SET_ADDRESS_MODE).
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

	DRM_DEBUG_KMS("nc4_ili9488: setting address mode=0x%02X for rotation=%u\n",
				  addr_mode, dbidev->rotation);
	mipi_dbi_command(dbi, ILI9488_CMD_SET_ADDRESS_MODE, addr_mode);

	// Flush entire display and enable backlight
	mipi_dbi18_enable_flush(dbidev, crtc_state, plane_state);

	DRM_DEBUG_KMS("nc4_ili9488: Display enabled dev=%s cs=%d\n",
				  dev_name(pipe->crtc.dev->dev),
				  to_spi_device(pipe->crtc.dev->dev)->chip_select);

out_exit:
	drm_dev_exit(idx);
}

/* ------------------------------------------------------------------------- */
/*         Simple Display Pipe Functions / DRM Driver Registration          */
/* ------------------------------------------------------------------------- */

static const struct drm_simple_display_pipe_funcs nc4_ili9488_pipe_funcs = {
	.mode_valid = mipi_dbi_pipe_mode_valid, // from drm_mipi_dbi
	.enable = sx035hv006_enable,
	.disable = mipi_dbi_pipe_disable, // from drm_mipi_dbi
	.update = mipi_dbi18_pipe_update,
};

static const struct drm_display_mode sx035hv006_mode = {
	DRM_SIMPLE_MODE(320, 480, 49, 73),
};

/* File ops for GEM-based DRM drivers */
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

/* DRM driver definition */
static struct drm_driver nc4_ili9488_driver = {
	.driver_features = DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC,
	.fops = &nc4_ili9488_fops,
	DRM_GEM_DMA_DRIVER_OPS_VMAP,
	.debugfs_init = mipi_dbi_debugfs_init,
	.name = "nc4_ili9488",
	.desc = "Ilitek ILI9488",
	.date = "20230414",
	.major = 1,
	.minor = 0,
};

/* ------------------------------------------------------------------------- */
/*                     Device Tree Match / SPI ID Table                      */
/* ------------------------------------------------------------------------- */

static const struct of_device_id nc4_ili9488_of_match[] = {
	{.compatible = "nc4_ili9488"},
	{}};
MODULE_DEVICE_TABLE(of, nc4_ili9488_of_match);

static const struct spi_device_id nc4_ili9488_id[] = {
	{"nc4_ili9488", 0},
	{}};
MODULE_DEVICE_TABLE(spi, nc4_ili9488_id);

/* ------------------------------------------------------------------------- */
/*                  Probe / Remove / Shutdown SPI Driver                     */
/* ------------------------------------------------------------------------- */

/**
 * nc4_ili9488_probe - Probe routine for the SPI driver
 * @spi: Pointer to the spi_device.
 *
 * Allocates a mipi_dbi_dev, sets up reset/dc GPIO lines if present,
 * obtains the backlight device, reads 'rotation', and calls
 * mipi_dbi18_dev_init() to register the DRM device.
 */
static int nc4_ili9488_probe(struct spi_device *spi)
{
	struct device *dev = &spi->dev;
	struct mipi_dbi_dev *dbidev;
	struct drm_device *drm;
	struct mipi_dbi *dbi;
	struct gpio_desc *dc;
	u32 rotation = 0;
	int ret;

	dev_info(dev, "Loading ILI9488 driver %s\n", ILI9488_DRIVER_VERSION);
	dev_info(dev, "nc4_ili9488: Probing device (dev=%s cs=%d)\n",
			 dev_name(dev), spi->chip_select);

	dbidev = devm_drm_dev_alloc(dev, &nc4_ili9488_driver,
								struct mipi_dbi_dev, drm);
	if (IS_ERR(dbidev))
	{
		dev_err(dev, "nc4_ili9488: Failed to allocate drm device\n");
		return PTR_ERR(dbidev);
	}

	dbi = &dbidev->dbi;
	drm = &dbidev->drm;

	/* Attempt to get optional reset and dc lines */
	dbi->reset = devm_gpiod_get_optional(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(dbi->reset))
	{
		dev_err_probe(dev, PTR_ERR(dbi->reset),
					  "nc4_ili9488: Failed to get 'reset' GPIO\n");
		return PTR_ERR(dbi->reset);
	}
	else if (dbi->reset)
	{
		dev_info(dev, "nc4_ili9488: reset GPIO acquired\n");
	}
	else
	{
		dev_info(dev, "nc4_ili9488: no reset GPIO defined\n");
	}

	dc = devm_gpiod_get_optional(dev, "dc", GPIOD_OUT_LOW);
	if (IS_ERR(dc))
	{
		dev_err_probe(dev, PTR_ERR(dc),
					  "nc4_ili9488: Failed to get 'dc' GPIO\n");
		return PTR_ERR(dc);
	}
	else if (dc)
	{
		dev_info(dev, "nc4_ili9488: dc GPIO acquired\n");
	}
	else
	{
		dev_info(dev, "nc4_ili9488: no dc GPIO defined\n");
	}

	dbidev->backlight = devm_of_find_backlight(dev);
	if (IS_ERR(dbidev->backlight))
	{
		dev_err(dev, "nc4_ili9488: Failed to find backlight\n");
		return PTR_ERR(dbidev->backlight);
	}
	dev_info(dev, "nc4_ili9488: backlight found and initialized\n");

	device_property_read_u32(dev, "rotation", &rotation);
	dev_info(dev, "nc4_ili9488: Rotation property: %u (dev=%s cs=%d)\n",
			 rotation, dev_name(dev), spi->chip_select);

	/* Force the SPI mode*/
	//spi->mode = NC4_ILI9488_SPI_MODE;
	/* Optionally force bits per word or other parameters */
	// spi->bits_per_word = 8;
	// spi->max_speed_hz  = 4000000;

	ret = mipi_dbi_spi_init(spi, dbi, dc);
	if (ret)
	{
		dev_err(dev, "nc4_ili9488: SPI init failed: %d\n", ret);
		return ret;
	}
	dev_info(dev, "nc4_ili9488: SPI init successful, mode=0x%X max_speed_hz=%u\n",
			 spi->mode, spi->max_speed_hz);

	ret = mipi_dbi18_dev_init(dbidev, &nc4_ili9488_pipe_funcs,
							  &sx035hv006_mode, rotation);
	if (ret)
	{
		dev_err(dev, "nc4_ili9488: mipi_dbi device init failed: %d\n", ret);
		return ret;
	}
	dev_info(dev, "nc4_ili9488: mipi_dbi device initialized\n");

	// Reset the DRM mode configuration to clean state
	drm_mode_config_reset(drm);

	ret = drm_dev_register(drm, 0);
	if (ret)
	{
		dev_err(dev, "nc4_ili9488: DRM device registration failed: %d\n",
				ret);
		return ret;
	}
	dev_info(dev, "nc4_ili9488: DRM device registered\n");

	// Associate this SPI device with the DRM device
	spi_set_drvdata(spi, drm);

	// Setup fbdev emulation for legacy /dev/fbX
	drm_fbdev_generic_setup(drm, 0);

	dev_info(dev, "nc4_ili9488: Probe successful (dev=%s cs=%d), device ready\n",
			 dev_name(dev), spi->chip_select);

	return 0;
}

/**
 * nc4_ili9488_remove - Remove routine for the SPI driver
 * @spi: Pointer to the spi_device being removed.
 */
static void nc4_ili9488_remove(struct spi_device *spi)
{
	struct drm_device *drm = spi_get_drvdata(spi);

	dev_info(&spi->dev, "nc4_ili9488: Removing device (dev=%s cs=%d)\n",
			 dev_name(&spi->dev), spi->chip_select);

	drm_dev_unplug(drm);
	drm_atomic_helper_shutdown(drm);
}

/**
 * nc4_ili9488_shutdown - Shutdown routine for the SPI driver
 * @spi: Pointer to the spi_device being shutdown.
 */
static void nc4_ili9488_shutdown(struct spi_device *spi)
{
	dev_info(&spi->dev, "nc4_ili9488: Shutdown called (dev=%s cs=%d)\n",
			 dev_name(&spi->dev), spi->chip_select);
	drm_atomic_helper_shutdown(spi_get_drvdata(spi));
}

/* SPI driver definition */
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

MODULE_SOFTDEP("pre: drm drm_kms_helper drm_mipi_dbi drm_dma_helper");
MODULE_DESCRIPTION("Ilitek ILI9488 DRM driver with extensive debugging");
MODULE_AUTHOR("IHOR NEPOMNIASHCHYI <nepomniashchyi.igor@gmail.com>");
MODULE_LICENSE("GPL");
