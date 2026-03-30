import math
from typing import Callable
from ursina import *
from globals import *
import os
import re
import zipfile
import urllib.request
import json
import csv

running = {}

def rebounded(func: Callable):
    running[func] = False
    def wrapper(*args, **kwargs):
        if running[func]:
            return
        running[func] = True
        func(*args, **kwargs)
        running[func] = False
    return wrapper

def spherical_to_cartesian(rho: float, phi: float, theta: float) -> tuple[float, float, float]:
    x = rho * math.sin(theta) * math.cos(phi)
    z = rho * math.sin(theta) * math.sin(phi)
    y = rho * math.cos(theta)
    return x, y, z

def draw_globe_line(
    globe: Entity, 
    rho: float, 
    color: Color,
    alpha: float,
    size: float,
    num_markers: int,
    phi: float | None = None,
    theta: float | None = None,
) -> None:
    assert (phi is None) ^ (theta is None)
    change_phi = phi is None
    for i in range(num_markers):
        angle = math.radians(i * (360 / num_markers))
        if change_phi:
            phi = angle
        else:
            theta = angle
        x, y, z = spherical_to_cartesian(rho, phi, theta)
        Entity(model="sphere", color=color, alpha=alpha, scale=size, position=(x, y, z), parent=globe)

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))

def download(url: str, base_dir: str = "data") -> str:
    filename = url.split("/")[-1]
    file_path = os.path.join(base_dir, filename)
    if os.path.exists(file_path):
        return file_path

    os.makedirs(base_dir, exist_ok=True)

    urllib.request.urlretrieve(url, file_path)

    return file_path

def download_and_extract(url: str, base_dir: str = "data") -> str:
    filename = url.split("/")[-1].removesuffix("?downloadformat=csv").removesuffix(".zip")
    if os.path.exists(os.path.join(base_dir, filename)):
        return os.path.join(base_dir, filename)
    if not filename.endswith(".zip"):
        filename += ".zip"
    folder_name = re.sub(r"\.zip$", "", filename)
    folder_path = os.path.join(base_dir, folder_name)
    zip_path = os.path.join(base_dir, filename)

    os.makedirs(base_dir, exist_ok=True)
    urllib.request.urlretrieve(url, zip_path)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(folder_path)

    os.remove(zip_path)
    return folder_path

def draw_boundaries(globe: Entity, radius: float, col: Color, step: int = 1) -> None:
    boundaries_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
    boundaries_path = download(boundaries_url, "data")
    with open(boundaries_path, "rb") as f:
        geojson = json.load(f)
    
    for feature in geojson["features"]:
        geometry = feature["geometry"]
        geom_type = geometry["type"]
        coords = geometry["coordinates"]
        
        polygons = coords if geom_type == "MultiPolygon" else [coords]
        
        for poly in polygons:
            outline = poly[0] if isinstance(poly[0][0], list) else poly
            
            if len(outline) < 20:
                continue
                
            vertices = []
            for lon, lat in outline[::step]:
                phi = math.radians(lon) 
                theta = math.radians(90 - lat)

                x, y, z = spherical_to_cartesian(radius, phi, theta)
                vertices.append(Vec3(x, y, z))

            if len(vertices) > 2:
                vertices.append(vertices[0])
                Entity(
                    model=Mesh(vertices=vertices, mode='line', static=True),
                    color=col,
                    parent=globe,
                    thickness=1,
                    name="boundary"
                )

def draw_centroids(globe: Entity, radius: float, col: Color, alpha: float, size: float) -> None:
    centroids_url = "https://raw.githubusercontent.com/google/dspl/master/samples/google/canonical/countries.csv"
    centroids_path = download(centroids_url, "data")
    with open(centroids_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                country = row["name"]

                phi = math.radians(lon)
                theta = math.radians(90 - lat)

                x, y, z = spherical_to_cartesian(radius, phi, theta)

                countries[country] = Entity(
                    model="sphere",
                    color=col,
                    scale=size,
                    alpha=alpha,
                    position=(x, y, z),
                    parent=globe,
                    collider="sphere",
                    name=country,
                )
            except Exception:
                print(f"Error parsing row: {row}")

def display_country_info(gui: Entity | None, country: str) -> Entity:
    if gui is None:
        gui = Entity(
            parent=camera.ui,
            model="quad",
            color=color.black,
            alpha=.5,
            scale=Vec2(0.5, 0.5),
            position=Vec2(-0.6, 0.2),
            name="country_info",
        )
        gui.text = Text(parent=gui, text=country, color=color.white, scale=5, origin=Vec2(0, 0), position=Vec2(0, 0.1))
    else:
        gui.enable()
        gui.text.text = country
    return gui

def add_hsv(col: Color, hsv: tuple[float, float, float]) -> Color:
    h, s, v = col.h_getter(), col.s_getter(), col.v_getter()
    return color.hsv(
        h + hsv[0],
        s + hsv[1],
        v + hsv[2],
    )

def get_gdp_data() -> None:
    gdp_data_url = "https://api.worldbank.org/v2/en/indicator/NY.GDP.MKTP.CD?downloadformat=csv"
    gdp_data = download_and_extract(gdp_data_url, "data")
    with open(os.path.join(gdp_data, "API_NY.GDP.MKTP.CD_DS2_en_csv_v2_133326.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                gdp = []
                for i in range(1, len(row[None])):
                    value = row[None][i]
                    if value == "":
                        value = gdp[-1] if gdp else .0
                    else:
                        value = float(value)
                    gdp.append(value)
                gdps[row["\ufeff\"Data Source\""]] = gdp
            except KeyError:
                print(f"Error parsing row: {row}")

        assert "Russia" not in gdps
        gdps["Russia"] = gdps["Russian Federation"]
        assert "Iran" not in gdps
        gdps["Iran"] = gdps["Iran, Islamic Rep."]
        assert "South Korea" not in gdps
        gdps["South Korea"] = gdps["Korea, Rep."]
        assert "North Korea" not in gdps
        gdps["North Korea"] = gdps["Korea, Dem. People's Rep."]
        assert "Myanmar [Burma]" not in gdps
        gdps["Myanmar"] = gdps["Myanmar"]
        assert "Vietnam" not in gdps
        gdps["Vietnam"] = gdps["Viet Nam"]
        assert "Venezuela" not in gdps
        gdps["Venezuela"] = gdps["Venezuela, RB"]
        assert "Yemen" not in gdps
        gdps["Yemen"] = gdps["Yemen, Rep."]
        assert "Congo [DRC]" not in gdps
        gdps["Congo [DRC]"] = gdps["Congo, Dem. Rep."]
        assert "Egypt" not in gdps
        gdps["Egypt"] = gdps["Egypt, Arab Rep."]
        for key in set(gdps.keys()) - set(countries.keys()):
            gdps.pop(key)
        for key in set(countries.keys()) - set(gdps.keys()):
            destroy(countries[key])
            countries.pop(key)
        assert len(gdps) == len(countries)
