# Include the configuration file
include config.env

# Module target
obj-m += nc4_ili9488.o

# Kernel build directory
KDIR ?= /lib/modules/$(shell uname -r)/build

# Output directory for build artifacts
BUILDS_DIR ?= $(BUILDS_DIR)

# Build the module
all:
	$(MAKE) -C $(KDIR) M=$(PWD) O=$(BUILDS_DIR) modules

# Clean the module
clean:
	$(MAKE) -C $(KDIR) M=$(PWD) O=$(BUILDS_DIR) clean
