from dataclasses import dataclass, replace


@dataclass(frozen=True)
class SnapCandidate:
    axis: str
    correction: float
    kind: str
    moving_anchor: str = ""
    target_anchor: str = ""
    references: tuple = ()
    placement: str = ""
    gap: float = 0.0


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
    return {"top": box.top, "bottom": box.bottom}


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


def _ranges_overlap(first_min, first_max, second_min, second_max):
    return min(first_max, second_max) > max(first_min, second_min)


def _horizontal_related(first, second):
    return _ranges_overlap(
        first.bottom,
        first.top,
        second.bottom,
        second.top,
    )


def _vertical_related(first, second):
    return _ranges_overlap(
        first.left,
        first.right,
        second.left,
        second.right,
    )


def _common_vertical_overlap(*boxes):
    bottom = max(box.bottom for box in boxes)
    top = min(box.top for box in boxes)
    return (bottom, top) if top > bottom else None


def _common_horizontal_overlap(*boxes):
    left = max(box.left for box in boxes)
    right = min(box.right for box in boxes)
    return (left, right) if right > left else None


def _horizontal_spacing_candidates(moving, targets):
    related = [target for target in targets if _horizontal_related(moving, target)]
    related.sort(key=lambda box: box.left)
    candidates = []
    for first, second in zip(related, related[1:]):
        if (
            first.right > second.left
            or not _horizontal_related(first, second)
            or _common_vertical_overlap(first, second, moving) is None
        ):
            continue
        existing_gap = second.left - first.right

        desired_left = (first.right + second.left - moving.width) / 2.0
        if desired_left >= first.right and desired_left + moving.width <= second.left:
            candidates.append(
                SnapCandidate(
                    "x",
                    desired_left - moving.left,
                    "spacing",
                    references=(first, second),
                    placement="between",
                    gap=desired_left - first.right,
                )
            )

        candidates.append(
            SnapCandidate(
                "x",
                second.right + existing_gap - moving.left,
                "spacing",
                references=(first, second),
                placement="after",
                gap=existing_gap,
            )
        )
        desired_left = first.left - existing_gap - moving.width
        candidates.append(
            SnapCandidate(
                "x",
                desired_left - moving.left,
                "spacing",
                references=(first, second),
                placement="before",
                gap=existing_gap,
            )
        )
    return candidates


def _vertical_spacing_candidates(moving, targets):
    related = [target for target in targets if _vertical_related(moving, target)]
    related.sort(key=lambda box: box.top, reverse=True)
    candidates = []
    for first, second in zip(related, related[1:]):
        if (
            first.bottom < second.top
            or not _vertical_related(first, second)
            or _common_horizontal_overlap(first, second, moving) is None
        ):
            continue
        existing_gap = first.bottom - second.top

        desired_top = (first.bottom + second.top + moving.height) / 2.0
        if desired_top <= first.bottom and desired_top - moving.height >= second.top:
            candidates.append(
                SnapCandidate(
                    "y",
                    desired_top - moving.top,
                    "spacing",
                    references=(first, second),
                    placement="between",
                    gap=first.bottom - desired_top,
                )
            )

        desired_top = second.bottom - existing_gap
        candidates.append(
            SnapCandidate(
                "y",
                desired_top - moving.top,
                "spacing",
                references=(first, second),
                placement="after",
                gap=existing_gap,
            )
        )
        desired_top = first.top + existing_gap + moving.height
        candidates.append(
            SnapCandidate(
                "y",
                desired_top - moving.top,
                "spacing",
                references=(first, second),
                placement="before",
                gap=existing_gap,
            )
        )
    return candidates


def _best_candidate(candidates, threshold):
    eligible = [candidate for candidate in candidates if abs(candidate.correction) <= threshold]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda candidate: (
            abs(candidate.correction),
            0 if candidate.kind == "alignment" else 1,
        ),
    )


def _with_collinear_references(candidate, targets):
    if candidate is None or candidate.kind != "alignment":
        return candidate
    if candidate.target_anchor.startswith("socket:"):
        return candidate
    anchors = _x_anchors if candidate.axis == "x" else _y_anchors
    moving_anchor_value = anchors(candidate.references[0])[candidate.target_anchor]
    references = tuple(
        target
        for target in targets
        if candidate.target_anchor in anchors(target)
        and abs(anchors(target)[candidate.target_anchor] - moving_anchor_value) <= 0.001
    )
    return replace(candidate, references=references)


def find_snaps(
    moving,
    targets,
    threshold_x,
    threshold_y,
    equal_spacing=True,
    axis_constraint=None,
):
    x_candidate = None
    y_candidate = None
    if axis_constraint != "y":
        x_candidates = _alignment_candidates(moving, targets, "x")
        if equal_spacing:
            x_candidates.extend(
                _horizontal_spacing_candidates(moving, targets)
            )
        x_candidate = _best_candidate(x_candidates, threshold_x)
        x_candidate = _with_collinear_references(x_candidate, targets)
    if axis_constraint != "x":
        y_candidates = _alignment_candidates(moving, targets, "y")
        if equal_spacing:
            y_candidates.extend(
                _vertical_spacing_candidates(moving, targets)
            )
        y_candidate = _best_candidate(y_candidates, threshold_y)
        y_candidate = _with_collinear_references(y_candidate, targets)
    return SnapResult(
        x_candidate.correction if x_candidate else 0.0,
        y_candidate.correction if y_candidate else 0.0,
        x_candidate,
        y_candidate,
    )


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


def _spacing_sequence(candidate, moving):
    first, second = candidate.references
    if candidate.placement == "between":
        return first, moving, second
    if candidate.placement == "after":
        return first, second, moving
    return moving, first, second


def _spacing_guides(candidate, moving):
    first, second, third = _spacing_sequence(candidate, moving)
    boxes = (first, second, third)
    segments = []
    if candidate.axis == "x":
        overlap = _common_vertical_overlap(*boxes)
        if overlap is None:
            return segments
        y = (overlap[0] + overlap[1]) / 2.0
        pairs = ((first.right, second.left), (second.right, third.left))
        for start, end in pairs:
            segments.append(GuideSegment((start, y), (end, y), "spacing"))
            segments.append(
                GuideSegment((start, y - 3.0), (start, y + 3.0), "spacing", False)
            )
            segments.append(
                GuideSegment((end, y - 3.0), (end, y + 3.0), "spacing", False)
            )
        return segments

    overlap = _common_horizontal_overlap(*boxes)
    if overlap is None:
        return segments
    x = (overlap[0] + overlap[1]) / 2.0
    pairs = ((first.bottom, second.top), (second.bottom, third.top))
    for start, end in pairs:
        segments.append(GuideSegment((x, start), (x, end), "spacing"))
        segments.append(
            GuideSegment((x - 3.0, start), (x + 3.0, start), "spacing", False)
        )
        segments.append(
            GuideSegment((x - 3.0, end), (x + 3.0, end), "spacing", False)
        )
    return segments


def guide_segments(result, moving):
    segments = []
    for candidate in (result.x_candidate, result.y_candidate):
        if candidate is None:
            continue
        if candidate.kind == "alignment":
            segments.extend(_alignment_guides(candidate, moving))
        else:
            segments.extend(_spacing_guides(candidate, moving))
    return segments
