from globals import *
import math
from ursina import *
from utils import *
app = Ursina()

window.color = add_hsv(color.white, (0, -.1, -.4))
globe = Entity(model="sphere", color=add_hsv(color.dark_gray, (0, 0, -.12)), scale=4, name="globe")
gui = None
hovered_country = None
hovered_country_name = None
hovered_country_info_text = None
similarity_scores = {}
similarity_signature = None
cluster_assignments = {}
cluster_mode_enabled = False
cluster_count_current = 4
selected_countries = []
selected_country = None
unselected_country = None

draw_globe_line(globe=globe, rho=0.5, color=color.white, alpha=.6, size=0.004, num_markers=100, theta=math.pi/2)
Entity(model="sphere", color=color.white, scale=0.008, position=Vec3(0, 0.5, 0), parent=globe)
Entity(model="sphere", color=color.white, scale=0.008, position=Vec3(0, -0.5, 0), parent=globe)
left_mouse_pressed = False
mouse_position = Vec3(0, 0)
camera.parent = globe

def unselect_all() -> None:
    global selected_countries, selected_country, unselected_country
    for country in selected_countries:
        country.alpha = .8
        country.scale = .02
    selected_countries.clear()
    selected_country = None
    unselected_country = None

unselect_all_button_base_color = add_hsv(color.dark_gray, (0, 0, -.8))
unselect_all_button_hover_color = color.dark_gray
log_scale_button_base_color = add_hsv(color.dark_gray, (0, 0, -.8))
log_scale_button_hover_color = color.dark_gray
cluster_button_base_color = add_hsv(color.dark_gray, (0, 0, -.8))
cluster_button_hover_color = color.dark_gray
use_log_scale = True

unselect_all_button = Button(
    text="Unselect All",
    scale=Vec2(.2, .07),
    position=Vec2(-.7, -0.35),
    color=unselect_all_button_base_color,
    highlight_color=unselect_all_button_hover_color,
    text_color=color.white,
    alpha=.5,
    on_click=unselect_all,
)

def toggle_log_scale() -> None:
    global cluster_assignments, use_log_scale
    use_log_scale = not use_log_scale
    if use_log_scale:
        log_scale_button.text = "Log Scale: On"
    else:
        log_scale_button.text = "Log Scale: Off"
    if cluster_mode_enabled:
        cluster_assignments = compute_cluster_assignments(int(cluster_count_slider.value))
        apply_cluster_colors()
    elif selected_countries:
        start_year_index = int(year_slider.value) - year_base
        end_year_index = int(end_year_slider.value) - year_base
        if end_year_index < start_year_index:
            end_year_index = start_year_index
        similarity_scores.clear()
        similarity_scores.update(compute_group_similarity(
            sorted(country.name for country in selected_countries),
            start_index=start_year_index,
            end_index=end_year_index,
            log_scale=use_log_scale,
        ))
        if cluster_mode_enabled:
            cluster_assignments = compute_cluster_assignments(int(cluster_count_slider.value))
            apply_cluster_colors()
        else:
            apply_similarity_colors()
    else:
        apply_year_colors(int(year_slider.value) - year_base, log_scale=use_log_scale)

log_scale_button = Button(
    text="Log Scale: On",
    scale=Vec2(.2, .07),
    position=Vec2(-.7, -0.45),
    color=log_scale_button_base_color,
    highlight_color=log_scale_button_hover_color,
    text_color=color.white,
    alpha=.5,
    on_click=toggle_log_scale,
)

def compute_cluster_assignments(num_clusters: int) -> dict[str, int]:
    start_year_index = int(year_slider.value) - year_base
    end_year_index = int(end_year_slider.value) - year_base
    if end_year_index < start_year_index:
        end_year_index = start_year_index
    assignments = cluster_countries_by_growth(
        start_index=start_year_index,
        end_index=end_year_index,
        log_scale=use_log_scale,
        num_clusters=num_clusters,
    )
    if not assignments:
        return {}
    grouped = {}
    for name, cluster_id in assignments.items():
        if cluster_id not in grouped:
            grouped[cluster_id] = []
        grouped[cluster_id].append(name)
    print("=== Country Clusters ===")
    print(f"Cluster scope: all {len(assignments)} countries")
    for cluster_id in sorted(grouped.keys()):
        members = sorted(grouped[cluster_id])
        print(f"Cluster {cluster_id} ({len(members)} countries)")
        print(", ".join(members))
    return assignments

def apply_cluster_legend_values() -> None:
    legend_title.text = "Cluster Legend"
    cluster_ids = sorted(set(cluster_assignments.values()))
    if not cluster_ids:
        for i in range(legend_num_steps):
            step = i / (legend_num_steps - 1)
            legend_points[i].color = add_hsv(color.red, (step * 340, 0, 0))
            legend_values[i].text = "-"
        return
    max_cluster_id = max(cluster_ids)
    for i in range(legend_num_steps):
        step = i / (legend_num_steps - 1)
        cluster_id = 1 + int(step * (max_cluster_id - 1)) if max_cluster_id > 1 else 1
        ratio = (cluster_id - 1) / (max_cluster_id - 1) if max_cluster_id > 1 else 0
        legend_points[i].color = add_hsv(color.red, (ratio * 340, 0, 0))
        legend_values[i].text = f"C{cluster_id}"

def apply_cluster_colors() -> None:
    apply_cluster_legend_values()
    max_cluster_id = max(cluster_assignments.values()) if cluster_assignments else 1
    for name, country in countries.items():
        cluster_id = cluster_assignments.get(name)
        if cluster_id is None:
            country.color = add_hsv(color.dark_gray, (0, 0, -.2))
            country.alpha = .25
            country.scale = .02
            continue
        ratio = (cluster_id - 1) / (max_cluster_id - 1) if max_cluster_id > 1 else 0
        country.color = add_hsv(color.red, (ratio * 340, 0, 0))
        country.alpha = .8
        country.scale = .02
    for country in selected_countries:
        country.color = color.white
        country.alpha = 1.
        country.scale = .03

def toggle_clustering() -> None:
    global cluster_assignments, cluster_mode_enabled
    if cluster_mode_enabled:
        cluster_mode_enabled = False
        cluster_assignments = {}
        cluster_button.text = "Cluster"
        cluster_count_slider.disable()
        cluster_count_slider_label.disable()
        if selected_countries:
            apply_similarity_colors()
        else:
            apply_year_colors(int(year_slider.value) - year_base, log_scale=use_log_scale)
        return
    cluster_mode_enabled = True
    cluster_button.text = "Stop Cluster"
    cluster_count_slider.enable()
    cluster_count_slider_label.enable()
    cluster_assignments = compute_cluster_assignments(int(cluster_count_slider.value))
    if not cluster_assignments:
        cluster_mode_enabled = False
        cluster_button.text = "Cluster"
        cluster_count_slider.disable()
        cluster_count_slider_label.disable()
        print("Unable to compute clusters for current year range.")
        return
    apply_cluster_colors()

cluster_button = Button(
    text="Cluster",
    scale=Vec2(.2, .07),
    position=Vec2(-.7, -0.25),
    color=cluster_button_base_color,
    highlight_color=cluster_button_hover_color,
    text_color=color.white,
    alpha=.5,
    on_click=toggle_clustering,
)

cluster_count_slider = Slider(
    parent=camera.ui,
    min=1,
    max=30,
    default=4,
    step=1,
    origin=Vec2(.5, .5),
    text_color=color.white,
    position=(-.82, -.03),
)
cluster_count_slider.disable()
cluster_count_slider_label = Text(
    parent=camera.ui,
    text="Cluster Count",
    color=color.white,
    scale=1.5,
    origin=Vec2(.5, .5),
    position=Vec2(-.53, .05),
)
cluster_count_slider_label.disable()

year_slider = Slider(
    parent=camera.ui,
    min=1960,
    max=2025,
    default=2000,
    step=1,
    origin=Vec2(.5, .5),
    text_color=color.white,
    position=(-.82, -.13),
)
year_slider_label = Text(
    parent=camera.ui,
    text="Start Year",
    color=color.white,
    scale=1.5,
    origin=Vec2(.5, .5),
    position=Vec2(-.53, -.05),
)
end_year_slider = Slider(
    parent=camera.ui,
    min=1960,
    max=2025,
    default=2025,
    step=1,
    origin=Vec2(.5, .5),
    text_color=color.white,
    position=(-.82, -.23),
    enabled=False,
)
end_year_slider_label = Text(
    parent=camera.ui,
    text="End Year",
    color=color.white,
    scale=1.5,
    origin=Vec2(.5, .5),
    position=Vec2(-.53, -.15),
)
end_year_slider_label.disable()

legend_panel = Entity(
    parent = camera.ui,
    model = "quad",
    color = color.black,
    alpha = .45,
    scale = Vec2(.40, .40),
    position = Vec2(.62, -.22),
)
legend_title = Text(
    parent = legend_panel,
    text = "GDP Legend",
    color = color.white,
    scale = 4,
    origin = Vec2(0, 0),
    position = Vec2(.0, .4),
)
legend_points = []
legend_values = []
legend_num_steps = 7
for i in range(legend_num_steps):
    y_pos = .2 - i * .09
    step = i / (legend_num_steps - 1)
    point = Entity(
        parent = legend_panel,
        model = "circle",
        color = add_hsv(color.red, (step * 360, 0, 0)),
        scale = (.07, .07),
        origin = Vec2(.0, .0),
        position = Vec2(-.12, y_pos),
    )
    value = Text(
        parent = legend_panel,
        text = "0",
        color = color.white,
        scale = 2.2,
        origin = Vec2(.0, .0),
        position = Vec2(.1, y_pos),
    )
    legend_points.append(point)
    legend_values.append(value)

year_base = 1960
current_year_index = None

def format_gdp_value(gdp_value: float) -> str:
    if gdp_value >= 1000000000000:
        return f"{gdp_value / 1000000000000:.1f}T"
    if gdp_value >= 1000000000:
        return f"{gdp_value / 1000000000:.1f}B"
    if gdp_value >= 1000000:
        return f"{gdp_value / 1000000:.1f}M"
    return f"{gdp_value:.0f}"

def get_country_gdp_info_text(country_name: str) -> str:
    if country_name not in gdps:
        return f"{country_name}\nGDP: N/A"
    if current_year_index is None:
        return f"{country_name}\nGDP: N/A"
    country_gdp_values = gdps[country_name]
    if current_year_index < 0 or current_year_index >= len(country_gdp_values):
        return f"{country_name}\nGDP: N/A"
    gdp_value = country_gdp_values[current_year_index]
    info_text = f"{country_name}\nGDP: {format_gdp_value(gdp_value)}"
    if similarity_scores:
        similarity_value = similarity_scores.get(country_name)
        if similarity_value is not None:
            info_text += f"\nSimilarity: {similarity_value:.3f}"
    return info_text

def apply_legend_values(year_index: int, log_scale: bool = True) -> None:
    legend_title.text = "GDP Legend"
    gdp_values = sorted(gdp[year_index] for gdp in gdps.values())
    if not gdp_values:
        return
    gdp_max = gdp_values[-1]
    gdp_scale_max = math.log1p(gdp_max) if log_scale else gdp_max
    for i in range(legend_num_steps):
        step = i / (legend_num_steps - 1)
        legend_points[i].color = add_hsv(color.red, (step * 340, 0, 0))
        scaled_value = step * gdp_scale_max
        gdp_value = math.expm1(scaled_value) if log_scale else scaled_value
        legend_values[i].text = format_gdp_value(gdp_value)

def apply_similarity_legend_values() -> None:
    legend_title.text = "Similarity Legend"
    ratio_values = sorted(clamp((score + 1) / 2, 0, 1) for score in similarity_scores.values())
    for i in range(legend_num_steps):
        step = i / (legend_num_steps - 1)
        if ratio_values:
            ratio_index = int(step * (len(ratio_values) - 1))
            ratio = ratio_values[ratio_index]
        else:
            ratio = step
        legend_points[i].color = add_hsv(color.red, (ratio * 340, 0, 0))
        legend_values[i].text = f"{ratio:.2f}"

def apply_year_colors(year_index: int, log_scale: bool = True) -> None:
    global current_year_index
    if "United States" not in gdps:
        return
    max_index = len(gdps["United States"]) - 1
    if max_index < 0:
        return
    if year_index < 0:
        year_index = 0
    if year_index > max_index:
        year_index = max_index
    current_year_index = year_index
    gdp_max = max(gdp[year_index] for gdp in gdps.values())
    if log_scale:
        gdp_max = math.log1p(gdp_max)
    for name, country in countries.items():
        gdp = gdps[name][year_index]
        if log_scale:
            gdp = math.log1p(gdp)
        ratio = (gdp / gdp_max) if gdp_max else 0
        col = add_hsv(color.red, (ratio * 340, 0, 0))
        country.color = col
        country.alpha = .8
        country.scale = .02
    apply_legend_values(year_index, log_scale=log_scale)

def apply_similarity_colors() -> None:
    apply_similarity_legend_values()
    for name, country in countries.items():
        score = similarity_scores.get(name, 0.0)
        ratio = (score + 1) / 2
        ratio = clamp(ratio, 0, 1)
        col = add_hsv(color.red, (ratio * 340, 0, 0))
        country.color = col
        country.alpha = .8
        country.scale = .02
    for country in selected_countries:
        country.color = color.white
        country.alpha = 1.
        country.scale = .03

def input(key: str) -> None:
    global left_mouse_pressed, mouse_position, camera_distance, selected_country, unselected_country
    if key == "right mouse down":
        mouse_position = mouse.position
        left_mouse_pressed = True
    elif key == "left mouse down":
        mouse_hovered_entity = mouse.hovered_entity
        if mouse_hovered_entity and mouse_hovered_entity.name in countries:
            if mouse_hovered_entity in selected_countries:
                unselected_country = mouse_hovered_entity
                selected_countries.remove(unselected_country)
            else:
                selected_country = mouse_hovered_entity
                selected_countries.append(selected_country)

    elif key == "right mouse up":
        left_mouse_pressed = False
    elif key == "left mouse up":
        pass

    if key == "scroll up":
        camera_distance = max(camera_distance - camera_zoom_speed, 0)
    elif key == "scroll down":
        camera_distance += camera_zoom_speed

camera.position = Vec3(spherical_to_cartesian(camera_distance, camera_phi, camera_theta))
camera.look_at(globe.position)

def update() -> None:
    global mouse_position, camera_phi, camera_theta, cluster_assignments, cluster_count_current, cluster_mode_enabled, current_year_index, gui, hovered_country, hovered_country_name, hovered_country_info_text, similarity_scores, similarity_signature, selected_country, unselected_country
    if left_mouse_pressed:
        mouse_delta = mouse.position - mouse_position
        mouse_position = mouse.position
        rotate_speed = camera_rotate_speed * (camera_distance - 0.5)
        camera_phi = camera_phi - mouse_delta.x * rotate_speed
        camera_theta = clamp(camera_theta + mouse_delta.y * rotate_speed, .01, math.pi - .01)
    camera.position = Vec3(spherical_to_cartesian(camera_distance, camera_phi, camera_theta))
    camera.animate("rotation_z", 0, duration=.2, curve=curve.in_sine)
    camera.look_at(globe.position)

    if hovered_country and hovered_country.name in countries and hovered_country not in selected_countries:
        hovered_country.alpha = .8
        hovered_country.scale = .02
    hovered_country = mouse.hovered_entity
    if hovered_country and hovered_country not in selected_countries and hovered_country.name in countries:
        info_text = get_country_gdp_info_text(hovered_country.name)
        if hovered_country_name != hovered_country.name:
            gui = display_country_info(gui, hovered_country.name, info_text)
            hovered_country_name = hovered_country.name
            hovered_country_info_text = info_text
        elif gui is None:
            gui = display_country_info(gui, hovered_country.name, info_text)
            hovered_country_info_text = info_text
        elif hovered_country_info_text != info_text:
            gui = display_country_info(gui, hovered_country.name, info_text)
            hovered_country_info_text = info_text
        hovered_country.alpha = .8
        hovered_country.scale = .025
    if not hovered_country or hovered_country.name not in countries:
        if gui is not None:
            gui.disable()
        hovered_country_name = None
        hovered_country_info_text = None
    if selected_country:
        selected_country.alpha = 1.
        selected_country.scale = .03
        selected_country = None
    elif unselected_country:
        unselected_country.alpha = .8
        unselected_country.scale = .02
        unselected_country = None

    selected_names = sorted(country.name for country in selected_countries)
    start_year_index = int(year_slider.value) - year_base
    end_year_index = int(end_year_slider.value) - year_base
    if end_year_index < start_year_index:
        end_year_index = start_year_index
        end_year_slider.value = year_base + end_year_index
    next_signature = tuple(selected_names)
    signature_with_range = (next_signature, start_year_index, end_year_index, use_log_scale)
    if signature_with_range != similarity_signature:
        similarity_signature = signature_with_range
        if cluster_mode_enabled:
            cluster_assignments = compute_cluster_assignments(int(cluster_count_slider.value))
            apply_cluster_colors()
            if selected_names:
                similarity_scores = compute_group_similarity(
                    selected_names,
                    start_index=start_year_index,
                    end_index=end_year_index,
                    log_scale=use_log_scale,
                )
            else:
                similarity_scores = {}
        elif selected_names:
            similarity_scores = compute_group_similarity(
                selected_names,
                start_index=start_year_index,
                end_index=end_year_index,
                log_scale=use_log_scale,
            )
            apply_similarity_colors()
        else:
            similarity_scores = {}
            apply_year_colors(current_year_index if current_year_index is not None else int(year_slider.value) - year_base, log_scale=use_log_scale)
        hovered_country_info_text = None

    cluster_count = int(cluster_count_slider.value)
    if cluster_count != cluster_count_current:
        cluster_count_current = cluster_count
        if cluster_mode_enabled:
            cluster_assignments = compute_cluster_assignments(cluster_count_current)
            apply_cluster_colors()

    if cluster_mode_enabled:
        legend_panel.disable()
    else:
        legend_panel.enable()

    if not selected_countries:
        unselect_all_button.disable()
        end_year_slider.disable()
        end_year_slider_label.disable()
        cluster_button.alpha = .5
    else:
        unselect_all_button.enable()
        end_year_slider.enable()
        end_year_slider_label.enable()
        cluster_button.alpha = 1.

    if unselect_all_button.hovered:
        unselect_all_button.color = unselect_all_button_hover_color
    else:
        unselect_all_button.color = unselect_all_button_base_color
    if log_scale_button.hovered:
        log_scale_button.color = log_scale_button_hover_color
    else:
        log_scale_button.color = log_scale_button_base_color
    if cluster_button.hovered:
        cluster_button.color = cluster_button_hover_color
    else:
        cluster_button.color = cluster_button_base_color

    year_index = start_year_index
    if year_index != current_year_index:
        if selected_countries:
            current_year_index = year_index
            hovered_country_info_text = None
        else:
            apply_year_colors(year_index, log_scale=use_log_scale)

draw_boundaries(globe, radius=0.501, col=add_hsv(color.green, (0, -.8, 0)))
draw_centroids(globe, radius=0.501, col=add_hsv(color.red, (0, 0, -.1)), alpha=.4, size=.02)
get_gdp_data()
apply_year_colors(int(year_slider.value) - year_base, log_scale=use_log_scale)
for _, country in countries.items():
    country.alpha = .8

app.run()