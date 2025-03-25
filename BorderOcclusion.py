import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import BoolProperty, EnumProperty
import rna_keymap_ui
bl_info = {
"name": "BorderOcclusion",
"location": "View3D > Add > Object > Border Occlusion",
"description": "Drag mause for seletion back and front faces by dorder",
"author": "Vladislav Kindushov",
"version": (0,5,5),
"blender": (2, 90, 0),
"category": "3D View",
}
addon_keymaps = []

# ke mod - defaults to lasso, icons changed, some fixes in modal


class VIEW3D_OT_BorderOcclusion(Operator):
    """Border Occlusion selection """
    bl_idname = "view3d.border_occlusion"
    bl_label = "Border Occlusion"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.space_data.type == "VIEW_3D"

    Deselect: BoolProperty(
        name="Deselect",
        description="",
        default = False,
    )
    Extend: BoolProperty(
        name="Extend",
        description="",
        default = False,
    )

    def modal(self, context, event):
        if not self.Select:
            # setting this to True here, since the 'invoke default's will (prob) ignore it (immediately) after
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

        # waiting for event.value release no longer works (maybe because of the 'invoke default's above?)
        if not event.is_repeat and self.Select:
        # if event.value == 'RELEASE' and self.Select:
            context.space_data.shading.show_xray = self.show_xray
            self.Extend = False
            self.Deselect = False
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
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new('view3d.border_occlusion', 'RIGHTMOUSE', 'CLICK_DRAG', shift=shift, ctrl=ctrl, alt=alt, head=True)

    if not prop is None:
        kmi.properties[prop] = prop_value

    global addon_keymaps
    addon_keymaps.append((km, kmi))





def FindConflict(box, item):
    ku = bpy.context.window_manager.keyconfigs.user
    km = ['3D View','3D View Generic','Object Mode', 'Mesh','Curve','Armature']
    for km_n in km: 
        for i in bpy.context.window_manager.keyconfigs.user.keymaps[km_n].keymap_items:
            if item.type == i.type and item.ctrl == i.ctrl and item.alt == i.alt and item.shift == i.shift and item.name != i.name:
                col = box.column()
                col.label(text='Conflict hotkey: ' + '3D View -> ' + km_n + ' -> ' + i.name + " : ")
                # col.prop(bpy.context.window_manager.keyconfigs.user.keymaps.get(km_n), i)
                rna_keymap_ui.draw_kmi([], ku, bpy.context.window_manager.keyconfigs.user.keymaps[km_n], i, box, 0)
                return None

def GetKMI():
    kc = bpy.context.window_manager.keyconfigs.user
    km = kc.keymaps.get('3D View')
    kmi=[]
    for i in km.keymap_items:
        if i.name == 'Border Occlusion' or i.name == 'VIEW3D_OT_border_occlusion':
            kmi.append(i)
    return kmi


def SwapIcon(self, context):
    icon_pos = bpy.context.preferences.addons[__name__].preferences.IconPosition
    try:
        bpy.types.VIEW3D_HT_header.remove(draw)
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
        name = "Icon Position",
        description = "",
        items=[ ("LEFT", "Left", "", 1),
                ("RIGHT", "Right", "", 2),
                ("NONE", "None", "", 3)],
        default="NONE",
        update = SwapIcon
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
        for i in km.keymap_items:
            if i.idname == "view3d.border_occlusion":
                rna_keymap_ui.draw_kmi([], ku, km, i, HotkeyBox, 0)
                FindConflict(ConflictBox, i)
        
        # for i in GetKMI()[-3:]:
        #     km.active()
        #     box = layout.box()
        #     col = box.column()
        #     col.context_pointer_set("keymap", km)
        #     rna_keymap_ui.draw_kmi([], kc, km, i, col, 0)


def draw(self, context):
    layout = self.layout
    if not bpy.context.scene.border_occlude_mode:
        icon = 'MOD_DASH'
    else:
        icon = 'SELECT_SET'

    layout.prop(bpy.context.scene, 'border_occlude_mode' ,icon=icon)



classes = (VIEW3D_OT_BorderOcclusion, BorderOccludePref)


def register():

    for i in classes:
        bpy.utils.register_class(i)
    
    bpy.types.Scene.border_occlude_mode = BoolProperty(
        name="",
        description="",
        default = False,
    )
    
    add_hotkey(prop='Deselect', prop_value=True,shift=False, ctrl=True)
    add_hotkey(prop='Extend', prop_value=True , shift=True, ctrl=False)
    add_hotkey()

    icon_pos = bpy.context.preferences.addons[__name__].preferences.IconPosition
    if icon_pos != "NONE":
        bpy.types.VIEW3D_MT_editor_menus.append(draw)

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.types.VIEW3D_HT_header.remove(draw)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw)

    for i in reversed(classes):
        bpy.utils.unregister_class(i)

    del bpy.types.Scene.border_occlude_mode

    addon_keymaps.clear()

if __name__ == "__main__":
    register()
