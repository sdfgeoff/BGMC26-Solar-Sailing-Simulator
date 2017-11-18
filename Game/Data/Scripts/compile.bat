gcc -c -Wall -Werror -fPIC -DBUILDING_EXAMPLE_DLL light.c
gcc -shared -o light.dll light.o -Wl,--out-implib,liblight_dll.a