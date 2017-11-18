import bge
import bgl
import mathutils
import ctypes
import os
import math

RESOLUTION = 128
NORMAL_TYPE = ctypes.c_ubyte * (RESOLUTION * RESOLUTION * 4)
VECTYPE = ctypes.c_float * 3

SHOW_DEBUG_PLANE = False


_accel_path = os.path.join(os.path.split(__file__)[0], "light.so")
ACCELERATOR = ctypes.cdll.LoadLibrary(_accel_path)
ACCELERATOR.test.restype = ctypes.c_float


import time
import math


class Vehicle:
    def __init__(self, scene, transform):
        self.scene = scene
        self.obj = scene.addObject('SUNJAMMER')
        self.obj.worldTransform = transform
        self.diameter = 10  # BU image size to catch the whole craft

        self.tex = RenderCamera(self.obj.children['LIGHTCAMERA'], self.obj.children['DEBUGPLANE'], RESOLUTION)
        self.tex.obj.visible = SHOW_DEBUG_PLANE
        self.sail = self.obj.children['SAIL']

        self.tilt = 0

        self.on_player_move = list()


    def set_tilt(self, tilt):
        self.tilt = tilt
        

    def update(self, light_source_obj):

        force, torque, light_vector = self._get_force_from_light(light_source_obj)
        torque.x = 0
        torque.y = 0
        force.z = 0

        force *= 0.5
        torque *= 5
        self.obj.applyForce(force, False)
        self.obj.applyTorque(torque, False)

        for funct in self.on_player_move:
            funct(self.obj, force, torque, light_vector)
        
        self.sail.localOrientation = [self.tilt, 0, 0]

        # Update amatures
        for obj in self.obj.childrenRecursive:
            if hasattr(obj, 'update'):
                obj.update()

    def _get_force_from_light(self, light_source_obj):
        # Move camera to sun position
        cam = self.tex.cam
        cam.worldPosition = light_source_obj.worldPosition.copy()
        cam.alignAxisToVect(light_source_obj.worldPosition - self.obj.worldPosition)

        light_vector = light_source_obj.worldPosition - self.obj.worldPosition
        dist = (light_vector).length
        cam.fov = math.degrees(math.atan(self.diameter / (2 * dist)) * 2)
        cam.near = max(dist - self.diameter, 0.1)
        cam.far = dist + self.diameter

        normal_data = self.do_light_render()  # THis updates self.tex.data
        
        # We need C performance wo work with the massive amount of data we just generated
        f_force = VECTYPE(0, 0, 0)
        f_torque = VECTYPE(0, 0, 0)
        ACCELERATOR.test(RESOLUTION, normal_data, f_force, f_torque)

        # Convert to vectors and transform into worldspace
        light_to_world = cam.worldOrientation
        force = light_to_world * mathutils.Vector(f_force)
        torque = light_to_world * mathutils.Vector(f_torque)

        force = force / (dist ** 2) * 1000
        torque = torque / (dist ** 2) * 1000

        light_vector.length = 1 / (light_vector.length ** 2) * 1000

        return force, torque, light_vector

    def do_light_render(self):
        made_invisible = list()
        for obj in self.obj.scene.objects:
            if obj.visible and 'HIDE_FROM_LIGHT' in obj:
                obj.visible = False
                made_invisible.append(obj)
        
        for obj in self.obj.childrenRecursive:
            if obj.visible and 'HIDE_FROM_LIGHT' not in obj:
                obj.color[0] = True
                obj.visible = True

        if SHOW_DEBUG_PLANE:
            self.tex.update()
            self.tex.obj.visible = True
        else:
            self.tex.obj.visible = False
        self.tex.refresh_buffer()

        for obj in self.obj.childrenRecursive:
            obj.color[0] = False

        for obj in made_invisible:
            obj.visible = True

        return NORMAL_TYPE.from_buffer(self.tex.data)
            

        
        


class RenderCamera:
    def __init__(self, cam, obj, res):
        self.cam = cam
        self.obj = obj
        self.tex = bge.texture.Texture(obj, 0)
        self.image = bge.texture.ImageRender(cam.scene, cam)
        self.image.background = [127, 127, 127, 127]
        self.image.capsize = [res, res]
        self.tex.source = self.image

        self.data = bytearray(res * res * 4)


    def update(self):
        self.tex.refresh(True)
        

    def refresh_buffer(self):
        '''Returns a 2D array of the pixels'''
        self.image.refresh(self.data, "RGBA")
        
