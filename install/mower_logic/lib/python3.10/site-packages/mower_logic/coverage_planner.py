#!/usr/bin/env python3
import json
import os
import math
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, shape
from shapely.affinity import rotate

ZONES_FILE = os.path.expanduser('~/mower_ws/zones.json')
SETTINGS_FILE = os.path.expanduser('~/mower_ws/settings.json')
OUTPUT_FILE = os.path.expanduser('~/mower_ws/mission_plan.json')

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lecture {path}: {e}")
    return default

def extract_polygons(data):
    polys = []
    if not data:
        return polys

    if data.get('type') == 'FeatureCollection':
        features = data.get('features', [])
    elif data.get('type') == 'Feature':
        features = [data]
    elif 'type' in data and 'coordinates' in data:
        features = [{'type': 'Feature', 'geometry': data}]
    else:
        features = []

    for feat in features:
        geom = feat.get('geometry') if isinstance(feat, dict) else None
        if geom:
            try:
                s_shape = shape(geom)
                if not s_shape.is_valid:
                    s_shape = s_shape.buffer(0)
                
                if isinstance(s_shape, Polygon):
                    polys.append(s_shape)
                elif isinstance(s_shape, MultiPolygon):
                    polys.extend(list(s_shape.geoms))
            except Exception as e:
                print(f"Erreur conversion géométrie: {e}")

    return polys

def get_best_angle(poly):
    rect = poly.minimum_rotated_rectangle
    if isinstance(rect, Polygon):
        coords = list(rect.exterior.coords)
        max_len = 0
        best_angle = 0
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length > max_len:
                max_len = length
                best_angle = math.degrees(math.atan2(dy, dx))
        return best_angle
    return 0.0

def generate_plan():
    zones_data = load_json(ZONES_FILE, {})
    settings = load_json(SETTINGS_FILE, {
        'tool_width': 0.25,
        'overlap': 0.05,
        'border_offset': 0.10,
        'num_contours': 2,
        'pattern': 'boustrophedon',
        'angle': 0
    })

    tool_width = float(settings.get('tool_width', 0.25))
    overlap = float(settings.get('overlap', 0.05))
    border_offset = float(settings.get('border_offset', 0.10))
    num_contours = int(settings.get('num_contours', 2))
    user_angle = float(settings.get('angle', 0))

    DEG_PER_METER = 0.000009 

    step_size_m = max(0.05, tool_width - overlap)
    step_size_deg = step_size_m * DEG_PER_METER
    border_offset_deg = border_offset * DEG_PER_METER

    polygons = extract_polygons(zones_data)

    if not polygons:
        print("Aucun polygone trouvé.")
        with open(OUTPUT_FILE, 'w') as f:
            json.dump([], f)
        return

    plan = []

    for main_poly in polygons:
        if main_poly.is_empty or main_poly.area < 1e-11:
            continue

        zone_plan = {
            "contours": [],
            "path": [],
            "start_point": None,
            "end_point": None
        }

        # 1. Génération des contours
        for i in range(num_contours):
            dist = border_offset_deg + (i * step_size_deg)
            buffered = main_poly.buffer(-dist)
            
            if buffered.is_empty:
                break

            sub_polys = [buffered] if isinstance(buffered, Polygon) else list(buffered.geoms)

            for sp in sub_polys:
                coords = [[lat, lon] for lon, lat in sp.exterior.coords]
                zone_plan["contours"].append(coords)
                
                for interior in sp.interiors:
                    icoords = [[lat, lon] for lon, lat in interior.coords]
                    zone_plan["contours"].append(icoords)

        # 2. Zone de remplissage centrale
        inner_dist = border_offset_deg + (num_contours * step_size_deg)
        
        ext_poly = Polygon(main_poly.exterior)
        inner_ext = ext_poly.buffer(-inner_dist)

        if not inner_ext.is_empty:
            holes_buffered = [Polygon(int_ring).buffer(inner_dist) for int_ring in main_poly.interiors]

            work_zone = inner_ext
            for h in holes_buffered:
                work_zone = work_zone.difference(h)

            if not work_zone.is_empty:
                opt_angle = user_angle if user_angle != 0 else get_best_angle(ext_poly)
                centroid = ext_poly.centroid

                rotated_work_zone = rotate(work_zone, -opt_angle, origin=centroid)

                minx, miny, maxx, maxy = rotated_work_zone.bounds
                
                scan_lines_group = []
                y = miny + (step_size_deg / 2.0)
                
                while y <= maxy:
                    scan_line = LineString([(minx - 1.0, y), (maxx + 1.0, y)])
                    inter = scan_line.intersection(rotated_work_zone)

                    lines_in_row = []
                    if isinstance(inter, LineString):
                        lines_in_row.append(inter)
                    elif isinstance(inter, MultiLineString):
                        lines_in_row.extend(list(inter.geoms))

                    lines_in_row.sort(key=lambda l: l.bounds[0])

                    if lines_in_row:
                        scan_lines_group.append(lines_in_row)

                    y += step_size_deg

                path_pts = []
                reverse = False

                for row in scan_lines_group:
                    # Inversion de l'ordre d'accès aux tronçons de la rangée
                    current_row = list(reversed(row)) if reverse else row
                    
                    for line in current_row:
                        orig_line = rotate(line, opt_angle, origin=centroid)
                        coords = list(orig_line.coords)
                        
                        # Inversion du sens de parcours de la ligne individuelle
                        if reverse:
                            coords.reverse()
                            
                        for pt in coords:
                            path_pts.append([pt[1], pt[0]])

                    reverse = not reverse

                if path_pts:
                    zone_plan["path"].extend(path_pts)

        if zone_plan["path"]:
            zone_plan["start_point"] = zone_plan["path"][0]
            zone_plan["end_point"] = zone_plan["path"][-1]
        elif zone_plan["contours"]:
            zone_plan["start_point"] = zone_plan["contours"][0][0]
            zone_plan["end_point"] = zone_plan["contours"][-1][-1]

        plan.append(zone_plan)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(plan, f, indent=2)
    print("Plan de trajectoire généré avec succès.")

if __name__ == '__main__':
    generate_plan()
