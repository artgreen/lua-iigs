
# apple commander
AC := ac
# disk image to target
XFER := axfer.po
# directory to hold binaries
EXE_DIR := build
SRC_DIR := src
# compiler flags
CFLAGS := -I -P -D +O

.PHONY: all testdisk luadisk clean cleanluacout cleandisk minitest bridgedisk

bridge: test.a testiface.a testbridge.a
	iix link test testiface testbridge $(SRC_DIR)/lvm $(SRC_DIR)/lua.lib KEEP=$@
test.a: test.c
test_iface.a: testiface.c
test_bridge.a: testbridge.c

lua: | $(EXE_DIR)
	+$(MAKE) -C src lua
luac: | $(EXE_DIR)
	+$(MAKE) -C src luac
clean:
	+$(MAKE) -C src clean
cleanexe:
	rm -f $(EXE_DIR)/*
cleanluacout:
	@rm -f -- luac.out
luac.out:
	iix $(EXE_DIR)/luac test.lua
minitest: cleanluacout luac.out
	iix $(EXE_DIR)/lua luac.out
bridgedisk: cleandisk bridge
	<bridge $(AC) -p $(XFER) bridge exe
	<bridge.out $(AC) -p $(XFER) bridge.out bin
	<bridge.lua $(AC) -p $(XFER) bridge.lua txt
	$(AC) -l $(XFER)
bridgesrcdisk: lua cleandisk bridge
	<$(EXE_DIR)/lua.lib $(AC) -p $(XFER) lua.lib lib
	<$(SRC_DIR)/lvm.a $(AC) -p $(XFER) lvm.a obj
	<luainc.shk $(AC) -p $(XFER) luainc.shk shk
	<testbridge.c $(AC) -p $(XFER) testbridge.cc src
	<test.c $(AC) -p $(XFER) test.cc src
	<testiface.c $(AC) -p $(XFER) testiface.cc src
	<testiface.h $(AC) -p $(XFER) testiface.h src
	<bridge.out $(AC) -p $(XFER) bridge.out bin
	<bridge.lua $(AC) -p $(XFER) bridge.lua txt
	$(AC) -l $(XFER)
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

%.a:
	iix compile $(CFLAGS) $<
