// SPDX-License-Identifier: GPL-2.0
/*
 * nc4_ili9488 DRM driver for multiple ILI9488-based TFT panels on SPI
 *
 * This driver creates a single DRM device with multiple connectors, one
 * for each ILI9488 panel described in the Device Tree. It uses SPI to send
 * commands and pixel data to the panels. It sets a fixed mode of 320x480.
 *
 * Key points:
 * - No fbdev emulation, direct DRM/KMS usage.
 * - Multiple panels handled by parsing DT child nodes.
 * - Debugging: dev_info(), dev_err() calls throughout.
 * - Simple pixel conversion from XRGB8888 to RGB666 (as RGB888 with dropped bits).
 *
 * NOTE: This code is an illustrative example. Adjustments may be required.
 */

#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
#include <linux/of.h>
#include <linux/of_device.h>
#include <linux/backlight.h>
#include <linux/property.h>

#include <drm/drm_atomic_helper.h>
#include <drm/drm_damage_helper.h>
#include <drm/drm_drv.h>
#include <drm/drm_fb_helper.h>
#include <drm/drm_format_helper.h>
#include <drm/drm_modes.h>
#include <drm/drm_modeset_helper_vtables.h>
#include <drm/drm_probe_helper.h>
#include <drm/drm_gem_dma_helper.h>
#include <drm/drm_gem_framebuffer_helper.h>
#include <drm/drm_print.h>

#define DRIVER_NAME "nc4_ili9488"
#define DRIVER_DESC "nc4_ili9488 DRM driver"
#define DRIVER_DATE "20241219"
#define DRIVER_MAJOR 1
#define DRIVER_MINOR 0

/* Driver version for reference in logs */
#define ILI9488_DRIVER_VERSION "v1.0-debug"

/*
 * ILI9488 Commands (subset)
 */
#define ILI9488_CMD_SLEEP_OUT             0x11
#define ILI9488_CMD_DISPLAY_ON            0x29
#define ILI9488_CMD_COLMOD                0x3A
#define ILI9488_CMD_MADCTL                0x36

/*
 * We assume a fixed mode 320x480 for simplicity.
 */
#define PANEL_WIDTH 320
#define PANEL_HEIGHT 480

/*
 * Structure to describe each panel
 */
struct nc4_ili9488_panel {
	struct spi_device *spi;
	struct gpio_desc *dc_gpio;
	struct gpio_desc *reset_gpio;
	struct gpio_desc *bl_gpio;

	bool backlight_on;
	u32 rotation;

	struct drm_connector connector;
	struct drm_encoder encoder;
	struct drm_crtc *crtc; /* shared crtc */
	struct drm_plane *primary;
	struct drm_device *drm;
};

static inline struct nc4_ili9488_panel *conn_to_panel(struct drm_connector *c)
{
	return container_of(c, struct nc4_ili9488_panel, connector);
}

/*
 * Panel Functions
 */

static void nc4_ili9488_hw_reset(struct nc4_ili9488_panel *panel)
{
	if (panel->reset_gpio) {
		gpiod_set_value_cansleep(panel->reset_gpio, 1);
		msleep(20);
		gpiod_set_value_cansleep(panel->reset_gpio, 0);
		msleep(120);
	}
}

static int nc4_ili9488_send_cmd(struct nc4_ili9488_panel *panel, u8 cmd,
				const u8 *data, size_t len)
{
	int ret;
	u8 buf[64];

	if (len > sizeof(buf)-1)
		return -EINVAL;

	/* DC low for command */
	gpiod_set_value_cansleep(panel->dc_gpio, 0);
	buf[0] = cmd;
	ret = spi_write(panel->spi, buf, 1);
	if (ret < 0) {
		dev_err(&panel->spi->dev, "CMD(0x%02X) write failed: %d\n", cmd, ret);
		return ret;
	}

	if (data && len > 0) {
		/* DC high for data */
		gpiod_set_value_cansleep(panel->dc_gpio, 1);
		memcpy(buf, data, len);
		ret = spi_write(panel->spi, buf, len);
		if (ret < 0)
			dev_err(&panel->spi->dev, "CMD DATA write failed: %d\n", ret);
	}

	return ret;
}

static int nc4_ili9488_init_panel(struct nc4_ili9488_panel *panel)
{
	/* Hardware reset */
	nc4_ili9488_hw_reset(panel);

	/* Basic init sequence (example) */
	dev_info(&panel->spi->dev, "[nc4_ili9488] Initializing panel for ILI9488 driver %s\n", ILI9488_DRIVER_VERSION);

	/* Exit sleep */
	nc4_ili9488_send_cmd(panel, ILI9488_CMD_SLEEP_OUT, NULL, 0);
	msleep(120);

	/* Pixel format: 18-bit (RGB666) */
	{
		u8 colmod = 0x66; /* 18-bit per pixel */
		nc4_ili9488_send_cmd(panel, ILI9488_CMD_COLMOD, &colmod, 1);
	}

	/* Memory access control */
	{
		u8 madctl = 0x48; /* Portrait, BGR order, etc. Adjust if needed */
		nc4_ili9488_send_cmd(panel, ILI9488_CMD_MADCTL, &madctl, 1);
	}

	/* Display ON */
	nc4_ili9488_send_cmd(panel, ILI9488_CMD_DISPLAY_ON, NULL, 0);
	msleep(100);

	/* Turn on backlight if available */
	if (panel->bl_gpio) {
		gpiod_set_value_cansleep(panel->bl_gpio, 1);
		panel->backlight_on = true;
	}

	dev_info(&panel->spi->dev, "[nc4_ili9488] Panel init done\n");
	return 0;
}

/*
 * DRM Structures and Functions
 */

static const struct drm_display_mode nc4_ili9488_mode = {
	.clock = 10000, /* Dummy, not really used for SPI panels */
	.hdisplay = PANEL_WIDTH,
	.hsync_start = PANEL_WIDTH + 20,
	.hsync_end = PANEL_WIDTH + 20 + 10,
	.htotal = PANEL_WIDTH + 40,
	.vdisplay = PANEL_HEIGHT,
	.vsync_start = PANEL_HEIGHT + 4,
	.vsync_end = PANEL_HEIGHT + 4 + 2,
	.vtotal = PANEL_HEIGHT + 8,
	.flags = DRM_MODE_FLAG_NHSYNC | DRM_MODE_FLAG_NVSYNC,
};

/* Connector funcs */
static enum drm_connector_status nc4_ili9488_conn_detect(struct drm_connector *connector, bool force)
{
	return connector_status_connected;
}

static int nc4_ili9488_conn_get_modes(struct drm_connector *connector)
{
	struct drm_display_mode *mode;
	mode = drm_mode_duplicate(connector->dev, &nc4_ili9488_mode);
	if (!mode)
		return 0;

	mode->type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED;
	drm_mode_probed_add(connector, mode);
	return 1;
}

static const struct drm_connector_funcs nc4_ili9488_connector_funcs = {
	.detect = nc4_ili9488_conn_detect,
	.fill_modes = drm_helper_probe_single_connector_modes,
	.destroy = drm_connector_cleanup,
	.reset = drm_atomic_helper_connector_reset,
	.atomic_duplicate_state = drm_atomic_helper_connector_duplicate_state,
	.atomic_destroy_state = drm_atomic_helper_connector_destroy_state,
};

static const struct drm_connector_helper_funcs nc4_ili9488_connector_helper_funcs = {
	.get_modes = nc4_ili9488_conn_get_modes,
};

/* Encoder funcs (simple) */
static const struct drm_encoder_funcs nc4_ili9488_encoder_funcs = {
	.destroy = drm_encoder_cleanup,
};

/* Plane funcs for primary */
static const struct drm_plane_funcs nc4_ili9488_plane_funcs = {
	.update_dirty = drm_atomic_helper_damage_merged,
	.destroy = drm_plane_cleanup,
	.reset = drm_atomic_helper_plane_reset,
	.atomic_duplicate_state = drm_atomic_helper_plane_duplicate_state,
	.atomic_destroy_state = drm_atomic_helper_plane_destroy_state,
};

/*
 * We will do a simple atomic_commit that triggers a full SPI update.
 * For simplicity, we just rely on a dumb buffer and do a software conversion.
 */

static void nc4_ili9488_convert_xrgb8888_to_rgb666(u8 *dst, const u32 *src, size_t pixels)
{
	/*
	 * XRGB8888: 8 bits per R,G,B
	 * RGB666: 6 bits per R,G,B
	 * We'll just shift right by 2 for each channel:
	 * R: src>>16, G: src>>8, B: src>>0
	 * Extract top 6 bits of each.
	 */
	while (pixels--) {
		u32 val = *src++;
		u8 r = (val >> 16) & 0xFF;
		u8 g = (val >> 8) & 0xFF;
		u8 b = val & 0xFF;

		r >>= 2;
		g >>= 2;
		b >>= 2;

		/* RGB666 packed in 3 bytes per pixel (full RGB888 but lower bits truncated) */
		*dst++ = r;
		*dst++ = g;
		*dst++ = b;
	}
}

static int nc4_ili9488_spi_update_panel(struct nc4_ili9488_panel *panel,
				       struct drm_framebuffer *fb,
				       struct drm_rect *rect)
{
	/*
	 * For simplicity, always update full frame.
	 * In practice, we can set window (0x2A,0x2B) and then write memory (0x2C).
	 */
	struct drm_gem_object *gem = drm_gem_fb_get_obj(fb, 0);
	if (!gem)
		return -EINVAL;

	u32 *vaddr;
	u8 *xfer_buf;
	size_t size = PANEL_WIDTH * PANEL_HEIGHT * 3;
	int ret = 0;
	struct iosys_map map;

	ret = drm_gem_fb_vmap(fb, &map, NULL);
	if (ret)
		return ret;

	vaddr = map.vaddr;
	xfer_buf = kzalloc(size, GFP_KERNEL);
	if (!xfer_buf) {
		drm_gem_fb_vunmap(fb, &map);
		return -ENOMEM;
	}

	nc4_ili9488_convert_xrgb8888_to_rgb666(xfer_buf, vaddr, PANEL_WIDTH * PANEL_HEIGHT);

	drm_gem_fb_vunmap(fb, &map);

	/* Set column/page address (full) */
	{
		u8 col_data[4] = {0x00,0x00, (PANEL_WIDTH-1)>>8, (PANEL_WIDTH-1)&0xFF};
		u8 row_data[4] = {0x00,0x00, (PANEL_HEIGHT-1)>>8, (PANEL_HEIGHT-1)&0xFF};

		nc4_ili9488_send_cmd(panel, 0x2A, col_data, 4);
		nc4_ili9488_send_cmd(panel, 0x2B, row_data, 4);
	}

	/* Memory write (0x2C) */
	gpiod_set_value_cansleep(panel->dc_gpio, 0);
	spi_write(panel->spi, "\x2C", 1);
	gpiod_set_value_cansleep(panel->dc_gpio, 1);

	ret = spi_write(panel->spi, xfer_buf, size);
	if (ret < 0)
		dev_err(&panel->spi->dev, "[nc4_ili9488] SPI write failed: %d\n", ret);

	kfree(xfer_buf);
	return ret;
}

/*
 * Simple atomic commit callback
 */

static const struct drm_crtc_funcs nc4_ili9488_crtc_funcs = {
	.destroy = drm_crtc_cleanup,
	.reset = drm_atomic_helper_crtc_reset,
	.atomic_duplicate_state = drm_atomic_helper_crtc_duplicate_state,
	.atomic_destroy_state = drm_atomic_helper_crtc_destroy_state,
};

static const struct drm_crtc_helper_funcs nc4_ili9488_crtc_helper_funcs = {
	.atomic_enable = drm_atomic_helper_crtc_atomic_enable,
	.atomic_disable = drm_atomic_helper_crtc_atomic_disable,
};

static const struct drm_plane_helper_funcs nc4_ili9488_plane_helper_funcs = {
	.atomic_update = drm_atomic_helper_primary_plane_update,
};

static const struct drm_encoder_helper_funcs nc4_ili9488_encoder_helper_funcs = {
	.atomic_enable = drm_atomic_helper_encoder_atomic_enable,
	.atomic_disable = drm_atomic_helper_encoder_atomic_disable,
};

static const struct drm_mode_config_funcs nc4_ili9488_mode_config_funcs = {
	.fb_create = drm_gem_fb_create,
	.atomic_check = drm_atomic_helper_check,
	.atomic_commit = drm_atomic_helper_commit,
};

/*
 * Atomic commit tail: Once we've got a framebuffer, perform SPI update.
 * We can hook into drm_atomic_helper_commit_tail to do updates after commit.
 */

static void nc4_ili9488_atomic_flush(struct drm_atomic_state *state)
{
	struct drm_device *dev = state->dev;
	struct drm_plane *plane;
	struct drm_plane_state *new_plane_state;
	drm_for_each_plane_mask(plane, dev, state->plane_mask) {
		new_plane_state = drm_atomic_get_new_plane_state(state, plane);
		if (new_plane_state && new_plane_state->fb) {
			/* Update all panels with the fb content */
			/* In a more complex scenario, track per-panel connectors. Here we do all. */
			struct drm_connector *conn;
			drm_for_each_connector(dev, conn) {
				if (conn->state && conn->state->crtc == new_plane_state->crtc) {
					struct nc4_ili9488_panel *panel = conn_to_panel(conn);
					nc4_ili9488_spi_update_panel(panel, new_plane_state->fb, NULL);
				}
			}
		}
	}
	drm_atomic_helper_commit_modeset_disables(dev, state);
	drm_atomic_helper_commit_hw_done(state);
	drm_atomic_helper_wait_for_vblanks(dev, state);
	drm_atomic_helper_cleanup_planes(dev, state);
}

static const struct drm_mode_config_helper_funcs nc4_ili9488_mode_config_helpers = {
	.atomic_commit_tail = nc4_ili9488_atomic_flush,
};

/*
 * Probe and setup
 */

static const struct of_device_id nc4_ili9488_of_match[] = {
	{ .compatible = "mycompany,ili9488" },
	{},
};
MODULE_DEVICE_TABLE(of, nc4_ili9488_of_match);

struct nc4_ili9488_drvdata {
	struct drm_device drm;
	struct drm_crtc crtc;
	struct drm_plane primary;
	struct drm_encoder encoder; /* one encoder shared by all connectors */
	struct spi_device *spi;
	struct gpio_desc *bl_gpio;
	struct list_head panels;
};

struct panel_list_entry {
	struct list_head list;
	struct nc4_ili9488_panel panel;
};

static int nc4_ili9488_create_connector_for_panel(struct nc4_ili9488_drvdata *drvdata,
						  struct device_node *np)
{
	struct spi_device *spi = drvdata->spi;
	struct panel_list_entry *ple;
	int ret;

	ple = devm_kzalloc(&spi->dev, sizeof(*ple), GFP_KERNEL);
	if (!ple)
		return -ENOMEM;

	ple->panel.spi = spi;
	ple->panel.bl_gpio = NULL; /* Will be set if found */
	ple->panel.rotation = 0;

	ple->panel.dc_gpio = devm_gpiod_get(&spi->dev, "dc", GPIOD_OUT_LOW);
	if (IS_ERR(ple->panel.dc_gpio)) {
		ret = PTR_ERR(ple->panel.dc_gpio);
		dev_err(&spi->dev, "Failed to get dc-gpios: %d\n", ret);
		return ret;
	}

	ple->panel.reset_gpio = devm_gpiod_get_optional_from_of_node(np, "reset-gpios", 0,
								      GPIOD_OUT_LOW, "reset");
	if (IS_ERR(ple->panel.reset_gpio)) {
		ret = PTR_ERR(ple->panel.reset_gpio);
		dev_err(&spi->dev, "Failed to get reset-gpios: %d\n", ret);
		return ret;
	}

	/* Shared backlight - we can just reuse one GPIO from any panel if desired.
	 * Or each panel node references the same GPIO.
	 */
	if (!drvdata->bl_gpio) {
		drvdata->bl_gpio = devm_gpiod_get_optional_from_of_node(np, "backlight-gpios", 0,
									GPIOD_OUT_LOW, "backlight");
		if (IS_ERR(drvdata->bl_gpio)) {
			ret = PTR_ERR(drvdata->bl_gpio);
			dev_err(&spi->dev, "Failed to get backlight-gpios: %d\n", ret);
			return ret;
		}
	}
	ple->panel.bl_gpio = drvdata->bl_gpio;

	of_property_read_u32(np, "rotation", &ple->panel.rotation);

	/* Initialize connector */
	drm_connector_init(&drvdata->drm, &ple->panel.connector,
			   &nc4_ili9488_connector_funcs, DRM_MODE_CONNECTOR_SPI);
	drm_connector_helper_add(&ple->panel.connector, &nc4_ili9488_connector_helper_funcs);

	ple->panel.connector.polled = DRM_CONNECTOR_POLL_CONNECT;
	drm_connector_attach_encoder(&ple->panel.connector, &drvdata->encoder);

	list_add_tail(&ple->list, &drvdata->panels);

	dev_info(&spi->dev, "[nc4_ili9488] Panel connector created\n");

	/* Init panel hardware */
	nc4_ili9488_init_panel(&ple->panel);

	return 0;
}

static int nc4_ili9488_probe(struct spi_device *spi)
{
	struct nc4_ili9488_drvdata *drvdata;
	struct device_node *child;
	int ret;

	dev_info(&spi->dev, "[nc4_ili9488] Probe start\n");

	drvdata = devm_kzalloc(&spi->dev, sizeof(*drvdata), GFP_KERNEL);
	if (!drvdata)
		return -ENOMEM;

	drvdata->spi = spi;
	INIT_LIST_HEAD(&drvdata->panels);

	spi_set_drvdata(spi, drvdata);

	/* DRM device init */
	drm_dev_init(&drvdata->drm, NULL, &spi->dev);
	drvdata->drm.driver_features = DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC;
	drvdata->drm.mode_config.funcs = &nc4_ili9488_mode_config_funcs;
	drvdata->drm.mode_config.helper_private = &nc4_ili9488_mode_config_helpers;
	drvdata->drm.mode_config.min_width = PANEL_WIDTH;
	drvdata->drm.mode_config.max_width = PANEL_WIDTH;
	drvdata->drm.mode_config.min_height = PANEL_HEIGHT;
	drvdata->drm.mode_config.max_height = PANEL_HEIGHT;

	/* CRTC, Encoder, Plane */
	drm_plane_init_primary(&drvdata->drm, &drvdata->primary, 0,
			       &nc4_ili9488_plane_funcs,
			       drm_format_default_rgb, ARRAY_SIZE(drm_format_default_rgb),
			       NULL, DRM_PLANE_TYPE_PRIMARY, NULL);
	drm_plane_helper_add(&drvdata->primary, &nc4_ili9488_plane_helper_funcs);

	drm_crtc_init_with_planes(&drvdata->drm, &drvdata->crtc, &drvdata->primary, NULL,
				  &nc4_ili9488_crtc_funcs, NULL);
	drm_crtc_helper_add(&drvdata->crtc, &nc4_ili9488_crtc_helper_funcs);

	drm_encoder_init(&drvdata->drm, &drvdata->encoder, &nc4_ili9488_encoder_funcs,
			  DRM_MODE_ENCODER_NONE, NULL);
	drm_encoder_helper_add(&drvdata->encoder, &nc4_ili9488_encoder_helper_funcs);

	/* Iterate over child nodes for panels */
	for_each_child_of_node(spi->dev.of_node, child) {
		ret = nc4_ili9488_create_connector_for_panel(drvdata, child);
		if (ret)
			dev_err(&spi->dev, "Failed to create panel connector: %d\n", ret);
	}

	drm_mode_config_reset(&drvdata->drm);

	ret = drm_dev_register(&drvdata->drm, 0);
	if (ret) {
		dev_err(&spi->dev, "Failed to register DRM device: %d\n", ret);
		drm_dev_put(&drvdata->drm);
		return ret;
	}

	dev_info(&spi->dev, "[nc4_ili9488] Probe complete, DRM device registered\n");
	return 0;
}

static int nc4_ili9488_remove(struct spi_device *spi)
{
	struct nc4_ili9488_drvdata *drvdata = spi_get_drvdata(spi);

	dev_info(&spi->dev, "[nc4_ili9488] Remove\n");

	drm_dev_unregister(&drvdata->drm);
	drm_dev_put(&drvdata->drm);
	return 0;
}

static struct spi_driver nc4_ili9488_driver = {
	.driver = {
		.name = DRIVER_NAME,
		.of_match_table = nc4_ili9488_of_match,
	},
	.probe = nc4_ili9488_probe,
	.remove = nc4_ili9488_remove,
};
module_spi_driver(nc4_ili9488_driver);

MODULE_DESCRIPTION(DRIVER_DESC);
MODULE_AUTHOR("Your Name <youremail@example.com>");
MODULE_LICENSE("GPL");
