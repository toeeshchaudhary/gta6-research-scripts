#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <intrin.h>
unsigned long long XDspActivate(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL chad!XDspActivate return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XDspConnectWithMaximumStreamLimit(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL chad!XDspConnectWithMaximumStreamLimit return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XDspDeactivate(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL chad!XDspDeactivate return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XDspDisconnect(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL chad!XDspDisconnect return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XDspSubmitCommand(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL chad!XDspSubmitCommand return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
