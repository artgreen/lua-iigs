
names := api attrib big bitwise bwcoercion calls closure code constructs coroutine cstack db errors events files gc gengc goto heavy literals locals main math nextvar pm sort strings tpack tracegc vararg verybig
passes := api attrib bitwise bwcoercion closure code events gc goto heavy literals pm tpack tracegc vararg
fails := big calls constructs coroutine db files gengc locals math strings sort
hangs := cstack errors verybig nextvar

ALL := $(foreach wrd, $(names),$(wrd).out)
PASSING := $(foreach wrd, $(passes),$(wrd).out)
FAILING := $(foreach wrd, $(fails),$(wrd).out)
HANGING := $(foreach wrd, $(hangs),$(wrd).out)

TIMEOUT := 30
TIMEOUT_EXE := /usr/bin/timeout
MEMCHECK := --memcheck
LUA := ../build/lua

.PHONEY: all tests fails clean

all: clean $(ALL)
tests: clean $(PASSING) $(FAILING)
passing: clean $(PASSING)
fails: clean $(FAILING)
hangs: clean $(HANGING)

clean:
	@rm -f *.out
api.out: api.lua
attrib.out: attrib.lua
big.out: big.lua
bitwise.out: bitwise.lua
bwcoercion.out: bwcoercion.lua
calls.out: calls.lua
closure.out: closure.lua
code.out: code.lua
constructs.out: constructs.lua
coroutine.out: coroutine.lua
cstack.out: cstack.lua
db.out: db.lua
errors.out: errors.lua
events.out: events.lua
files.out: files.lua
gc.out: gc.lua
gengc.out: gengc.lua
goto.out: goto.lua
heavy.out: heavy.lua
literals.out: literals.lua
locals.out: locals.lua
math.out: math.lua
nextvar.out: nextvar.lua
pm.out: pm.lua
sort.out: sort.lua
strings.out: strings.lua
tpack.out: tpack.lua
tracegc.out: tracegc.lua
vararg.out: vararg.lua
verybig.out: verybig.lua
%.out:
	@echo =============================================
	@echo $@
	@echo =============================================
	@-$(TIMEOUT_EXE) $(TIMEOUT) iix $(MEMCHECK) $(LUA) $< #> $@ 2>&1 || (echo "$@ Failed" && cat $@)
	@echo ============================================^
