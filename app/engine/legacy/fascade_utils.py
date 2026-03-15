from typing import Dict, List, Optional

from shapely.geometry import LineString

FASCADE_DISTANCE_THRESHOLD = 2.0  # feet
FASCADE_MAX_DISTANCE = 15.0  # feet (max search radius if no candidates)
FASCADE_DISTANCE_STEP = 1.0  # feet
FASCADE_SAMPLE_SPACING = 0.5  # feet


def compute_fascade_assignments(
    floor_plan: Dict,
    distance_threshold: float = FASCADE_DISTANCE_THRESHOLD,
    sample_spacing: float = FASCADE_SAMPLE_SPACING,
    max_distance: float = FASCADE_MAX_DISTANCE,
    distance_step: float = FASCADE_DISTANCE_STEP,
) -> Dict:
    """
    Assign façade (perimeter) segments to nearby columns and walls.

    Returns a dict containing aggregated lengths and individual segment geometry.
    """
    polygon = floor_plan.get('slab_polygon')
    if polygon is None or polygon.is_empty:
        return _empty_result(distance_threshold, 0.0)

    try:
        boundary_line = LineString(list(polygon.exterior.coords))
    except Exception:
        return _empty_result(distance_threshold, 0.0)

    perimeter = boundary_line.length
    if perimeter <= 0:
        return _empty_result(distance_threshold, 0.0)

    column_points = floor_plan.get('column_points', [])
    column_labels = floor_plan.get('column_labels', [])
    walls = floor_plan.get('walls', [])

    def build_candidates(threshold: float) -> List[Dict]:
        candidates: List[Dict] = []

        for idx, point in enumerate(column_points):
            label = column_labels[idx] if idx < len(column_labels) else f"UNLABELED_{idx}"
            try:
                distance = point.distance(boundary_line)
            except Exception:
                continue

            if distance <= threshold:
                candidates.append({
                    'label': label,
                    'geom': point,
                    'type': 'column',
                    'column_index': idx,
                    'wall_index': None,
                })

        for wall in walls:
            wall_line = wall.get('wall_line')
            if wall_line is None:
                continue
            try:
                distance = wall_line.distance(boundary_line)
            except Exception:
                continue

            if distance <= threshold:
                label = f"WALL_{wall.get('wall_index', 'UNK')}"
                candidates.append({
                    'label': label,
                    'geom': wall_line,
                    'type': 'wall',
                    'column_index': None,
                    'wall_index': wall.get('wall_index'),
                })

        return candidates

    def sample_polyline(start_distance: float, end_distance: float) -> List[tuple]:
        coords: List[tuple] = []
        sample_step = max(0.25, sample_spacing)
        distance = start_distance

        while distance < end_distance - 1e-6:
            point = boundary_line.interpolate(distance, normalized=False)
            coords.append((point.x, point.y))
            distance += sample_step

        end_point = boundary_line.interpolate(end_distance, normalized=False)
        coords.append((end_point.x, end_point.y))
        return coords

    def assign_segments(candidates: List[Dict]) -> (Dict, float, float, List[Dict]):
        if not candidates:
            return {}, 0.0, 0.0, []

        length_map: Dict[str, float] = {}
        segments: List[Dict] = []
        max_distance_seen = 0.0
        step = max(0.25, sample_spacing)
        traversed = 0.0

        current_label: Optional[str] = None
        current_candidate: Optional[Dict] = None
        current_start = 0.0

        def finalize_segment(end_distance: float):
            nonlocal current_label, current_candidate, current_start
            if current_label is None or current_candidate is None:
                return

            segment_length = end_distance - current_start
            if segment_length <= 1e-6:
                return

            coords = sample_polyline(current_start, end_distance)
            if len(coords) < 2:
                return

            segments.append({
                'label': current_label,
                'type': current_candidate.get('type'),
                'column_index': current_candidate.get('column_index'),
                'wall_index': current_candidate.get('wall_index'),
                'length': segment_length,
                'start_distance': current_start,
                'end_distance': end_distance,
                'polyline_points': coords,
            })

        while traversed < perimeter - 1e-8:
            next_distance = min(traversed + step, perimeter)
            segment_length = next_distance - traversed
            midpoint = traversed + segment_length / 2.0

            try:
                boundary_point = boundary_line.interpolate(midpoint, normalized=False)
            except Exception:
                traversed = next_distance
                continue

            best_label = None
            best_candidate = None
            best_distance = None

            for candidate in candidates:
                try:
                    candidate_distance = candidate['geom'].distance(boundary_point)
                except Exception:
                    continue

                if best_distance is None or candidate_distance < best_distance:
                    best_distance = candidate_distance
                    best_label = candidate['label']
                    best_candidate = candidate

            if best_label is not None and best_candidate is not None:
                length_map[best_label] = length_map.get(best_label, 0.0) + segment_length
                if best_distance is not None and best_distance > max_distance_seen:
                    max_distance_seen = best_distance

                if current_label != best_label:
                    finalize_segment(traversed)
                    current_label = best_label
                    current_candidate = best_candidate
                    current_start = traversed
            else:
                finalize_segment(traversed)
                current_label = None
                current_candidate = None

            traversed = next_distance

        finalize_segment(perimeter)
        assigned_total = sum(length_map.values())
        return length_map, assigned_total, max_distance_seen, segments

    threshold = distance_threshold
    while threshold <= max_distance + 1e-9:
        candidates = build_candidates(threshold)
        if not candidates:
            threshold += distance_step
            continue

        length_map, assigned_total, max_distance_seen, segments = assign_segments(candidates)
        coverage_ratio = (assigned_total / perimeter) if perimeter > 1e-9 else 0.0

        return {
            'length_map': length_map,
            'segments': segments,
            'perimeter': perimeter,
            'assigned_total': assigned_total,
            'coverage_ratio': coverage_ratio,
            'threshold_used': threshold,
            'candidate_count': len(candidates),
            'max_distance_seen': max_distance_seen,
        }

    # No candidates even at max distance
    return _empty_result(max_distance, perimeter)


def _empty_result(threshold: float, perimeter: float) -> Dict:
    return {
        'length_map': {},
        'segments': [],
        'perimeter': perimeter,
        'assigned_total': 0.0,
        'coverage_ratio': 0.0,
        'threshold_used': threshold,
        'candidate_count': 0,
        'max_distance_seen': 0.0,
    }
