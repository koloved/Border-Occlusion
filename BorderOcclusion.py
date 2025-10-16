import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import BoolProperty, EnumProperty
import rna_keymap_ui
import bmesh
from mathutils import Vector

bl_info = {
    "name": "BorderOcclusion",
    "location": "View3D > Add > Object > Border Occlusion",
    "description": "Drag mouse for selection back and front faces by border",
    "author": "Vladislav Kindushov",
    "version": (0, 6, 4),
    "blender": (4, 5, 0),
    "category": "3D View",
}

addon_keymaps = []


class VIEW3D_OT_BorderOcclusion(Operator):
    """Border Occlusion selection"""
    bl_idname = "view3d.border_occlusion"
    bl_label = "Border Occlusion"
    bl_options = {"REGISTER", "UNDO"}

    Deselect: BoolProperty(
        name="Deselect",
        description="",
        default=False,
    )
    
    Extend: BoolProperty(
        name="Extend",
        description="",
        default=False,
    )
    
    BackfaceOnly: BoolProperty(
        name="Backface Only",
        description="Select only vertices on backfaces",
        default=False,
    )

    # internal runtime storage
    _timer = None
    _space = None
    _area = None
    _prev_show_xray = None
    _running = False
    Select = False
    SelectMode = False

    @classmethod
    def poll(cls, context):
        return context.space_data and context.space_data.type == "VIEW_3D"

    def _force_xray_on(self):
        # Safely enforce X-Ray only for the invoking space
        if self._space and hasattr(self._space, "shading"):
            self._space.shading.show_xray = True  # scoped to this View3D space[web:34]

    def _restore_xray(self):
        if self._space and self._prev_show_xray is not None:
            self._space.shading.show_xray = self._prev_show_xray  # restore original state[web:34]

    def filter_backface_selection(self, context):
        """Keep only vertices/edges/faces that belong to backfaces"""
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return

        rv3d = context.region_data
        view_rot = rv3d.view_rotation
        view_direction = view_rot @ Vector((0.0, 0.0, -1.0))

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        if bm.edges:
            bm.edges.ensure_lookup_table()

        world_matrix = obj.matrix_world
        normal_matrix = world_matrix.to_3x3().inverted().transposed()

        backface_faces = set()
        backface_edges = set()
        backface_verts = set()

        for face in bm.faces:
            world_normal = (normal_matrix @ face.normal).normalized()
            if world_normal.dot(view_direction) > 0.0:
                backface_faces.add(face.index)
                for e in face.edges:
                    backface_edges.add(e.index)
                for v in face.verts:
                    backface_verts.add(v.index)

        # Deselect anything not on backfaces
        for f in bm.faces:
            if f.select and f.index not in backface_faces:
                f.select = False
        for e in bm.edges:
            if e.select and e.index not in backface_edges:
                e.select = False
        for v in bm.verts:
            if v.select and v.index not in backface_verts:
                v.select = False

        # Keep selection consistent across modes
        bm.select_flush_mode()  # sync selection to active mode[web:57]
        bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

    def modal(self, context, event):
        # Keep X-Ray pinned while this operator runs
        if event.type == 'TIMER' and self._running:
            self._force_xray_on()  # periodic enforcement to avoid other handlers toggling it[web:103][web:100]
            return {'RUNNING_MODAL'}

        # Kick off Blender's selection operator once
        if not self.Select:
            self.Select = True
            if self.Deselect:
                if self.SelectMode:
                    bpy.ops.view3d.select_lasso('INVOKE_DEFAULT', mode='SUB')
                else:
                    bpy.ops.view3d.select_box('INVOKE_DEFAULT', wait_for_input=False, mode='SUB')
            elif self.Extend:
                if self.SelectMode:
                    bpy.ops.view3d.select_lasso('INVOKE_DEFAULT', mode='ADD')
                else:
                    bpy.ops.view3d.select_box('INVOKE_DEFAULT', wait_for_input=False, mode='ADD')
            else:
                if self.SelectMode:
                    bpy.ops.view3d.select_lasso('INVOKE_DEFAULT', mode='SET')
                else:
                    bpy.ops.view3d.select_box('INVOKE_DEFAULT', wait_for_input=False, mode='SET')
            return {'RUNNING_MODAL'}

        # Finish on RMB release or ESC, and also when Blender stops sending repeats
        if (event.type in {'RIGHTMOUSE', 'ESC'} and event.value in {'RELEASE', 'PRESS'}) or (not event.is_repeat and self.Select):
            # Apply backface filtering if requested
            if self.BackfaceOnly:
                self.filter_backface_selection(context)  # post-filter selected elements[web:57]
            self._running = False
            self._restore_xray()  # restore original X-Ray state[web:34]
            # clean timer
            wm = context.window_manager
            if self._timer is not None:
                wm.event_timer_remove(self._timer)  # stop periodic enforcement[web:103]
                self._timer = None
            # reset flags
            self.Extend = False
            self.Deselect = False
            self.BackfaceOnly = False
            return {'FINISHED'}

        # Let other handlers (like Screencast Keys) receive events while we keep re-enabling X-Ray via timer
        return {'PASS_THROUGH'}  # cooperative modal; timer keeps X-Ray pinned[web:103][web:106]

    def invoke(self, context, event):
        # Scope to the invoking View3D space
        self._area = context.area
        self._space = context.space_data
        self._prev_show_xray = self._space.shading.show_xray  # remember original state[web:34]
        self._force_xray_on()  # enable X-Ray immediately[web:34]

        # Start a frequent timer to keep X-Ray enabled during the operator (fights external toggles)
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.05, window=context.window)  # 20 Hz keep-alive[web:103]
        self._running = True

        self.Select = False
        self.SelectMode = not context.scene.border_occlude_mode
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def add_hotkey(prop=None, prop_value=None, shift=False, ctrl=False, alt=False):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            'view3d.border_occlusion', 'RIGHTMOUSE', 'CLICK_DRAG',
            shift=shift, ctrl=ctrl, alt=alt, head=True
        )
        if prop is not None:
            kmi.properties[prop] = prop_value
        global addon_keymaps
        addon_keymaps.append((km, kmi))


def FindConflict(box, item):
    ku = bpy.context.window_manager.keyconfigs.user
    km_names = ['3D View', '3D View Generic', 'Object Mode', 'Mesh', 'Curve', 'Armature']
    for km_n in km_names:
        if km_n in ku.keymaps:
            for i in ku.keymaps[km_n].keymap_items:
                if (item.type == i.type and item.ctrl == i.ctrl and
                    item.alt == i.alt and item.shift == i.shift and
                    item.name != i.name):
                    col = box.column()
                    col.label(text='Conflict hotkey: ' + '3D View -> ' + km_n + ' -> ' + i.name + " : ")
                    rna_keymap_ui.draw_kmi([], ku, ku.keymaps[km_n], i, box, 0)
                    return None


def SwapIcon(self, context):
    icon_pos = bpy.context.preferences.addons[__name__].preferences.IconPosition
    for cls, place in ((bpy.types.VIEW3D_HT_header, draw), (bpy.types.VIEW3D_MT_editor_menus, draw)):
        try:
            cls.remove(place)
        except:
            pass
    if icon_pos == "LEFT":
        bpy.types.VIEW3D_MT_editor_menus.append(draw)
    elif icon_pos == "RIGHT":
        bpy.types.VIEW3D_HT_header.append(draw)


class BorderOccludePref(AddonPreferences):
    bl_idname = __name__

    IconPosition: EnumProperty(
        name="Icon Position",
        description="",
        items=[
            ("LEFT", "Left", "", 1),
            ("RIGHT", "Right", "", 2),
            ("NONE", "None", "", 3)
        ],
        default="LEFT",
        update=SwapIcon
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.prop(self, 'IconPosition')
        HotkeyBox = layout.row().box()
        ConflictBox = layout.row().box()
        ConflictBox.label(text="Conflict:")

        ku = bpy.context.window_manager.keyconfigs.user
        km = ku.keymaps.get('3D View')
        if km:
            for i in km.keymap_items:
                if i.idname == "view3d.border_occlusion":
                    rna_keymap_ui.draw_kmi([], ku, km, i, HotkeyBox, 0)
                    FindConflict(ConflictBox, i)


def draw(self, context):
    layout = self.layout
    icon = 'MOD_DASH' if not bpy.context.scene.border_occlude_mode else 'SELECT_SET'
    layout.prop(bpy.context.scene, 'border_occlude_mode', icon=icon)


classes = (VIEW3D_OT_BorderOcclusion, BorderOccludePref)


def register():
    for i in classes:
        bpy.utils.register_class(i)
    bpy.types.Scene.border_occlude_mode = BoolProperty(name="", description="", default=False)
    # Ctrl+Alt+Shift+drag = Backface only selection
    add_hotkey(prop='BackfaceOnly', prop_value=True, shift=True, ctrl=True, alt=True)
    # Ctrl+drag = Extend selection
    add_hotkey(prop='Extend', prop_value=True, shift=False, ctrl=True, alt=False)
    # Ctrl+Shift+drag = Deselect
    add_hotkey(prop='Deselect', prop_value=True, shift=True, ctrl=True, alt=False)

    icon_pos = bpy.context.preferences.addons[__name__].preferences.IconPosition
    if icon_pos == "LEFT":
        bpy.types.VIEW3D_MT_editor_menus.append(draw)
    elif icon_pos == "RIGHT":
        bpy.types.VIEW3D_HT_header.append(draw)


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    try:
        bpy.types.VIEW3D_HT_header.remove(draw)
    except:
        pass
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw)
    except:
        pass
    for i in reversed(classes):
        bpy.utils.unregister_class(i)
    del bpy.types.Scene.border_occlude_mode


if __name__ == "__main__":
    register()
