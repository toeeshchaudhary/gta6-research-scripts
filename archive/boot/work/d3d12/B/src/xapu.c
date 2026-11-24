#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <intrin.h>
unsigned long long XApuConnect(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xapu!XApuConnect return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XApuDequeueResult(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xapu!XApuDequeueResult return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XApuDisconnect(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xapu!XApuDisconnect return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XApuEnqueueCommand(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xapu!XApuEnqueueCommand return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long XApuGetResultCount(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL xapu!XApuGetResultCount return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
