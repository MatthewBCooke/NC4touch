kmscon Behavior:

kmscon configures the DRM/KMS pipeline during boot, enabling both displays (LCD_0 and LCD_1) and resolving initialization issues.
However, it locks the framebuffers (fb0 and fb1), preventing other applications (e.g., fbi) from rendering images.
Without kmscon:

Disabling kmscon frees the framebuffers but reverts to the pre-kms behavior where only LCD_1 works, and LCD_0 remains blank.
This suggests kmscon applies critical DRM/KMS configurations during boot.
Hypothesis:

kmscon uses libraries like libkms++ to initialize the DRM pipeline, assigning CRTCs, connectors, and planes. These steps need to be replicated manually or through an alternative service.

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
