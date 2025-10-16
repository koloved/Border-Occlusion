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
    "version": (0, 6, 3),
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

    @classmethod
    def poll(cls, context):
        return context.space_data.type == "VIEW_3D"

    def filter_backface_selection(self, context):
        """Keep only vertices/edges/faces that belong to backfaces"""
        obj = context.active_object
        
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return
        
        # Get view direction from region data
        rv3d = context.region_data
        
        # Get view direction in world space
        view_rot = rv3d.view_rotation
        view_direction = view_rot @ Vector((0.0, 0.0, -1.0))
        
        # Work with BMesh
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        # Ensure lookup tables are up to date
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        if bm.edges:
            bm.edges.ensure_lookup_table()
        
        # Get world matrix for transforming normals
        world_matrix = obj.matrix_world
        normal_matrix = world_matrix.to_3x3().inverted().transposed()
        
        # Find all backfaces and their components
        backface_indices = set()
        backface_verts = set()
        backface_edges = set()
        
        for face in bm.faces:
            # Transform face normal to world space
            world_normal = (normal_matrix @ face.normal).normalized()
            
            # Calculate dot product with view direction
            # Positive value means facing away from camera (backface)
            dot = world_normal.dot(view_direction)
            
            if dot > 0:  # This is a backface
                backface_indices.add(face.index)
                for vert in face.verts:
                    backface_verts.add(vert.index)
                for edge in face.edges:
                    backface_edges.add(edge.index)
        
        # First, deselect all non-backface components
        for face in bm.faces:
            if face.select and face.index not in backface_indices:
                face.select = False
        
        for edge in bm.edges:
            if edge.select and edge.index not in backface_edges:
                edge.select = False
        
        for vert in bm.verts:
            if vert.select and vert.index not in backface_verts:
                vert.select = False
        
        # Flush selection to prevent auto-selection of frontfaces
        # This ensures faces don't get auto-selected if all their verts are selected
        bm.select_flush_mode()
        
        # Update the mesh
        bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

    def modal(self, context, event):
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

        if not event.is_repeat and self.Select:
            # Restore xray setting
            context.space_data.shading.show_xray = self.show_xray
            
            # Apply backface filtering if requested
            if self.BackfaceOnly:
                self.filter_backface_selection(context)
            
            # Reset properties
            self.Extend = False
            self.Deselect = False
            self.BackfaceOnly = False
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.show_xray = context.space_data.shading.show_xray
        context.space_data.shading.show_xray = True
        self.Select = False
        self.SelectMode = not context.scene.border_occlude_mode
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def add_hotkey(prop=None, prop_value=None, shift=False, ctrl=False, alt=False):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new('view3d.border_occlusion', 'RIGHTMOUSE', 'CLICK_DRAG', 
                                   shift=shift, ctrl=ctrl, alt=alt, head=True)

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
    try:
        bpy.types.VIEW3D_HT_header.remove(draw)
    except:
        pass
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw)
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
    if not bpy.context.scene.border_occlude_mode:
        icon = 'MOD_DASH'
    else:
        icon = 'SELECT_SET'

    layout.prop(bpy.context.scene, 'border_occlude_mode', icon=icon)


classes = (VIEW3D_OT_BorderOcclusion, BorderOccludePref)


def register():
    for i in classes:
        bpy.utils.register_class(i)
    
    bpy.types.Scene.border_occlude_mode = BoolProperty(
        name="",
        description="",
        default=False,
    )
    
    # Ctrl+Alt+Shift+drag = Backface only selection
    add_hotkey(prop='BackfaceOnly', prop_value=True, shift=True, ctrl=True, alt=True)
    # Ctrl+drag = Extend selection
    add_hotkey(prop='Extend', prop_value=True, shift=False, ctrl=True, alt=False)
    # Plain drag = Normal selection
    add_hotkey(shift=False, ctrl=False, alt=False)

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
