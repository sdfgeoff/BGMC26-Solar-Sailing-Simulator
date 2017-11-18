#ifdef _WIN32
    #define DLLSPEC __declspec(dllexport)
#else
    #define DLLSPEC
#endif

DLLSPEC void test(uint16_t resolution, uint8_t* data, float* force, float* torque);