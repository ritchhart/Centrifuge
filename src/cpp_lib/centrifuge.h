#pragma once

#if defined(_WIN32) || defined(__CYGWIN__)
  #ifdef CENTRIFUGE_EXPORTS
    #define CENTRIFUGE_API __declspec(dllexport)
  #else
    #define CENTRIFUGE_API __declspec(dllimport)
  #endif
#else
  #define CENTRIFUGE_API
#endif

extern "C" {

CENTRIFUGE_API int add(int a, int b);
CENTRIFUGE_API const char* hello();

}
