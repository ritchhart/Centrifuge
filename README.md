Mostly claude generated code recreating a wrapper for the Agilent Centrifuge and agilent centrifuge loader.
Relavent dll's are in the foldeer (as well as many extras the vendor had bundled)
**Claude assumed you put these dll's somewhere specific their location is not correct as is**
I've tested the python api as is and it works! The only real hiccup is that it runs a layer of 32bit activex thus needs 32 bit python. The activex is non-nogtiable NONE of the functions work without it.
