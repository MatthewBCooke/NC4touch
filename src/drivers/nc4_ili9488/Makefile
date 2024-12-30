obj-m += nc4_ili9488.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean


# Module target
obj-m += nc4_ili9488.o

# Kernel build directory
KDIR ?= /lib/modules/$(shell uname -r)/build

# Enable debugging during build
# -DDEBUG: Enables general kernel debugging
# -DCONFIG_DRM_DEBUG: Enables DRM-specific debugging macros like DRM_DEBUG_KMS
# -DCONFIG_DYNAMIC_DEBUG: Ensures dynamic debug support
ccflags-y := -DDEBUG -DCONFIG_DRM_DEBUG -DCONFIG_DYNAMIC_DEBUG

# Optional: Add additional debug self-tests for DRM during development
# Uncomment the following line to enable DRM self-tests (useful for diagnostics)
# ccflags-y += -DCONFIG_DRM_DEBUG_SELFTESTS

# Build the module
all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

# Clean the module
clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
