#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <intrin.h>
unsigned long long AcpHalAllocateShapeContexts(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!AcpHalAllocateShapeContexts return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long AcpHalCreate(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!AcpHalCreate return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long AcpHalReleaseShapeContexts(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!AcpHalReleaseShapeContexts return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long ApuAlloc(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!ApuAlloc return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long ApuCreateHeap(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!ApuCreateHeap return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long ApuFree(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!ApuFree return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long ApuIsVirtualAddressValid(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!ApuIsVirtualAddressValid return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long ApuMapApuAddress(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!ApuMapApuAddress return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
unsigned long long ApuMapVirtualAddress(void) { static LONG once; if (!InterlockedExchange(&once,1) || getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL acphal!ApuMapVirtualAddress return_pc=%p result=0\n",_ReturnAddress());fflush(stderr);} return 0; }
