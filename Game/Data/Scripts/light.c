#include <stdio.h>
#include <stdint.h>
#include <math.h>


void test(uint16_t resolution, uint8_t* data, float* force, float* torque)
{
    uint16_t res = resolution - 1;
    // Iterate through each pixel
    for (uint32_t i=0; i < resolution*resolution; i++){
        //Find distance from center of the image
        float center_x = ((float)(i % resolution) / res - 0.5) * 2.0;
        float center_y = ((float)(i / resolution) / res - 0.5) * 2.0;
        float center_z = 0.0;

        float light_x = 0.0;  // Light vector
        float light_y = 0.0;
        float light_z = 1.0;
        
        // Extract Vector components
        float surface_x = (float)data[i*4 + 0] / 128.0 - 1.0;
        float surface_y = (float)data[i*4 + 1] / 128.0 - 1.0;
        float surface_z = (float)data[i*4 + 2] / 128.0 - 1.0;
        //float w = ((float)data[i*4 + 0]) / 127.0;  // Spare channel

        // Project screen-space light vector (0, 0, 1) onto the surface normal
        // This gives us the imparted momentum
        float dot = surface_x * light_x + surface_y * light_y + surface_z * light_z;
        float momentum_x = -surface_x * dot * 2;  // * 2 because the light is bouncing off = double momentum
        float momentum_y = -surface_y * dot * 2;  // - because force is a reaction
        float momentum_z = -surface_z * dot * 2;

        // Cross product of imparted modentum with the radius from screen center
        // to give us a torque
        float torque_x = center_y * momentum_z - center_z * momentum_y;
        float torque_y = center_z * momentum_x - center_x * momentum_z;
        float torque_z = center_x * momentum_y - center_y * momentum_x;

        //printf("cx %f      cy %f\n", center_x, center_y);

        force[0] += momentum_x;
        force[1] += momentum_y;
        force[2] += momentum_z;

        torque[0] += torque_x;
        torque[1] += torque_y;
        torque[2] += torque_z;
    }

    // Normalize for area
    force[0] = force[0] / (resolution * resolution);
    force[1] = force[1] / (resolution * resolution);
    force[2] = force[2] / (resolution * resolution);

    torque[0] = torque[0] / (resolution * resolution);
    torque[1] = torque[1] / (resolution * resolution);
    torque[2] = torque[2] / (resolution * resolution);
}