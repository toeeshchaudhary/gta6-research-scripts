#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <intrin.h>
unsigned long long XGCreateTextureComputer(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xg_xs!XGCreateTextureComputer return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XGSuggestSwizzleMode(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xg_xs!XGSuggestSwizzleMode return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
