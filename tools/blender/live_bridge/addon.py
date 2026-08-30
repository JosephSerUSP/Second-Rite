"""Blender add-on entry point for the Thestra Live Bridge."""

from __future__ import annotations

import secrets
import time
import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty, IntProperty, StringProperty

from .server import LiveBridgeServer, register_operator, unregister_operator

_server = None
_last_status = ""


def _stop_server():
    global _server
    if _server:
        _server.stop(); _server = None


def _running():
    return bool(_server and _server.running)


@persistent
def _bridge_file_reload(*_args):
    _stop_server()


@persistent
def _bridge_blender_exit(*_args):
    _stop_server()


class ThestraBridgePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    port: IntProperty(name="Port", default=8765, min=1024, max=65535)
    token: StringProperty(name="Session token", default="", subtype="PASSWORD", options={"SKIP_SAVE"})
    def draw(self, context):
        self.layout.prop(self, "port"); self.layout.prop(self, "token")


class THESTRA_OT_bridge_start(bpy.types.Operator):
    bl_idname = "thestra.bridge_start"; bl_label = "Start Bridge"
    def execute(self, context):
        global _server, _last_status
        _stop_server()
        prefs = context.preferences.addons[__package__].preferences
        # A token is a per-session capability, never a reusable Blender-file
        # credential. Rotate it on every start (and expose an explicit rotate
        # button for an already-running session).
        prefs.token = secrets.token_urlsafe(24)
        try:
            _server = LiveBridgeServer(prefs.token, prefs.port); _server.start()
        except Exception as exc:
            prefs.token = ""; _last_status = str(exc)
            self.report({"ERROR"}, str(exc)); return {"CANCELLED"}
        _last_status = "Bridge started"
        self.report({"INFO"}, f"Bridge on 127.0.0.1:{_server.port}; use the Copy Token button")
        return {"FINISHED"}


class THESTRA_OT_bridge_stop(bpy.types.Operator):
    bl_idname = "thestra.bridge_stop"; bl_label = "Stop Bridge"
    def execute(self, _context):
        global _last_status
        _stop_server(); _last_status = "Bridge stopped"
        return {"FINISHED"}


class THESTRA_OT_bridge_rotate_token(bpy.types.Operator):
    bl_idname = "thestra.bridge_rotate_token"; bl_label = "Rotate Token"
    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        prefs.token = secrets.token_urlsafe(24)
        if _running(): _server.token = prefs.token
        self.report({"INFO"}, "Token rotated; existing clients must reconnect")
        return {"FINISHED"}


class THESTRA_OT_bridge_copy_token(bpy.types.Operator):
    bl_idname = "thestra.bridge_copy_token"; bl_label = "Copy Token"
    bl_description = "Copy the ephemeral bridge token to the clipboard"
    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        if not _running() or not prefs.token:
            self.report({"ERROR"}, "Start the bridge first")
            return {"CANCELLED"}
        context.window_manager.clipboard = prefs.token
        self.report({"INFO"}, "Session token copied")
        return {"FINISHED"}


class THESTRA_OT_bridge_share_context(bpy.types.Operator):
    bl_idname = "thestra.bridge_share_context"; bl_label = "Share Context"
    def execute(self, _context):
        global _last_status
        if not _running(): self.report({"ERROR"}, "Start the bridge first"); return {"CANCELLED"}
        from .server import _read
        try: result = _read("share_context", {})
        except Exception as exc:
            _last_status = str(exc); self.report({"ERROR"}, str(exc)); return {"CANCELLED"}
        _last_status = result["path"]
        self.report({"INFO"}, "Context shared for the external agent")
        return {"FINISHED"}


class THESTRA_OT_bridge_capture(bpy.types.Operator):
    bl_idname = "thestra.bridge_capture"; bl_label = "Capture Shared View"
    kind: EnumProperty(items=(("viewport", "Viewport", ""), ("selection", "Selection", ""), ("camera", "Game Camera", "")))
    def execute(self, _context):
        global _last_status
        if not _running(): self.report({"ERROR"}, "Start the bridge first"); return {"CANCELLED"}
        from .server import _read
        try:
            result = _read("capture_game_camera" if self.kind == "camera" else
                           "capture_selection" if self.kind == "selection" else "capture_viewport",
                           {"filename": f"shared-{self.kind}-{int(time.time() * 1000)}.png"})
        except Exception as exc:
            _last_status = str(exc)
            self.report({"ERROR"}, str(exc)); return {"CANCELLED"}
        _last_status = result["path"]
        self.report({"INFO"}, f"Captured {result['path']}")
        return {"FINISHED"}


def _context_summary_for_panel():
    from .server import _context_summary
    return _context_summary()


class THESTRA_PT_live_bridge(bpy.types.Panel):
    bl_label = "Thestra Live Bridge"; bl_idname = "THESTRA_PT_live_bridge"
    bl_space_type = "VIEW_3D"; bl_region_type = "UI"; bl_category = "Thestra"
    def draw(self, context):
        layout = self.layout
        running = _running()
        layout.label(text="Running" if running else "Stopped", icon="LINKED" if running else "UNLINKED")
        layout.operator("thestra.bridge_stop" if running else "thestra.bridge_start")
        if running:
            layout.label(text=f"Port: {_server.port}")
            layout.label(text=f"Session: {_server.session_id}")
            row = layout.row(align=True)
            row.operator("thestra.bridge_copy_token")
            row.operator("thestra.bridge_rotate_token")
            layout.operator("thestra.bridge_share_context")
            row = layout.row(align=True)
            for kind, label in (("viewport", "Viewport"), ("selection", "Selection"), ("camera", "Game")):
                op = row.operator("thestra.bridge_capture", text=label); op.kind = kind
            if _server.latest_share:
                layout.label(text=f"Latest: {str(_server.latest_share.get('path', ''))[-48:]}")
        if _last_status:
            layout.label(text=_last_status[-80:])
        obj = context.active_object
        layout.label(text=f"Active: {obj.name if obj else 'None'}")
        layout.label(text=f"Material: {obj.active_material.name if obj and obj.active_material else 'None'}")
        layout.label(text="File has unsaved changes" if bpy.data.is_dirty else "File unchanged",
                     icon="ERROR" if bpy.data.is_dirty else "CHECKMARK")


_CLASSES = (ThestraBridgePreferences, THESTRA_OT_bridge_start, THESTRA_OT_bridge_stop,
            THESTRA_OT_bridge_rotate_token, THESTRA_OT_bridge_copy_token,
            THESTRA_OT_bridge_share_context,
            THESTRA_OT_bridge_capture, THESTRA_PT_live_bridge)
def register():
    register_operator()
    for cls in _CLASSES: bpy.utils.register_class(cls)
    if _bridge_file_reload not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(_bridge_file_reload)
    quit_pre = getattr(bpy.app.handlers, "quit_pre", None)
    if quit_pre is not None and _bridge_blender_exit not in quit_pre:
        quit_pre.append(_bridge_blender_exit)
def unregister():
    _stop_server()
    if _bridge_file_reload in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_bridge_file_reload)
    quit_pre = getattr(bpy.app.handlers, "quit_pre", None)
    if quit_pre is not None and _bridge_blender_exit in quit_pre:
        quit_pre.remove(_bridge_blender_exit)
    for cls in reversed(_CLASSES): bpy.utils.unregister_class(cls)
    unregister_operator()
