import json
import os
import math
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import transform
import pyproj

DATA_DIR = os.path.expanduser('~/mower_ws/src/mower_web/data')
ZONES_FILE = os.path.join(DATA_DIR, 'zones.geojson')
PATH_FILE = os.path.join(DATA_DIR, 'path.geojson')

def generate_coverage_path(turn_count=2, cut_width=0.4, overlap=0.05, angle_deg=0, ref_edge=None):
    if not os.path.exists(ZONES_FILE):
        return {"type": "FeatureCollection", "features": []}

    try:
        with open(ZONES_FILE, 'r') as f:
            zones_data = json.load(f)
    except Exception as e:
        print(f"[PathPlanner] Erreur GeoJSON: {e}")
        return {"type": "FeatureCollection", "features": []}

    features = zones_data.get('features', [])
    if not features:
        return {"type": "FeatureCollection", "features": []}

    main_zone_coords = None
    obstacles_coords = []

    for f in features:
        props = f.get('properties', {})
        geom = f.get('geometry', {})
        if geom.get('type') == 'Polygon':
            coords = geom['coordinates'][0]
            if props.get('type') in ['horaire', 'manual']:
                if not main_zone_coords:
                    main_zone_coords = coords
            elif props.get('type') == 'antihoraire':
                obstacles_coords.append(coords)

    if not main_zone_coords or len(main_zone_coords) < 3:
        return {"type": "FeatureCollection", "features": []}

    # Projections Cartographiques WGS84 -> UTM
    ref_lon, ref_lat = main_zone_coords[0][0], main_zone_coords[0][1]
    utm_zone = int((ref_lon + 180) / 6) + 1
    utm_crs = f"+proj=utm +zone={utm_zone} +datum=WGS84 +units=m +no_defs"
    
    project_to_utm = pyproj.Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True).transform
    project_to_gps = pyproj.Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True).transform

    poly_gps = Polygon(main_zone_coords, holes=obstacles_coords)
    poly_utm = transform(project_to_utm, poly_gps)

    # Orientation basée sur un bord cliqué ou sur l'angle sélectionné
    final_angle_deg = float(angle_deg)
    if ref_edge and isinstance(ref_edge, dict) and 'click_lat' in ref_edge and 'click_lng' in ref_edge:
        click_pt_utm = transform(project_to_utm, Point(ref_edge['click_lng'], ref_edge['click_lat']))
        exterior_coords = list(poly_utm.exterior.coords)
        
        min_dist = float('inf')
        best_segment = None
        
        for i in range(len(exterior_coords) - 1):
            p1 = exterior_coords[i]
            p2 = exterior_coords[i+1]
            seg = LineString([p1, p2])
            dist = seg.distance(click_pt_utm)
            if dist < min_dist:
                min_dist = dist
                best_segment = (p1, p2)

        if best_segment:
            dx = best_segment[1][0] - best_segment[0][0]
            dy = best_segment[1][1] - best_segment[0][1]
            final_angle_deg = math.degrees(math.atan2(dy, dx))

    effective_width = max(0.1, float(cut_width) - float(overlap))
    path_lines_utm = []

    # Tournières
    current_poly = poly_utm
    for i in range(int(turn_count)):
        offset_dist = -(effective_width / 2.0) if i == 0 else -effective_width
        current_poly = current_poly.buffer(offset_dist, join_style=2)
        
        if current_poly.is_empty:
            break
            
        geoms = current_poly.geoms if hasattr(current_poly, 'geoms') else [current_poly]
        for g in geoms:
            if hasattr(g, 'exterior'):
                path_lines_utm.append(g.exterior)

    # Lignes parallèles
    if not current_poly.is_empty:
        minx, miny, maxx, maxy = current_poly.bounds
        diag = math.sqrt((maxx - minx)**2 + (maxy - miny)**2)
        
        y = miny - diag
        angle_rad = math.radians(final_angle_deg + 90)
        
        while y <= maxy + diag:
            x0, y0 = minx - diag, y
            x1, y1 = maxx + diag, y
            
            cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
            
            rx0 = cx + (x0 - cx) * math.cos(angle_rad) - (y0 - cy) * math.sin(angle_rad)
            ry0 = cy + (x0 - cx) * math.sin(angle_rad) + (y0 - cy) * math.cos(angle_rad)
            rx1 = cx + (x1 - cx) * math.cos(angle_rad) - (y1 - cy) * math.sin(angle_rad)
            ry1 = cy + (x1 - cx) * math.sin(angle_rad) + (y1 - cy) * math.cos(angle_rad)

            line = LineString([(rx0, ry0), (rx1, ry1)])
            intersection = current_poly.intersection(line)

            if not intersection.is_empty:
                inter_geoms = intersection.geoms if hasattr(intersection, 'geoms') else [intersection]
                for g in inter_geoms:
                    if g.geom_type == 'LineString':
                        path_lines_utm.append(g)

            y += effective_width

    # Export GeoJSON
    path_features = []
    for line in path_lines_utm:
        line_gps = transform(project_to_gps, line)
        coords_gps = list(line_gps.coords)
        path_features.append({
            "type": "Feature",
            "properties": {"type": "path_line"},
            "geometry": {
                "type": "LineString",
                "coordinates": coords_gps
            }
        })

    result_geojson = {"type": "FeatureCollection", "features": path_features}
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PATH_FILE, 'w') as f:
        json.dump(result_geojson, f, indent=2)

    print(f"[PathPlanner] OK: {len(path_features)} lignes générées (Angle={final_angle_deg:.1f}°).")
    return result_geojson
