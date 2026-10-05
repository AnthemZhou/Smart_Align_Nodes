from dataclasses import dataclass, replace
from itertools import product


@dataclass(frozen=True)
class SnapCandidate:
    axis: str
    correction: float
    kind: str
    moving_anchor: str = ""
    target_anchor: str = ""
    references: tuple = ()


@dataclass(frozen=True)
class SnapResult:
    correction_x: float = 0.0
    correction_y: float = 0.0
    x_candidate: SnapCandidate = None
    y_candidate: SnapCandidate = None


@dataclass(frozen=True)
class GuideSegment:
    start: tuple
    end: tuple
    kind: str
    fade: bool = True


def _x_anchors(box):
    if box.is_reroute:
        return {"center": box.center_x}
    return {"left": box.left, "right": box.right}


def _y_anchors(box):
    if box.is_reroute:
        return {"middle": box.center_y}
    return {"top": box.top}


def _alignment_candidates(moving, targets, axis):
    moving_anchors = _x_anchors(moving) if axis == "x" else _y_anchors(moving)
    candidates = []
    for target in targets:
        if axis == "y" and moving.is_reroute and not target.is_reroute:
            for anchor, target_value in target.socket_ys:
                candidates.append(
                    SnapCandidate(
                        axis="y",
                        correction=target_value - moving.center_y,
                        kind="alignment",
                        moving_anchor="middle",
                        target_anchor=anchor,
                        references=(target,),
                    )
                )
        target_anchors = _x_anchors(target) if axis == "x" else _y_anchors(target)
        for anchor, moving_value in moving_anchors.items():
            if anchor not in target_anchors:
                continue
            candidates.append(
                SnapCandidate(
                    axis=axis,
                    correction=target_anchors[anchor] - moving_value,
                    kind="alignment",
                    moving_anchor=anchor,
                    target_anchor=anchor,
                    references=(target,),
                )
            )
    return candidates


def _nearest_alignments(candidates, threshold, limit=4):
    eligible = [
        candidate
        for candidate in candidates
        if abs(candidate.correction) <= threshold
    ]
    eligible.sort(key=lambda candidate: abs(candidate.correction))
    return eligible[:limit]


def _grid_axis_candidates(moving, axis, grid_size):
    if not grid_size or grid_size <= 0.0:
        return []
    if axis == "x":
        anchor = moving.center_x if moving.is_reroute else moving.left
        anchor_name = "center" if moving.is_reroute else "left"
    else:
        anchor = moving.center_y if moving.is_reroute else moving.top
        anchor_name = "middle" if moving.is_reroute else "top"
    nearest_index = round(anchor / grid_size)
    candidates = []
    for index in (nearest_index, nearest_index - 1, nearest_index + 1):
        target = index * grid_size
        candidates.append(
            SnapCandidate(
                axis=axis,
                correction=target - anchor,
                kind="grid",
                moving_anchor=anchor_name,
                target_anchor="grid",
            )
        )
    candidates.sort(key=lambda candidate: abs(candidate.correction))
    return candidates


def boxes_overlap(first, second):
    return (
        min(first.right, second.right) > max(first.left, second.left)
        and min(first.top, second.top) > max(first.bottom, second.bottom)
    )


def _placement_is_free(
    moving,
    targets,
    correction_x,
    correction_y,
    candidates=(),
):
    placed = moving.translated(correction_x, correction_y)
    socket_target_ids = {
        id(target)
        for candidate in candidates
        if candidate is not None and candidate.target_anchor.startswith("socket:")
        for target in candidate.references
    }
    return not any(
        boxes_overlap(placed, target)
        for target in targets
        if not target.is_frame and id(target) not in socket_target_ids
    )


def _with_collinear_references(candidate, targets):
    if candidate is None or candidate.kind != "alignment":
        return candidate
    if candidate.target_anchor.startswith("socket:"):
        return candidate
    anchors = _x_anchors if candidate.axis == "x" else _y_anchors
    target_value = anchors(candidate.references[0])[candidate.target_anchor]
    references = tuple(
        target
        for target in targets
        if candidate.target_anchor in anchors(target)
        and abs(anchors(target)[candidate.target_anchor] - target_value) <= 0.001
    )
    return replace(candidate, references=references)


def _choice_rank(choice):
    x_candidate, y_candidate = choice
    candidates = tuple(
        candidate for candidate in (x_candidate, y_candidate) if candidate is not None
    )
    alignment_count = sum(candidate.kind == "alignment" for candidate in candidates)
    missing_count = 2 - len(candidates)
    correction = sum(abs(candidate.correction) for candidate in candidates)
    return (-alignment_count, missing_count, correction)


def find_snaps(
    moving,
    targets,
    threshold_x,
    threshold_y,
    axis_constraint=None,
    grid_size=None,
):
    if axis_constraint == "y":
        x_choices = [None]
    else:
        x_choices = _nearest_alignments(
            _alignment_candidates(moving, targets, "x"),
            threshold_x,
        )
        x_choices.extend(_grid_axis_candidates(moving, "x", grid_size))
        x_choices.append(None)

    if axis_constraint == "x":
        y_choices = [None]
    else:
        y_choices = _nearest_alignments(
            _alignment_candidates(moving, targets, "y"),
            threshold_y,
        )
        y_choices.extend(_grid_axis_candidates(moving, "y", grid_size))
        y_choices.append(None)

    choices = sorted(product(x_choices, y_choices), key=_choice_rank)
    for x_candidate, y_candidate in choices:
        correction_x = x_candidate.correction if x_candidate else 0.0
        correction_y = y_candidate.correction if y_candidate else 0.0
        if x_candidate is None and y_candidate is None:
            break
        if not _placement_is_free(
            moving,
            targets,
            correction_x,
            correction_y,
            (x_candidate, y_candidate),
        ):
            continue
        return SnapResult(
            correction_x,
            correction_y,
            _with_collinear_references(x_candidate, targets),
            _with_collinear_references(y_candidate, targets),
        )
    return SnapResult()


def _alignment_guides(candidate, moving):
    targets = candidate.references
    target = targets[0]
    boxes = (moving, *targets)
    if candidate.axis == "x":
        x = _x_anchors(target)[candidate.target_anchor]
        return [
            GuideSegment(
                (x, min(box.bottom for box in boxes) - 8.0),
                (x, max(box.top for box in boxes) + 8.0),
                "alignment",
            )
        ]
    if candidate.target_anchor.startswith("socket:"):
        y = dict(target.socket_ys)[candidate.target_anchor]
    else:
        y = _y_anchors(target)[candidate.target_anchor]
    return [
        GuideSegment(
            (min(box.left for box in boxes) - 8.0, y),
            (max(box.right for box in boxes) + 8.0, y),
            "alignment",
        )
    ]


def _grid_guides(candidate, moving):
    if candidate.axis == "x":
        x = _x_anchors(moving)[candidate.moving_anchor]
        return [
            GuideSegment(
                (x, moving.bottom - 12.0),
                (x, moving.top + 12.0),
                "grid",
            )
        ]
    y = _y_anchors(moving)[candidate.moving_anchor]
    return [
        GuideSegment(
            (moving.left - 12.0, y),
            (moving.right + 12.0, y),
            "grid",
        )
    ]


def guide_segments(result, moving):
    segments = []
    for candidate in (result.x_candidate, result.y_candidate):
        if candidate is None:
            continue
        if candidate.kind == "alignment":
            segments.extend(_alignment_guides(candidate, moving))
        elif candidate.kind == "grid":
            segments.extend(_grid_guides(candidate, moving))
    return segments
