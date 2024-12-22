obj-m += nc4_ili9488.o

KDIR ?= /lib/modules/$(shell uname -r)/build

ccflags-y := -DDEBUG

default:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
