
# apple commander
AC := ac
# nulib2 for shrinkit
NULIB := nulib2

# disk image to target
XFER := axfer.po
EXE_DISK := luags.po
LIB_DISK := lualib.po
EXE_VOL := LUAGS
LIB_VOL := LUALIB
# lua .h files for lua.lib
LUA_INC := luainc.shk
SHK_FILE := luags.shk

# directory to hold binaries
EXE_DIR := build
SRC_DIR := src
# compiler flags
CFLAGS := -I -P -D +O

.PHONY: all testdisk luadisk clean cleanluacout cleandisk minitest bridgedisk release cleanrelease

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
	iix $(EXE_DIR)/lua poker.lua
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
	@<$(EXE_DIR)/lua $(AC) -p $(XFER) lua exe
	@<examples/blackjack.lua $(AC) -ptx $(XFER) blackjack.lua
	@<examples/replcli.lua $(AC) -ptx $(XFER) replcli.lua
	@<examples/more.lua $(AC) -ptx $(XFER) more.lua
	@$(AC) -l $(XFER)
luacdisk: cleandisk luac
	<$(EXE_DIR)/luac $(AC) -p $(XFER) luac exe
	$(AC) -l $(XFER)
cleanrelease:
	@rm -f -- $(EXE_DISK) $(LIB_DISK)
release: cleanrelease clean $(EXE_DISK) $(LIB_DISK)
	$(NULIB) -a lua.shk $(EXE_DIR)/lua $(EXE_DIR)/luac test.lua
$(EXE_DISK): luac lua
	@$(AC) -pro800 $(EXE_DISK) LUAGS
	@<$(EXE_DIR)/lua $(AC) -p $(EXE_DISK) lua exe
	@<$(EXE_DIR)/luac $(AC) -p $(EXE_DISK) luac exe
	@<test.lua $(AC) -ptx $(EXE_DISK) test.lua
	@<examples/blackjack.lua $(AC) -ptx $(EXE_DISK) blackjack.lua
	@<examples/replcli.lua $(AC) -ptx $(EXE_DISK) replcli.lua
	@<examples/more.lua $(AC) -ptx $(XFER) more.lua
	@$(AC) -l $(EXE_DISK)
$(LIB_DISK): lua
	@$(AC) -pro800 $(LIB_DISK) LUALIB
	@<$(EXE_DIR)/lua.lib $(AC) -p $(LIB_DISK) lua.lib lib
	@<luainc.shk $(AC) -p $(XFER) luainc.shk shk
	@$(AC) -l $(LIB_DISK)
cleandisk:
	@$(AC) -pro800 $(XFER) XFER
$(EXE_DIR):
	@mkdir -p $@

%.a:
	iix compile $(CFLAGS) $<
