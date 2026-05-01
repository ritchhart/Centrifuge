Mostly claude generated code recreating a wrapper for the Agilent Centrifuge and agilent centrifuge loader.

Relavent dll's are in the dll folder 
**Claude assumed you put these dll's somewhere specific - I believe it assumes you call regsvr32.exe on one/both of the dlls which I think should populate the folder in Program Files x86**
I've tested the python api as is and it works! The only real hiccup is that it runs a layer of 32bit activex thus needs 32 bit python. The activex is non-nogtiable NONE of the functions work without it.
