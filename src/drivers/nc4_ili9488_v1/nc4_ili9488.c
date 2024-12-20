// nc4_ili9488.c
// A Linux DRM driver for multiple ILI9488 panels on a single SPI bus
// Author: Your Name
// License: GPL-2.0-only (as is common for kernel code)

#include "nc4_ili9488.h"
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/gpio/consumer.h>
#include <linux/of.h>
#include <linux/of_device.h>
#include <linux/delay.h>
#include <drm/drm_atomic_helper.h>
#include <drm/drm_modes.h>
#include <drm/drm_simple_kms_helper.h>
#include <drm/drm_probe_helper.h>
#include <drm/drm_edid.h>

#define DRIVER_NAME "nc4_ili9488"
#define DRIVER_DESC "nc4_ili9488 DRM/KMS driver"
#define DRIVER_DATE "20241219"
#define DRIVER_MAJOR 1
#define DRIVER_MINOR 0

/* Driver version for reference in logs */
#define ILI9488_DRIVER_VERSION "v1.0-debug"

/* Basic ILI9488 commands (placeholders for init) */
#define ILI9488_CMD_SLEEP_OUT       0x11
#define ILI9488_CMD_DISPLAY_ON      0x29
#define ILI9488_CMD_PIXEL_FORMAT    0x3A
#define ILI9488_CMD_MADCTL          0x36

/* Fixed mode for ILI9488: 320x480 */
static const struct drm_display_mode ili9488_mode = {
	.name = "320x480",
	.clock = 6400, /* pixel clock in kHz (approx) */
	.hdisplay = 320,
	.hsync_start = 320 + 10,
	.hsync_end = 320 + 10 + 10,
	.htotal = 320 + 10 + 10 + 10,
	.vdisplay = 480,
	.vsync_start = 480 + 4,
	.vsync_end = 480 + 4 + 4,
	.vtotal = 480 + 4 + 4 + 4,
	.flags = DRM_MODE_FLAG_NHSYNC | DRM_MODE_FLAG_NVSYNC,
};

/* Forward declarations */
static int nc4_ili9488_enable_backlight(struct nc4_ili9488_device *priv, bool on);

/* Helpers to write commands/data over SPI */
static int nc4_ili9488_write_cmd(struct nc4_ili9488_panel *panel, u8 cmd)
{
	gpiod_set_value(panel->dc_gpio, 0); /* DC low for command */
	return spi_write(panel->spi, &cmd, 1);
}

static int nc4_ili9488_write_data(struct nc4_ili9488_panel *panel, const u8 *data, size_t len)
{
	gpiod_set_value(panel->dc_gpio, 1); /* DC high for data */
	return spi_write(panel->spi, data, len);
}

static int nc4_ili9488_panel_init(struct nc4_ili9488_panel *panel)
{
	dev_info(panel->dev, "Initializing ILI9488 panel with driver %s\n", ILI9488_DRIVER_VERSION);

	/* Hardware reset */
	if (panel->reset_gpio) {
		gpiod_set_value(panel->reset_gpio, 1);
		msleep(10);
		gpiod_set_value(panel->reset_gpio, 0);
		msleep(20);
		gpiod_set_value(panel->reset_gpio, 1);
		msleep(120);
	}

	/* Example init sequence */
	nc4_ili9488_write_cmd(panel, ILI9488_CMD_SLEEP_OUT);
	msleep(120);
	nc4_ili9488_write_cmd(panel, ILI9488_CMD_DISPLAY_ON);

	/* Set pixel format to 18-bit */
	{
		u8 fmt = 0x66; /* RGB666 */
		nc4_ili9488_write_cmd(panel, ILI9488_CMD_PIXEL_FORMAT);
		nc4_ili9488_write_data(panel, &fmt, 1);
	}

	/* Memory access control - no rotation, BGR if needed */
	{
		u8 madctl = 0x00; /* Adjust as needed for orientation */
		nc4_ili9488_write_cmd(panel, ILI9488_CMD_MADCTL);
		nc4_ili9488_write_data(panel, &madctl, 1);
	}

	dev_info(panel->dev, "ILI9488 panel initialized\n");
	return 0;
}

/* Convert XRGB8888 to RGB666 and write to panel.
   This is a simplistic pixel update assuming full screen updates. */
int nc4_ili9488_write_pixels(struct nc4_ili9488_panel *panel, u32 *buf, int width, int height)
{
	int x, y;
	int ret;
	u8 cmd_colset[4] = {0x00, 0x00, (width-1)>>8, (width-1)&0xFF};
	u8 cmd_rowset[4] = {0x00, 0x00, (height-1)>>8, (height-1)&0xFF};

	/* Set column address */
	nc4_ili9488_write_cmd(panel, 0x2A);
	nc4_ili9488_write_data(panel, cmd_colset, 4);

	/* Set row address */
	nc4_ili9488_write_cmd(panel, 0x2B);
	nc4_ili9488_write_data(panel, cmd_rowset, 4);

	/* Memory write */
	nc4_ili9488_write_cmd(panel, 0x2C);

	/* Now write pixel data: RGB666 = 3 bytes per pixel, but last 2 bits ignored */
	gpiod_set_value(panel->dc_gpio, 1);
	for (y = 0; y < height; y++) {
		for (x = 0; x < width; x++) {
			u32 pix = buf[y * width + x];
			/* XRGB8888 -> RGB666: Just take top 6 bits of R,G,B:
			 * R = (pix >> 16) & 0xff; G = (pix >> 8) & 0xff; B = pix & 0xff;
			 * RGB666 means 6 bits per color, so >>2 to get from 8-bit to 6-bit.
			 */
			u8 r = (pix >> 16) >> 2;
			u8 g = (pix >> 8) >> 2;
			u8 b = (pix & 0xff) >> 2;

			u8 data[3] = {(r & 0x3F), (g & 0x3F), (b & 0x3F)};
			/* Shift bits into proper positioning: For simplicity, send them as
			   RRRRRRGG GGGGBBBB BBBB (we might need to adjust bit ordering 
			   depending on panel's exact requirement, but let's assume linear) */

			/* Actually, ILI9488 expects RGB in 3 bytes per pixel for 18-bit:
			   data = [R6bits, G6bits, B6bits], each occupying top 6 bits. 
			   If exact bit ordering differs, adjust here. */

			/* Just send as is, top bits used. For a real panel, you might need
			   to shift them left by 2 bits to align with 8-bit boundaries: 
			   R in top bits of first byte, etc. Let's do that: */
			u8 send[3] = { (r << 2), (g << 2), (b << 2) };
			ret = spi_write(panel->spi, send, 3);
			if (ret)
				return ret;
		}
	}
	return 0;
}

/* DRM callbacks */

static enum drm_connector_status nc4_ili9488_connector_detect(struct drm_connector *connector, bool force)
{
	return connector_status_connected;
}

static const struct drm_connector_funcs nc4_ili9488_connector_funcs = {
	.reset = drm_atomic_helper_connector_reset,
	.fill_modes = drm_helper_probe_single_connector_modes,
	.detect = nc4_ili9488_connector_detect,
	.atomic_destroy_state = drm_atomic_helper_connector_destroy_state,
	.atomic_duplicate_state = drm_atomic_helper_connector_duplicate_state,
};

static int nc4_ili9488_connector_get_modes(struct drm_connector *connector)
{
	struct nc4_ili9488_panel *panel = container_of(connector, struct nc4_ili9488_panel, connector);

	drm_mode_probed_add(connector, drm_mode_duplicate(connector->dev, &panel->mode));
	return 1;
}

static const struct drm_connector_helper_funcs nc4_ili9488_connector_helper_funcs = {
	.get_modes = nc4_ili9488_connector_get_modes,
};

static const uint32_t nc4_ili9488_formats[] = { DRM_FORMAT_XRGB8888 };

static void nc4_ili9488_pipe_enable(struct drm_simple_display_pipe *pipe,
				    struct drm_crtc_state *crtc_state,
				    struct drm_plane_state *plane_state)
{
	// Panel enable: turn on backlight if not on
	struct nc4_ili9488_device *priv = container_of(pipe->crtc.dev, struct nc4_ili9488_device, drm);
	nc4_ili9488_enable_backlight(priv, true);
}

static void nc4_ili9488_pipe_disable(struct drm_simple_display_pipe *pipe)
{
	struct nc4_ili9488_device *priv = container_of(pipe->crtc.dev, struct nc4_ili9488_device, drm);
	/* If desired, you could turn off backlight here if no panels active */
	// For simplicity, leave backlight on. Or count active panels to decide.
}

static void nc4_ili9488_pipe_update(struct drm_simple_display_pipe *pipe,
				    struct drm_plane_state *old_state)
{
	struct drm_plane_state *new_state = pipe->plane.state;
	struct nc4_ili9488_panel *panel = container_of(pipe, struct nc4_ili9488_panel, pipe);
	struct drm_framebuffer *fb = new_state->fb;
	if (!fb)
		return;

	/* Map the framebuffer and write pixels out */
	struct drm_gem_cma_object *bo = drm_fb_cma_get_gem_obj(fb, 0);
	u32 *buf = (u32 *)bo->vaddr;

	nc4_ili9488_write_pixels(panel, buf, fb->width, fb->height);
}

static const struct drm_simple_display_pipe_funcs nc4_ili9488_pipe_funcs = {
	.enable = nc4_ili9488_pipe_enable,
	.disable = nc4_ili9488_pipe_disable,
	.update = nc4_ili9488_pipe_update,
};

static int nc4_ili9488_enable_backlight(struct nc4_ili9488_device *priv, bool on)
{
	int i;
	bool any_active = false;
	for (i = 0; i < priv->panel_count; i++) {
		if (priv->panels[i].backlight_gpio)
			any_active = true;
	}
	if (!any_active)
		return 0;

	/* If we have a shared backlight line, just set it to on/off */
	// For now, always turn it on if requested; never turn off if multiple panels might need it.
	if (on && !priv->backlight_active) {
		/* Set backlight GPIO high */
		// Assume active high backlight
		gpiod_set_value(priv->panels[0].backlight_gpio, 1);
		priv->backlight_active = true;
	} else if (!on && priv->backlight_active) {
		gpiod_set_value(priv->panels[0].backlight_gpio, 0);
		priv->backlight_active = false;
	}
	return 0;
}

static const struct drm_mode_config_funcs nc4_ili9488_mode_config_funcs = {
	.atomic_check = drm_atomic_helper_check,
	.atomic_commit = drm_atomic_helper_commit,
};

static const struct of_device_id nc4_ili9488_of_match[] = {
	{ .compatible = "mycompany,ili9488" },
	{}
};
MODULE_DEVICE_TABLE(of, nc4_ili9488_of_match);

static int nc4_ili9488_probe(struct spi_device *spi)
{
	struct device *dev = &spi->dev;
	struct nc4_ili9488_device *priv;
	struct drm_device *drm;
	struct device_node *child;
	int ret;
	int panel_index = 0;

	dev_info(dev, "Probing %s\n", DRIVER_NAME);

	/* Allocate and init DRM device */
	priv = devm_kzalloc(dev, sizeof(*priv), GFP_KERNEL);
	if (!priv)
		return -ENOMEM;

	drm = &priv->drm;
	drm_dev_init(drm, &drm_simple_driver_fops, dev);
	drm->dev_private = priv;

	/* Initialize mode_config */
	drm_mode_config_init(drm);
	drm->mode_config.min_width = 320;
	drm->mode_config.min_height = 480;
	drm->mode_config.max_width = 320;
	drm->mode_config.max_height = 480;
	drm->mode_config.funcs = &nc4_ili9488_mode_config_funcs;

	/* Find panel child nodes */
	for_each_child_of_node(dev->of_node, child) {
		if (panel_index >= NC4_ILI9488_MAX_PANELS) {
			dev_warn(dev, "Max panels exceeded\n");
			break;
		}

		struct nc4_ili9488_panel *panel = &priv->panels[panel_index];

		panel->dev = dev;
		panel->spi = spi;
		spi->max_speed_hz = 32000000; /* Example: 32MHz, adjust as stable */
		spi_setup(spi);

		panel->reset_gpio = devm_gpiod_get_from_of_node(dev, child, "reset-gpios", 0, GPIOD_OUT_LOW, "ili9488_reset");
		if (IS_ERR(panel->reset_gpio)) {
			dev_err(dev, "Failed to get reset-gpios\n");
			panel->reset_gpio = NULL;
		}

		panel->dc_gpio = devm_gpiod_get_from_of_node(dev, child, "dc-gpios", 0, GPIOD_OUT_LOW, "ili9488_dc");
		if (IS_ERR(panel->dc_gpio)) {
			dev_err(dev, "Failed to get dc-gpios\n");
			panel->dc_gpio = NULL;
			continue;
		}

		/* Shared backlight - only need one but we can store in each */
		panel->backlight_gpio = devm_gpiod_get_from_of_node(dev, child, "backlight-gpios", 0, GPIOD_OUT_LOW, "ili9488_bl");
		if (IS_ERR(panel->backlight_gpio)) {
			dev_info(dev, "No backlight GPIO found. Panel will still run.\n");
			panel->backlight_gpio = NULL;
		}

		/* Initialize panel */
		panel->mode = ili9488_mode;
		ret = nc4_ili9488_panel_init(panel);
		if (ret) {
			dev_err(dev, "Failed to init panel %d\n", panel_index);
			continue;
		}

		/* Create display pipeline for this panel */
		ret = drm_simple_display_pipe_init(drm, &panel->pipe, &nc4_ili9488_pipe_funcs,
						   nc4_ili9488_formats, ARRAY_SIZE(nc4_ili9488_formats),
						   NULL, &panel->connector);
		if (ret) {
			dev_err(dev, "Failed to init display pipe for panel %d\n", panel_index);
			continue;
		}

		drm_connector_helper_add(&panel->connector, &nc4_ili9488_connector_helper_funcs);
		panel->connector.funcs = &nc4_ili9488_connector_funcs;

		drm_connector_register(&panel->connector);

		/* Set panel as enabled (later can handle disable) */
		dev_info(dev, "Panel %d registered\n", panel_index);
		panel_index++;
	}

	priv->panel_count = panel_index;

	/* Register DRM device */
	ret = drm_dev_register(drm, 0);
	if (ret) {
		dev_err(dev, "Failed to register DRM device\n");
		goto err_cleanup;
	}

	drm_fbdev_emulation = 0; /* Ensure no fbdev emulation */
	drm_atomic_helper_disable_all(drm, drm->mode_config.acquire_ctx);

	drm_kms_helper_poll_init(drm);

	dev_info(dev, "%s probe complete with %d panel(s)\n", DRIVER_NAME, priv->panel_count);
	return 0;

err_cleanup:
	drm_mode_config_cleanup(drm);
	drm_dev_put(drm);
	return ret;
}

static int nc4_ili9488_remove(struct spi_device *spi)
{
	struct device *dev = &spi->dev;
	struct nc4_ili9488_device *priv = dev_get_drvdata(dev);
	struct drm_device *drm = &priv->drm;

	drm_dev_unplug(drm);
	drm_atomic_helper_shutdown(drm);
	drm_mode_config_cleanup(drm);
	drm_dev_put(drm);
	dev_info(dev, "%s removed\n", DRIVER_NAME);
	return 0;
}

static const struct spi_device_id nc4_ili9488_id[] = {
	{ "nc4_ili9488", 0 },
	{}
};
MODULE_DEVICE_TABLE(spi, nc4_ili9488_id);

static struct spi_driver nc4_ili9488_driver = {
	.driver = {
		.name = DRIVER_NAME,
		.of_match_table = nc4_ili9488_of_match,
	},
	.id_table = nc4_ili9488_id,
	.probe = nc4_ili9488_probe,
	.remove = nc4_ili9488_remove,
};

module_spi_driver(nc4_ili9488_driver);

MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION(DRIVER_DESC);
MODULE_LICENSE("GPL");
