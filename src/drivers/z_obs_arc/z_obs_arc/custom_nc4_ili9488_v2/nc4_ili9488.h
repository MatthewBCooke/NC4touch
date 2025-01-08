/* nc4_ili9488.h
 *
 * Header file for nc4_ili9488 DRM driver
 */

#ifndef __NC4_ILI9488_H__
#define __NC4_ILI9488_H__

#include <linux/gpio/consumer.h>
#include <linux/spi/spi.h>
#include <drm/drm_crtc.h>
#include <drm/drm_crtc_helper.h>
#include <drm/drm_encoder.h>
#include <drm/drm_connector.h>
#include <drm/drm_plane.h>
#include <drm/drm_device.h>
#include <drm/drm_modes.h>
#include <drm/drm_simple_kms_helper.h>

#define NC4_ILI9488_MAX_PANELS 3

struct nc4_ili9488_panel {
	struct device *dev;
	struct spi_device *spi;
	struct gpio_desc *reset_gpio;
	struct gpio_desc *dc_gpio;
	struct gpio_desc *backlight_gpio; /* shared among panels, same line */
	bool backlight_on;

	/* DRM objects specific to this panel */
	struct drm_simple_display_pipe pipe; 
	struct drm_connector connector;
	struct drm_encoder encoder;

	/* Mode info */
	struct drm_display_mode mode;
};

struct nc4_ili9488_device {
	struct drm_device drm;
	struct drm_plane primary_plane[NC4_ILI9488_MAX_PANELS];
	struct nc4_ili9488_panel panels[NC4_ILI9488_MAX_PANELS];
	int panel_count;

	/* Shared SPI master, backlight gpio might be duplicated across panels */
	bool backlight_active;
};

int nc4_ili9488_panel_init(struct nc4_ili9488_panel *panel);
int nc4_ili9488_write_pixels(struct nc4_ili9488_panel *panel, u32 *buf, int width, int height);

#endif /* __NC4_ILI9488_H__ */
