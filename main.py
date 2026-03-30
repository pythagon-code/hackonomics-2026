from ursina import vec3
from globals import *
import math
from ursina import *
from utils import *

app = Ursina()

window.color = add_hsv(color.white, (0, -.2, -.4))
globe = Entity(model="sphere", color=add_hsv(color.dark_gray, (0, 0, -.1)), scale=4, name="globe")
gui = None
country = None

draw_globe_line(globe=globe, rho=0.5, color=color.cyan, alpha=.6, size=0.004, num_markers=100, theta=math.pi/2)
Entity(model="sphere", color=color.cyan, alpha=.7, scale=0.008, position=Vec3(0, 0.5, 0), parent=globe)
Entity(model="sphere", color=color.cyan, alpha=.7, scale=0.008, position=Vec3(0, -0.5, 0), parent=globe)
left_mouse_pressed = False
mouse_position = Vec3(0, 0)
camera.parent = globe

def input(key: str) -> None:
    global left_mouse_pressed, mouse_position, camera_distance
    if key == "left mouse down":
        mouse_position = mouse.position
        left_mouse_pressed = True
    elif key == "left mouse up":
        left_mouse_pressed = False
    if key == "scroll up":
        camera_distance = max(camera_distance - camera_zoom_speed, 0)
    elif key == "scroll down":
        camera_distance += camera_zoom_speed

camera.position = Vec3(spherical_to_cartesian(camera_distance, camera_phi, camera_theta))
camera.look_at(globe.position)

def update() -> None:
    global mouse_position, camera_phi, camera_theta, gui, country
    if left_mouse_pressed:
        mouse_delta = mouse.position - mouse_position
        mouse_position = mouse.position
        rotate_speed = camera_rotate_speed * (camera_distance - 0.5)
        camera_phi = camera_phi - mouse_delta.x * rotate_speed
        camera_theta = clamp(camera_theta + mouse_delta.y * rotate_speed, .01, math.pi - .01)
    camera.position = Vec3(spherical_to_cartesian(camera_distance, camera_phi, camera_theta))
    camera.rotation_z = 0
    camera.look_at(globe.position)

    if country and country.name in countries:
        country.alpha = .4
    country = mouse.hovered_entity
    if country and country.name in countries:
        gui = display_country_info(gui, country.name)
        country.alpha = 1
    else:
        if gui is not None:
            gui.disable()


draw_boundaries(globe, radius=0.501, col=color.turquoise)
draw_centroids(globe, radius=0.501, col=add_hsv(color.red, (0, 0, -.1)), alpha=.4, size=.02)
get_gdp_data()

app.run()