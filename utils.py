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
from scipy.cluster.hierarchy import fcluster, linkage

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

def display_country_info(gui: Entity | None, country: str, info_text: str) -> Entity:
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
        gui.text = Text(parent=gui, text=info_text, color=color.white, scale=5, origin=Vec2(0, 0), position=Vec2(0, 0.1))
    else:
        gui.enable()
        gui.text.text = info_text
    return gui

def add_hsv(col: Color, hsv: tuple[float, float, float]) -> Color:
    h, s, v = col.h_getter(), col.s_getter(), col.v_getter()
    return color.hsv(
        h + hsv[0],
        s + hsv[1],
        v + hsv[2],
    )

def compute_growth_series(series: list[float], start_index: int = 0, end_index: int | None = None, log_scale: bool = True) -> list[float]:
    if end_index is None:
        end_index = len(series) - 1
    start_index = max(start_index, 0)
    end_index = min(end_index, len(series) - 1)
    if end_index - start_index < 1:
        return []
    growth = []
    for i in range(start_index + 1, end_index + 1):
        prev_value = max(series[i - 1], 1e-9)
        value = max(series[i], 1e-9)
        if log_scale:
            growth.append(math.log(value) - math.log(prev_value))
        else:
            growth.append((value - prev_value) / prev_value)
    return growth

def normalize_series(series: list[float]) -> list[float]:
    if not series:
        return []
    mean_value = sum(series) / len(series)
    variance = sum((value - mean_value) ** 2 for value in series) / len(series)
    std_value = math.sqrt(variance)
    if std_value < 1e-12:
        return [0.0 for _ in series]
    return [(value - mean_value) / std_value for value in series]

def correlation(series_a: list[float], series_b: list[float]) -> float:
    if not series_a or not series_b:
        return 0.0
    size = min(len(series_a), len(series_b))
    if size == 0:
        return 0.0
    x = series_a[:size]
    y = series_b[:size]
    numerator = sum(a * b for a, b in zip(x, y))
    denom_x = math.sqrt(sum(a * a for a in x))
    denom_y = math.sqrt(sum(b * b for b in y))
    denominator = denom_x * denom_y
    if denominator < 1e-12:
        return 0.0
    return numerator / denominator

def compute_group_similarity(selected_names: list[str], start_index: int = 0, end_index: int | None = None, log_scale: bool = True) -> dict[str, float]:
    if not selected_names:
        return {}
    selected_growth = []
    for name in selected_names:
        if name not in gdps:
            continue
        growth = normalize_series(compute_growth_series(gdps[name], start_index, end_index, log_scale))
        if growth:
            selected_growth.append(growth)
    if not selected_growth:
        return {}
    min_size = min(len(growth) for growth in selected_growth)
    reference = []
    for i in range(min_size):
        reference.append(sum(growth[i] for growth in selected_growth) / len(selected_growth))
    scores = {}
    for name, series in gdps.items():
        country_growth = normalize_series(compute_growth_series(series, start_index, end_index, log_scale))
        scores[name] = correlation(reference, country_growth)
    return scores

def cluster_similarity_scores(scores: dict[str, float], num_clusters: int = 4) -> dict[int, list[tuple[str, float]]]:
    if not scores:
        return {}
    items = sorted(scores.items(), key=lambda item: item[0])
    if len(items) == 1:
        name, score = items[0]
        return {1: [(name, score)]}
    values = [[score] for _, score in items]
    clusters = min(num_clusters, len(items))
    linkage_matrix = linkage(values, method="ward")
    labels = fcluster(linkage_matrix, t=clusters, criterion="maxclust")
    grouped = {}
    for idx, label in enumerate(labels):
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(items[idx])
    for label in grouped:
        grouped[label] = sorted(grouped[label], key=lambda item: item[1], reverse=True)
    return grouped

def cluster_countries_by_growth(start_index: int = 0, end_index: int | None = None, log_scale: bool = True, num_clusters: int = 4) -> dict[str, int]:
    growth_by_country = {}
    for name, series in gdps.items():
        growth = normalize_series(compute_growth_series(series, start_index, end_index, log_scale))
        if growth:
            growth_by_country[name] = growth
    if not growth_by_country:
        return {}
    min_size = min(len(values) for values in growth_by_country.values())
    if min_size <= 0:
        return {}
    names = sorted(growth_by_country.keys())
    rows = [growth_by_country[name][:min_size] for name in names]
    if len(rows) == 1:
        return {names[0]: 1}
    clusters = min(num_clusters, len(rows))
    linkage_matrix = linkage(rows, method="ward")
    labels = fcluster(linkage_matrix, t=clusters, criterion="maxclust")
    assignments = {}
    for idx, label in enumerate(labels):
        assignments[names[idx]] = int(label)
    return assignments

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
