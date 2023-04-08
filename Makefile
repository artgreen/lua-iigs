
# apple commander
AC := ac
# disk image to target
XFER := axfer.po
# directory to hold binaries
EXE_DIR := build

.PHONY: all testdisk luadisk clean cleanluacout cleandisk minitest

lua: | $(EXE_DIR)
	+$(MAKE) -C src lua
luac: | $(EXE_DIR)
	+$(MAKE) -C src luac
clean:
	+$(MAKE) -C src clean
cleanluacout:
	@rm -f -- luac.out
luac.out:
	iix $(EXE_DIR)/luac test.lua
minitest: cleanluacout luac.out
	iix $(EXE_DIR)/lua luac.out
testdisk: cleanluacout luac luadisk luac.out
	<luac.out $(AC) -p $(XFER) luac.out bin
	<test.lua $(AC) -p $(XFER) test.lua txt
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
