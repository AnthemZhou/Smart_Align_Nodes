"""One undo transaction, with bounded redraw/recheck for auto-sized Frames."""
from time import perf_counter
from dataclasses import replace
import bpy

from .context import selected_nodes_from_context
from .geometry import union_boxes
from .layout import (LayoutSettings, solve_layout, layout_diagnostics,
                     geometry_matches_plan, frame_redraw_tolerance)
from .layout_adapter import (capture_layout, capture_restore_state, restore_state,
                             apply_locations, format_layout_report)
from .preferences import get_preferences
from .translations import translate
from .layout_routing import plan_internal_routes
from .layout_route_adapter import RouteTransaction


class SMART_ALIGN_NODES_OT_auto_layout(bpy.types.Operator):
    bl_idname = "smart_align_nodes.auto_layout"
    bl_label = "Arrange Selected Nodes"
    bl_description = "Arrange selected nodes and all contents of selected Frames using socket and boundary alignment"
    bl_options = {"REGISTER", "UNDO"}
    _timer = None

    @classmethod
    def poll(cls, context):
        if getattr(getattr(context, "area", None), "type", None) != "NODE_EDITOR":
            return False
        tree, nodes = selected_nodes_from_context(context)
        return tree is not None and bool(nodes) and getattr(tree, "is_editable", True)

    def _begin(self, context):
        self._routing = None
        self._route_transactions = []
        self._tree, _selected = selected_nodes_from_context(context)
        if self._tree is None or not getattr(self._tree, "is_editable", True):
            raise ValueError("An editable node tree is required.")
        self._restore = capture_restore_state(self._tree)
        self._started = perf_counter()
        self._snapshot, self._links, self._metadata = capture_layout(self._tree)
        selected_boxes = [n.box for n in self._snapshot if n.selected]
        if not selected_boxes:
            raise ValueError("Select nodes to arrange.")
        bounds = union_boxes(selected_boxes)
        self._anchor = (bounds.left, bounds.top)
        prefs = get_preferences(context)
        self._settings = LayoutSettings(
            avoid_fixed=getattr(prefs, "layout_avoid_fixed", True),
            horizontal_gap=getattr(prefs, "layout_horizontal_gap", 100),
        )
        self._metadata['horizontal_gap'] = self._settings.horizontal_gap
        self._plan = solve_layout(self._snapshot, self._links, self._settings, self._anchor)
        self._routing_snapshot, self._routing_links = self._snapshot, self._links
        self._verification_links = self._links
        self._metadata['solve_calls'] = 1
        self._metadata['solve_total_ms'] = self._plan.metrics['solve_ms']
        self._passes = 0
        self._area = context.area
        self._apply()

    def _apply(self):
        # Finish route planning before exposing any new positions. Apply cards
        # and reroutes in the same event, then allow Blender to draw both.
        routing_started = perf_counter()
        routing_stats = {}
        preserved = {key for result in self._plan.partial_results if result['method'] == 'preserved'
                     for key in result['nodes']}
        routing_selected = {n.key for n in self._snapshot
                            if n.selected and not n.protected and n.key not in preserved}
        if "Cycle or unverified zone: preserved connected component internally." in self._plan.warnings:
            routing_selected.clear()
        routing_snapshot = [replace(n, selected=n.key in routing_selected) for n in self._routing_snapshot]
        routes = plan_internal_routes(routing_snapshot, self._routing_links, self._plan.boxes, stats=routing_stats)
        self._metadata['routing_plan_ms'] = self._metadata.get('routing_plan_ms', 0) + (perf_counter()-routing_started)*1000
        started = perf_counter()
        written = apply_locations(self._tree, self._plan.locations)
        self._metadata['location_writes'] = self._metadata.get('location_writes',0)+written
        self._metadata["write_ms"] = self._metadata.get("write_ms", 0) + (perf_counter()-started)*1000
        self._routing = RouteTransaction(self._tree, routes, routing_selected)
        # Register before apply so an exception midway through link creation
        # still rolls back this pass, followed by any earlier correction passes.
        self._route_transactions.append(self._routing)
        self._routing.apply()
        self._metadata['wire_routes'] = self._routing.plans
        self._metadata['routing_search'] = routing_stats
        self._metadata['routing_passes'] = len(self._route_transactions)
        self._metadata['routing_applied_before_redraw'] = True
        self._metadata['routing_link_writes'] = sum(t.link_writes for t in self._route_transactions)
        self._area.tag_redraw()
        self._last_apply = perf_counter()

    def execute(self, context):
        # EXEC_DEFAULT cannot wait for a draw; explicitly reject Frame transactions.
        tree, nodes = selected_nodes_from_context(context)
        if tree and any(n.type == "FRAME" or n.parent is not None for n in nodes):
            self.report({"WARNING"}, translate("Frame layouts require interactive invocation for redraw verification."))
            return {"CANCELLED"}
        try:
            self._begin(context)
            return self._finish(context)
        except Exception as error:
            return self._fail(context, error)

    def invoke(self, context, event):
        try:
            self._begin(context)
            # All invocations get a redraw verification, including plain nodes.
            self._timer = context.window_manager.event_timer_add(0.08, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}
        except Exception as error:
            return self._fail(context, error)

    def modal(self, context, event):
        if event.type in {"ESC", "RIGHTMOUSE", "WINDOW_DEACTIVATE"} or context.area != self._area:
            return self._fail(context, "Layout cancelled.")
        # Blender 5.1 Event exposes no timer identity. Ignore early events from
        # other modal timers and allow a redraw between correction passes.
        if event.type != "TIMER" or perf_counter() - self._last_apply < 0.06:
            return {"RUNNING_MODAL"}
        try:
            self._passes += 1
            snapshot, links, _metadata = capture_layout(self._tree)
            self._metadata['verification_snapshot_ms'] = self._metadata.get('verification_snapshot_ms',0)+_metadata['snapshot_ms']
            geometry_scale = _metadata['geometry_scale']
            self._metadata['frame_redraw_tolerance'] = frame_redraw_tolerance(geometry_scale)
            if geometry_matches_plan(snapshot, links, self._plan, self._verification_links,
                                     geometry_scale=geometry_scale):
                self._plan.boxes = {n.key: n.box for n in snapshot}
                self._plan.locations = {n.key: n.location for n in snapshot}
                self._metadata['verified_after_redraw'] = True
                self._metadata['verification_reused_plan'] = True
                return self._finish(context)
            plan = solve_layout(snapshot, links, self._settings, self._anchor)
            self._routing_snapshot, self._routing_links = snapshot, links
            self._verification_links = links
            self._metadata['solve_calls'] += 1
            self._metadata['solve_total_ms'] += plan.metrics['solve_ms']
            # Compare actual locations against the freshly solved absolute targets.
            delta = max((max(abs(n.location[i]-plan.locations[n.key][i]) for i in (0, 1))
                         for n in snapshot), default=0)
            if delta <= 0.1:
                self._plan.warnings = list(dict.fromkeys(self._plan.warnings + plan.warnings))
                self._plan.boxes = {n.key: n.box for n in snapshot}
                self._plan.locations = {n.key: n.location for n in snapshot}
                self._metadata["verified_after_redraw"] = True
                self._apply()
                return self._finish(context)
            if self._passes >= 4:
                return self._fail(context, "Frame geometry did not stabilize within 4 redraws; restored original layout.")
            self._plan = plan
            self._apply()
            return {"RUNNING_MODAL"}
        except Exception as error:
            return self._fail(context, error)

    def _remove_timer(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def _finish(self, context):
        self._remove_timer(context)
        self._metadata["redraw_passes"] = self._passes
        self._metadata["total_ms"] = (perf_counter()-self._started)*1000
        self._plan.metrics["moved"] = sum(
            any(abs(self._plan.locations[n.key][i] - n.location[i]) > 0.1 for i in (0, 1))
            for n in self._snapshot
        )
        diagnostic_started = perf_counter()
        created = {name for t in self._route_transactions for name in t.created}
        removed = {name for t in self._route_transactions for name in t.removed}
        self._plan.metrics['generated_reroutes'] = sum(
            name in self._tree.nodes and name not in self._restore for name in created)
        self._plan.metrics['reused_reroutes'] = self._routing.reused
        self._plan.metrics['removed_auto_reroutes'] = sum(
            name in self._restore and name not in self._tree.nodes for name in removed)
        self._plan.metrics['selected'] += len(self._metadata['reusable_reroutes'])
        self._plan.metrics['moved'] += sum(
            any(abs(self._tree.nodes[key].location_absolute[i]-self._restore[key]['absolute'][i]) > .1
                for i in (0,1)) for key in self._metadata['reusable_reroutes'])
        self._plan.metrics.update(layout_diagnostics(self._snapshot, self._links, self._plan.boxes,
                                                    routes=self._routing.plans))
        self._metadata["diagnostic_ms"] = (perf_counter()-diagnostic_started)*1000
        if self._plan.metrics["estimated_wire_node_hits"]:
            self._plan.warnings.append("Internal selection wires may still be obstructed; see Smart Align Layout Debug.")
        if self._plan.metrics["node_overlaps"]:
            self._plan.warnings.append("Residual node overlaps remain in preserved or fixed content; see debug report.")
        self._metadata["total_ms"] = (perf_counter()-self._started)*1000
        report = format_layout_report(self._snapshot, self._links, self._plan, self._metadata)
        text = bpy.data.texts.get("Smart Align Layout Debug") or bpy.data.texts.new("Smart Align Layout Debug")
        text.clear()
        text.write(report)
        self._area.tag_redraw()
        if self._plan.warnings:
            self.report({"WARNING"}, " ".join(translate(message) for message in self._plan.warnings))
        elif self._plan.metrics.get("partial_scopes") and not self._plan.metrics["moved"]:
            self.report({"INFO"}, translate("Layout checked; current positions were preserved."))
        else:
            self.report({"INFO"}, translate("Arranged {count} nodes; socket positions are estimates.").format(
                count=self._plan.metrics['selected']))
        return {"FINISHED"}

    def _fail(self, context, error):
        self._remove_timer(context)
        rollback_error = None
        for transaction in reversed(getattr(self, '_route_transactions', [])):
            try:
                transaction.rollback()
            except Exception as failure:
                rollback_error = failure
        if hasattr(self, "_restore"):
            try:
                restore_state(self._tree, self._restore)
                self._area.tag_redraw() if hasattr(self, "_area") else None
            except Exception as failure:
                rollback_error = failure
        message = translate(str(error))
        if rollback_error:
            message += " " + translate("Rollback incomplete: {error}").format(error=rollback_error)
        self.report({"WARNING"}, message)
        return {"CANCELLED"}

    def cancel(self, context):
        self._fail(context, "Layout cancelled.")
