
# apple commander
AC := ac
# disk image to target
XFER := axfer.po
EXE_DIR := build

.PHONY: all

lua: | $(EXE_DIR)
	+$(MAKE) -C src lua
luac: | $(EXE_DIR)
	+$(MAKE) -C src luac
clean:
	+$(MAKE) -C src clean
luadisk: cleandisk lua
	<$(EXE_DIR)/lua $(AC) -p $(XFER) lua exe
	$(AC) -l $(XFER)
luacdisk: cleandisk luac
	<$(EXE_DIR)/luac $(AC) -p $(XFER) luac exe
	$(AC) -l $(XFER)
cleandisk:
	$(AC) -pro800 $(XFER) XFER
$(EXE_DIR):
	mkdir -p $@
