#!/usr/bin/env python3
import math
from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.affinity import rotate
import pyproj

class PathGenerator:
    def __init__(self, zone_latlng, exclusions_latlng=None, num_tours=2, width=0.4):
        self.raw_latlng = zone_latlng
        self.exclusions_raw = exclusions_latlng or []
        self.num_tours = int(num_tours)
        self.spacing = float(width)

        ref_lat, ref_lng = zone_latlng[0]['lat'], zone_latlng[0]['lng']
        utm_zone = int((ref_lng + 180) / 6) + 1
        
        self.proj_utm = pyproj.Proj(proj='utm', zone=utm_zone, ellps='WGS84', datum='WGS84', units='m')
        self.proj_latlng = pyproj.Proj(proj='longlat', datum='WGS84')

    def _to_utm(self, lat, lng):
        return pyproj.transform(self.proj_latlng, self.proj_utm, lng, lat)

    def _to_latlng(self, x, y):
        lng, lat = pyproj.transform(self.proj_utm, self.proj_latlng, x, y)
        return {'lat': lat, 'lng': lng}

    def generate(self):
        utm_coords = [self._to_utm(p['lat'], p['lng']) for p in self.raw_latlng]
        poly = Polygon(utm_coords)
        if not poly.is_valid or poly.area == 0:
            return None

        waypoints = []

        # 1. TOURNIÈRES EXTÉRIEURES (Périmètre complet)
        for i in range(self.num_tours):
            offset_dist = -(self.spacing * (i + 0.5))
            tour_poly = poly.buffer(offset_dist, join_style=2)
            if tour_poly.is_empty or not isinstance(tour_poly, Polygon):
                break
            coords = list(tour_poly.exterior.coords)
            tour_gps = [self._to_latlng(x, y) for x, y in coords]
            waypoints.append({'type': 'headland', 'index': i, 'points': tour_gps})

        # Emprise utile
        inner_margin = -(self.spacing * self.num_tours)
        workable_poly = poly.buffer(inner_margin, join_style=2)

        # 2. TRAITEMENT DES EXCLUSIONS & DÉCOUPE DES POCHES
        excl_buffered_list = []
        for excl in self.exclusions_raw:
            excl_utm = [self._to_utm(p['lat'], p['lng']) for p in excl]
            e_poly = Polygon(excl_utm)
            if e_poly.is_valid:
                # Buffer de protection autour de l'obstacle
                buffer_dist = self.spacing * self.num_tours
                e_buffered = e_poly.buffer(buffer_dist, join_style=2)
                excl_buffered_list.append(e_buffered)

                # Tournières de l'obstacle
                for i in range(self.num_tours):
                    e_tour = e_poly.buffer(self.spacing * (i + 0.5), join_style=2)
                    if not e_tour.is_empty:
                        coords = list(e_tour.exterior.coords)
                        waypoints.append({'type': 'exclusion_headland', 'points': [self._to_latlng(x, y) for x, y in coords]})

        # Soustraction géométrique des obstacles
        non_obstacle_area = workable_poly
        if excl_buffered_list:
            for eb in excl_buffered_list:
                non_obstacle_area = non_obstacle_area.difference(eb)

        # 3. ALIGNEMENT
        ext_coords = list(poly.exterior.coords)
        max_len = 0
        ref_angle = 0
        for i in range(len(ext_coords) - 1):
            p1, p2 = ext_coords[i], ext_coords[i+1]
            dist = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            if dist > max_len:
                max_len = dist
                ref_angle = math.atan2(p2[1]-p1[1], p2[0]-p1[0])

        # 4. BALAYAGE AVEC PROLONGEMENT DANS LES TOURNIÈRES (Overlap +w/2)
        if not non_obstacle_area.is_empty:
            origin_pt = poly.centroid
            rot_poly = rotate(non_obstacle_area, -ref_angle, use_radians=True, origin=origin_pt)
            minx, miny, maxx, maxy = rot_poly.bounds

            lines = []
            y = miny + self.spacing / 2.0
            direction = True

            overlap_margin = self.spacing / 2.0  # Prolongement dans la tournière pour zéro oubli dans les pointes

            while y < maxy:
                scan_line = LineString([(minx - 50, y), (maxx + 50, y)])
                inter = rot_poly.intersection(scan_line)
                
                if not inter.is_empty:
                    segments = []
                    if isinstance(inter, LineString):
                        segments = [inter]
                    elif isinstance(inter, MultiLineString):
                        segments = list(inter.geoms)

                    for seg in segments:
                        p1, p2 = seg.coords[0], seg.coords[-1]
                        
                        # Extension des extrémités du segment de w/2
                        ext_x1 = p1[0] - overlap_margin if p1[0] < p2[0] else p1[0] + overlap_margin
                        ext_x2 = p2[0] + overlap_margin if p2[0] > p1[0] else p2[0] - overlap_margin
                        
                        extended_seg = LineString([(ext_x1, y), (ext_x2, y)])
                        
                        rot_seg = rotate(extended_seg, ref_angle, use_radians=True, origin=origin_pt)
                        coords = list(rot_seg.coords)
                        if not direction:
                            coords.reverse()
                        lines.append([self._to_latlng(x, y) for x, y in coords])

                y += self.spacing
                direction = not direction

            waypoints.append({'type': 'swaths', 'lines': lines})

        return waypoints
