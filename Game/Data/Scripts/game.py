import mathutils
import bge
import aud
import math
import time
import os
import random
from vehicle import Vehicle

ZOOM_SMOOTH = 0.9
CAM_MOTION_SMOOTH = 0.9
SAIL_TILT_SMOOTHING = 0.95

POWERUP_COUNT = 15

ROOT_PATH = os.path.join(os.path.split(os.path.realpath(__file__))[0], '../../')

START_TEXT = '''Press H for help'''
HELP_TEXT = '''\
This is a solar sailing simulator. The only source of motion for your craft
is the sun. Gravity pulls your craft towards the sun, and the light bounces
off the sail to push you away. You can tilt the sail using the arrow keys.

If you use the sail to speed up your orbit, you will move away from the
sun. If you use the sail to slow down your orbit, you will move towards
the sun. Be careful not to end up in the sun (hot) or to far away from
the sun (no power).

Collect the comets (yes I know that a comet's tail should face away from
the sun - deal with it)
'''

PICKUP_TEXT = '''You have collected {} comets'''

SUN_DEATH_TEXT = '''\
The sun may be your source of power, but that doesn't mean you should
get so close.

Press R to restart'''

DISTANCE_DEATH_TEXT = '''\
You entered interstellar space and were never seen again.

Press R to restart'''


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

        self.sound = Sound()

        try:
            next(s for s in bge.logic.getSceneList() if s.name == 'Interface')
            hud = True
        except StopIteration:
            hud = False
            print("Ho HUD Scene Detected. Running with no GUI")
        if hud:
            self.hud = HUD()
            self.vehicle.on_player_move.append(self.hud.on_player_move)
        else:
            self.hud = None

        self.tilt = 0
        self.death = False

        self.powerups = list()
        for i in range(POWERUP_COUNT):
            if i < POWERUP_COUNT/2:
                self.add_powerup(120)  # Some furthur out - but only when initially populating the map
            else:
                self.add_powerup(60)

    def add_powerup(self, max_dist):
        self.powerups.append(Powerup(self.sun, max_dist))
        self.added_powerup_time = time.time()


    def update(self):
        self.vehicle.update(self.sun)

        if self.hud is not None:
            self.hud.update()
        
        self.camera.update([self.vehicle.obj, self.sun])

        dist_from_sun = (self.vehicle.obj.worldPosition - self.sun.worldPosition).length
        self.sound.set_sun_volume(max(0, 30 - dist_from_sun) * 0.05)

        # Gravity
        for obj in self.scene.objects:
            if obj is not self.sun and obj.getPhysicsId() != 0:
                dist = (self.sun.worldPosition - obj.worldPosition)
                if dist.length > 0:
                    dist.length = (obj.mass*self.sun.parent.mass) / (dist.length ** 2)
                    obj.applyForce(
                        dist,
                        False
                    )

        target_tilt = 0
        if bge.events.LEFTARROWKEY in bge.logic.keyboard.active_events:
            target_tilt -= 1
        if bge.events.RIGHTARROWKEY in bge.logic.keyboard.active_events:
            target_tilt += 1

        self.tilt = self.tilt * SAIL_TILT_SMOOTHING + target_tilt * (1.0 - SAIL_TILT_SMOOTHING)
        self.vehicle.set_tilt(self.tilt)

        
        if dist_from_sun < 4.0:
            self.death = SUN_DEATH_TEXT
            if dist_from_sun < 1.0:
                self.vehicle.obj.worldLinearVelocity = [0, 0, 0]
                self.vehicle.obj.suspendDynamics(True)
                self.sun.parent.suspendDynamics(True)
        elif dist_from_sun > 240:
            self.death = DISTANCE_DEATH_TEXT

        if self.death is not False:
            # Player Died
            if bge.logic.keyboard.events[bge.events.RKEY] != 0:
                bge.logic.restartGame()
            self.hud.text.text = self.death
            self.hud.text.color = [0, 0, 1, 1]
            self.vehicle.obj.localScale *= 0.9
            self.vehicle.obj.worldLinearVelocity *= 0.5

        else:
            if bge.logic.keyboard.events[bge.events.DKEY] == 1:
                prev = self.vehicle.render_debug_plane
                self.vehicle.render_debug_plane = not prev
                self.hud.debug_plane.visible = not prev


        for powerup in self.powerups[:]:
            powerup.update(self.vehicle)
            if powerup.remove:
                self.powerups.remove(powerup)
                self.add_powerup(60)


        



class Powerup:
    def __init__(self, sun, max_dist=60):
        self.obj = sun.scene.addObject('COMET')
        self.graphics = self.obj
        vect = mathutils.Vector([1, 0, 0])
        vect.rotate(mathutils.Euler([0, 0, random.random()*3.14*2]))
        vect.length = 10 + random.random() * max_dist

        self.obj.worldPosition = sun.worldPosition + vect
        scale = random.random() + 0.5
        self.obj.localScale = [scale] * 3

        vel = vect.cross([0, 0, 1])
        vel.length = (sun.parent.mass * self.obj.mass/vect.length)**0.5
        self.obj.worldLinearVelocity = vel

        self.on_pickup = list()

        self.obj['PIVOT'] = 100 / vect.length * scale
        self.graphics.color[0] = random.random()
        self.graphics.color[1] = 0.0

        self.picked_up = False
        self.remove = False
        

    def update(self, vehicle):
        if self.remove:
            return

        dist = (vehicle.obj.worldPosition - self.obj.worldPosition).length
        if dist < 3 and not self.picked_up:
            for funct in self.on_pickup:
                funct()
            sound = aud.Factory(os.path.join(ROOT_PATH, 'Data/Audio/pickup.wav'))
            sound_handle = aud.device().play(sound)
            self.picked_up = True
            

        if self.picked_up:
            self.graphics.color[1] *= 0.95
            if self.graphics.color[1] < 0.05:
                self.remove = True
                self.obj.endObject()
        else:
            if self.graphics.color[1] < 1.0:
                self.graphics.color[1] += 0.05

        self.obj.worldOrientation = [0, 0, math.atan2(self.obj.worldLinearVelocity.y, self.obj.worldLinearVelocity.x)]
        self.graphics.color[0] += (self.obj.worldLinearVelocity.length) * 0.0010 / self.obj.localScale[0]

        
        
    @property
    def worldPosition(self):
        return self.obj.worldPosition


class Camera:
    def __init__(self, obj):
        self.obj = obj
        self.zoom = 50

    def update(self, target_objs):

        # Average target position
        minimum_pos = mathutils.Vector([999, 999, 999])
        maximum_pos = mathutils.Vector([-999, -999, -999])
        for count, obj in enumerate(target_objs):
            pos = obj.worldPosition
            minimum_pos[0] = min(minimum_pos[0], pos[0])
            minimum_pos[1] = min(minimum_pos[1], pos[1])
            minimum_pos[2] = min(minimum_pos[2], pos[2])
            maximum_pos[0] = max(maximum_pos[0], pos[0])
            maximum_pos[1] = max(maximum_pos[1], pos[1])
            maximum_pos[2] = max(maximum_pos[2], pos[2])

        center = minimum_pos.lerp(maximum_pos, 0.5)
        dist = (minimum_pos - maximum_pos)
            
        self.zoom = max(10, ((abs(dist.x * 1.2))**2 + (abs(dist.y * 2.2))**2) ** 0.5 + 10)
        zoom = self.zoom
        self.obj.worldPosition.z = self.obj.worldPosition.z * ZOOM_SMOOTH + zoom * (1.0 - ZOOM_SMOOTH)

        self.obj.worldPosition.xy = self.obj.worldPosition.xy * CAM_MOTION_SMOOTH + center.xy * (1.0 - CAM_MOTION_SMOOTH)


class Sound:
    def __init__(self):
        self.device = aud.device()
        self.music = aud.Factory(os.path.join(ROOT_PATH, 'Data/Audio/Stellardrone - Light Years - 03 Eternity.mp3'))
        self.music = self.music.loop(-1)
        self.music_handle = self.device.play(self.music)

        self.sun = aud.Factory(os.path.join(ROOT_PATH, 'Data/Audio/sun.wav'))
        self.sun = self.sun.loop(-1)
        self.sun_handle = self.device.play(self.sun)
        self.sun_handle.pitch = 0.8

    def set_sun_volume(self, sun_volume):
        self.sun_handle.volume = sun_volume
        


class HUD:
    def __init__(self):
        self.scene = next(s for s in bge.logic.getSceneList() if s.name == 'Interface')
        self.force_meter = self.scene.objects['ACCELEROMETER']
        self.velocity_meter = self.scene.objects['VELOCITY']
        self.light_meter = self.scene.objects['LIGHTDIRECTION']
        self.set_widget_visible(False)

        self.text = self.scene.objects['TEXT']
        self.text.text = START_TEXT

        self.text_time = time.time()
        

        self.debug_plane = self.scene.objects['DEBUG']
        self.debug_plane.visible = False

    def set_widget_visible(self, visible):
        self.force_meter.visible = visible
        self.velocity_meter.visible = visible
        self.light_meter.visible = visible
        self.scene.objects['Circle'].visible = visible
        
        

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

    def update(self):
        if self.text_time + 5.0 < time.time():
            self.text.color *= 0.99
        if bge.logic.keyboard.events[bge.events.HKEY] != 0:
            self.text.color = [1, 1, 1, 1]
            self.text.text = HELP_TEXT
            