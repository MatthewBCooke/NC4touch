# Module target
obj-m += nc4_ili9488.o

# Kernel build directory
KDIR ?= /lib/modules/$(shell uname -r)/build

# Build the module
all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

# Clean the module
clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
