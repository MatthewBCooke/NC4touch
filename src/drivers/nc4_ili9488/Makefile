KDIR ?= /lib/modules/`uname -r`/build
#ccflags-y := -DDEBUG

default:
	$(MAKE) -C $(KDIR) M=$$PWD

#install:
#	$(MAKE) -C $(KDIR) M=$$PWD modules_install

clean:
	$(MAKE) -C $(KDIR) M=$$PWD clean
