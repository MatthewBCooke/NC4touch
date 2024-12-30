# kmscon Behavior:

kmscon configures the DRM/KMS pipeline during boot, enabling both displays (LCD_0 and LCD_1) and resolving initialization issues.
However, it locks the framebuffers (fb0 and fb1), preventing other applications (e.g., fbi) from rendering images.
Without kmscon:

Disabling kmscon frees the framebuffers but reverts to the pre-kms behavior where only LCD_1 works, and LCD_0 remains blank.
This suggests kmscon applies critical DRM/KMS configurations during boot.
Hypothesis:

kmscon uses libraries like libkms++ to initialize the DRM pipeline, assigning CRTCs, connectors, and planes. These steps need to be replicated manually or through an alternative service.

# Commands

Check kmscon Processes:
```
ps aux | grep kmscon
```

Stop and Disable kmscon:
```
sudo systemctl stop kmsconvt@tty1
sudo systemctl disable kmsconvt@tty1
```

Re-enable kmscon:
```
sudo systemctl enable kmsconvt@tty1
sudo systemctl start kmsconvt@tty1
```

Re-start kmscon service
```
sudo systemctl restart kmsconvt@tty1.service
```

Check status:
```
sudo systemctl status kmsconvt@tty1.service
```

# Procedure

Restart with kmscon enabled

Run the following:
```
dmesg | grep -i drm > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/dmesg_drm.log
sudo journalctl -u kmsconvt@tty1.service --no-pager > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/kmscon_boot.log
sudo cat /sys/kernel/debug/dri/0/state > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/drm_state_card0.log
sudo cat /sys/kernel/debug/dri/1/state > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/drm_state_card1.log
ls -l /sys/class/drm/ > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/drm_devices.log
ls -l /sys/class/drm/card0 > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/card0_info.log
ls -l /sys/class/drm/card1 > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/card1_info.log
ls -l /dev/fb* > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/framebuffer_devices.log
sudo fbset -fb /dev/fb0 > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/fb0_info.log
sudo fbset -fb /dev/fb1 > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/fb1_info.log
sudo fuser /dev/fb0 /dev/fb1 > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/framebuffer_users.log
cat /sys/class/drm/card0-SPI-1/status > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/connector_card0_status.log
cat /sys/class/drm/card1-SPI-2/status > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/connector_card1_status.log
dmesg > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/dmesg_full.log
sudo journalctl --since "30 minutes ago" | grep kmscon > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/kmscon_recent.log
sudo journalctl -b | grep kmscon > /home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs/kmscon_boot_only.log

```


sudo fbi -d /dev/fb0 -T 1 /home/nc4/TouchscreenApparatus/data/images/A01.bmp
sudo fbi -d /dev/fb1 -T 1 /home/nc4/TouchscreenApparatus/data/images/A01.bmp