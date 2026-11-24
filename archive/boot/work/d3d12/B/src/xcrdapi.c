#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <intrin.h>
unsigned long long DStorageGetFactory(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xcrdapi!DStorageGetFactory return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
