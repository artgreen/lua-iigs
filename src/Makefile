#
# Crappy Makefile
#
EXE_DIR := ../build

names := lapi lauxlib lbaselib lcode lcorolib lctype ldblib ldebug ldo ldump lfunc lgc linit liolib llex lmathlib lmem loadlib lobject lopcodes loslib lparser lstate lstring lstrlib ltable ltablib ltm lundump lzio lvm
SRCS := $(names:%=*.c)
OBJS := $(foreach wrd, $(names),$(wrd).a)
ADDS := $(foreach wrd, $(names),+$(wrd).a)
CFLAGS := -I -P -D +O

.PHONY: luac_conf lua_conf all clean test libluac liblua
all: lua

libluac: luac_conf $(OBJS) luac.lib
luac.lib:
	@echo "Making luac.lib"
	@iix makelib $@ $(ADDS) || rm -f -- $@   # we need to delete the lib file on error

liblua: lua_conf $(OBJS) lua.lib
lua.lib:
	@echo "Making lua.lib"
	@iix makelib $@ $(ADDS) || rm -f -- $@  # we need to delete the lib file on error
	@cp $@ $(EXE_DIR)/$@
lua_conf:
ifeq ($(shell grep "LUAC" parseconf.h),)
else
	@echo "Switching to LUA build"
	@echo '#define BUILD_IS_LUA' > parseconf.h
	@# make sure new library gets built
	@rm -f lua.lib
endif
lua: liblua lua.a
	@iix link lua.a lvm lua.lib KEEP=$@
	@cp $@ $(EXE_DIR)
luac_conf:
ifeq ($(shell grep LUAC parseconf.h),)
	@echo "Switching to LUAC build"
	@echo '#define BUILD_IS_LUAC' > parseconf.h
	@# make sure new library gets built
	@rm -f luac.lib
endif
luac: libluac luac.a
	@iix link luac.a lvm luac.lib KEEP=$@
	@cp $@ $(EXE_DIR)
clean:
	@rm -f -- *.sym *.a *.b *.d *.e *.root lua luac *.lib
	@#rm -f -- $(EXE_DIR)/*.lib $(EXE_DIR)/lua $(EXE_DIR)/luac

# Dependencies
lapi.a: lapi.c lprefix.h lua.h luaconf.h lapi.h llimits.h lstate.h \
 lobject.h ltm.h lzio.h lmem.h ldebug.h ldo.h lfunc.h lgc.h lstring.h \
 ltable.h lundump.h lvm.h
lauxlib.a: lauxlib.c lprefix.h lua.h luaconf.h lauxlib.h
lbaselib.a: lbaselib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
lcode.a: lcode.c lprefix.h lua.h luaconf.h lcode.h llex.h lobject.h \
 llimits.h lzio.h lmem.h lopcodes.h lparser.h ldebug.h lstate.h ltm.h \
 ldo.h lgc.h lstring.h ltable.h lvm.h
lcorolib.a: lcorolib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
lctype.a: lctype.c lprefix.h lctype.h lua.h luaconf.h llimits.h
ldblib.a: ldblib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
ldebug.a: ldebug.c lprefix.h lua.h luaconf.h lapi.h llimits.h lstate.h \
 lobject.h ltm.h lzio.h lmem.h lcode.h llex.h lopcodes.h lparser.h \
 ldebug.h ldo.h lfunc.h lstring.h lgc.h ltable.h lvm.h
ldo.a: ldo.c lprefix.h lua.h luaconf.h lapi.h llimits.h lstate.h \
 lobject.h ltm.h lzio.h lmem.h ldebug.h ldo.h lfunc.h lgc.h lopcodes.h \
 lparser.h lstring.h ltable.h lundump.h lvm.h parseconf.h
ldump.a: ldump.c lprefix.h lua.h luaconf.h lobject.h llimits.h lstate.h \
 ltm.h lzio.h lmem.h lundump.h
lfunc.a: lfunc.c lprefix.h lua.h luaconf.h ldebug.h lstate.h lobject.h \
 llimits.h ltm.h lzio.h lmem.h ldo.h lfunc.h lgc.h
lgc.a: lgc.c lprefix.h lua.h luaconf.h ldebug.h lstate.h lobject.h \
 llimits.h ltm.h lzio.h lmem.h ldo.h lfunc.h lgc.h lstring.h ltable.h
linit.a: linit.c lprefix.h lua.h luaconf.h lualib.h lauxlib.h
liolib.a: liolib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
llex.a: llex.c lprefix.h lua.h luaconf.h lctype.h llimits.h ldebug.h \
 lstate.h lobject.h ltm.h lzio.h lmem.h ldo.h lgc.h llex.h lparser.h \
 lstring.h ltable.h parseconf.h
lmathlib.a: lmathlib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
lmem.a: lmem.c lprefix.h lua.h luaconf.h ldebug.h lstate.h lobject.h \
 llimits.h ltm.h lzio.h lmem.h ldo.h lgc.h
loadlib.a: loadlib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
lobject.a: lobject.c lprefix.h lua.h luaconf.h lctype.h llimits.h \
 ldebug.h lstate.h lobject.h ltm.h lzio.h lmem.h ldo.h lstring.h lgc.h \
 lvm.h
lopcodes.a: lopcodes.c lprefix.h lopcodes.h llimits.h lua.h luaconf.h
loslib.a: loslib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
lparser.a: lparser.c lprefix.h lua.h luaconf.h lcode.h llex.h lobject.h \
 llimits.h lzio.h lmem.h lopcodes.h lparser.h ldebug.h lstate.h ltm.h \
 ldo.h lfunc.h lstring.h lgc.h ltable.h parseconf.h
lstate.a: lstate.c lprefix.h lua.h luaconf.h lapi.h llimits.h lstate.h \
 lobject.h ltm.h lzio.h lmem.h ldebug.h ldo.h lfunc.h lgc.h llex.h \
 lstring.h ltable.h parseconf.h
lstring.a: lstring.c lprefix.h lua.h luaconf.h ldebug.h lstate.h \
 lobject.h llimits.h ltm.h lzio.h lmem.h ldo.h lstring.h lgc.h
lstrlib.a: lstrlib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
ltable.a: ltable.c lprefix.h lua.h luaconf.h ldebug.h lstate.h lobject.h \
 llimits.h ltm.h lzio.h lmem.h ldo.h lgc.h lstring.h ltable.h lvm.h
ltablib.a: ltablib.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h
ltm.a: ltm.c lprefix.h lua.h luaconf.h ldebug.h lstate.h lobject.h \
 llimits.h ltm.h lzio.h lmem.h ldo.h lgc.h lstring.h ltable.h lvm.h
lua.a: lua.c lprefix.h lua.h luaconf.h lauxlib.h lualib.h parseconf.h
luac.a: luac.c lprefix.h lua.h luaconf.h lauxlib.h ldebug.h lstate.h parseconf.h \
 lobject.h llimits.h ltm.h lzio.h lmem.h lopcodes.h lopnames.h lundump.h
lundump.a: lundump.c lprefix.h lua.h luaconf.h ldebug.h lstate.h \
 lobject.h llimits.h ltm.h lzio.h lmem.h ldo.h lfunc.h lstring.h lgc.h \
 lundump.h
lvm.a: lvm.c lprefix.h lua.h luaconf.h ldebug.h lstate.h lobject.h \
 llimits.h ltm.h lzio.h lmem.h ldo.h lfunc.h lgc.h lopcodes.h lstring.h \
 ltable.h lvm.h ljumptab.h
lzio.a: lzio.c lprefix.h lua.h luaconf.h llimits.h lmem.h lstate.h \
 lobject.h ltm.h lzio.h

%.a:
	iix compile $(CFLAGS) $<
