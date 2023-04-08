
# apple commander
AC := ac
# disk image to target
XFER := axfer.po

.PHONY: all

lua:
	+$(MAKE) -C src lua
luac:
	+$(MAKE) -C src luac
clean:
	+$(MAKE) -C src clean
luadisk: cleandisk lua
	<build/lua $(AC) -p $(XFER) lua exe
	$(AC) -l $(XFER)
luacdisk: cleandisk luac
	<luac $(AC) -p $(XFER) luac exe
	$(AC) -l $(XFER)
cleandisk:
	$(AC) -pro800 $(XFER) XFER
