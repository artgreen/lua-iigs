# Targeted regression checks and the broader upstream suite are separate.
PYTHON ?= python3
LUA ?= ../build/lua
TIMEOUT ?= 300
RUN = $(PYTHON) ../tools/run-tests.py --lua $(LUA) --timeout $(TIMEOUT)
passes := api attrib big bitwise bwcoercion calls constructs coroutine closure code cstack db errors events gc gengc goto heavy literals locals main math nextvar pm sort strings tpack tracegc vararg verybig
# Stock GoldenGate EOF/text issues remain despite the adapted hardware pass.
# An unexpected local pass requires reclassification.
fails := files

.PHONY: all tests passing fails suite clean
all: tests
tests:
	$(RUN)
passing:
	$(RUN) $(passes)
fails:
	$(RUN) --expect-failure $(fails)
suite: passing fails
clean:
	rm -f -- *.out
