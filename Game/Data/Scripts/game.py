import mathutils
import bge
import math
import time
from vehicle import Vehicle

ZOOM_SPEED = -0.02
ZOOM_SMOOTH = 0.9
CAM_MOTION_SMOOTH = 0.5
SAIL_TILT_SMOOTHING = 0.95

def init(cont):
    cont.owner['SIMULATION'] = Simulation(cont.owner.scene)
    cont.script = __name__  + '.run'

def run(cont):
    cont.owner['SIMULATION'].update()


class Simulation:
    def __init__(self, scene):
        self.scene = scene
        self.vehicle = Vehicle(scene, mathutils.Matrix.Translation([40, 0, 0]) * mathutils.Matrix.Rotation(1.51, 4, 'Y'))
        self.vehicle.obj.worldLinearVelocity = [0, 4, 0]
        self.sun = scene.objects['SUN']
        self.camera = Camera(scene.objects['Camera'])
        
        self.hud = HUD()
        self.vehicle.on_player_move.append(self.hud.on_player_move)

        self.tilt = 0


    def update(self):
        self.vehicle.update(self.sun)
        self.camera.update(self.vehicle.obj)

        if bge.events.WHEELUPMOUSE in bge.logic.mouse.active_events:
            self.camera.zoom += ZOOM_SPEED
        elif bge.events.WHEELDOWNMOUSE in bge.logic.mouse.active_events:
            self.camera.zoom -= ZOOM_SPEED

        # Gravity
        for obj1 in self.scene.objects:
            for obj2 in self.scene.objects:
                if obj1 != obj2 and obj1.getPhysicsId() != 0 and obj2.getPhysicsId() != 0:
                    dist = (obj1.worldPosition - obj2.worldPosition)
                    if dist.length > 0:
                        dist.length = (obj1.mass + obj2.mass) / (dist.length ** 2)
                        obj1.applyForce(
                            -dist,
                            False
                        )

        target_tilt = 0
        if bge.events.LEFTARROWKEY in bge.logic.keyboard.active_events:
            target_tilt += 1
        if bge.events.RIGHTARROWKEY in bge.logic.keyboard.active_events:
            target_tilt -= 1

        self.tilt = self.tilt * SAIL_TILT_SMOOTHING + target_tilt * (1.0 - SAIL_TILT_SMOOTHING)
        self.vehicle.set_tilt(self.tilt)

class Camera:
    def __init__(self, obj):
        self.obj = obj
        self.zoom = 0.5

    def update(self, target_obj):
        self.zoom = min(1, max(0, self.zoom))
        zoom = (self.zoom ** 2) * 180 + 10
        self.obj.worldPosition.z = self.obj.worldPosition.z * ZOOM_SMOOTH + zoom * (1.0 - ZOOM_SMOOTH)

        self.obj.worldPosition.xy = self.obj.worldPosition.xy * CAM_MOTION_SMOOTH + target_obj.worldPosition.xy * (1.0 - CAM_MOTION_SMOOTH)


class HUD:
    def __init__(self):
        self.scene = next(s for s in bge.logic.getSceneList() if s.name == 'Interface')
        self.force_meter = self.scene.objects['ACCELEROMETER']
        self.velocity_meter = self.scene.objects['VELOCITY']
        self.light_meter = self.scene.objects['LIGHTDIRECTION']
        

    def on_player_move(self, obj, force, torque, light_vector):
        self.force_meter.worldOrientation = [0, 0, math.atan2(-force.x, force.y)]
        self.force_meter.localScale.y = force.length * 3
        if self.force_meter.localScale.y > 1.0:
            self.force_meter.localScale.y = 1.0
            self.force_meter.color = [1, 0, 0, 1]
        else:
            self.force_meter.color = [0, 1, 0, 1]

            
        self.velocity_meter.worldOrientation = [0, 0, math.atan2(-obj.worldLinearVelocity.x, obj.worldLinearVelocity.y)]
        self.velocity_meter.localScale.y = min(obj.worldLinearVelocity.length / 10, 1.0)
        if self.velocity_meter.localScale.y > 1.0:
            self.velocity_meter.localScale.y = 1.0
            self.velocity_meter.color = [1, 0, 0, 1]
        else:
            self.velocity_meter.color = [1.0, 0.0, 1.0, 1]

        self.light_meter.worldOrientation = [0, 0, math.atan2(-light_vector.x, light_vector.y)]
        brightness = min(light_vector.length, 1)
        self.light_meter.color = [1 * brightness, 1 * brightness, 0, 1]