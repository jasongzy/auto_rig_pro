import bpy, bmesh, math, re, operator, os, difflib, time, sys, ast
from io import StringIO
from math import degrees, pi, radians, ceil
from bpy.types import Panel, UIList
import mathutils
from mathutils import Vector, Euler, Matrix
from . import auto_rig_datas as ard
from . import auto_rig_reset, auto_rig, utils
from .utils import *
from bpy_extras.io_utils import ExportHelper
from bpy.props import IntProperty, BoolProperty, FloatProperty, StringProperty, EnumProperty, CollectionProperty, PointerProperty
from bpy.types import Operator, PropertyGroup, Panel, Menu


#print ("\n Starting Auto-Rig Pro: Game Engine Exporter... \n")

fingers_deform = ["thumb1", "c_thumb2", "c_thumb3", 'c_index1_base', "index1", "c_index2", "c_index3", 'c_middle1_base', "middle1", "c_middle2", "c_middle3", 'c_ring1_base', "ring1", "c_ring2", "c_ring3", 'c_pinky1_base', "pinky1", "c_pinky2", "c_pinky3"]

fingers_names = ["pinky", "ring", "index", "middle", "thumb"]

bend_bones = ['c_ankle_bend', 'c_leg_bend_02', 'c_leg_bend_01', 'c_knee_bend', 'c_thigh_bend_02', 'c_thigh_bend_01', 'c_thigh_bend_contact', 
            'c_waist_bend.x', 'c_root_bend.x', 
            'c_shoulder_bend', 'c_arm_bend', 'c_elbow_bend', 'c_forearm_bend', 'c_wrist_bend', 
            'c_bot_bend', 'c_neck_01.x']

bend_bones_spine_only = ['c_waist_bend.x', 'c_root_bend.x', 'c_bot_bend', 'c_neck_01.x']

for i in range(1, 33):
    str_idx = '%02d' % i
    bend_bones.append('c_spine_'+str_idx+'_bend.x')
    bend_bones_spine_only.append('c_spine_'+str_idx+'_bend.x')
    

bend_bones_add = ['c_ankle_bend', 'c_leg_bend_02', 'c_leg_bend_01', 'c_knee_bend', 'c_thigh_bend_02', 'c_thigh_bend_01', 'c_thigh_bend_contact', 'c_waist_bend.x', 'c_shoulder_bend', 'c_arm_bend', 'c_elbow_bend', 'c_forearm_bend', 'c_wrist_bend']

default_facial_bones = ['c_eyebrow_full', 'c_eyebrow_01_end', 'c_eyebrow_01', 'c_eyebrow_02', 'c_eyebrow_03', 'c_eye', 'c_eye_offset', 'eyelid_bot', 'eyelid_top', 'jawbone.x', 'c_lips_smile', 'c_eye_target']

additional_facial_bones = ['c_teeth_bot', 'c_teeth_top', 
                        'c_lips_bot', 'c_lips_bot_01', 'c_lips_top', 'c_lips_top_01', 'c_lips_corner_mini',
                        'c_chin_01', 'c_chin_02', 'c_cheek_smile', 'c_nose_03', 'c_nose_01', 'c_nose_02', 'c_cheek_inflate', 'c_eye_ref_track', 
                        'tong_03', 'tong_02', 'tong_01', 
                        'c_skull_01', 'c_skull_02', 'c_skull_03', 
                        'c_eyelid_top_01', 'c_eyelid_top_02', 'c_eyelid_top_03', 'c_eyelid_bot_01', 'c_eyelid_bot_02', 'c_eyelid_bot_03', 'c_eyelid_corner_01', 'c_eyelid_corner_02', 'c_eyelid_twk_top', 'c_eyelid_twk_bot']

facial_transfer_jaw = ["c_lips_bot_01", "c_lips_bot", "c_teeth_bot", "c_chin_01", "c_chin_02", "tong_03", "tong_01", "tong_02"]
facial_transfer_head = [i for i in additional_facial_bones if not (i in facial_transfer_jaw or 'eyelid' in i)]

blender_version = bpy.app.version_string

##########################  CLASSES  ##########################
class ActionItem(PropertyGroup):
    action: PointerProperty(type=bpy.types.Action)


class ActionsList(PropertyGroup):
    name: StringProperty(default="", description="Actions List Name")
    actions : CollectionProperty(type=ActionItem, description="Collection of actions in this set")
    exportable: BoolProperty(default=True, description="Export this list of actions")
    action_to_add: PointerProperty(type=bpy.types.Action)


class ARP_OT_actions_list_add_action(Operator):
    """Add an action"""
    bl_idname = "arp.actions_list_add_action"
    bl_label = "Add Action"
    bl_options = {'UNDO'}

    def execute(self, context):
        _add_actions_list_action(self)
        return {'FINISHED'}


class ARP_OT_actions_list_remove_action(Operator):
    """Remove an action"""
    bl_idname = "arp.actions_list_remove_action"
    bl_label = "Remove Action"
    bl_options = {'UNDO'}

    action_name: StringProperty(default='')

    def execute(self, context):
        _remove_actions_list_action(self)
        return {'FINISHED'}


class ARP_OT_actions_list_add(Operator):
    """Add an action list"""
    bl_idname = "arp.actions_list_add"
    bl_label = "Add Actions List"
    bl_options = {'UNDO'}

    def execute(self, context):
        _add_actions_list(self)
        return {'FINISHED'}


class ARP_OT_actions_list_remove(Operator):
    """Remove an action list"""
    bl_idname = "arp.actions_list_remove"
    bl_label = "Remove Actions List"
    bl_options = {'UNDO'}


    def execute(self, context):
        _remove_actions_list(self)
        return {'FINISHED'}


class ARP_OT_actions_list_move(Operator):
    """Move entry"""
    bl_idname = "arp.actions_list_move"
    bl_label = "Move Actions List"
    bl_options = {'UNDO'}

    direction: StringProperty(default="UP")

    def execute(self, context):
        try:
            scn = context.scene
            fac = -1
            if self.direction == 'DOWN':
                fac = 1

            target_idx = scn.arp_export_actlist_idx + fac
            if target_idx < 0:
                target_idx = len(scn.arp_export_actlist)-1
            if target_idx > len(scn.arp_export_actlist)-1:
                target_idx = 0

            scn.arp_export_actlist.move(scn.arp_export_actlist_idx, target_idx)
            scn.arp_export_actlist_idx = target_idx

        except:
            pass

        return {'FINISHED'}


class ARP_UL_actions_list(UIList):
    #icon_name = 'CHECKBOX_HLT'
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, translate=False)
        icon_name = 'CHECKBOX_HLT' if item.exportable else 'CHECKBOX_DEHLT'
        row.prop(item, "exportable", text="", icon=icon_name, emboss=False)


    def invoke(self, context, event):
        pass
        
        
class ARP_OT_GE_show_retro(Operator):
    """Show backward-compatibility options"""

    bl_idname = "arp.show_retro_options_ge"
    bl_label = "Backward-compatibility options:"
    bl_options = {'UNDO'}

    def draw(self, context):
        scn = context.scene
        layout = self.layout    
        layout.prop(scn, "arp_retro_axes", text="Export: Old Arms-Feet Orientation")
        layout.prop(scn, "arp_retro_action_prefix", text="Export: Actions Prefix")
        layout.prop(scn, "arp_retro_export_soft_fix", text="Export: Soft-Link Old Thigh/Arms Positions")
        layout.prop(scn, "arp_retro_ge_mesh", text="Export: Duplicate mesh data names (.001)")
        layout.prop(scn, "arp_retro_ge_UE_twist_pos", text="Export: Old UE humanoid twist bones position")
        layout.prop(scn, "arp_retro_ge_frame_range", text="Export: Add one frame ending the action")
        

    def invoke(self, context, event):
        # Open dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}
        
        
class ARP_OT_GE_unset_const_bones(Operator):
    """Unset the selected bones with constant keyframe interpolation when exporting.\nOnly deforming bones must be selected"""

    bl_idname = "arp.unset_const_bones"
    bl_label = "unset_const_bones"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == "POSE" or context.mode == "EDIT_ARMATURE":
            return True

    def execute(self, context):
        cur_mod = get_current_mode()

        _set_const_bones(False)

        restore_current_mode(cur_mod)

        mess = "Unset bones with constant keyframe interpolation"
        self.report({"INFO"}, mess)
        return {'FINISHED'}
        
        
class ARP_OT_GE_set_const_bones(Operator):
    """Set the selected bones with constant keyframe interpolation when exporting.\nOnly deforming bones must be selected"""

    bl_idname = "arp.set_const_bones"
    bl_label = "set_const_bones"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == "POSE" or context.mode == "EDIT_ARMATURE":
            return True

    def execute(self, context):
        cur_mod = get_current_mode()

        _set_const_bones(True)

        restore_current_mode(cur_mod)

        mess = "Set bones with constant keyframe interpolation"
        self.report({"INFO"}, mess)
        return {'FINISHED'}


class ARP_OT_GE_unset_softlink_bones(Operator):
    """Unset the selected bones as soft-linked"""

    bl_idname = "arp.unset_softlink_bones"
    bl_label = "unset_softlink_bones"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == "POSE" or context.mode == "EDIT_ARMATURE":
            return True

    def execute(self, context):
        cur_mod = get_current_mode()

        _set_softlink_bones(False)

        restore_current_mode(cur_mod)

        mess = "Unset custom bones"
        self.report({"INFO"}, mess)
        return {'FINISHED'}


class ARP_OT_GE_set_softlink_bones(Operator):
    """Set the selected bones as soft-linked in the exported skeleton, for stretchy bones:\nscale values are maintained to 1, while keeping the actual stretched bone position\nOnly deforming bones must be selected"""

    bl_idname = "arp.set_softlink_bones"
    bl_label = "set_softlink_bones"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == "POSE" or context.mode == "EDIT_ARMATURE":
            return True

    def execute(self, context):
        cur_mod = get_current_mode()

        _set_softlink_bones(True)

        restore_current_mode(cur_mod)

        mess = "Set as soft-linked bones"
        self.report({"INFO"}, mess)
        return {'FINISHED'}


class ARP_OT_GE_unset_custom_bones(Operator):
    """Remove the selected bones from the exported skeleton"""

    bl_idname = "arp.unset_custom_bones"
    bl_label = "unset_custom_bones"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == "POSE" or context.mode == "EDIT_ARMATURE":
            return True

    def execute(self, context):
        cur_mod = get_current_mode()

        _set_custom_bones(False)

        restore_current_mode(cur_mod)

        mess = "Unset custom bones"
        self.report({"INFO"}, mess)
        return {'FINISHED'}


class ARP_OT_GE_set_custom_bones(Operator):
    """Add the selected bones in the exported skeleton (useful for bones added manually in the ARP armature)"""

    bl_idname = "arp.set_custom_bones"
    bl_label = "set_custom_bones"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == "POSE" or context.mode == "EDIT_ARMATURE":
            return True

    def execute(self, context):
        cur_mod = get_current_mode()

        _set_custom_bones(True)

        restore_current_mode(cur_mod)

        mess = "Set as custom bones"
        self.report({"INFO"}, mess)
        return {'FINISHED'}


class ARP_OT_GE_fix_rig(Operator):
    """Fix the rig issues automatically when possible(set stretch to 0, disable Preserve Volume...)"""

    bl_idname = "arp.fix_rig_export"
    bl_label = "fix_rig"
    bl_options = {'UNDO'}

    def execute(self, context):
        _fix_rig(self)
        
        mess = "Warning, the following operations were applied:\n-Disabled all possible arms and legs stretches\n-Disabled Preserve Volume on skinned meshes\nThis may somehow change the result, it's recommended to check\nthat animations still look good in the scene, correct them if necessary."  
        auto_rig.display_popup_message(mess, header='Rig fixed!', icon_type='INFO')

        return {'FINISHED'}


class ARP_OT_GE_check_rig(Operator):
    #tooltip
    """Check the rig to find possible export related errors"""

    bl_idname = "arp.check_rig_export"
    bl_label = "check_rig"
    bl_options = {'UNDO'}

    def execute(self, context):
        self.message_final = ""
        self.non_armature_actions = []
        self.scale_object_action = []
        self.preserve_volume_enabled = []
        self.stretch_controllers = []
        self.auto_stretch_controllers = []
        self.bendy_bones_limbs = []
        self.invalid_modifiers = []
        self.soft_ik_limbs = []        

        _check_rig(self)
        
        if len(self.bendy_bones_limbs):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '---------- Bendy Bones Limbs ----------'
            self.message_final += '\nSome bendy-bones limbs were found. Bendy-Bones are not exportable to Fbx'
        
        if len(self.invalid_modifiers):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '---------- Invalid Modifiers ----------'
            self.message_final += '\nThese objects have invalid armature modifiers.\nThey may have no target armature, or too many armature modifiers.'
            for objname in self.invalid_modifiers:
                self.message_final += '\n" ' + objname + ' "'

        if len(self.non_armature_actions):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '------ Corrupted Animations ------'
            self.message_final += '\nThese actions are exported while they do not contain bones keyframes,\nit may possibly corrupt other exported animations:'
            for act_name in self.non_armature_actions:
                self.message_final += '\n" ' + act_name + ' "'
            self.message_final += '\nEnable "Only Containing" to exclude from export these actions by name.'

        if len(self.scale_object_action):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '-------- Scaled Object --------'
            self.message_final += '\nThese actions are exported while they contain scale keyframes at\n object level:'
            for act_name in self.scale_object_action:
                self.message_final += '\n" ' + act_name + ' "'
            self.message_final += '\nDelete objects keyframes.'

        if len(self.preserve_volume_enabled):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '-------- Preserve Volume ---------'
            self.message_final += '\nThese objects have an armature modifier with "Preserve Volume" enabled,\nthis should be disabled to see the correct deformations.'
            for i, objname in enumerate(self.preserve_volume_enabled):
                if i < 3:
                    self.message_final += '\n" ' + objname + ' "'
                else:
                    self.message_final += '\nand '+str(len(self.preserve_volume_enabled)-i)+' others...'
                    break

        if len(self.stretch_controllers):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '------------ Stretch -------------'
            self.message_final += '\nThese controllers are used to stretch the arms and legs,\nit can potentially lead to bones rotation issues.\nSet their position to 0 to clear any stretch.'
            for controllername in self.stretch_controllers:
                self.message_final += '\n" ' + controllername + ' "'

        if len(self.auto_stretch_controllers):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '---------- Auto-Stretch ----------'
            self.message_final += '\nThese controllers have Auto-Stretch enabled, or Stretch Length different from 1,\nit can potentially lead to bones rotation issues.'
            for controllername in self.auto_stretch_controllers:
                self.message_final += '\n" ' + controllername + ' "'
        
        if len(self.soft_ik_limbs):
            if self.message_final != "":
                self.message_final += '\n'
            self.message_final += '--------------- Soft IK ---------------'
            self.message_final += '\nThese limbs have Soft IK enabled, it can potentially lead to bones rotation \nissues.'
            for limbname in self.soft_ik_limbs:
                self.message_final += '\n" ' + limbname + ' "'
                
        print(self.message_final)


        if len(self.message_final):
            auto_rig.display_popup_message(self.message_final, header='Some issues were found:', icon_type='ERROR')            
        else:
            auto_rig.display_popup_message("No issues found, ready to export.", header='Passed!', icon_type='INFO')

        return {'FINISHED'}


class ARP_OT_delete_action(Operator):
    """Delete the selected action"""

    bl_idname = "arp.delete_action"
    bl_label = "The action will be permanently removed from the scene, ok?"
    bl_options = {'UNDO'}

    action_name : StringProperty(default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            if self.action_name != "":
                if bpy.data.actions.get(self.action_name):
                    bpy.data.actions.remove(bpy.data.actions[self.action_name], do_unlink=True)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_toggle_action(Operator):
    """Enable or disable this action from export"""

    bl_idname = "arp.toggle_action"
    bl_label = "toggle_action_export"
    bl_options = {'UNDO'}

    action_name : StringProperty(default="")

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            if self.action_name != "":
                act = bpy.data.actions.get(self.action_name)
                if act:
                    found_prop = False
                    if len(act.keys()) > 0:
                        if "arp_export" in act.keys():
                            act["arp_export"] = not act["arp_export"]
                            found_prop = True
                    if not found_prop:
                        act["arp_export"] = False

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_set_mped_rig(Operator):
    """Create and set the Mped armature as the deforming armature"""

    bl_idname = "id.set_mped_rig"
    bl_label = "set_mped_rig"
    bl_options = {'UNDO'}

    actions_pushed_changed = []

    @classmethod
    def poll(cls, context):
        if context.active_object:
            return is_arp_armature(context.active_object)

    def execute(self, context):
        self.multiple_twist_bones = False
        self.armature_proxy_name = None
        self.selected_bone_names = []
        self.is_arp_armature = is_arp_armature(context.active_object)

        context.scene.arp_export_rig_type = 'UNIVERSAL'
        arm = bpy.context.active_object

        limb_sides.get_multi_limbs()

        # proxy and overrides not supported yet in this debug feature
        if is_proxy(arm) or arm.override_library:
            self.report({"ERROR"}, "Proxy and overrides not yet supported here")
            return {"FINISHED"}

        # check if multiple twist bones are used
        check_multiple_twist_bones(self)

        print("Multiple twist bones:", self.multiple_twist_bones)

        # Force twist bones export if multiple twist bones are set, and set the twist face to 1.0
        if self.multiple_twist_bones:
            print("Force twist bones export because multiple twist bones were found.")
            context.scene.arp_export_twist = True
            context.scene.arp_twist_fac = 1.0

        # store selected bones
        self.selected_bone_names = [b.name for b in bpy.context.active_object.data.bones if b.select and b.use_deform]

        bpy.ops.object.mode_set(mode='OBJECT')
        rig_name = bpy.context.active_object.name
        rig_add_name = get_rig_add(rig_name)

        arp_bones_data.collect(rig_name)

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            scn = context.scene
            # save current weights for restoration later
            _save_mesh_weights(rig_name)
            
            # set mped
            _set_mped_rig(rig_name, rig_add_name, True, self)
            
            # custom renaming
            if scn.arp_export_renaming:
                rename_custom(self)
                
            # custom export script
            _run_custom_export_script()
                
            # select arp armature
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            set_active_object(arm.name)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_set_humanoid_rig(Operator):
    """Create and set the humanoid armature as the deforming armature\nWarning, breaks Auto-Rig Pro editing and export tools, use with care"""

    bl_idname = "id.set_humanoid_rig"
    bl_label = "set_humanoid_rig"
    bl_options = {'UNDO'}

    actions_pushed_changed = []

    @classmethod
    def poll(cls, context):
        if context.active_object:
            return is_arp_armature(context.active_object)


    def execute(self, context):
        self.multiple_twist_bones = False
        self.armature_proxy_name = None
        self.armature_name = bpy.context.active_object.name
        self.selected_bone_names = []

        arm = bpy.context.active_object
        
        # proxy and overrides not supported yet in this debug feature
        if is_proxy(arm) or arm.override_library:
            self.report({"ERROR"}, "Proxy and overrides not yet supported here")
            return {"FINISHED"}

        context.scene.arp_export_rig_type = 'HUMANOID'
        scn = context.scene
        
        # is it really a humanoid rig?
        if not check_humanoid_limbs():
            self.report({"ERROR"}, ' This is not a humanoid rig: it contains duplicated limbs or non-humanoid limbs.\nSwitch to Universal type instead.')
            return {'FINISHED'}
        
        # check if multiple twist bones are used
        check_multiple_twist_bones(self)

        print("Multiple twist bones:", self.multiple_twist_bones)

        self.selected_bone_names = [b.name for b in bpy.context.active_object.data.bones if b.select and b.use_deform]
        
        # at least one deforming bone selected if export only selection?
        if scn.arp_ge_sel_bones_only:
            if len(self.selected_bone_names) == 0:
                self.report({"ERROR"}, ' No deforming bones are selected while "Selected Bones Only" is enabled in the export settings\nSelect at least one deforming bone')
                return {'FINISHED'}


        # Force twist bones export if multiple twist bones are set, and set the twist face to 1.0
        if self.multiple_twist_bones:
            print("Force twist bones export because multiple twist bones were found.")
            scn.arp_export_twist = True
            scn.arp_twist_fac = 1.0

        bpy.ops.object.mode_set(mode='OBJECT')
        
        _rig_add_name = get_rig_add(bpy.context.active_object.name)
        rig_name = bpy.context.active_object.name

        arp_bones_data.collect(rig_name)

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            # save current weights for restoration later
            _save_mesh_weights(rig_name)
            
            # set humanoid
            _set_humanoid_rig(rig_name, _rig_add_name, True, self)
            
            if scn.arp_engine_type == 'UNREAL':
                if scn.arp_rename_for_ue:
                    rename_for_ue()
                    # Mannequin Axes?
                    if scn.arp_mannequin_axes:
                        _set_mannequin_orientations(self)
                        
                # IK Bones?
                if scn.arp_ue_ik:
                    _add_ik_bones()
                    
            elif scn.arp_engine_type == 'GODOT':
                if scn.arp_rename_for_godot:
                    rename_for_godot()
            
            # custom renaming
            if scn.arp_export_renaming:
                rename_custom(self)
                    
            # custom export script
            _run_custom_export_script()
            
            # select arp armature
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            set_active_object(self.armature_name)
            

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_unset_export_rig(Operator):
    """Unset the export armature"""

    bl_idname = "id.unset_export_rig"
    bl_label = "unset_export_rig"
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.active_object:
            if 'arp_export_rig_set' in context.active_object.keys():
                return True
        return False
        
    
    def execute(self, context):
        arp_armature_name = bpy.context.active_object.name
        humanoid_name = bpy.context.active_object['arp_export_rig_set']
        
        if get_object(humanoid_name) == None:
            self.report({'ERROR'}, "The Humanoid armature has not been set")
            del context.active_object['arp_export_rig_set']
            return{'FINISHED'}
      
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _unset_export_rig(arp_armature_name, humanoid_name)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ExportPresetsToDel:
    list = []
    
    def update(self):
        print('Update export preset to del...')
        self.list = []       
        
        for p in ARP_MT_ge_import_preset_menu.custom_presets:
            self.list.append(p)
        
    def remove_entry(self, name):
        print('Remove export preset to del:', name)
        self.list.remove(name)
    
    def __init__(self):
        return
                
export_presets_todel = ExportPresetsToDel()

        
class ARP_OT_ge_remove_preset(Operator):
    """Remove export preset"""

    bl_idname = 'arp.ge_remove_preset'
    bl_label = 'Remove export preset'  
   
    
    def invoke(self, context, event):
        update_ge_presets()        
        export_presets_todel.update()
        # Open dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
    def draw(self, context):
        layout = self.layout
        
        if len(export_presets_todel.list):
            for p in export_presets_todel.list:
                row = layout.row(align=True)
                row.label(text=p)
                op = row.operator('arp.exec_rem_export_presets', text='', icon='X')
                op.name = p             
        else:
            layout.label(text='No export preset added yet!')
        
    def execute(self, context):
        return {'FINISHED'}
        
        
class ARP_OT_exec_rem_export_presets(Operator):
    """Remove the export preset"""
    
    bl_idname = 'arp.exec_rem_export_presets'
    bl_label = 'Remove'
    
    name: StringProperty(default='')
    
    def execute(self, context):
        print('Deleting', self.name, '...')        
     
        preset_path = bpy.context.preferences.addons[__package__.split('.')[0]].preferences.ge_presets_path    
        if not (preset_path.endswith("\\") or preset_path.endswith('/')):
            preset_path += '/'
        
        filepath = preset_path+self.name+'.py'
        filepath = os.path.abspath(filepath)# automatically adds the driver letter if the path does not contain any

        # remove file
        try:
            os.remove(filepath)
            print('  Removed successfully preset file', filepath)                
        except:
            print('  Could not remove preset file', filepath)
            
        # update list
        export_presets_todel.remove_entry(self.name)
        update_ge_presets()
        
        return {'FINISHED'}
        
        
class ARP_OT_ge_load_preset(Operator):
    """Load export settings"""

    bl_idname = 'arp.ge_load_preset'
    bl_label = 'ge_load_preset'  
    
    preset_name: StringProperty(default='')
    filepath: StringProperty(subtype="FILE_PATH", default='py') 
    
    def execute(self, context):           
        custom_dir = bpy.context.preferences.addons[__package__.split('.')[0]].preferences.ge_presets_path
        if not (custom_dir.endswith("\\") or custom_dir.endswith('/')):
            custom_dir += '/'
            
        try:
            os.listdir(custom_dir)
        except:
            self.report({'ERROR'}, 'The Game Engine presets directory seems invalid: '+custom_dir+'\nCheck the path in the addon preferences')
            return

        self.filepath = custom_dir + self.preset_name+'.py'  
        
        _load_preset(self)
        
        return {'FINISHED'}
        
        
class ARP_OT_ge_save_preset(Operator):
    """Save export settings"""

    bl_idname = 'arp.ge_save_preset'
    bl_label = 'Save export preset'  
    
    preset_name: StringProperty(default='CoolPreset')
    filepath: StringProperty(subtype="FILE_PATH", default='py') 
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
    
    def draw(self, context):
        layout = self.layout            
        layout.prop(self, 'preset_name', text='Preset Name')
        layout.separator()
   
    def execute(self, context): 
        # get filepath
        custom_dir = bpy.context.preferences.addons[__package__.split('.')[0]].preferences.ge_presets_path
        if not (custom_dir.endswith("\\") or custom_dir.endswith('/')):
            custom_dir += '/'  

        if not os.path.exists(os.path.dirname(custom_dir)):
            print('File path does not exist:', custom_dir)
            try:
                print('Try to create it...')
                os.makedirs(os.path.dirname(custom_dir))
                print('Created successfully.')
            except:
                pass
                
        self.filepath = custom_dir + self.preset_name+'.py'
        
        _save_preset(self)
        
        update_ge_presets()
        
        return {'FINISHED'}
        
        
class ARP_MT_ge_import_preset_menu(Menu):    
    bl_label = 'Import custom preset'
    
    custom_presets = []
    
    def draw(self, _context):
        layout = self.layout
        for cp in self.custom_presets:
            op = layout.operator('arp.ge_load_preset', text=cp.title()).preset_name = cp
            
            
            
def update_ge_presets():
    presets_directory = bpy.context.preferences.addons[__package__.split('.')[0]].preferences.ge_presets_path
    
    if not (presets_directory.endswith("\\") or presets_directory.endswith('/')):
        presets_directory += '/'

    try:
        os.listdir(presets_directory)
    except:
        #print("The custom presets directory seems invalid:", presets_directory)
        return

    ARP_MT_ge_import_preset_menu.custom_presets = []
    
    for file in os.listdir(presets_directory):
        if not file.endswith('.py'):
            continue
            
        preset_name = file.replace('.py', '')
        
        if preset_name in ARP_MT_ge_import_preset_menu.custom_presets:
            continue

        ARP_MT_ge_import_preset_menu.custom_presets.append(preset_name)
        
        
limb_sides = auto_rig.Limb_Sides()


def check_multiple_twist_bones(self):    
     
    bpy.ops.object.mode_set(mode='OBJECT')

    if len(limb_sides.arm_sides) > 0:
        for arm_side in limb_sides.arm_sides:
            arm_ref = get_data_bone('arm_ref'+arm_side)
            if len(arm_ref.keys()) > 0:
                if 'twist_bones_amount' in arm_ref.keys():
                    if arm_ref["twist_bones_amount"] > 1:
                        self.multiple_twist_bones = True

    if len(limb_sides.leg_sides) > 0 and self.multiple_twist_bones == False:
        for leg_side in limb_sides.leg_sides:
            thigh_ref = get_data_bone('thigh_ref'+leg_side)
            if len(thigh_ref.keys()) > 0:
                if 'twist_bones_amount' in thigh_ref.keys():
                    if thigh_ref["twist_bones_amount"] > 1:
                        self.multiple_twist_bones = True
                        
    '''# disable for now, see above
    if work_on_editable_proxy or work_on_editable_override:
        # delete temporary armature copy data
        bpy.ops.object.mode_set(mode='OBJECT')
        armature_local = get_object("ARP_EDITABLE_ARMATURE")
        bpy.data.objects.remove(armature_local, do_unlink = True)
        # restore selection
        for obj_name in sel_objs_names:
            set_active_object(obj_name)
        set_active_object(arm_name)
    '''    


class ARP_OT_export(Operator):
    """Export Auto-Rig Pro character"""
    bl_idname = "arp.export"
    bl_label = "Export"
    
    def execute(self, context):
        print('')
        
        # variables saving changed parameters, to be restored after export
        self.arm_scale = None
        self.actions_units_changed = []
        self.actions_x100_changed = []
        self.actions_were_exported = False
        self.actions_pushed_changed = []
        self.save_auto_key = context.scene.tool_settings.use_keyframe_insert_auto
        self.saved_collection_vis = [i.hide_viewport for i in bpy.data.collections]        
        self.saved_unit_settings = {}
        self.current_selection = None
        self.NLA_tweak_state = False
        
        self.armature_name = ""
        self.armature_add_name = ""
        self.armature_proxy_name = None
        self.is_override = False
        self.armature_source_name = None# source name for overridden armatures
        self.linked_collection = None
        self.collection_has_been_linked = False
        self.char_objects = None
        self.spline_objects = None
        self.message_final = ""
        self.non_armature_actions = []
        self.invalid_mesh_names = []
        self.shape_keys_data = {}
        self.meshes_names_dict = {}
        self.multiple_twist_bones = False
        self.selected_bone_names = []
        proxy_picker_value = None
        armature_base_name = ''
        
        export_timer_total = 0.0
        
        

        try:
            time_start = time.time()
            
            scn = bpy.context.scene
            
            # store file path
            scn.arp_ge_fp = self.filepath
            
            # Store current frame
            current_frame_saved = scn.frame_current
            
            # store current unit settings
            for prop_name in dir(context.scene.unit_settings):                
                if not is_rna_prop(prop_name):
                    self.saved_unit_settings[prop_name] = getattr(context.scene.unit_settings, prop_name)

            # -- Initial checks and warnings --
            # Is the armature selected?
            if bpy.context.active_object == None:
                self.report({"ERROR"}, 'Select the armature to export')
                return {'FINISHED'}

            # set the armature as active object (if any)
            if bpy.context.active_object.type != "ARMATURE":
                for obj in bpy.context.selected_objects:
                    if obj.type == "ARMATURE":
                        set_active_object(obj.name)
                        break                        
            
            self.is_arp_armature = is_arp_armature(bpy.context.active_object)
            self.current_selection = [bpy.context.active_object.name, [i.name for i in bpy.context.selected_objects]]

            if bpy.context.active_object.type != "ARMATURE":
                self.report({"ERROR"}, 'Select the armature to export')
                return {'FINISHED'}
            else:
                # updated to 4x ?
                if bpy.app.version >= (4,0,0) and self.is_arp_armature:
                    if not 'arp_updated_4.0' in bpy.context.active_object.data.keys():
                        self.report({"ERROR"}, 'The rig must be updated to Blender 4x before exporting.\nSee Auto-Rig Pro menu.\n ')
                        return {'FINISHED'}
            
                # check at least one deforming bone is selected if "Selected Bones Only" is enabled
                self.selected_bone_names = [b.name for b in bpy.context.active_object.data.bones if b.select and b.use_deform]
                
                if scn.arp_ge_sel_bones_only:                    
                    if len(self.selected_bone_names) == 0:
                        self.report({'ERROR'}, 'No deforming bones selected, while Selected Bones Only is enabled.\nSelect at least one deforming bone.')
                        return {'FINISHED'}
            
                # check lengthy rig name, not supported
                if len(bpy.context.active_object.name) > 56:
                    self.report({"ERROR"},  'Rig name is too long, please shorten it to 56 characters:\n'+'"'+bpy.context.active_object.name+'"')
                    return {'FINISHED'}
            
                # is the armature a proxy?
                armature_base_name = bpy.context.active_object.name
                if is_proxy(bpy.context.active_object):
                    armature_base_name = bpy.context.active_object.proxy.name
                    self.armature_proxy_name = armature_base_name
                    print("The armature is a proxy. Real name =", armature_base_name)

                # is the armature overridden?
                if bpy.context.active_object.override_library:
                    self.is_override = True
                    self.armature_source_name = bpy.context.active_object.override_library.reference.name
                    print('The armature is overridden')

                    # check Blender version, if 2.90, overrides can't be exported because they can't be localized from script
                    # other versions (2.83, 2.91, 2.92...) are fine.
                    if bpy.app.version >= (2,90,0) and bpy.app.version < (2,91,0):
                        self.report({"ERROR"}, "Overrides can't be exported with Blender 2.90.\nUse 2.83, 2.91 or above")
                        return {'FINISHED'}

                
                # iterate over meshes
                objects_list = [obj for obj in scn.objects] if scn.arp_ge_sel_only == False else [obj for obj in bpy.context.selected_objects]
                for obj in objects_list:
                    if obj.type != "MESH":
                        continue
                    if obj.find_armature() == None:
                        continue
                    if obj.find_armature().name == armature_base_name:
                        # Check for lengthy names
                        if len(obj.name) > 56:
                            self.report({"ERROR"},  'Object name is too long, please shorten it to 56 characters:\n'+'"'+obj.name+'"')
                            return {'FINISHED'}
                            
                        # Check for materials linked to Object instead of Data
                        # is a mesh with shape keys linked to the selected armature?
                        if obj.data.shape_keys:                                
                            # is material linked to object?
                            is_ob_material = any(ms.link == 'OBJECT' for ms in obj.material_slots)
                            if is_ob_material:
                                self.report({"ERROR"}, '"' + obj.name + '" is a deformed mesh with shape keys, with material linked set to Object. Shape keys cannot be exported.\nLink the material to Data instead.')
                                return {'FINISHED'}
                                
                        # Check for normal tangent space, does not comply with Ngons
                        if self.export_format == 'FBX' and scn.arp_use_tspace:
                            for poly in obj.data.polygons:
                                if len(poly.vertices) > 4:
                                    self.report({"ERROR"}, '"' + obj.name + '" object contains polygons with more than 4 vertices. Does not comply with Tangent Space normals.\nEither disable Tangent Space export or split N-gons to quads')
                                    return {'FINISHED'}
                                    

                # check that Match to Rig has been performed after a Smart session
                if 'has_match_to_rig' in bpy.context.active_object.data.keys():
                    if bpy.context.active_object.data['has_match_to_rig'] == False:
                        self.report({'ERROR'}, 'Click "Match to Rig" before exporting')
                        return {'FINISHED'}
                    
                    
                limb_sides.get_multi_limbs()

                # check the facial bones are up to date
                if len(limb_sides.head_sides):
                    jawbone_x = get_data_bone("jawbone.x")
                    c_jawbone_x = get_data_bone("c_jawbone.x")
                    eyelid_top = get_data_bone("eyelid_top.l")
                    c_eyelid_top = get_data_bone("c_eyelid_top.l")

                    if (jawbone_x == None and c_jawbone_x) or (eyelid_top == None and c_eyelid_top):
                        error_message = "Armature not up to date. Click 'Update Armature'"
                        print(error_message)
                        self.report({"ERROR"}, error_message)
                        return {'FINISHED'}

                # check if multiple twist bones are used
                check_multiple_twist_bones(self)

                print("Multiple twist bones:", self.multiple_twist_bones)

                # Force twist bones export if multiple twist bones are set, and set the twist face to 1.0
                if self.multiple_twist_bones:
                    print("Force twist bones export because multiple twist bones were found.")
                    scn.arp_export_twist = True
                    scn.arp_twist_fac = 1.0

                bpy.ops.object.mode_set(mode='OBJECT')


            self.armature_name = bpy.context.active_object.name

            # Can the rig_add be found?
            rig_add = get_rig_add(armature_base_name)
            if rig_add == None and bpy.context.active_object.arp_secondary_type == "ADDITIVE":
                error_message = 'rig_add not found. Invalid rig hierarchy.'
                print(error_message)
                self.report({"ERROR"}, error_message)
                return {'FINISHED'}

            self.armature_add_name = rig_add

            limb_sides.get_multi_limbs()

            if scn.arp_export_rig_type == 'HUMANOID':
                # is it really a humanoid rig?
                if not check_humanoid_limbs():
                    self.report({"ERROR"}, ' This is not a humanoid rig: it contains duplicated limbs or non-humanoid limbs.\nSwitch to Universal type instead.')
                    return {'FINISHED'}

            # If it's a proxy, make sure to link the character collection to the scene first
            if self.armature_proxy_name:
                print("The armature is a proxy: link collection in the scene...")
                # get the rig collection
                rig_col = None
                armat = get_object(self.armature_proxy_name)
                for col in armat.users_collection:
                    if col.name.endswith("_rig"):
                        rig_col = col
                        print("  Rig collection:", rig_col.name)
                        break

                # New method to find the character collection, simply get the parent collection since it should be the parent
                character_col = None
                if rig_col:
                    print("  Find character collection...")
                    for col in bpy.data.collections:
                        if len(col.children):
                            for child_c in col.children:
                                if child_c == rig_col:
                                    character_col = col
                                    print("  Char collection:", character_col.name)
                                    break

                if character_col:
                    # check meshes are not named as the collection
                    if len(armat.children):
                        for child_o in armat.children:
                            if child_o.name == character_col.name:
                                self.report({"ERROR"}, 'An object is named as the character collection: "'+character_col.name+'"\nNot supported, please change its name.')
                                return {'FINISHED'}

                    for child_col in character_col.children:
                        if child_col == rig_col:
                            # make sure it's not already linked
                            already_linked = False
                            for ccol in scn.collection.children:
                                if ccol == character_col:
                                    already_linked = True
                            # link it
                            if not already_linked:
                                scn.collection.children.link(character_col)
                                self.collection_has_been_linked = True
                                print("  Proxy Character collection linked.")
                            self.linked_collection = character_col.name

                if not self.linked_collection:
                    self.report({"ERROR"}, 'Character collection not found.')
                    return {'FINISHED'}

            # Is the NLA in tweak mode?
            #   save current layout            
            self.NLA_tweak_state = nla_exit_tweak()

            print('\n..............................Starting ARP '+ self.export_format +'Export..............................')

            # Disable the proxy picker to avoid bugs
            proxy_picker_value = disable_proxy_picker()

            # Disable auto-keyframe
            scn.tool_settings.use_keyframe_insert_auto = False

            # Enable all collections visibility
            for col in bpy.data.collections:
                is_cs_collection = False
                if len(col.objects) > 0:
                    for obj in col.objects:
                        if obj.name.startswith('cs_'):
                            is_cs_collection = True
                            break
                if not is_cs_collection:
                    col.hide_viewport = False            
            
            # Create copy objects
            create_copies(self)
            
            # Initialize arp_armatures scales
            self.arm_scale = get_object(self.armature_name+'_arpexp').scale[0]

            if self.arm_scale != 1.0:
                init_armatures_scales(self.armature_name, self.armature_add_name, self)
                print("Scale initialized from", self.arm_scale, "to 1.0")

            def clear_all_parents(armature_name):
                set_active_object(armature_name)
                bpy.ops.object.mode_set(mode='EDIT')

                for b in bpy.context.active_object.data.edit_bones:
                    b.parent = None

                if "b" in locals():
                    del b

                bpy.ops.object.mode_set(mode='POSE')
                # ensure transforms are unlocked
                for b in bpy.context.active_object.pose.bones:
                    b.lock_location[0] = b.lock_location[1] = b.lock_location[2] = False
                    b.lock_scale[0] = b.lock_scale[1] = b.lock_scale[2] = False

                bpy.ops.object.mode_set(mode='OBJECT')


            def initialize_fbx_armature_rotation(root_armature_name):
                print("\nApply armature rotation...")
                root_armature = get_object(root_armature_name)
                obj_list = [i for i in bpy.context.selected_objects]

                # unlink current action from the armature if any
                if root_armature.animation_data:
                    root_armature.animation_data.action = None

                # add -90 degrees rotation offset on X
                root_armature.rotation_euler[1] = root_armature.rotation_euler[2] = 0.0
                root_armature.rotation_euler[0] = math.radians(-90)

                # disable Copy Transforms constraint
                if not scn.arp_ue_root_motion:
                    if len(root_armature.constraints):
                        if root_armature.constraints[0].type == "COPY_TRANSFORMS":
                            enable_constraint(root_armature.constraints[0], False)
                           
                            # add copy location and copy scale instead
                            cns1 = root_armature.constraints.new("COPY_LOCATION")
                            cns1.name = "Copy Location"
                            cns1.target = get_object(self.armature_name + "_arpexp")
                            cns2 = root_armature.constraints.new("COPY_SCALE")
                            cns2.name = "Copy Scale"
                            cns2.target = get_object(self.armature_name + "_arpexp")

                if bpy.app.version < (2,90,0):# 2.90 version and higher doesn't need it
                    # unparent meshes before applying rotation
                    bpy.context.evaluated_depsgraph_get().update()
                    bpy.context.evaluated_depsgraph_get().update()
                    parent_objects(obj_list, None)

                # apply rotation
                set_active_object(root_armature_name)
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                set_active_object(root_armature_name)
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

                if bpy.app.version < (2,90,0):# 2.90 version and higher doesn't need it
                    # parent meshes to armature
                    bpy.context.evaluated_depsgraph_get().update()
                    parent_objects(obj_list, root_armature)

                # revert rotation
                root_armature.rotation_euler[0] = math.radians(90)

                # offset rotation on baked armature object keyframes too
                for act in bpy.data.actions:
                    if not check_id_root(act):
                        continue
                    if not len(act.keys()):
                        continue
                    if not "arp_baked_action" in act.keys():
                        continue
                    for fc in act.fcurves:
                        if fc.data_path == "rotation_euler" and fc.array_index == 0:
                            for kf in fc.keyframe_points:
                                kf.co[1] += math.radians(90)
                                kf.handle_left[1] += math.radians(90)
                                kf.handle_right[1] += math.radians(90)

                # apply meshes rotation
                if scn.arp_init_fbx_rot_mesh:
                    print("  Apply meshes rotations...")
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')

                    for o in obj_list:
                        if o.type == "MESH":
                            set_active_object(o.name)

                    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    set_active_object(root_armature_name)

                # end initialize_fbx_armature_rotation()


            # Collect custom bones
            arp_bones_data.collect(self.armature_name)
            custom_bones_list = arp_bones_data.custom_bones_list

            #   debug prints
            max_display = 5
            if len(custom_bones_list) > max_display:
                s = []
                for i in range(0, max_display):
                    s.append(custom_bones_list[i])

                print('Custom Bones:', s, '... and', str(len(custom_bones_list)-max_display), 'others')
            else:
                print('Custom Bones:', custom_bones_list)
                

            # Humanoid Export?
            if scn.arp_export_rig_type == 'HUMANOID':

                # Set the humanoid armature
                _set_humanoid_rig(self.armature_name, self.armature_add_name, False, self)
                
                if scn.arp_engine_type == 'UNREAL':
                    if scn.arp_rename_for_ue:
                        rename_for_ue()

                        if scn.arp_mannequin_axes:
                            _set_mannequin_orientations(self)

                    if scn.arp_ue_ik:
                        _add_ik_bones()
                
                elif scn.arp_engine_type == 'GODOT':
                    if scn.arp_rename_for_godot:
                        rename_for_godot()
                    
                # custom renaming
                if scn.arp_export_renaming:
                    rename_custom(self)

                # if no parent is enabled, clear all parents
                if scn.arp_export_noparent:
                    clear_all_parents("rig_humanoid")
               
                # custom export script
                _run_custom_export_script()
                
                # Bake Actions?
                if scn.arp_bake_anim and len(bpy.data.actions):
                    _bake_all(self.armature_name, "rig_humanoid", self)                    
                else:                    
                    _bake_pose("rig_humanoid")

                # x100 units?
                if (scn.arp_export_bake_axis_convert == False and scn.arp_engine_type == 'UNITY' and self.export_format == 'FBX') or scn.arp_engine_type in ['UNREAL', 'OTHERS'] or self.export_format == 'GLTF':
                    if (scn.arp_units_x100 and self.export_format == 'FBX') or (scn.arp_ge_gltf_unitsx100 and self.export_format == 'GLTF'):
                        _set_units_x100_baked(self.armature_name, self)

                # Parent the meshes to the humanoid rig
                parent_meshes_to_baked_armature(self, 'rig_humanoid')

                # Initialize Fbx armature rotation?
                if (scn.arp_export_bake_axis_convert == False and scn.arp_engine_type == 'UNITY' and self.export_format == 'FBX') or scn.arp_engine_type in ['UNREAL', 'OTHERS']:
                    if scn.arp_init_fbx_rot:
                        initialize_fbx_armature_rotation("rig_humanoid")

                # Select objects to export                
                _select_exportable(self.armature_name)

                # Rename "rig_humanoid" to def name
                #   avoid name clashing
                for obj in bpy.data.objects:
                    if obj.name == scn.arp_export_rig_name:
                        obj.name = scn.arp_export_rig_name + "_temp"

                rig_humanoid = get_object("rig_humanoid")
                rig_humanoid.name = scn.arp_export_rig_name
                rig_humanoid['arp_rig_name'] = self.armature_name+'_arpbob'

            # M-Ped Export?
            if scn.arp_export_rig_type == 'UNIVERSAL':
                # Set the mped armature
                _set_mped_rig(self.armature_name, self.armature_add_name, False, self)

                # custom renaming
                if scn.arp_export_renaming:
                    rename_custom(self)

                # if no parent is enabled, clear all parents
                if scn.arp_export_noparent:
                    clear_all_parents("rig_mped")
                
                # custom export script
                _run_custom_export_script()

                # Bake Actions?
                if scn.arp_bake_anim and len(bpy.data.actions):
                    _bake_all(self.armature_name, "rig_mped", self)
                else:
                    _bake_pose("rig_mped")
                
                # x100 units?
                if (scn.arp_export_bake_axis_convert == False and scn.arp_engine_type == 'UNITY' and self.export_format == 'FBX') or scn.arp_engine_type in ['UNREAL', 'OTHERS'] or self.export_format == 'GLTF':
                    if (scn.arp_units_x100 and self.export_format == 'FBX') or (scn.arp_ge_gltf_unitsx100 and self.export_format == 'GLTF'):
                        _set_units_x100_baked(self.armature_name, self)
                
                # Parent the meshes to the mped rig
                parent_meshes_to_baked_armature(self, "rig_mped")

                # Initialize Fbx armature rotation?
                if (scn.arp_export_bake_axis_convert == False and scn.arp_engine_type == 'UNITY' and self.export_format == 'FBX') or scn.arp_engine_type in ['UNREAL', 'OTHERS']:
                    if scn.arp_init_fbx_rot:
                        initialize_fbx_armature_rotation("rig_mped")

                # Select objects to export
                _select_exportable(self.armature_name)
                
                # Rename "rig_mped" to def name
                #   avoid name clashing
                if scn.arp_export_rig_name == '':# should never be blank
                    scn.arp_export_rig_name = 'root'
                for obj in bpy.data.objects:
                    if obj.name == scn.arp_export_rig_name:
                        obj.name = scn.arp_export_rig_name + "_temp"

                rig_mped = get_object("rig_mped")
                rig_mped.name = scn.arp_export_rig_name
                rig_mped['arp_rig_name'] = self.armature_name+'_arpbob'
                
            
            # GLTF will rebake animation if there are any constraints, even muted
            # leading to always set keyf interp to linear
            # Delete constraints
            if self.export_format == 'GLTF':                
                bpy.ops.object.mode_set(mode='POSE')
                
                for pb in bpy.context.active_object.pose.bones:
                    for cns in pb.constraints:
                        if cns.enabled == False:
                            pb.constraints.remove(cns)
                            
                bpy.ops.object.mode_set(mode='OBJECT')
                
            
            # Rename to right names before export
            print("  Renaming to def names...")
            for obj in bpy.data.objects:
                if "_arpexp" in obj.name:
                    if get_object(obj.name.replace("_arpexp", "")):
                        #rename base object to "_arpbob" instead, temporarily
                        obj_name = obj.name.replace("_arpexp", "")
                        base_obj = get_object(obj_name)
                        base_obj.name = obj_name + "_arpbob"

                        #rename _arpexp to right name
                        obj.name = obj.name.replace('_arpexp', '')
                        
                        # rename object mesh data                        
                        if scn.arp_retro_ge_mesh == False and base_obj.data:
                            # base object
                            base_data_name = base_obj.data.name
                            try:
                                base_obj.data.name = base_data_name + '_arpbob'
                            except:# newer Blender version 4.1+ forbids that for linked meshes
                                pass
                                
                            # arpexp
                            obj.data.name = base_data_name
            
            #print(br)
            
            prep_time = round(time.time() - time_start, 2)
            export_timer_total += prep_time
            print("Export Prep Time:", prep_time, "seconds.")            
            
            # Export to file
            time_start = time.time()
            
            #   support of multiple files export, one per action
            export_ids = ['all_actions']
            
            if scn.arp_bake_type == 'ACTIONS' and scn.arp_export_separate_fbx and scn.arp_bake_anim:
                export_ids = [act.name for act in bpy.data.actions if is_action_exportable(act)]
                
                # action list may still be null if no exported actions are found. 
                # Set to 'all_actions' in that case
                if len(export_ids) == 0:
                    export_ids = ['all_actions']
            
            # Unity's bake axis conversion settings
            _apply_scale = 'FBX_SCALE_NONE'
            _axis_fwd = '-Z'
            _axis_up = 'Y'
            _use_st = True
            if (scn.arp_export_bake_axis_convert and scn.arp_engine_type == 'UNITY' and self.export_format == 'FBX'):
                print('\n  Apply Bake Axis Conversion settings...')
                _apply_scale = 'FBX_SCALE_ALL'
                _axis_fwd = '-Y'
                _axis_up = 'Z'            
                _use_st = False
            
            for export_id in export_ids:
                print('\n..............................'+self.export_format+' Export ' + '[' + export_id + ']..............................')

                def_fp = self.filepath
                if export_id != 'all_actions':
                    if scn.arp_export_file_separator == 'NONE':
                        dir_path = os.path.dirname(self.filepath)
                        def_fp = os.path.join(dir_path, export_id + '.fbx')
                    else:
                        def_fp = self.filepath[:-4] + scn.arp_export_file_separator + export_id + '.fbx'
                
                if self.export_format == 'FBX':
                    bpy.ops.arp_export_scene.fbx(filepath=def_fp, use_selection=True, 
                    global_scale=scn.arp_global_scale, apply_unit_scale=True, apply_scale_options=_apply_scale,
                    axis_forward=_axis_fwd, axis_up=_axis_up, use_space_transform=_use_st,
                    use_mesh_modifiers=scn.arp_apply_mods, use_subsurf=False, mesh_smooth_type=scn.arp_mesh_smooth_type,
                    use_armature_deform_only=True, add_leaf_bones=False, primary_bone_axis=scn.arp_bone_axis_primary_export, 
                    secondary_bone_axis=scn.arp_bone_axis_secondary_export,
                    use_tspace=scn.arp_use_tspace,
                    bake_anim_simplify_factor=scn.arp_simplify_fac, bake_anim_step=scn.arp_ge_bake_sample, bake_anim_force_startend_keying=scn.arp_ge_startend_keying,
                    shape_keys_baked_data=str(self.shape_keys_data), mesh_names_data=str(self.meshes_names_dict),
                    use_custom_props=True,
                    path_mode='COPY' if scn.arp_export_tex else 'AUTO', embed_textures=scn.arp_export_tex, export_action_only=export_id,
                    use_triangles=scn.arp_export_triangulate, colors_type=scn.arp_ge_vcol_type
                    )
                    
                elif self.export_format == 'GLTF':
                    from .. import glTF2ExportUserExtension
                    glTF2ExportUserExtension.export_action_only = export_id
                    def_fp = def_fp[:-4]# .FBX > .GLTF
                    
                    args = {
                        'filepath':def_fp, 'use_selection':True, 'export_format':scn.arp_ge_gltf_format,
                        'export_apply':scn.arp_apply_mods,# mesh modifiers
                        'export_texcoords':True, 'export_normals':True, 'export_colors':True, 
                        'export_animations':True, 'export_anim_single_armature':True, 'export_frame_range':False,
                        'export_force_sampling':scn.arp_ge_gltf_sample_anim, 'export_nla_strips':True if scn.arp_bake_type == 'ACTIONS' else False, 
                        'export_optimize_animation_size':False, 'export_reset_pose_bones':True, 'export_current_frame':False,
                        'export_morph':True, 'export_morph_normal':scn.arp_ge_gltf_sk_normals, 'export_morph_tangent':scn.arp_ge_gltf_sk_tangents,
                        'export_skins':True, 'export_all_influences':scn.arp_ge_gltf_all_inf, 'export_def_bones':True, 
                        'export_image_format':'AUTO' if scn.arp_export_tex else 'NONE', 'export_tangents':scn.arp_use_tspace, 'export_yup':True, 'export_attributes':True, 'export_materials':'EXPORT',
                        'export_extras':True
                        }
                    if bpy.app.version >= (3,6,0):
                        args['export_animation_mode'] = 'ACTIONS'
                        
                    bpy.ops.export_scene.gltf(**args)
        
            exporter_timer = round(time.time() - time_start, 2)
            export_timer_total += exporter_timer
            print(self.export_format, "Exporter Time:", exporter_timer, "seconds.")
            print(self.export_format, "(Total Time):", export_timer_total, "seconds.")
            
            
        #finally:
        #   pass
        
        finally:     
            time_start = time.time()
            
            if get_object(scn.arp_export_rig_name):
                # check if mesh objects have same names as bones
                bone_names = [b.name for b in get_object(scn.arp_export_rig_name).data.bones]

                for obj in bpy.data.objects:                
                    if len(obj.modifiers):# only skinned meshes
                        if obj.find_armature():
                            if obj.find_armature().name == scn.arp_export_rig_name:
                                if obj.name in bone_names:
                                    self.invalid_mesh_names.append(obj.name)
                
            # -- Revert Changes --
            # revert object names
            print("Revert object name changes...")
            for m in bpy.data.meshes:
                if '_ARPEXPORTTEMP' in m.name:
                    m.name = m.name.replace('_ARPEXPORTTEMP', '')
                    
            for obj in bpy.data.objects:
                if '_arpbob' in obj.name:
                    if get_object(obj.name.replace('_arpbob', '')):
                        # arpexp
                        obj_name = obj.name.replace('_arpbob', '')
                        obj_export = get_object(obj_name)
                        obj_export.name = obj_name + '_arpexp'

                        # base object
                        obj.name = obj.name.replace('_arpbob', '')
                        
                        # rename object mesh data
                        if scn.arp_retro_ge_mesh == False and obj_export.data:
                            # arpexp
                            base_data_name = obj_export.data.name
                            obj_export.data.name = base_data_name + '_arpexp'
                            
                            # base object
                            try:# newer Blender version 4.1+ forbids that for linked meshes
                                obj.data.name = base_data_name
                            except:
                                pass
                        
                    else:
                        print("    Cannot find base object name", obj.name)

            # revert animation curves location scale (x100 Units)
            if self.saved_unit_settings['scale_length'] != scn.unit_settings.scale_length:
                print("\nRevert units changes")
                for act_i in self.actions_x100_changed:
                    action_name = act_i[0]
                    lib = act_i[1]
                    action = None
                    
                    if lib:
                        for act in bpy.data.actions:
                            if act.name == action_name and act.library == lib:
                                action = act
                    else:
                        action = bpy.data.actions[action_name]
                    #print("RESTORING ACTION SCALE", action_name)
                    for fcurve in action.fcurves:
                        if 'location' in fcurve.data_path:
                            for point in fcurve.keyframe_points:
                                point.co[1] *= 0.01
                                point.handle_left[1] *= 0.01
                                point.handle_right[1] *= 0.01
                
                if "action_name" in locals():
                    del action_name
                
                # start by restoring the unit system value, since changing it will unexpectedly reset others to default values
                scn.unit_settings.system = self.saved_unit_settings['system']
                
                for prop_name in self.saved_unit_settings:
                    if prop_name != 'system':
                        value = self.saved_unit_settings[prop_name]
                        try:# if Unit System is None, the attributes may be locked
                            setattr(scn.unit_settings, prop_name, value)
                        except:
                            pass
                

            # revert actions
            if scn.arp_bake_anim:
                print("Reverting baked actions...")

                for action in bpy.data.actions:
                    if not check_id_root(action):
                        continue
                    if not len(action.keys()):
                        continue
                    if not "arp_baked_action" in action.keys():
                        continue

                    base_action_name = action.name+"_%temp"

                    if scn.arp_retro_action_prefix:
                        trim_idx = 2
                        if scn.arp_export_rig_type == 'UNIVERSAL':
                            trim_idx = 3
                        base_action_name = action.name[trim_idx:]+"_%temp"
                    #print("removing action", action.name)
                    bpy.data.actions.remove(action, do_unlink=True)

                    base_action = bpy.data.actions.get(base_action_name)
                    if base_action == None:
                        print(base_action_name, "not found, skip")
                        continue
                    base_action.name = base_action_name.replace("_%temp", "")

            # revert animation curves initialized scale
            if self.arm_scale != 1.0:
                print("\nRevert action translation scale, since armature scale is:", self.arm_scale)
                for actionname in self.actions_units_changed:
                    action = bpy.data.actions[actionname]
                    print('  revert action', action.name)
                    for fcurve in action.fcurves:
                        # only bones have scaled location because of armature scale initilalized, because they're in armature space
                        # object (armature) don't need it
                        if 'location' in fcurve.data_path and "pose.bones[" in fcurve.data_path:
                            for point in fcurve.keyframe_points:
                                point.co[1] *= 1/self.arm_scale
                                point.handle_left[1] *= 1/self.arm_scale
                                point.handle_right[1] *= 1/self.arm_scale

            # revert push bend bones
            if scn.arp_keep_bend_bones and scn.arp_push_bend and (get_object(self.armature_name).arp_secondary_type == "ADDITIVE"):
                print("\nRevert Push Bend Bones")
                for _actionname in self.actions_pushed_changed:
                    _action = bpy.data.actions[_actionname]
                    _push_bend_bones(_action, 0.5)


            print("Deleting copies...")

            for obj in bpy.data.objects:
                # Remove arp_parent_bone tag
                if obj.get("arp_parent_bone"):
                    del obj["arp_parent_bone"]

                if "_arpexp" in obj.name or obj.name == "rig_humanoid" or obj.name == scn.arp_export_rig_name or obj.name == "rig_mped" or "arp_dummy_mesh" in obj.name:
                    # make sure to remove armature data too
                    if obj.type == "ARMATURE":
                        arm_data = bpy.data.armatures.get(obj.data.name)

                    delete_object(obj)
                    try:
                        bpy.data.armatures.remove(arm_data, do_unlink=True)
                    except:
                        pass

            for m in bpy.data.meshes:
                if "arp_dummy_mesh" in m.name:
                    bpy.data.meshes.remove(m, do_unlink = True)

            # Rename the renamed root/arp_export_rig_name object if any
            if get_object(scn.arp_export_rig_name + "_temp"):
                get_object(scn.arp_export_rig_name + "_temp").name = scn.arp_export_rig_name

            # Hide rig_add
            if self.armature_add_name:
                rig_add_ob = get_object(self.armature_add_name)
                if rig_add_ob:
                    hide_object(rig_add_ob)

            # Set auto-key if needed
            scn.tool_settings.use_keyframe_insert_auto = self.save_auto_key

            # Restore collections visibility
            for i, vis_value in enumerate(self.saved_collection_vis):
                bpy.data.collections[i].hide_viewport = vis_value

            # Unlink linked collection (if proxy)
            if self.linked_collection and self.collection_has_been_linked:
                scn.collection.children.unlink(bpy.data.collections.get(self.linked_collection))
                print("Proxy Character collection unlinked.")

            # Restore current frame
            scn.frame_current = current_frame_saved
            
            
            #Restore the proxy picker
            restore_picker(proxy_picker_value)

            # Restore selection
            set_active_object(self.current_selection[0])
            for i in self.current_selection[1]:
                get_object(i).select_set(True)                
            
            # Restore NLA tweak mode
            nla_restore_tweak(self.NLA_tweak_state)               
            
            bpy.context.evaluated_depsgraph_get().update()

            # Workaround to fix the update issue (mesh is kind of frozen, jiggle) with proxy armatures
            if self.armature_proxy_name:
                base_arm_proxy = get_object(self.armature_name)      
                hide_object(base_arm_proxy)
                bpy.context.evaluated_depsgraph_get().update()
                unhide_object(base_arm_proxy)
            print("\nARP" + self.export_format + " Export Done!")   

            revert_timer = round(time.time() - time_start, 2)
            export_timer_total += revert_timer
            print("Revert changes time:", revert_timer, "seconds.")
        
        self.report({'INFO'}, 'Character Exported')
        
        
        #   show popup message
        prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
        
        if prefs.show_export_popup or len(self.non_armature_actions) or len(self.invalid_mesh_names):        
            # set text
            fp = self.filepath
            '''# limit line length, disable for now
            max_len = 69
            if len(self.filepath) > max_len:
                fp = fp[:max_len]+'\n'+fp[max_len:]
            '''
            self.message_final = fp+'\n'
            minutes = export_timer_total//60 
            time_mess = ''
            if minutes > 0:
                plural='' if minutes <= 1 else 's'              
                time_mess += str(int(minutes))+' minute'+plural+' and '
            time_mess += str(int(export_timer_total%60))+' seconds'
            self.message_final += '('+time_mess+')'
            
            # invalid actions
            if len(self.non_armature_actions):
                self.message_final += '\nSome actions have been exported, that do not contain bones data:'
                for act_name in self.non_armature_actions:
                    self.message_final += '\n " '+act_name+' "'
                self.message_final += '\nMay corrupt character animation!\nMake sure to export only valid rig actions\n'
              
            # object/bone names conflict
            if len(self.invalid_mesh_names):
                self.message_final += '\nSome objects have names identical to bones names.\nThey will likely conflict on import. Renaming is recommended:'
                for objname in self.invalid_mesh_names:
                    self.message_final += '\n" ' + objname + ' "'
                self.message_final += '\n'
            
            # display
            #auto_rig.display_popup_message(self.message_final, header='Export Complete!', icon_type='INFO')
            # the report_message() function does display Ok-Cancel button unfortunately, but only way to prevent the popup to close automatically if the cursor has moved
            bpy.ops.arp.report_message('INVOKE_DEFAULT', message=self.message_final, icon_type = 'INFO')
            print(self.message_final)

        return {'FINISHED'}


    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ARP_OT_bind_humanoid(Operator):

    #tooltip
    """Bind the Humanoid armature to the Auto-Rig Pro armature"""

    bl_idname = "id.bind_humanoid"
    bl_label = "bind_humanoid"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.active_object:
            if get_object("rig_humanoid") != None:
                if len(get_object('rig_humanoid').keys()) > 0:
                    #if 'set' in get_object('rig_humanoid').keys():
                    if get_object('rig_humanoid')['binded'] == 0:# and get_object('rig_humanoid')['set'] == 1:
                        return True
                    else:
                        return False
                else:
                    return True
            else:
                return False


    def execute(self, context):
        if get_object("rig_humanoid") == None:
            self.report({'ERROR'}, "Please append the Humanoid armature in the scene.")
            return{'FINISHED'}

        if get_object("rig") == None:
            self.report({'ERROR'}, "Please append the Auto-Rig Pro armature in the scene.")
            return{'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        #save current state
        current_mode = context.mode
        current_obj = context.active_object

        _constraint_rig(False)

        #restore state
        try:
            set_active_object(current_obj.name)
            bpy.ops.object.mode_set(mode=current_mode)

        except:
            pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_unbind_humanoid(Operator):
    """Unbind the Humanoid armature to the Auto-Rig Pro armature. \nUnbind when exporting multiple baked actions. Bind before baking actions"""

    bl_idname = "id.unbind_humanoid"
    bl_label = "unbind_humanoid"
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        if context.active_object:
            rig_h = get_object("rig_humanoid")
            if rig_h:
                if rig_h.keys() > 0:
                    if rig_h['binded'] == 1:
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False


    def execute(self, context):
        if get_object("rig_humanoid") == None:
            self.report({'ERROR'}, "Please append the Humanoid armature in the scene.")
            return{'FINISHED'}

        if get_object("rig") == None:
            self.report({'ERROR'}, "Please append the Auto-Rig Pro armature in the scene.")
            return{'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        #save current state
        current_mode = context.mode
        current_obj = context.active_object

        _constraint_rig(True)

        try:
            set_active_object(current_obj.name)
            bpy.ops.object.mode_set(mode=current_mode)
        except:
            pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}




############ FUNCTIONS ##############################################################
def _save_preset(self):
    scn = bpy.context.scene
    
    settings_list = ['arp_export_rig_type', 'arp_engine_type', 'arp_ue4', 'arp_rename_for_ue', 'arp_rename_for_godot', 'arp_export_twist', 'arp_twist_fac', 'arp_keep_bend_bones', 'arp_full_facial', 'arp_push_bend', 'arp_mannequin_axes', 'arp_ue_ik', 'arp_ue_ik_anim', 'arp_ue_root_motion', 'arp_only_containing', 'arp_export_name_string', 'arp_units_x100', 'arp_bake_anim', 'arp_bake_type', 'arp_frame_range_type', 'arp_export_start_frame', 'arp_export_end_frame', 'arp_bake_only_active', 'arp_simplify_fac', 'arp_ge_bake_sample', 'arp_ge_startend_keying', 'arp_global_scale', 'arp_mesh_smooth_type', 'arp_use_tspace', 'arp_bone_axis_primary_export', 'arp_bone_axis_secondary_export', 'arp_fix_fbx_rot', 'arp_fix_fbx_matrix', 'arp_init_fbx_rot', 'arp_init_fbx_rot_mesh', 'arp_export_tex', 'arp_ge_sel_only', 'arp_ge_sel_bones_only', 'arp_see_actions', 'arp_export_noparent', 'arp_export_rig_name', 'arp_export_act_name', 'arp_export_file_separator', 'arp_export_actlist_idx', 'arp_export_use_actlist', 'arp_export_separate_fbx', 'arp_export_renaming', 'arp_rename_fp', 'arp_custom_export_script', 'arp_apply_mods', 'arp_apply_subsurf', 'arp_retro_ge_UE_twist_pos', 'arp_retro_ge_frame_range', 'arp_export_bake_axis_convert', 'arp_ge_add_dummy_mesh', 'arp_ge_force_rest_pose_export', 'arp_ge_gltf_format', 'arp_ge_gltf_all_inf', 'arp_ge_gltf_sk_normals', 'arp_ge_gltf_sk_tangents', 'arp_ge_gltf_unitsx100', 'arp_ge_gltf_sample_anim', 'arp_export_triangulate', 'arp_ge_vcol_type', 'arp_ge_master_traj', 'arp_ge_export_metacarp', 'arp_export_actlist']
    
    export_settings = {}
    for setting in settings_list:
        if setting == 'arp_export_actlist':# need to convert CollectionProperties to string manually
            actlists = {}
            for actlist in scn.arp_export_actlist:
                #name, actions, exportable    
                actions_dict = {}
                for act in actlist.actions:
                    exportable = True
                    if 'arp_export' in act.action.keys():
                        exportable = act.action['arp_export']
                    actions_dict[act.action.name] = exportable
                    
                actlists[actlist.name] = [actlist.exportable, actions_dict]
            
            export_settings[setting] = actlists
        else:
            export_settings[setting] = getattr(scn, setting)

    file = open(self.filepath, 'w', encoding='utf8', newline='\n')
    
    file.write(str(export_settings))
    file.close()
    print('Exported preset file:', self.filepath)
    

def _load_preset(self):
    filepath = self.filepath
    scn = bpy.context.scene
   
    # read file
    file = open(filepath, 'r') if sys.version_info >= (3, 11) else open(filepath, 'rU')
  
    file_lines = file.readlines()
    settings_list_str = str(file_lines[0])
    file.close()
    
    # import data
    settings_list = ast.literal_eval(settings_list_str)     
    
    for setting in settings_list:
    
        # need to convert dict to CollectionProperties manually
        if setting == 'arp_export_actlist':
            print('Import arp_export_actlist')
            actlists = settings_list[setting]
            for actlist_name in actlists:
                print('  import Action List:', actlist_name)
                actlist = scn.arp_export_actlist.get(actlist_name)
                if actlist == None:# create Actions List
                    print('Create Action List', actlist_name)
                    actlist = scn.arp_export_actlist.add()
                    actlist.name = actlist_name
                
                actlist_settings = actlists[actlist_name]# > [exportable, actions_dict]            
                actlist.exportable = actlist_settings[0]
                
                actions_dict = actlist_settings[1]
                
                # add Actions to Actions List
                for act_name in actions_dict:
                    is_action_exportable = actions_dict[act_name]
                    
                    action = bpy.data.actions.get(act_name)
                    
                    # if the action does not exist in the file, skip
                    if action == None:
                        continue
                        
                    # does the action item already exist?
                    action_item = None
                    for act_item in actlist.actions:
                        try:
                            if act_item.action.name == act_name:
                                action_item = act_item
                                break
                        except:
                            pass
                    
                     # create it if necessary
                    if action_item == None:
                        action_item = actlist.actions.add()
                        action_item.action = action
                        action['arp_export'] = is_action_exportable
           
        # standard auto settings
        else:
            setting_val = settings_list[setting]
            try:
                setattr(scn, setting, setting_val)
            except:
                print('Setting not found, skip:', setting)
        

    print('Imported preset file:', filepath)


def _add_actions_list_action(self):
    scn = bpy.context.scene
    current_actlist = scn.arp_export_actlist[scn.arp_export_actlist_idx]


    # only if the action field is set
    if current_actlist.action_to_add:

        # Clean-up
        # actions may have been deleted by the user previously
        # then look for None actions and remove them from the set
        if len(current_actlist.actions):
            print('Remove invalids...')
            print('initial length', len(current_actlist.actions))

            complete = False
            while complete == False:
                found_none = False
                for i, act in enumerate(current_actlist.actions):
                    print(i)
                    if act.action == None:
                        print('  Remove', i)
                        current_actlist.actions.remove(i)
                        found_none = True
                        break
                        
                if found_none == False:       
                    complete = True
                    
            print('Invalid removed.')
            
        
        found = False
        # make sure the action is not already in it
        if len(current_actlist.actions):
            for act in current_actlist.actions:                
                if act.action.name == current_actlist.action_to_add.name:
                    found = True
                    print('Action already in, do not add it')

        # add it
        if not found:
            new_action = current_actlist.actions.add()
            new_action.action = current_actlist.action_to_add


def _remove_actions_list_action(self):
    scn = bpy.context.scene
    action_to_remove = bpy.data.actions.get(self.action_name)

    if action_to_remove:
        current_actlist = scn.arp_export_actlist[scn.arp_export_actlist_idx]

        for i, act_item in enumerate(current_actlist.actions):
            if act_item.action == action_to_remove:
                current_actlist.actions.remove(i)


def _add_actions_list(self):
    scn = bpy.context.scene
    actionslist = scn.arp_export_actlist.add()
    actionslist.name = 'ActionsList'
    scn.arp_export_actlist_idx = len(scn.arp_export_actlist)-1


def _remove_actions_list(self):
    scn = bpy.context.scene
    scn.arp_export_actlist.remove(scn.arp_export_actlist_idx)

    if scn.arp_export_actlist_idx > len(scn.arp_export_actlist)-1:
        scn.arp_export_actlist_idx = len(scn.arp_export_actlist)-1


def restore_picker(value):
    scn = bpy.context.scene
    if value != None:
        try:
            scn.Proxy_Picker.active = value
        except:
            pass


def disable_proxy_picker():
    scn = bpy.context.scene
    proxy_picker_value = False
    try:
        proxy_picker_value = scn.Proxy_Picker.active
        scn.Proxy_Picker.active = False
    except:
        pass

    return proxy_picker_value


def check_humanoid_limbs():
    # check if the rig limbs are set up as a humanoid
    context = bpy.context
    rig = context.active_object

    limb_sides.get_multi_limbs()

    three_bones_leg = False
    # check if there are 3 bones legs
    for lside in limb_sides.leg_sides:
        if get_data_bone("thigh_b_ref"+lside):
            three_bones_leg = True
            break

    found_root = True
    if get_data_bone("c_root_master.x") == None:
        found_root = False

    if context.scene.arp_export_rig_type == 'HUMANOID':
        #print(len(limb_sides.arm_sides), len(limb_sides.leg_sides), len(limb_sides.head_sides), len(limb_sides.ear_sides), found_root, rig.rig_spine_count, three_bones_leg)
        if (len(limb_sides.leg_sides) > 2 or len(limb_sides.head_sides) > 1 or len(limb_sides.ear_sides) > 2 or not found_root or rig.rig_spine_count < 1) or three_bones_leg:
            return False

    return True


def create_copies(self):
    print("\nCreate copies...")
    scn = bpy.context.scene
    # proxy?
    if self.armature_proxy_name:
        print("  The armature is a proxy. Real name =", self.armature_proxy_name)
    
    arm = get_object(self.armature_name)
    
    # store actions
    actions_list = [action.name for action in bpy.data.actions]
    rig_action = None
    if arm.animation_data:
        if arm.animation_data.action:
            rig_action = arm.animation_data.action

    # get meshes
    print("  Get character objects...")
    
    self.char_objects, self.spline_objects = get_char_objects(self, arm_name=self.armature_name, arm_add_name=self.armature_add_name, arm_proxy=self.armature_proxy_name, arm_source=self.armature_source_name)
    if len(self.char_objects) <= 10:
        print("  Character objects:", self.char_objects)
    else:
        print_list = [self.char_objects[i] for i in range(0,10)]
        print("  Character objects:", print_list, "... and", str(len(self.char_objects)-10), "others")

    if len(self.spline_objects):
        print("  Spline objects:", self.spline_objects)

    #clear selection and mode
    set_active_object(self.armature_name)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    
    # set back to rest pose to avoid Spline IK hook offsets
    arm.data.pose_position = 'REST'
    
    def duplicate_active_object():
        obj_dupli = bpy.context.active_object.copy()
        obj_dupli.data = obj_dupli.data.copy()
        scn.collection.objects.link(obj_dupli)
        #bpy.ops.object.make_single_user(object=True, obdata=True, material=False, animation=False)
        bpy.context.view_layer.update()

        return obj_dupli
        
            
    # duplicate
    for obj_name in self.char_objects + self.spline_objects:
        print("  operating on object", obj_name)
        
        # make sure it's selectable
        unhide_object(get_object(obj_name))
        selectable_state = get_object(obj_name).hide_select
        get_object(obj_name).hide_select = False
        bpy.context.evaluated_depsgraph_get().update()

        # select it
        set_active_object(obj_name)

        # switch to Object Mode
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass

        # get shape key action if any
        current_sk_action = None
        try:
            current_sk_action = get_object(obj_name).data.shape_keys.animation_data.action
        except:
            pass

        # duplicate
        obj_dupli = duplicate_active_object()

        # select duplicate
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(obj_dupli.name)

        # previous method, doesn't seem anymore needed with newer duplication method
        # make duplicated proxy objects editable for Blender versions >= 2.90, (already editable by default with previous versions)
        #if self.armature_proxy_name and utils.blender_version._float >= 290:
        #    obj_dupli.data = obj_dupli.data.copy()
        #    bpy.ops.object.make_local(type='SELECT_OBDATA')
        #    bpy.ops.object.make_single_user(object=True, obdata=True, material=False, animation=False)
        
        if self.is_override:
            #obj_dupli.data = obj_dupli.data.copy()
            bpy.ops.object.make_local(type='SELECT_OBDATA')
            #bpy.ops.object.make_single_user(object=True, obdata=True, material=False, animation=False)

        obj_dupli.name = obj_name + "_arpexp"
        
        # store the mesh data names match in a dict, in case the original data name cannot be renamed because it is linked + shape keys without drivers
        # in order to debug the shape_keys_bake_dict
        if get_object(obj_name).type == "MESH":
            self.meshes_names_dict[obj_dupli.data.name] = get_object(obj_name).data.name
            
        # assign object's shape key action if any
        if current_sk_action != None:
            bpy.context.active_object.data.shape_keys.animation_data.action = current_sk_action
            #print("  Assign action", current_sk_action.name)
        
        bpy.ops.object.select_all(action='DESELECT')

        # restore selectable state
        if get_object(obj_name):
            get_object(obj_name).hide_select = selectable_state


    rig_arpexp = get_object(self.armature_name+"_arpexp")
    
    # set back to pose
    arm.data.pose_position = rig_arpexp.data.pose_position = 'POSE'
  
    
    # Fix for driver dependency updates problems with proxy armatures
    if self.armature_proxy_name or self.armature_source_name:

        # unprotect layers
        if bpy.app.version < (4,0,0):
            for i in range(0,32):
                rig_arpexp.data.layers_protected[i] = False

        # hack for driver updates
        drivers_arm = rig_arpexp.animation_data.drivers
        for dr in drivers_arm:
            dr.driver.expression += " "
            dr.driver.expression = dr.driver.expression[:-1]

        # remap shape keys drivers target object to the armature duplicate
        to_replace = ""
        if self.armature_proxy_name:
            to_replace = self.armature_proxy_name
        elif self.armature_source_name:
            to_replace = self.armature_source_name

        for obj_name in self.char_objects:
            ob = get_object(obj_name + "_arpexp")

            if ob.type != "MESH":
                continue

            drivers = get_shape_keys_drivers(ob)
            if drivers:
                for dr in drivers:
                    replace_driver_target_object(dr, to_replace, self.armature_name + "_arpexp")

    
    # apply topology changing and deforming modifiers with shape keys
    mods_types_deform = ['NORMAL_EDIT', 'WEIGHTED_NORMAL', 'ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE', 'EDGE_SPLIT', 'NODES', 'MASK',
                            'MIRROR', 'REMSESH', 'SCREW', 'SKIN', 'SOLIDIFY', 'TRIANGULATE', 'SUBSURF', 'TRIANGULATE', 'VOLUME_TO_MESH', 'WELD',
                            'WIREFRAME', 'CAST', 'CURVE', 'DISPLACE', 'HOOK', 'LAPLACIANDEFORM', 'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 
                            'SIMPLE_DEFORM', 'SMOOTH', 'CORRECTIVE_SMOOTH', 'LAPLACIANSMOOTH', 'SURFACE_DEFORM', 'WARP', 'WAVE', 'CLOTH', 'EXPLODE',
                            'FLUID', 'OCEAN', 'SOFT_BODY']
                            
    exclude_mods = ['ARMATURE', 'SUBSURF']
    if scn.arp_apply_subsurf:
        exclude_mods.remove('SUBSURF')
     
    if scn.arp_apply_mods:
        arm.data.pose_position = rig_arpexp.data.pose_position = 'REST'
        
        for obj_name in self.char_objects + self.spline_objects:
            obj_sk = get_object(obj_name+'_arpexp')
            apply_sk_mods = False
            if obj_sk.type == "MESH":     
                # if subsurf export disabled, remove subsurf modifiers, to prevent apply when real Fbx export
                if scn.arp_apply_subsurf == False:                    
                    for mod in obj_sk.modifiers:
                        if mod.type == 'SUBSURF':
                            obj_sk.modifiers.remove(mod)
                            
                # if has shape keys and 'deform' modifiers, tag it to apply modifiers
                if obj_sk.data.shape_keys and len(obj_sk.modifiers):
                    if len(obj_sk.data.shape_keys.key_blocks):
                        for mod in obj_sk.modifiers:
                            if mod.type in mods_types_deform:
                                apply_sk_mods = True
                                
            if apply_sk_mods:
                # duplicate the mesh
                print("  Applying topology changing/deforming modifiers with shape keys of object: ["+obj_sk.name+"]...")
                bpy.ops.object.select_all(action='DESELECT')
                set_active_object(obj_sk.name)
                dupli_mesh = duplicate_active_object()

                # store driver variables with shape keys as target, since the mesh duplication does not preserve them
                sk_driver_dict = {}
                sk_anim_data = obj_sk.data.shape_keys.animation_data
                if sk_anim_data and sk_anim_data.drivers:
                    for dr in sk_anim_data.drivers:
                        for i, var in enumerate(dr.driver.variables):
                            if var.targets[0].id_type == 'KEY':
                                target_id = var.targets[0].id
                                if target_id:
                                    sk_driver_dict[dr.data_path+' '+var.name] = dr.data_path, var.name, target_id.name          
                                
                                
                # delete shape keys on the original mesh
                print("  remove shape keys data...")
                set_active_object(obj_sk.name)
                for i in reversed(range(len(obj_sk.data.shape_keys.key_blocks))):
                    #print("remove sk", obj_sk.data.shape_keys.key_blocks[i])
                    obj_sk.active_shape_key_index = i
                    bpy.ops.object.shape_key_remove()
                    
                # apply modifiers
                for mod in obj_sk.modifiers:
                    if mod.type in exclude_mods or mod.show_render == False:
                        continue
                    if mod.show_render and mod.show_viewport == False:
                        mod.show_viewport = True
                    set_active_object(obj_sk.name)
                    apply_modifier(mod.name)

                # transfer shape keys
                print("  transfer shape keys data...", dupli_mesh.name + ' > ' + obj_sk.name)
                
                transfer_shape_keys_deformed(dupli_mesh, obj_sk, apply_mods=True)
                
                # restore driver variables with shape keys as target
                for dp_var in sk_driver_dict:
                    sk_anim_data = obj_sk.data.shape_keys.animation_data
                    dp, var_name, shape_keys_name = sk_driver_dict[dp_var]            
                    dr = sk_anim_data.drivers.find(dp)
                    var = dr.driver.variables.get(var_name)
                    var.targets[0].id = bpy.data.shape_keys.get(shape_keys_name)
                
                # NLA shape keys tracks must be backed up too
                copy_shapekeys_tracks(dupli_mesh, obj_sk)

                # delete duplicate
                if dupli_mesh:
                    bpy.data.objects.remove(dupli_mesh, do_unlink=True)
                
                print("  Done")
                        
        arm.data.pose_position = rig_arpexp.data.pose_position = 'POSE'
    
    # parent meshes to armature
    for obj_name in self.char_objects + self.spline_objects:        
        ob = get_object(obj_name + '_arpexp')
        if ob.type == 'MESH' or ob.type == 'CURVE':
            ob_mat = ob.matrix_world.copy()
            # preserve mesh-mesh parent
            mesh_parent = False
            if ob.parent:
                if ob.parent.type == 'MESH' and ob.parent.name in self.char_objects:
                    mesh_parent = True
                    par_name = ob.parent.name if '_arpexp' in ob.parent.name else ob.parent.name+'_arpexp'                  
                    ob.parent = get_object(par_name)
            # else, parent to armature
            if not mesh_parent:
                ob.parent = get_object(self.armature_name+'_arpexp')
                
            ob.matrix_world = ob_mat

    deforming_arm = self.armature_name

    if self.armature_proxy_name:
        deforming_arm = self.armature_proxy_name

    # retarget modifiers
    # assign the _arpexp rig as target for armature and hooks modifiers
    # and retarget target object
    for obj in bpy.data.objects:
        if not '_arpexp' in obj.name:
            continue
        if obj.type != 'MESH' and obj.type != 'CURVE':
            continue
        if len(obj.modifiers) == 0:
            continue

        valid_armature_mod = None

        for mod in obj.modifiers:

            # Retarget modifiers objects
            if 'target' in dir(mod):
                if mod.target:
                    mod.target = get_object(mod.target.name + '_arpexp')

            if mod.type != 'ARMATURE' and mod.type != 'HOOK':
                continue

            if mod.object != None:
                if mod.object.name == deforming_arm:
                    mod.object = get_object(self.armature_name + '_arpexp')

                    if valid_armature_mod == None:
                        valid_armature_mod = mod.name

                # delete the rig_add modifier
                if mod.object != None:
                    if 'rig_add' in mod.object.name:
                        obj.modifiers.remove(mod)

        # multiple armatures modifiers are not handled, only keep one
        if valid_armature_mod == None:
            continue
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.name != valid_armature_mod:
                obj.modifiers.remove(mod)


    # Link the duplicated armature to the duplicated IK splines if any
    # This fixes cyclic errors when IK spline bones remain linked to the original proxy armature/ curves
    if len(self.spline_objects):
        bpy.ops.object.mode_set(mode='OBJECT')
        set_active_object(rig_arpexp.name)
        
        # change Spline IK constraint targets
        for b in rig_arpexp.pose.bones:
            if not is_bone_in_layer(b.name, 'mch_01'):
                continue
            if len(b.constraints):
                for cns in b.constraints:
                    if cns.type != "SPLINE_IK":
                        continue
                    if cns.target == None:
                        continue
                    if not "_arpexp" in cns.target.name:
                        cns.target = get_object(cns.target.name+"_arpexp")

    
    # delete duplicated actions
    for action in bpy.data.actions:
        if not action.name in actions_list:
            bpy.data.actions.remove(action, do_unlink=True)

    # assign the current action to the duplicated rig   
    if rig_action:
        get_object(self.armature_name+"_arpexp").animation_data.action = rig_action

    print("Copied.")

def is_proxy_bone(bone):
    if bone.parent:
        bone_parent1 = bone.parent.name
    else:
        bone_parent1 = "None"

    if '_proxy' in bone.name or 'Picker' in bone_parent1 or bone.name == "Picker":
        return True
        

def set_inverse_child(b, cns_name):
    pbone = bpy.context.active_object.pose.bones[b]
    context_copy = bpy.context.copy()
    context_copy["constraint"] = pbone.constraints[cns_name]
    bpy.context.active_object.data.bones.active = pbone.bone
    try:
        bpy.ops.constraint.childof_set_inverse(context_copy, constraint=cns_name, owner='BONE')
    except:
        print('Invalid bone constraint to set inverse child, skip it', b)


def is_facial_enabled(armature):
    # for single head skeleton only
    head_ref = armature.data.bones.get('head_ref.x')
    if head_ref:
        if 'facial' in head_ref.keys():    
            if head_ref['facial'] == 1:
                return True
        else:# backward-compatibility, "manual" evaluation       
            return bool(armature.data.bones.get("jaw_ref.x"))
    return False


def is_facial_bone(bone_name):
    for facebone in default_facial_bones:
        if facebone in bone_name:
            return True

    for facebone1 in additional_facial_bones:
        if facebone1 in bone_name:
            return True


def is_bend_bone(bone_name):
    for bbone in bend_bones:
        if bbone in bone_name:
            return True


def is_bend_bone_spine_only(bone_name):
    for bbone in bend_bones_spine_only:
        if bbone in bone_name:
            return True


def _push_bend_bones(act, fac):
    for fcurve in act.fcurves:
        for bbone in bend_bones_add:
            if bbone in fcurve.data_path:
                for key in fcurve.keyframe_points:
                    if not 'scale' in fcurve.data_path:
                        key.co[1] *= fac
                        key.handle_left[1] *= fac
                        key.handle_right[1] *= fac

                    else:
                        key.co[1] = 1 + (key.co[1] -1) * fac
                        key.handle_left[1] = 1 + (key.handle_left[1] -1) * fac
                        key.handle_right[1] = 1 + (key.handle_right[1] -1) * fac
                break


def init_armatures_scales(armature_name, armature_add_name, self):

    rig_humanoid = None

    set_active_object(armature_name + "_arpexp")
    bpy.ops.object.mode_set(mode='OBJECT')

    arp_armature = get_object(armature_name+'_arpexp')
    rig_scale = arp_armature.scale[0]
    rig_add = None
    if armature_add_name:
        rig_add = get_object(armature_add_name + '_arpexp')
    if rig_add:
        unhide_object(rig_add)

    # Apply Scale
    if rig_add:
        rig_add.scale = arp_armature.scale
    if get_object("rig_humanoid"):
        rig_humanoid = get_object("rig_humanoid")
        rig_humanoid.scale = arp_armature.scale

    if rig_add:
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(rig_add.name)
        bpy.ops.object.mode_set(mode='OBJECT')
        # apply scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(arp_armature.name)
    bpy.ops.object.mode_set(mode='EDIT')

    roll_dict = {}
    for ebone in bpy.context.active_object.data.edit_bones:
        roll_dict[ebone.name] = ebone.roll

    bpy.ops.object.mode_set(mode='OBJECT')
    # apply scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # bug, applying armature scale may lead to incorrect bone roll
    # copy back roll from previous state
    bpy.ops.object.mode_set(mode='EDIT')
    for ebone_name in roll_dict:
        get_edit_bone(ebone_name).roll = roll_dict[ebone_name]

    bpy.ops.object.mode_set(mode='OBJECT')

    print("scaling location:", rig_scale)
    # Apply scale to animation curves
    
    for action in bpy.data.actions:
        has_changed = False
        for fcurve in action.fcurves:
            skip = False
            if 'location' in fcurve.data_path and fcurve.data_path.startswith("pose.bones["):
                for point in fcurve.keyframe_points:
                    point.co[1] *= rig_scale
                    point.handle_left[1] *= rig_scale
                    point.handle_right[1] *= rig_scale
                    has_changed = True

        # keep track of modified actions to revert later
        if has_changed:
            self.actions_units_changed.append(action.name)
            
    # Apply scale to Transformation constraints
    bpy.ops.object.mode_set(mode='POSE')
    
    for pb in bpy.context.active_object.pose.bones:
        if len(pb.constraints):
            for cns in pb.constraints:
                if cns.type == "TRANSFORM":
                    if cns.subtarget.startswith('c_foot_roll_cursor'):
                        cns.from_min_x *= rig_scale
                        cns.from_max_x *= rig_scale
                        cns.from_min_z *= rig_scale
                        cns.from_max_z *= rig_scale
    
    # Reset stretches
        #store active pose    
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.copy()

        #need to reset the pose
    auto_rig_reset.reset_all()
        #reset constraints
    for pbone in bpy.context.active_object.pose.bones:
        try:
            pbone.constraints["Stretch To"].rest_length = 0.0
        except:
            pass

        #restore the pose
    bpy.ops.pose.paste(flipped=False)

    if rig_add:
        hide_object(rig_add)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


    # Rig Humanoid
    if get_object("rig_humanoid"):
        # Apply Scale
        rig_humanoid = get_object("rig_humanoid")

        set_active_object("rig_humanoid")
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Reset Child Of constraints

        #   bind to main armature if not bound
        bind_state = rig_humanoid["binded"]
        _constraint_rig(False)

        #   set arp in rest pose
        arp_armature.data.pose_position = "REST"
        bpy.context.evaluated_depsgraph_get().update()

        #   reset child of constraints
        bpy.ops.object.mode_set(mode='POSE')
        
        _layers = enable_all_armature_layers()

        for pbone in bpy.context.active_object.pose.bones:
            if len(pbone.constraints) > 0:
                for cns in pbone.constraints:
                    if 'Child Of' in cns.name:
                        set_inverse_child(pbone.name, cns.name)

        restore_armature_layers(_layers)

        #restore bind state
        if bind_state == 0:
            _constraint_rig(True)

        #Set arp in pose
        arp_armature.data.pose_position = "POSE"
        bpy.context.evaluated_depsgraph_get().update()


def parent_meshes_to_baked_armature(self, baked_armature_name):
    baked_armature = get_object(baked_armature_name)
    armature_base = get_object(self.armature_name)
    armature_arpexp = get_object(self.armature_name + "_arpexp")

    # set to rest pose
    armature_base.data.pose_position = 'REST'
    armature_arpexp.data.pose_position = 'REST'
    baked_armature.data.pose_position = 'REST'

    # clear actions
    current_action = None
    if baked_armature.animation_data:
        current_action = baked_armature.animation_data.action
        baked_armature.animation_data.action = None
        
    
    if armature_arpexp.animation_data:
        armature_arpexp.animation_data.action = None
        
    #  disable any drivers on transforms channels temporarily
    arm_exp_dr_muted = []
    if armature_arpexp.animation_data:
        for dr in armature_arpexp.animation_data.drivers:
            if dr.data_path in ['location', 'rotation_euler', 'rotation_quaternion', 'scale']:
                if dr.mute == False:
                    dr.mute = True
                    arm_exp_dr_muted.append([dr.data_path, dr.array_index])    
    
    # disable constraints temporarily
    arm_exp_cns_muted = []
    for cns in armature_arpexp.constraints:
        if cns.enabled:
            cns.enabled = False
            arm_exp_cns_muted.append(cns.name)
            
                
    # init location, rotation    
    armature_arpexp.location = armature_arpexp.rotation_euler = [0,0,0]
    baked_armature_loc_rot = [baked_armature.location.copy(), baked_armature.rotation_euler.copy()]
    baked_armature.location = baked_armature.rotation_euler = [0,0,0]

    bpy.context.evaluated_depsgraph_get().update()

    # parent meshes
    for obj_name in self.char_objects:        
        ob = get_object(obj_name+"_arpexp")

        if ob.type == "MESH":
            mat = ob.matrix_world
            
            # preserve mesh-mesh parent
            mesh_parent = False
            if ob.parent:
                if ob.parent.type == 'MESH':
                    continue

            if not mesh_parent:            
                ob.parent = baked_armature
                ob.matrix_world = mat

    # restore location, rotation
    baked_armature.location, baked_armature.rotation_euler = baked_armature_loc_rot

    # restore pose
    armature_base.data.pose_position = 'POSE'
    armature_arpexp.data.pose_position = 'POSE'
    baked_armature.data.pose_position = 'POSE'
    
    # restore muted drivers
    for dp, arr_idx in arm_exp_dr_muted:
        fc = armature_arpexp.animation_data.drivers.find(dp, index=arr_idx)
        fc.mute = False
        
    # restore muted constraints
    for cns_name in arm_exp_cns_muted:
        armature_arpexp.constraints.get(cns_name).enabled = True

    # restore actions
    if armature_base.animation_data:# possible bug: the action turns to red then is not saved after exporting. Fix it by re-assigning the action.
        armature_base.animation_data.action = armature_base.animation_data.action

    if current_action:
        baked_armature.animation_data.action = current_action
 

def _add_ik_bones():
    bpy.ops.object.mode_set(mode='EDIT')

    scn = bpy.context.scene
    skel = bpy.context.active_object

    sides = [".l", ".r"]
    if scn.arp_rename_for_ue:
        sides = ["_l", "_r"]

    hand_name = 'hand'
    foot_name = 'foot'
    hand_gun_name = 'ik_hand_gun'
    hand_root_name = 'ik_hand_root'
    foot_root_name = 'ik_foot_root'
    foot_ik_name = 'ik_foot'
    hand_ik_name = 'ik_hand'

    # Add bones
    # feet
    #   create the IK root bone
    foot_root = create_edit_bone(foot_root_name, deform=True)
    foot_root.head, foot_root.tail = Vector((0,0,0)), Vector((0,1,0))
    foot_root.roll = 0.0

    for side in sides:
        foot = get_edit_bone(foot_name + side)
        if foot:
            # create the IK foot
            foot_ik = create_edit_bone(foot_ik_name + side, deform=True)
            foot_ik.head, foot_ik.tail = foot.head.copy(), foot.tail.copy()
            foot_ik.roll = foot.roll
            foot_ik.parent = get_edit_bone(foot_root_name)

    # hands
    # First check the right hand is there, since "ik_hand_gun" is located at the the right hand location
    hand_r = get_edit_bone(hand_name + sides[1])
    if hand_r:
        # create the IK root bone
        ik_hand_root = create_edit_bone(hand_root_name, deform=True)
        ik_hand_root.head, ik_hand_root.tail = Vector((0,0,0)), Vector((0,1,0))
        ik_hand_root.roll = 0.0

        # create the IK hand gun
        ik_hand_gun = create_edit_bone(hand_gun_name, deform=True)
        ik_hand_gun.head, ik_hand_gun.tail = hand_r.head.copy(), hand_r.tail.copy()
        ik_hand_gun.roll = hand_r.roll
        ik_hand_gun.parent = ik_hand_root

        # create the IK hands
        for side in sides:
            hand = get_edit_bone(hand_name + side)
            ik_hand = create_edit_bone(hand_ik_name+side, deform=True)
            ik_hand.head, ik_hand.tail = hand.head.copy(), hand.tail.copy()
            ik_hand.roll = hand.roll
            ik_hand.parent = ik_hand_gun


    bpy.ops.object.mode_set(mode='POSE')


    # Set constraints
    if scn.arp_ue_ik_anim:
        # feet
        for side in sides:
            foot_ik = get_pose_bone(foot_ik_name+side)
            if foot_ik == None:
                continue

            # copy transform constraint
            cns = foot_ik.constraints.new("COPY_TRANSFORMS")
            cns.target = skel
            cns.subtarget = foot_name+side


        # hands
        for side in sides:

            hand_ik = get_pose_bone(hand_ik_name+side)
            if hand_ik == None:
                continue

            # hand gun
            if side.endswith('r'):
                ik_hand_gun = get_pose_bone(hand_gun_name)
                cns = ik_hand_gun.constraints.new("COPY_TRANSFORMS")
                cns.target = skel
                cns.subtarget = hand_name+side

            # hands
            cns = hand_ik.constraints.new("COPY_TRANSFORMS")
            cns.target = skel
            cns.subtarget = hand_name+side


        bpy.ops.object.mode_set(mode='EDIT')


def _set_const_bones(state):
    context = bpy.context
    arm = context.active_object

    # disable mirror x
    mirror_state = arm.data.use_mirror_x
    arm.data.use_mirror_x = False

    # operate on both pose and edit bones data
    for mode in ["POSE", "EDIT"]:
        bpy.ops.object.mode_set(mode=mode)

        if context.mode == "POSE":
            sel_bones = context.selected_pose_bones
        elif context.mode == "EDIT_ARMATURE":
            sel_bones = context.selected_editable_bones

        for bone in sel_bones:
            if state:
                # add cc prop
                bone["const_interp"] = 1
            else:
                # remove cc prop
                try:
                    del bone["const_interp"]
                except:
                    pass

    # restore mirror x
    arm.data.use_mirror_x = mirror_state
        
        
def _set_softlink_bones(state):
    context = bpy.context
    arm = context.active_object

    # disable mirror x
    mirror_state = arm.data.use_mirror_x
    arm.data.use_mirror_x = False

    # operate on both pose and edit bones data
    for mode in ["POSE", "EDIT"]:
        bpy.ops.object.mode_set(mode=mode)

        if context.mode == "POSE":
            sel_bones = context.selected_pose_bones
        elif context.mode == "EDIT_ARMATURE":
            sel_bones = context.selected_editable_bones

        for bone in sel_bones:
            if state:
                # add cc prop
                bone["softlink"] = 1
            else:
                # remove cc prop
                try:
                    del bone["softlink"]
                except:
                    pass

    # restore mirror x
    arm.data.use_mirror_x = mirror_state


def _set_custom_bones(state):
    context = bpy.context
    arm = context.active_object

    # disable mirror x
    mirror_state = arm.data.use_mirror_x
    arm.data.use_mirror_x = False


    # operate on both pose and edit bones data
    for mode in ["POSE", "EDIT"]:
        bpy.ops.object.mode_set(mode=mode)

        if context.mode == "POSE":
            sel_bones = context.selected_pose_bones
        elif context.mode == "EDIT_ARMATURE":
            sel_bones = context.selected_editable_bones

        for bone in sel_bones:
            if state:
                # add cc prop
                bone["cc"] = 1
            else:
                # remove cc prop
                try:
                    del bone["cc"]
                except:
                    pass

    # restore mirror x
    arm.data.use_mirror_x = mirror_state


def _check_rig(self):
    scn = bpy.context.scene
    rig = None
    rig_list = [i for i in bpy.context.selected_objects if i.type == "ARMATURE"]
    if len(rig_list) == 0:
        return
    else:
        rig = rig_list[0]

    print("Check and fix actions...")
    # Clean actions, unexpected temporary actions may be left in the file data
    for act in bpy.data.actions:
        is_temp = act.name.endswith("_%temp")
    
        if is_temp:
            base_name = act.name
            while base_name.endswith("_%temp"):
                base_name = base_name[:-6]

            base_action = bpy.data.actions.get(base_name)
            if base_action:
                if not check_id_root(base_action):
                    bpy.data.actions.remove(base_action, do_unlink=True)
            act.name = base_name
    
    for act in bpy.data.actions:
        if len(act.keys()):
            if "arp_baked_action" in act.keys():
                bpy.data.actions.remove(act, do_unlink=True)


    print("Check current state...")
    set_active_object(rig.name)
   
    for b in rig.data.bones:
        # check for bendy bones limbs, not export compliant
        if 'arp_bbones' in b.keys():
            print('Bendy-Bones limbs found')
            self.bendy_bones_limbs.append(b.name)
            break
            
        # check for Soft IK, not export compliant
        if is_bone_in_layer(b.name, 'Reference'):
            if 'leg_softik' in b.keys():
                if b['leg_softik']:                   
                    self.soft_ik_limbs.append('leg'+get_bone_side(b.name))
            if 'arm_softik' in b.keys():
                if b['arm_softik']:
                    self.soft_ik_limbs.append('arm'+get_bone_side(b.name))
        
    bpy.ops.object.mode_set(mode='POSE')

    for b in rig.pose.bones:
        if scn.arp_export_noparent:
            break

        if "_proxy" in b.name:
            continue            
        
        # stretchy controllers not zeroed out
        if b.name.startswith("c_stretch_arm.") or b.name.startswith("c_stretch_leg.") or b.name.startswith("c_stretch_arm_dupli") or b.name.startswith("c_stretch_leg_dupli"):
            if b.location != Vector((0,0,0)):
                if not b.name in self.stretch_controllers:
                    print(b.name + " has invalid location: " + str(b.location))
                    self.stretch_controllers.append(b.name)

        # stretch properties not zeroed out
        #   spline IK
        if b.name.startswith("c_spline_root"):
            if b["y_scale"] != 2 or b["stretch_mode"] != 1:
                if not b.name in self.auto_stretch_controllers:
                    print(b.name + " has invalid IK spline stretch")
                    self.auto_stretch_controllers.append(b.name)

        #   ik
        if b.name.startswith("c_hand_ik.") or b.name.startswith("c_foot_ik.") or b.name.startswith("c_hand_ik_dupli") or b.name.startswith("c_foot_ik_dupli"):
            if b['auto_stretch'] != 0:
                if round(b['auto_stretch'], 2) == 0.0:
                    b['auto_stretch'] = 0.0# auto correct floating point imprecision
                else:
                    if not b.name in self.auto_stretch_controllers:
                        print(b.name + " has invalid auto_stretch: " + str(b['auto_stretch']))
                        self.auto_stretch_controllers.append(b.name)

            if b['stretch_length'] != 1.0:
                if round(b['stretch_length'], 2) == 1.0:
                    b['stretch_length'] = 1.0# auto correct floating point imprecision
                else:
                    if not b.name in self.auto_stretch_controllers:
                        print(b.name + " has invalid stretch_length: " + str(b['stretch_length']))
                        self.auto_stretch_controllers.append(b.name)
        #   fk
        if b.name.startswith("c_hand_fk.") or b.name.startswith("c_foot_fk.") or b.name.startswith("c_hand_fk_dupli") or b.name.startswith("c_foot_fk_dupli"):
            if b['stretch_length'] != 1.0:
                if round(b['stretch_length'], 2) == 1.0:
                    b['stretch_length'] = 1.0# auto correct floating point imprecision
                else:
                    if not b.name in self.auto_stretch_controllers:
                        print(b.name + " has invalid stretch_length: " + str(b['stretch_length']))
                        self.auto_stretch_controllers.append(b.name)
                        
    
            
    if len(bpy.data.actions):
        print("Checking actions...")

        actions = bpy.data.actions
        current_action = None
        try:
            current_action = rig.animation_data.action
        except:
            pass

        for action in actions:

            if not check_id_root(action):
                continue

            export_this_action = True

            # if "only active" enabled, skip non active actions
            if scn.arp_bake_only_active:
                if action != rig.animation_data.action:
                    export_this_action = False

            # if "only containing" enabled, check the action name contains the given word
            if scn.arp_only_containing:
                if not scn.arp_export_name_string in action.name:
                    export_this_action = False

            if export_this_action or current_action == action:
                print(action.name, "is exported")
                # Check if this action contains no bones fcurves. If so, can lead to wrong animation export
                found_bone_fcurve = False

                for fc in action.fcurves:
                    if "pose.bones[" in fc.data_path:
                        if not scn.arp_export_noparent:
                            #print("  checking stretch controllers...")

                            if ("c_stretch_arm" in fc.data_path or "c_stretch_leg" in fc.data_path) and "location" in fc.data_path:
                                for keyf in fc.keyframe_points:
                                    if keyf.co[1] != 0.0:
                                        bname = fc.data_path.split('"')[1]
                                        if not bname in self.stretch_controllers:
                                            print("this fcurve contains c_stretch_leg invalid keyframes: "+str(keyf.co[1])+"\n"+fc.data_path)
                                            self.stretch_controllers.append(bname)
                                        break

                            elif ("c_hand_ik" in fc.data_path or "c_foot_ik" in fc.data_path):
                                if ']["auto_stretch"]' in fc.data_path:
                                    for keyf in fc.keyframe_points:
                                        if keyf.co[1] != 0.0:
                                            bname = fc.data_path.split('"')[1]
                                            if not bname in self.auto_stretch_controllers:
                                                print("this fcurve contains auto_stretch invalid keyframes: "+str(keyf.co[1])+"\n"+fc.data_path)
                                                self.auto_stretch_controllers.append(bname)
                                            break

                                elif ']["stretch_length"]' in fc.data_path:
                                    for keyf in fc.keyframe_points:
                                        if keyf.co[1] != 1.0:
                                            bname = fc.data_path.split('"')[1]
                                            if not bname in self.auto_stretch_controllers:
                                                print("this fcurve contains stretch_length invalid keyframes: "+str(keyf.co[1])+"\n"+fc.data_path)
                                                self.auto_stretch_controllers.append(bname)
                                            break

                            elif ("c_hand_fk" in fc.data_path or "c_foot_fk" in fc.data_path):
                                if ']["stretch_length"]' in fc.data_path:
                                    for keyf in fc.keyframe_points:
                                        if keyf.co[1] != 1.0:
                                            bname = fc.data_path.split('"')[1]
                                            if not bname in self.auto_stretch_controllers:
                                                print("this fcurve contains stretch_length invalid keyframes: "+str(keyf.co[1])+"\n"+fc.data_path)
                                                self.auto_stretch_controllers.append(bname)
                                            break

                    # check for scale on object data (armature)
                    elif "scale" in fc.data_path:
                        if not action.name in self.scale_object_action:
                            self.scale_object_action.append(action.name)
                            print("This action contains scale keyframe on object data", action.name)

                    #print("  checking non bones keyframes...")
                    if "pose.bones[" in fc.data_path or 'key_blocks[' in fc.data_path:
                        found_bone_fcurve = True


                if not found_bone_fcurve:
                    self.non_armature_actions.append(action.name)
                    print("This action contains no bones keyframes:", action.name)


    print("Checking preserve volume modifiers...")
    for obj in bpy.data.objects:
        if len(obj.modifiers) > 0:
            for mod in obj.modifiers:
                if mod.type != "ARMATURE":
                    continue
                if mod.use_deform_preserve_volume:
                    self.preserve_volume_enabled.append(obj.name)

    print("Checking invalid armature modifiers...")
    for obj in bpy.data.objects:
        if len(obj.modifiers):
            armature_mod_count = 0
            for mod in obj.modifiers:
                if mod.type != "ARMATURE":
                    continue
                armature_mod_count += 1
                if mod.object == None and not obj.name in self.invalid_modifiers:
                    self.invalid_modifiers.append(obj.name)

                if armature_mod_count > 2 and not obj.name in self.invalid_modifiers:
                    self.invalid_modifiers.append(obj.name)

    
    bpy.ops.object.mode_set(mode='POSE')
    
    
    
def _fix_rig(self):

    scn = bpy.context.scene
    rig = None
    rig_list = [i for i in bpy.context.selected_objects if i.type == "ARMATURE"]
    if len(rig_list) == 0:
        return
    else:
        rig = rig_list[0]

    print("Check current state...")
    set_active_object(rig.name)
    bpy.ops.object.mode_set(mode='POSE')

    for b in rig.pose.bones:
        if scn.arp_export_noparent:
            break

        if "_proxy" in b.name:
            continue

        # zero out controllers
        if b.name.startswith("c_stretch_arm.") or b.name.startswith("c_stretch_leg.") or b.name.startswith("c_stretch_arm_dupli") or b.name.startswith("c_stretch_leg_dupli"):
            if b.location != Vector((0,0,0)):
                b.location = [0,0,0]

        # zero out properties
            # spline IK
        if b.name.startswith("c_spline_root"):
            b["y_scale"] = 2
            b["stretch_mode"] = 1

            # arms and legs
        if b.name.startswith("c_hand_ik.") or b.name.startswith("c_foot_ik.") or b.name.startswith("c_hand_ik_dupli") or b.name.startswith("c_foot_ik_dupli"):
            if b['auto_stretch'] != 0.0:
                b['auto_stretch'] = 0.0

            if b['stretch_length'] != 1.0:
                b['stretch_length'] = 1.0

        if b.name.startswith("c_hand_fk.") or b.name.startswith("c_foot_fk.") or b.name.startswith("c_hand_fk_dupli") or b.name.startswith("c_foot_fk_dupli"):
            if b['stretch_length'] != 1.0:
                b['stretch_length'] = 1.0

    if len(bpy.data.actions) > 0:
        print("Checking actions...")

        actions = bpy.data.actions
        current_action = None
        try:
            current_action = rig.animation_data.action
        except:
            pass

        for action in actions:
            if not check_id_root(action):
                continue

            export_this_action = True

            # Is "only containing" enable? If yes does the action name contains the given word?
            if scn.arp_only_containing:
                if not scn.arp_export_name_string in action.name:
                    export_this_action = False

            if export_this_action or action == current_action:
                print(action.name, "is exported")
                # Check if this action contains no bones fcurves. If so, can lead to wrong animation export
                found_bone_fcurve = False

                for fc in action.fcurves:
                    if "pose.bones[" in fc.data_path:
                        if not scn.arp_export_noparent:

                            #print("  checking stretch controllers...")

                            if ("c_stretch_arm" in fc.data_path or "c_stretch_leg" in fc.data_path) and "location" in fc.data_path:
                                for keyf in fc.keyframe_points:
                                    keyf.co[1] = 0.0
                                    keyf.handle_left[1] = 0.0
                                    keyf.handle_right[1] = 0.0

                            elif ("c_hand_ik" in fc.data_path or "c_foot_ik" in fc.data_path):
                                if ']["auto_stretch"]' in fc.data_path:
                                    for keyf in fc.keyframe_points:
                                        keyf.co[1] = 0.0
                                        print("set to 0!")
                                        keyf.handle_left[1] = 0.0
                                        keyf.handle_right[1] = 0.0

                                elif ']["stretch_length"]' in fc.data_path:
                                    for keyf in fc.keyframe_points:
                                        keyf.co[1] = 1.0
                                        keyf.handle_left[1] = 1.0
                                        keyf.handle_right[1] = 1.0

                            elif ("c_hand_fk" in fc.data_path or "c_foot_fk" in fc.data_path):
                                if ']["stretch_length"]' in fc.data_path:
                                    for keyf in fc.keyframe_points:
                                        keyf.co[1] = 1.0
                                        keyf.handle_left[1] = 1.0
                                        keyf.handle_right[1] = 1.0

                    # remove scale keyframes at object level
                    elif "scale" in fc.data_path:
                        action.fcurves.remove(fc)

    print("Fixing preserve volume modifiers...")
    for obj in bpy.data.objects:

        if len(obj.modifiers) > 0:
            for mod in obj.modifiers:

                if mod.type != "ARMATURE":
                    continue

                if mod.use_deform_preserve_volume:
                    mod.use_deform_preserve_volume = False


def _set_mannequin_orientations(self):
    scn = bpy.context.scene

    set_active_object("rig_humanoid")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object("rig_humanoid")
    bpy.ops.object.mode_set(mode='EDIT')

    rig_humanoid = get_object("rig_humanoid")
    arp_armature = get_object(self.armature_name)
    arp_armature.data.pose_position = "REST"
    arp_exp_armature = get_object(self.armature_name+'_arpexp')
    if (arp_exp_armature):# unavailable when setting humanoid with debug tools
        arp_exp_armature.data.pose_position = "REST"
    
    scn.tool_settings.transform_pivot_point = 'ACTIVE_ELEMENT'

    _spine = ['pelvis', 'spine', 'neck', 'head']
    _arms = ['clavicle', 'upperarm', 'lowerarm']
    _hand = ['hand']
    _fingers = ['thumb', 'index', 'middle', 'ring', 'pinky']
    _legs = ['thigh', 'calf']
    _foot = ['foot']
    _toes = ['ball']

    bones_transforms_dict = {}

    print("\nSet Mannequin Axes bones...")

    # display layers
    if bpy.app.version < (4,0,0):  
        rig_humanoid.data.layers[0] = True
        rig_humanoid.data.layers[16] = True
        rig_humanoid.data.layers[17] = True

    print("  Build transform dict...")

    # build the dict of the humanoid bones to orient, 
    # excluding custom bones, bend bones, helper bones...
    def is_bone_extra_limb(eb):
        if eb.name.startswith('c_tail_') or eb.name.startswith('c_breast_') \
            or "arp_spline" in eb.keys() or eb.name.startswith("c_ear_") \
            or 'arp_kilt' in eb.keys() or "arp_feather" in eb.keys():
                return True
        else:
            return False
        
    
    for e_bone in rig_humanoid.data.edit_bones:
        if not is_custom_bone(e_bone.name) and not is_bend_bone(e_bone.name) and not 'arp_ge_helper' in e_bone.keys() and not is_facial_bone(e_bone.name):
            if not is_bone_extra_limb(e_bone):
                bones_transforms_dict[e_bone.name] = e_bone.head.copy(), e_bone.tail.copy(), e_bone.roll

    rotate_value = 0.0
    rotate_axis = 'X'
    roll_value = 0.0

    print("  Unparent objects from bones...")
    unparented_meshes_bone = {}
    for i in bpy.data.objects:
        if not i.name.endswith("_arpexp"):
            continue
        if i.parent_type == "BONE" and i.parent_bone != "" and i.parent == get_object("rig_humanoid"):
            unparented_meshes_bone[i.name] = i.parent_bone

    for mesh_name in unparented_meshes_bone:
        mesh_obj = get_object(mesh_name)
        mesh_mat = mesh_obj.matrix_world.copy()
        mesh_obj.parent = None
        bpy.context.evaluated_depsgraph_get().update()
        mesh_obj.matrix_world = mesh_mat

    print('  Add new bones...')
    # Add new _childof and _orient bones
    # to match UE mannequin bones orientations
    created_bones_dict = {}
    for bone_name in bones_transforms_dict:
        bone_to_create_name = ''
        rotate_value = 0.0
        roll_value = 0.0
        rotate_axis = Vector((1,0,0))

        # spine
        for b in _spine:
            if b in bone_name:
                rotate_value = -pi/2
                roll_value = math.radians(-90)
                bone_to_create_name = bone_name
                rotate_axis = 'X'
                break

        # arms
        if bone_to_create_name == '':
            for b in _arms:
                if b in bone_name:
                    if bone_name.endswith(".l") or bone_name.endswith("_l"):

                        rotate_value = pi/2
                        roll_value = 0.0
                        if scn.arp_retro_axes:
                            rotate_value = -pi/2
                            roll_value = math.radians(180)

                    if bone_name.endswith(".r") or bone_name.endswith("_r"):

                        rotate_value = pi/2
                        roll_value = math.radians(180)
                        if scn.arp_retro_axes:
                            rotate_value = -pi/2
                            roll_value = math.radians(0)

                    bone_to_create_name = bone_name
                    rotate_axis = 'Z'
                    break

        # hand
        if bone_to_create_name == '':
            for b in _hand:
                if b in bone_name:
                    if bone_name.endswith(".l") or bone_name.endswith("_l"):
                        rotate_value = -pi/2
                        roll_value = math.radians(-90)

                    if bone_name.endswith(".r") or bone_name.endswith("_r"):
                        rotate_value = pi/2
                        roll_value = math.radians(-90)

                    bone_to_create_name = bone_name
                    rotate_axis = 'X'
                    break

        # fingers
        if bone_to_create_name == '':
            for b in _fingers:
                if b in bone_name:
                    if bone_name.endswith(".l") or bone_name.endswith("_l"):
                        rotate_value = -pi/2
                        roll_value = math.radians(-90)

                    if bone_name.endswith(".r") or bone_name.endswith("_r"):
                        rotate_value = pi/2
                        roll_value = math.radians(-90)

                    bone_to_create_name = bone_name
                    rotate_axis = 'X'
                    break

        # legs
        if bone_to_create_name == '':
            for b in _legs:
                if b in bone_name:
                    if bone_name.endswith(".l") or bone_name.endswith("_l"):
                        rotate_value = pi/2
                        roll_value = math.radians(180)

                    if bone_name.endswith(".r") or bone_name.endswith("_r"):
                        rotate_value = pi/2
                        roll_value = math.radians(0)

                    bone_to_create_name = bone_name
                    rotate_axis = 'Z'
                    break

        # foot
        if bone_to_create_name == '':
            for b in _foot:
                if b in bone_name:
                    if bone_name.endswith(".l") or bone_name.endswith("_l"):
                        rotate_value = pi
                        roll_value = math.radians(90)

                    if bone_name.endswith(".r") or bone_name.endswith("_r"):
                        rotate_value = 0.0
                        roll_value = math.radians(-90)

                    bone_to_create_name = bone_name
                    rotate_axis = 'Z'
                    break

        # toes
        if bone_to_create_name == '':
            for b in _toes:
                if b in bone_name:
                    if bone_name.endswith(".l") or bone_name.endswith("_l"):
                        rotate_value = -pi/2
                        roll_value = math.radians(-90)

                    if bone_name.endswith(".r") or bone_name.endswith("_r"):
                        rotate_value = pi/2
                        roll_value = math.radians(-90)

                    bone_to_create_name = bone_name
                    rotate_axis = 'X'
                    break


        if bone_to_create_name != '' and get_edit_bone(bone_to_create_name+'_orient') == None:
            # create _childof bones
            new_bone = create_edit_bone(bone_to_create_name+'_childof', deform=False)
            new_bone.head = bones_transforms_dict[bone_to_create_name][0]
            new_bone.tail = bones_transforms_dict[bone_to_create_name][1]
            new_bone.roll = bones_transforms_dict[bone_to_create_name][2]
            get_edit_bone(bone_to_create_name).use_deform = False
            
            set_bone_layer(new_bone, 'ge_childof', show_new_layer=True)
           
            # store the new bones in a dict
            created_bones_dict[bone_to_create_name] = rotate_value, roll_value, rotate_axis

    # hack to update armature data
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.mode_set(mode='EDIT')

    for bone_name in created_bones_dict:
        # Set "child_of" bones rotation
        # fetch values from dict
        rotate_value, roll_value, rotate_axis = created_bones_dict[bone_name]

        # select
        bpy.ops.armature.select_all(action='DESELECT')
        select_edit_bone(bone_name + "_childof", mode=2)

        # rotate
        bone_childof = get_edit_bone(bone_name + "_childof")
        save_head_pos = bone_childof.head.copy()

        if rotate_value:
            def_rotate_value = rotate_value
            _axis = bone_childof.x_axis if rotate_axis == "X" else bone_childof.z_axis
            rotate_edit_bone(bone_childof, def_rotate_value, _axis)

        bone_childof.roll += roll_value

        # flatten toes, foot
        if 'foot' in bone_name:
             # flatten vertically 95% since 100% may lead to rotation artefact in Unreal
            bone_childof.tail[2] += (bone_childof.head[2]-bone_childof.tail[2])*0.95
            #set roll
            bpy.ops.armature.select_all(action='DESELECT')
            bone_childof.select = True
            bone_childof.select_head = True
            bone_childof.select_tail = True
            bpy.ops.armature.calculate_roll(type='GLOBAL_NEG_X')


        elif 'ball' in bone_name:
            bone_childof.tail[1] = bone_childof.head[1]
            bone_childof.tail[0] = bone_childof.head[0]

        # special spine orientations
        elif 'spine_01' in bone_name:
            bone_childof.tail[2] = bone_childof.head[2]
            def_rotate_value = math.radians(-7)
            rotate_edit_bone(bone_childof, def_rotate_value, bone_childof.z_axis)

        elif 'spine_' in bone_name:
            bone_childof.tail[2] = bone_childof.head[2]
            def_rotate_value = math.radians(8)
            rotate_edit_bone(bone_childof, def_rotate_value, bone_childof.z_axis)

        # Create main orient bones
        new_bone1 = create_edit_bone(bone_name+'_orient', deform=True)
        new_bone1.head, new_bone1.tail, new_bone1.roll = bone_childof.head.copy(), bone_childof.tail.copy(), bone_childof.roll
        set_bone_layer(new_bone1, 'ge_orient', show_new_layer=True)


    # add childof bones constraints
    bpy.ops.object.mode_set(mode='POSE')

    for bone_name in created_bones_dict:
        childof_pbone = get_pose_bone(bone_name + "_childof")
        cns = childof_pbone.constraints.new('CHILD_OF')
        cns.name = "Child Of"
        cns.target = rig_humanoid
        cns.subtarget = bone_name
        cns.inverse_matrix = get_pose_bone(bone_name).bone.matrix_local.to_4x4().inverted()

        #add main orient bone constraint
        orient_pbone = get_pose_bone(bone_name + "_orient")
        cns1 = orient_pbone.constraints.new('COPY_TRANSFORMS')
        cns1.name = "Copy Transforms"
        cns1.target = rig_humanoid
        cns1.subtarget = bone_name + "_childof"

    bpy.ops.object.mode_set(mode='EDIT')    
    
    print("  Set parents...")

    if 'ebone' in locals():
        del ebone

    # Set parents
    for ebone in rig_humanoid.data.edit_bones:
        # _orient bones parent
        if '_orient' in ebone.name:
            associated_bone = get_edit_bone(ebone.name.replace('_orient', ""))
            if associated_bone.parent:
                ebone.parent = get_edit_bone(associated_bone.parent.name + "_orient")
                continue

        # _facial bones parent
        for facial_bone in default_facial_bones:
            if ebone.parent != None:
                if facial_bone in ebone.name and get_edit_bone(ebone.parent.name + "_orient") != None:
                    ebone.parent = get_edit_bone(ebone.parent.name + "_orient")
                    break

        for add_facebone in additional_facial_bones:
            if ebone.parent != None:
                if add_facebone in ebone.name and get_edit_bone(ebone.parent.name + "_orient") != None:
                    ebone.parent = get_edit_bone(ebone.parent.name + "_orient")
                    break

        # custom controllers, bend bones
        if is_custom_bone(ebone.name) or is_bend_bone(ebone.name):
            if ebone.parent:
                bone_parent_orient = get_edit_bone(ebone.parent.name + "_orient")
                if bone_parent_orient:
                    ebone.parent = bone_parent_orient

        # extra limbs
        if is_bone_extra_limb(ebone):
            if ebone.parent:
                bone_parent_orient = get_edit_bone(ebone.parent.name + "_orient")
                if bone_parent_orient:
                    ebone.parent = bone_parent_orient


    print("  Rename bones...")
    # rename all
    for ebone in rig_humanoid.data.edit_bones:
        # exclude custom bones, bend bones, facial bones, tail bones, 
        # breast bones, spline bones, ear bones, helper bones, kilt bones
        if not is_custom_bone(ebone.name) and not is_bend_bone(ebone.name) and not is_facial_bone(ebone.name) \
            and not 'arp_ge_helper' in ebone.keys() and not is_bone_extra_limb(ebone):
            
            if not '_orient' in ebone.name and not '_childof' in ebone.name :
                ebone.name = ebone.name + "_basebone"
                # debug, users may accidentally enable some controller deform property, leading to issues
                if ebone.name.startswith("c_toes_pivot"):
                    ebone.use_deform = False
                set_bone_layer(ebone, 'ge_basebone', show_new_layer=True)

    for ebone in rig_humanoid.data.edit_bones:
        if '_orient' in ebone.name:
            ebone.name = ebone.name.replace('_orient', '')
            set_bone_layer(ebone, 'Deform', show_new_layer=True)

    
    # specials: swap arms and thigh twist bones position to match accurately the UE humanoid skeleton
    if scn.arp_retro_ge_UE_twist_pos == False:
        for i in range(1,33):
            idx = '%02d' % i
            idx_next = '%02d' % (i+1)
            for side in ('_l', '_r', '_l_childof', '_r_childof'):
            
                limb_list = [['thigh', 'calf']]
                if scn.arp_ue4 == False:# the arm twist bone of the UE4 humanoid is at the root (shoulder) position, unlike the thigh twist in the middle
                    limb_list.append(['upperarm', 'lowerarm'])
                    
                for limb in limb_list:
                    b1_name = limb[0]
                    b2_name = limb[1]
                    twist_eb = get_edit_bone(b1_name+'_twist_'+idx+side)
                    twist_eb_next = get_edit_bone(b1_name+'_twist_'+idx_next+side)
                    
                    if twist_eb and twist_eb_next:
                        vec = twist_eb_next.head - twist_eb.head
                        twist_eb.head += vec
                        twist_eb.tail += vec
                    elif twist_eb:
                        if arp_armature.arp_secondary_type in ['NONE', 'ADDITIVE']:
                            b2_eb = get_edit_bone(b2_name+side)
                            if b2_eb:
                                vec = b2_eb.head - twist_eb.head
                                twist_eb.head += vec/2
                                twist_eb.tail += vec/2
                        elif arp_armature.arp_secondary_type == 'TWIST_BASED':
                            c_b1_eb = get_edit_bone('c_'+b1_name+side)                    
                            if c_b1_eb:
                                vec = c_b1_eb.head - twist_eb.head
                                twist_eb.head += vec
                                twist_eb.tail += vec

    
    # ensure all deforming bones are in layer 17
    for ebone in rig_humanoid.data.edit_bones:
        if ebone.use_deform:
            if bpy.app.version >= (4,0,0):
                set_bone_layer(ebone, 'Deform', multi=True)
                get_armature_collections(rig_humanoid).get('Deform').is_visible = True
            else:
                ebone.layers[17] = True                
                
    # rename vgroups
    print("  Rename vgroups...")
    
    for obj in bpy.data.objects:
        if len(obj.vertex_groups):
            for vgroup in obj.vertex_groups:
                if '_basebone' in vgroup.name:
                    vgroup.name = vgroup.name.replace('_basebone', '')

    bpy.ops.object.mode_set(mode='POSE')

    
    # display only final bones layer
    if bpy.app.version >= (4,0,0):
        get_armature_collections(rig_humanoid).get('Layer 1').is_visible = False
        get_armature_collections(rig_humanoid).get('Layer 2').is_visible = False
        get_armature_collections(rig_humanoid).get('ge_childof').is_visible = False
        get_armature_collections(rig_humanoid).get('ge_orient').is_visible = False
        get_armature_collections(rig_humanoid).get('ge_basebone').is_visible = False
        
        sort_armature_collections(rig_humanoid, custom_collection='Deform', to_index=0)
        
        # remove empty collections
        col_names = [col.name for col in get_armature_collections(rig_humanoid)]# make a copy of current collections, necessary for proper removal
        
        for col_name in col_names:
            collec = get_armature_collections(rig_humanoid).get(col_name)
            if len(collec.bones) == 0:
                rig_humanoid.data.collections.remove(collec)
    else:
        rig_humanoid.data.layers[0] = False
        rig_humanoid.data.layers[1] = False
        rig_humanoid.data.layers[16] = False
    
    # set rot to euler, orientation artefact when importing in Unreal with quaternions...
    for pbone in bpy.context.active_object.pose.bones:
        pbone.rotation_mode = 'XYZ'

    print("  Reparent objects to bones...")
    for mesh_name in unparented_meshes_bone:
        mesh_obj = get_object(mesh_name)
        mesh_mat = mesh_obj.matrix_world.copy()
        mesh_obj.parent = get_object("rig_humanoid")
        mesh_obj.parent_type = "BONE"
        mesh_obj.parent_bone = unparented_meshes_bone[mesh_name.replace("_basebone", "")]
        bpy.context.evaluated_depsgraph_get().update()
        mesh_obj.matrix_world = mesh_mat

    arp_armature.data.pose_position = "POSE"    
    if (arp_exp_armature):# unavailable when setting humanoid with debug tools
        arp_exp_armature.data.pose_position = "POSE"

    print("  Done.")
    # end _set_mannequin_orientations()


def _bake_pose(baked_armature_name):
    arm = get_object(baked_armature_name)
    set_active_object(baked_armature_name)
    
    bpy.ops.object.mode_set(mode='POSE')    

    # store matrices
    mat_list = {}
    obj_mat  = None

    for b in arm.pose.bones:
        mat_list[b.name] = b.matrix.copy()

    obj_mat = arm.matrix_world.copy()

    # mute constraints
    for b in arm.pose.bones:
        for cns in b.constraints:
            enable_constraint(cns, False)
           
    for cns in arm.constraints:
        enable_constraint(cns, False)
       
    # restore matrices
    arm.matrix_world = obj_mat

    for bname in mat_list:
        arm.pose.bones.get(bname).matrix = mat_list[bname]


def _bake_all(armature_name, baked_armature_name, self):
    scn = bpy.context.scene
    arp_armature = get_object(armature_name + '_arpexp')
    baked_armature = get_object(baked_armature_name)
    base_armature = get_object(armature_name)
    base_rot = baked_armature.rotation_euler.copy()

    def prepare_for_baking():
        if baked_armature.animation_data:
            baked_armature.animation_data.action = None

        # when exporting root motion, initialize the baked armature location and rotation
        if scn.arp_ue_root_motion:
            baked_armature.location = arp_armature.location.copy()
            baked_armature.rotation_euler = base_rot
            
        bpy.ops.object.mode_set(mode='POSE')
        
        enable_all_armature_layers()

        # Only select the deforming bones for baking
        bpy.ops.pose.select_all(action='DESELECT')
        bpy.ops.pose.select_all(action='SELECT')

        if scn.arp_mannequin_axes:
            bpy.ops.pose.select_all(action='DESELECT')

            for pbone in baked_armature.pose.bones:
                split = pbone.name.split("_")
                if split[len(split)-1] != "childof" and split[len(split)-1] != "basebone":
                    pbone.bone.select = True
    
    
    if scn.arp_bake_type == "NLA":
        print("...................................NLA baking...................................")

        # bind the rig
        _constraint_rig(False)
        print("  Bound.")

        # set action blend type to Replace to avoid issues (e.g. when used with Animations Layers addon)
        act_blend_type = []
        act_blend_type.append(arp_armature.animation_data.action_blend_type)
        act_blend_type.append(base_armature.animation_data.action_blend_type)# save values
        arp_armature.animation_data.action_blend_type = "REPLACE"
        base_armature.animation_data.action_blend_type = "REPLACE"

        # Bake
        #  frame range
        fs = None
        fe = None

        if scn.arp_frame_range_type != 'CUSTOM' and scn.arp_frame_range_type != 'SCENE':
            scn.arp_frame_range_type = 'SCENE'

        if scn.arp_frame_range_type == "CUSTOM":
            fs = scn.arp_export_start_frame
            fe = scn.arp_export_end_frame
        elif scn.arp_frame_range_type == "SCENE":
            fs = scn.frame_start
            fe = scn.frame_end

        prepare_for_baking()

        act_export_name = 'Animation'
        name_idx = 1
        while bpy.data.actions.get(act_export_name):# avoid name conflict
            if name_idx == 1:
                act_export_name += str(name_idx)
            else:
                act_export_name = act_export_name[:-1] + str(name_idx)

            name_idx += 1


        # bake animations
        if self.export_format == 'GLTF':# subframe baking not supported with GLTF
            scn.arp_ge_bake_sample = 1.0
        
        print("  Baking NLA:", act_export_name, '['+str(int(fs))+'-'+str(int(fe))+']')
        
        bake_anim(frame_start=fs, frame_end=fe, only_selected=True, bake_bones=True, bake_object=True, 
                    shape_keys=True, _self=self, action_export_name=act_export_name, sampling_rate=scn.arp_ge_bake_sample)

        try:
            # set action name
            baked_armature.animation_data.action.name = act_export_name
        except:
            print("    Error when setting the baked action name")

        # set fake user
        baked_armature.animation_data.action.use_fake_user = True

        # tag the baked action
        bpy.data.actions.get(act_export_name)["arp_baked_action"] = 1

        self.actions_were_exported = True


        # restore actions blend types
        arp_armature.animation_data.action_blend_type = act_blend_type[0]
        base_armature.animation_data.action_blend_type = act_blend_type[1]


        # unbind the rig
        _constraint_rig(True)
        print("  Unbound")


    elif scn.arp_bake_type == "ACTIONS" and len(bpy.data.actions) > 0:
        print("..............................Found actions, baking..............................")

        actions = [act for act in bpy.data.actions]

        # bind the rig
        _constraint_rig(False)
        print("  Bound.")

        # store original active action
        original_action = base_armature.animation_data.action
        original_transforms = [base_armature.location.copy(), base_armature.rotation_euler.copy(), 
                                base_armature.rotation_quaternion.copy(), base_armature.scale.copy()]
        
        # set action blend type to Replace to avoid issues (e.g. when used with Animations Layers addon)
        act_blend_type = []
        act_blend_type.append(arp_armature.animation_data.action_blend_type)
        act_blend_type.append(base_armature.animation_data.action_blend_type)# save values
        arp_armature.animation_data.action_blend_type = "REPLACE"
        base_armature.animation_data.action_blend_type = "REPLACE"


        for action in actions:
            #print('\n'+action.name)
            if not check_id_root(action):# typically shape keys action 
                continue

            action_name_split = action.name.split('_')

            bake_this_action = False

            if scn.arp_export_use_actlist:# export using the actions list manager
                for act_list in scn.arp_export_actlist:                    
                    if act_list.exportable == False:
                        continue

                    for act_item in act_list.actions:
                        # Is the action enabled for export?
                        if len(action.keys()):
                            if 'arp_export' in action.keys():
                                if action['arp_export'] == False:
                                    continue

                        if act_item.action == action:
                            bake_this_action = True
                            break

            else:# export with standard settings                
                # Is the action already a baked one?   
                if len(action.keys()) == 0:
                    bake_this_action = True
                else:
                    if not "arp_baked_action" in action.keys():
                        bake_this_action = True

                # If "Only Active" enabled, only bake current action
                if scn.arp_bake_only_active:                  
                    if action == base_armature.animation_data.action:                       
                        bake_this_action = True
                    else:
                        bake_this_action = False

                else:
                    # If "Only containing" enabled, only bake actions with the given name
                    if scn.arp_only_containing:
                        if not scn.arp_export_name_string in action.name:
                            bake_this_action = False

                    # Is the action enabled for export?
                    if len(action.keys()) > 0:
                        if "arp_export" in action.keys():
                            if action["arp_export"] == False:
                                bake_this_action = False

            
            if bake_this_action:
                #print("  Baking action:", action.name)
                frame_range =action.frame_range
                if bpy.app.version >= (4,0,0) and scn.arp_retro_ge_frame_range:
                    frame_range[1] += 1
                    
                # Check if this action contains no bones fcurves. If so, can lead to wrong animation export, a message is shown at the end to warn the user
                found_bone_fcurve = False

                for fc in action.fcurves:
                    if "pose.bones[" in fc.data_path or 'key_blocks[' in fc.data_path:
                        found_bone_fcurve = True
                        break

                if not found_bone_fcurve:
                    self.non_armature_actions.append(action.name)
                    print("  This action contains no bones keyframes:", action.name)                
                
                # Add 0.01 angle offset to rotation keyframes if values == 0.0 to fix wrong rotation export
                if scn.arp_fix_fbx_rot:
                    set_active_object(arp_armature.name)

                    bpy.ops.object.mode_set(mode='POSE')

                    for pbone in bpy.context.active_object.pose.bones:
                        if pbone.name.startswith("c_") or is_custom_bone(pbone.name):
                            if pbone.rotation_euler[0] == 0.0:
                                pbone.rotation_euler[0] += 0.0002
                            if pbone.rotation_euler[1] == 0.0:
                                pbone.rotation_euler[1] += 0.0002
                            if pbone.rotation_euler[2] == 0.0:
                                pbone.rotation_euler[2] += 0.0002


                    bpy.ops.object.mode_set(mode='OBJECT')

                    bpy.ops.object.select_all(action='DESELECT')

                    set_active_object(baked_armature.name)

                # assign the action to the object
                arp_armature.animation_data.action = action

                # and to the original rig for shape keys driver baking
                base_armature.animation_data.action = action

                prepare_for_baking()

                # rename base action with suffix _%temp in order to name the baked action with the base name
                act_export_name = action.name
                if scn.arp_retro_action_prefix:# backward-compatibility, use prefixes for action names
                    act_export_name = "mp_"+action.name if scn.arp_export_rig_type == 'UNIVERSAL' else 'h_'+action.name
                try:# linked actions cannot be renamed
                    action.name = action.name+"_%temp"
                except:
                    pass

                # get frame ranges
                fs = None
                fe = None

                if scn.arp_frame_range_type == "FULL":
                    fs = frame_range[0]
                    fe = frame_range[1]
                elif scn.arp_frame_range_type == "CUSTOM":
                    fs = scn.arp_export_start_frame
                    fe = scn.arp_export_end_frame
                elif scn.arp_frame_range_type == "SCENE":
                    fs = scn.frame_start
                    fe = scn.frame_end
                elif scn.arp_frame_range_type == "MARKERS":
                    # default fallback if no markers are found, export all frames
                    fs = frame_range[0]
                    fe = frame_range[1]

                    # look for markers
                    for marker in action.pose_markers:
                        if marker.name.lower() == "start":
                            fs = marker.frame
                        elif marker.name.lower() == "end":
                            fe = marker.frame
                
                if self.export_format == 'GLTF':# subframe baking not supported with GLTF
                    scn.arp_ge_bake_sample = 1.0                
                
                
                
                # Bake bones transforms
                print("  Baking action:", act_export_name, '['+str(int(fs))+'-'+str(int(fe))+']')
                
                bake_anim(frame_start=fs, frame_end=fe, only_selected=True, bake_bones=True, bake_object=True,
                        shape_keys=True, _self=self, action_export_name=act_export_name, sampling_rate=scn.arp_ge_bake_sample)
                
                # Bake fcurve of custom properties driving shape keys if any
                # Disable it for now, useless since shape keys are already baked previously
                # Also, do not work if the shape key driver bone holding the props is not a custom bone (may not exist in the exported rig)
                '''
                for ob in bpy.data.objects:
                    if ob.type == "MESH" and "_arpexp" in ob.name:
                        sk_drivers = get_shape_keys_drivers(ob)

                        if sk_drivers != None:
                            for dr in sk_drivers:
                                for var in dr.driver.variables:
                                    if var.type != "SINGLE_PROP":
                                        continue
                                        
                                    prop_dp = var.targets[0].data_path
                                    spl = prop_dp.split('"')
                                    # if it's a custom property, copy the fcurve
                                    if len(spl) != 5:
                                        continue
                                        
                                    fcurve_source = arp_armature.animation_data.action.fcurves.find(prop_dp)

                                    if fcurve_source == None:
                                        continue
                                    
                                    #print("    Found custom prop driver fcurves for SK, copy it", prop_dp)
                                    if bpy.context.active_object.animation_data.action.fcurves.find(fcurve_source.data_path) == None:                                       
                                        new_fc = bpy.context.active_object.animation_data.action.fcurves.new(fcurve_source.data_path)

                                        for fr in range(int(frame_range[0]), int(frame_range[1])):
                                            val = fcurve_source.evaluate(fr)
                                            new_fc.keyframe_points.insert(fr, val)
                '''
                
                try:
                    # set action name
                    baked_armature.animation_data.action.name = act_export_name

                    # set fake user
                    baked_armature.animation_data.action.use_fake_user = True
                except:
                    print("    Error when assigning the action because it's used in the NLA. Remove it from the NLA to export.")

                # tag the baked action
                baked_action = bpy.data.actions.get(act_export_name)
                baked_action["arp_baked_action"] = 1
                
                # copy action custom properties if any
                for prop_name in action.keys():
                    baked_action[prop_name] = action[prop_name]
                    

                self.actions_were_exported = True
                
                # Add 0.01 angle offset to rotation keyframes if values == 0.0 to fix wrong rotation export
                if scn.arp_fix_fbx_rot:
                    for fcurve in baked_action.fcurves:
                        if 'rotation' in fcurve.data_path and "pose.bones" in fcurve.data_path:
                            for point in fcurve.keyframe_points:
                                if point.co[1] == 0.0:
                                    point.co[1] += 0.0002
                                    point.handle_left[1] += 0.0002
                                    point.handle_right[1] += 0.0002
                    

        # restore original active action
        base_armature.animation_data.action = original_action
        base_armature.location, base_armature.rotation_euler, base_armature.rotation_quaternion, base_armature.scale = original_transforms
        
        # restore actions blend types
        arp_armature.animation_data.action_blend_type = act_blend_type[0]
        base_armature.animation_data.action_blend_type = act_blend_type[1]

        print("  Actions baked.")

        # unbind the rig
        _constraint_rig(True)
        print("  Unbound")


def _select_exportable(armature_name):
    scn = bpy.context.scene
    arp_armature = get_object(armature_name + '_arpexp')
    
    baked_armature_name = ''

    if bpy.context.scene.arp_export_rig_type == 'HUMANOID':
        baked_armature_name = "rig_humanoid"
    if bpy.context.scene.arp_export_rig_type == 'UNIVERSAL':
        baked_armature_name = "rig_mped"

    set_active_object(arp_armature.name)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


    # Select meshes with export armature modifier
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            # objects parented to bones
            if obj.parent:
                if obj.parent_type == "BONE" and obj.parent.name == baked_armature_name:
                    set_active_object(obj.name)
                    bpy.ops.object.mode_set(mode='OBJECT')
                    select_children(obj.name, ob_type='MESH')# select children too               
                    #print("Collected mesh", obj.name)

            # objects with armature modifiers
            if len(obj.modifiers) > 0:
                #print(obj.name)
                for modif in obj.modifiers:
                    if modif.type != 'ARMATURE':
                        continue
                    if modif.object:
                        #print(modif.object.name, obj.name)
                        if modif.object.name == baked_armature_name:
                            set_active_object(obj.name)
                            bpy.ops.object.mode_set(mode='OBJECT')
                            select_children(obj.name, ob_type='MESH')# select children too
                            #print("Collected mesh", obj.name)


    #check if the meshes have shape keys and disable subsurf if any before export
    exclude_mods = ['SUBSURF', 'SMOOTH', 'MASK', 'MULTIRES']
    if scn.arp_apply_subsurf:
        exclude_mods.remove('SUBSURF')
        
    if scn.arp_apply_mods == False:
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                if obj.data.shape_keys:
                    if len(obj.data.shape_keys.key_blocks):
                        if len(obj.modifiers):
                            for modif in obj.modifiers:
                                if modif.show_render:
                                    if modif.type in exclude_mods:
                                        #print(obj.name + " has shape keys, " + modif.type + " modifier won't be exported.")
                                        obj.modifiers.remove(modif)

    # select the export armature
    if get_object(baked_armature_name) != None:
        unhide_object(get_object(baked_armature_name))
        set_active_object(baked_armature_name)


def get_char_objects(self, arm_name=None, arm_add_name=None, arm_proxy=None, arm_source=None):
    rig_add = None
    scn = bpy.context.scene
    if arm_add_name:
        rig_add = get_object(arm_add_name)

    list_char_objects = [arm_name]
    list_spline_objects = []

    if rig_add:
        list_char_objects.append(arm_add_name)
        unhide_object(rig_add)
        rig_add.hide_select = False

    deforming_arm = arm_name

    if arm_proxy != None:# proxy armature name
        deforming_arm = arm_proxy
 
    # Append meshes
    objs = []

    if scn.arp_ge_sel_only:
        objs = [obj for obj in bpy.context.selected_objects]
    else:
        objs = [obj for obj in bpy.context.view_layer.objects]# collect objects in view_layer only, objects in file data may be not accessible

    for obj in objs:
        # Remove arp_parent_bone tag if any
        if obj.get("arp_parent_bone"):
            del obj["arp_parent_bone"]

        if obj.type == 'MESH' and not is_object_hidden(obj):
            # obj parented to bone
            if obj.parent:
                if obj.parent.name == deforming_arm and obj.parent_type == "BONE":
                    if obj.parent_bone != '':
                        list_char_objects.append(obj.name)
                        obj["arp_parent_bone"] = obj.parent_bone
                        
                        # include mesh children as well
                        child_list = get_children(obj.name, ob_type='MESH')
                        for childname in child_list:
                            list_char_objects.append(childname)
                            
                        continue# continue to avoid user error. Some cases were reported where meshes were parented to bones + armature modifier, which is invalid

            # obj with armature modifiers
            if len(obj.modifiers):
                for mod in obj.modifiers:
                    if mod.type == "ARMATURE" and mod.show_viewport:
                        if mod.object:
                            if mod.object.name == deforming_arm:
                                if not obj.name in list_char_objects:# maybe already registered if both mesh-mesh parent and armature deform
                                    list_char_objects.append(obj.name)
                                
                                # include mesh children as well
                                child_list = get_children(obj.name, ob_type='MESH')
                                for childname in child_list:
                                    if not childname in list_char_objects:# maybe already registered if both mesh-mesh parent and armature deform
                                        list_char_objects.append(childname)
                                break

        elif obj.type == "CURVE" and obj.name.startswith("spline_ik_curve"):
            if obj.parent:
                if obj.parent.name == deforming_arm:# Spline IKs curves          
                    list_spline_objects.append(obj.name)
   
                   
    #check if the meshes have shape keys and disable subsurf if any before export
    if scn.arp_apply_mods == False and scn.arp_apply_subsurf == False:
        for obj_name in list_char_objects:
            obj = get_object(obj_name)
            if obj.type == 'MESH':
                if obj.data.shape_keys != None:
                    if len(obj.data.shape_keys.key_blocks) > 0:
                        if len(obj.modifiers) > 0:
                            for modif in obj.modifiers:
                                if modif.type == 'SUBSURF' or modif.type == "MULTIRES":
                                    modif.show_render = False
                                    modif.show_viewport = False
                                    print('\nMesh', obj.name, 'has shape keys, disable', modif.type,  'modifiers for export')


    # if the armature only is exported, add an extra dummy mesh to allow the armature's rest pose export and correct hierarchy in Unity
    add_dummy_mesh = self.export_format == 'FBX' and ((scn.arp_engine_type == 'UNREAL' and self.is_arp_armature) or scn.arp_ge_add_dummy_mesh)
    if add_dummy_mesh:
        if (len(list_char_objects) == 2 and rig_add) or len(list_char_objects) == 1:
            dum_ob = create_dummy_mesh()
            new_mod = dum_ob.modifiers.new(type="ARMATURE", name="rig")
            new_mod.object = get_object(arm_name)
            list_char_objects.append(dum_ob.name)
            print("Created dummy mesh")
            
    
    # Check if objects are in visible view layer. If not, do not export. Unaccessible data
    to_remove = []
    for obj_name in list_char_objects:
        found = False
        for v_o in bpy.context.view_layer.objects:
            if v_o == get_object(obj_name):
                found = True
        if not found:
            to_remove.append(obj_name)
    
    for obj_name in to_remove:
        list_char_objects.remove(obj_name)
        print("  <!>Exclude:", obj_name, "from char objects, is in unaccessible view layer")
            
    return list_char_objects, list_spline_objects


def create_dummy_mesh():
    dummy_mesh = bpy.data.meshes.new("arp_dummy_mesh")
    dummy_object = bpy.data.objects.new("arp_dummy_mesh", dummy_mesh)
    bpy.context.scene.collection.objects.link(dummy_object)
    return(dummy_object)


def get_rig_add(rig_name):
    _rig_add_name = None
    arm_parent = get_object(rig_name).parent

    if arm_parent:
        for child in arm_parent.children:
            if child.name.endswith("rig_add"):
                _rig_add_name = child.name
                break

    return _rig_add_name


def get_shape_keys_drivers(_obj):
    try:
        sk_drivers = _obj.data.shape_keys.animation_data.drivers
    except:
        return None

    return sk_drivers



def _set_units_x100_baked(armature_name, self):
    
    scn = bpy.context.scene
    scn.tool_settings.use_keyframe_insert_auto = False
    current_frame = scn.frame_current#save current frame
    
    if scn.unit_settings.system == 'NONE' or (scn.unit_settings.system != 'NONE' and (scn.unit_settings.scale_length > 1.0-0.0003 and scn.unit_settings.scale_length < 1.0+0.0003)):
        print("..............................Set Units x100 (baked)..............................")

        rig = get_object(armature_name+'_arpexp')
        rig_scale = rig.scale[0]
        baked_armature_name = ''

        if scn.arp_export_rig_type == 'HUMANOID':
            baked_armature_name = 'rig_humanoid'
        if scn.arp_export_rig_type == 'UNIVERSAL':
            baked_armature_name = 'rig_mped'

        baked_armature = get_object(baked_armature_name)

        #Collect meshes
        meshes = []

        for obj in bpy.data.objects:
            if obj.type == 'MESH' and not is_object_hidden(obj):
                if len(obj.modifiers) == 0:
                    continue
                for mod in obj.modifiers:
                    if mod.type != 'ARMATURE':
                        continue
                    if mod.object == None:
                        continue
                    if mod.object.name == baked_armature_name:
                        meshes.append(obj)

        bpy.ops.object.mode_set(mode='OBJECT')

        for mesh in meshes:
            bpy.ops.object.select_all(action='DESELECT')

            # Unlock scale transform
            set_active_object(mesh.name)

            for i in range(0,3):
                mesh.lock_scale[i] = False

            # Apply Data Transfer modifier if any
            if len(bpy.context.active_object.modifiers) > 0:
                for mod in bpy.context.active_object.modifiers:
                    if mod.type == "DATA_TRANSFER":
                        apply_modifier(mod.name)

            # Scale shape keys drivers
            has_sk_drivers = False

            try:
                drivers_list = mesh.data.shape_keys.animation_data.drivers
                has_sk_drivers = True
            except:
                pass

        if 'mesh' in locals():
            del mesh

        # Scale armatures transforms x100
        bpy.ops.object.select_all(action='DESELECT')

        set_active_object(baked_armature_name)
        set_active_object(rig.name)

        #   first make sure to delete scale keyframe on the baked armature
        for action in bpy.data.actions:
            if not check_id_root(action):
                continue
            if not len(action.keys()):
                continue
            if not "arp_baked_action" in action.keys():
                continue

            for _fcurve in action.fcurves:
                if _fcurve.data_path == "scale":
                    action.fcurves.remove(_fcurve)

        #   trigger the update manually, does not update automatically
        if baked_armature.animation_data:
            current_action = baked_armature.animation_data.action
            if current_action:
                current_action_name = current_action.name
                baked_armature.animation_data.action = None
                bpy.context.evaluated_depsgraph_get().update()
                baked_armature.animation_data.action = bpy.data.actions[current_action_name]

        
        #  disable any drivers on transforms channels temporarily
        arm_exp_dr_muted = []
        if rig.animation_data:
            for dr in rig.animation_data.drivers:
                if dr.data_path in ['location', 'rotation_euler', 'rotation_quaternion', 'scale']:
                    if dr.mute == False:
                        dr.mute = True
                        arm_exp_dr_muted.append([dr.data_path, dr.array_index])    
        
        # disable constraints temporarily
        arm_exp_cns_muted = []
        for cns in rig.constraints:
            if cns.enabled:
                cns.enabled = False
                arm_exp_cns_muted.append(cns.name)
        
        #   scale them
        for _obj in bpy.context.selected_objects:
            _obj.location *= 100
            _obj.scale *= 100

        bpy.context.evaluated_depsgraph_get().update()
        
        meshes_bone_par = []
        unparented_meshes = []
        unparented_meshes_bone = {}
        for i in bpy.data.objects:
            if i.name.endswith("_arpexp") and i.parent_type == "BONE" and i.parent_bone != "" and i.parent == baked_armature:
                unparented_meshes_bone[i.name] = i.parent_bone
                meshes_bone_par.append(i)

        # unparent mesh children
        for mesh in meshes:
            if mesh.parent == rig:
                unparented_meshes.append(mesh.name)                
                mesh_mat = mesh.matrix_world.copy()
                mesh.parent = None
                bpy.context.evaluated_depsgraph_get().update()
                mesh.matrix_world = mesh_mat

        #   also bone parented meshes
        for mesh_name in unparented_meshes_bone:
            mesh_obj = get_object(mesh_name)
            mesh_mat = mesh_obj.matrix_world.copy()
            mesh_obj.parent = None
            bpy.context.evaluated_depsgraph_get().update()
            mesh_obj.matrix_world = mesh_mat

        # Apply scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.context.evaluated_depsgraph_get().update()

        # Scale anim location curves x100
        for action in bpy.data.actions:

            if not check_id_root(action):
                continue

            has_changed = False
            for fcurve in action.fcurves:
                if 'location' in fcurve.data_path:
                    for point in fcurve.keyframe_points:
                        point.co[1] *= 100
                        point.handle_left[1] *= 100
                        point.handle_right[1] *= 100
                        has_changed = True

            # keep track of modified actions, to revert changes later
            if has_changed:              
                self.actions_x100_changed.append([action.name, action.library])

        # Scale location values, necessary if no actions are exported
        if not self.actions_were_exported:
            for pb in rig.pose.bones:
                pb.location *= 100
            for pb in baked_armature.pose.bones:
                pb.location *= 100

        # reparent mesh children
        for meshname in unparented_meshes:
            mesh = get_object(meshname)
            mesh_mat = mesh.matrix_world.copy()
            get_object(meshname).parent = rig
            bpy.context.evaluated_depsgraph_get().update()
            mesh.matrix_world = mesh_mat

        #   and bone parented meshes
        for mesh_name in unparented_meshes_bone:
            mesh_obj = get_object(mesh_name)
            mesh_mat = mesh_obj.matrix_world.copy()
            mesh_obj.parent = baked_armature
            mesh_obj.parent_type = "BONE"
            mesh_obj.parent_bone = unparented_meshes_bone[mesh_name]
            bpy.context.evaluated_depsgraph_get().update()
            mesh_obj.matrix_world = mesh_mat

        # Initialize meshes scale
        for mesh in meshes + meshes_bone_par:
            
            set_active_object(mesh.name)
            # multiply scalable value of modifiers
            if len(mesh.modifiers) > 0:
                for mod in mesh.modifiers:
                    if mod.type == "MIRROR":
                        mod.merge_threshold *= 100
                    elif mod.type == "SOLIDIFY":
                        mod.thickness *= 100
                    elif mod.type == "BEVEL":
                        mod.width *= 100
                    elif mod.type == 'SHRINKWRAP':
                        if mod.target:
                            tar_ob = mod.target
                            tar_average_scale = (tar_ob.scale[0] + tar_ob.scale[1] + tar_ob.scale[2]) / 3
                            mod.offset *= tar_average_scale

        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        bpy.ops.object.mode_set(mode='OBJECT')

        # restore muted drivers
        for dp, arr_idx in arm_exp_dr_muted:
            fc = rig.animation_data.drivers.find(dp, index=arr_idx)
            fc.mute = False
            
        # restore muted constraints
        for cns_name in arm_exp_cns_muted:
            rig.constraints.get(cns_name).enabled = True
        
        # Change units system
        scn.unit_settings.system = 'METRIC'
        scn.unit_settings.scale_length = 0.01

        # Refresh
        scn.frame_current = current_frame
        scn.frame_set(scn.frame_current)#debug


        print('  x100 Units (baked) set successfully.')


def _unset_export_rig(arp_armature_name, humanoid_name):
    print('Unset export rig...')
    arp_armature = get_object(arp_armature_name)
    humanoid_armature = get_object(humanoid_name)
    
    #set surface subdivision to 0 to speed up
    simplify = bpy.context.scene.render.use_simplify #save
    simplify_value = bpy.context.scene.render.simplify_subdivision
    bpy.context.scene.render.use_simplify = True#set
    bpy.context.scene.render.simplify_subdivision = 0
    
    # get all deformed meshes
    skinned_meshes = []
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        if obj.find_armature() == None:
            continue
        
        if obj.find_armature().name == humanoid_name:
            skinned_meshes.append(obj.name)
            
    print('  Restoring ARP weights...')
    for obj_name in skinned_meshes:
        obj = get_object(obj_name)
        
        # restore vertex groups/weights
        if 'arp_saved_weights' in obj.keys():          
            # remove all existing groups
            vg_names = [vg.name for vg in obj.vertex_groups]# make a copy to avoid corrupted iteration when deleting
            for vg_name in vg_names:
                vg = obj.vertex_groups.get(vg_name)
                obj.vertex_groups.remove(vg)
                
            # restore saved groups 
            weight_dict = obj['arp_saved_weights']
              
            for grp_name in weight_dict:
                if weight_dict[grp_name] == None:# empty group, just create it
                    vg = obj.vertex_groups.get(grp_name)
                    if vg == None:
                        vg = obj.vertex_groups.new(name=grp_name)
                else:
                    weight_list = weight_dict[grp_name]               
                    for i, j in enumerate(weight_list):                 
                        vi, vertex_weight = weight_list[i]
                        vi = int(vi)
                        vg = obj.vertex_groups.get(grp_name)
                        if vg == None:
                            vg = obj.vertex_groups.new(name=grp_name)
                        vg.add([vi], vertex_weight, 'REPLACE')
                
                
        # restore armature modifiers
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                if mod.object:
                    if mod.object.name == humanoid_name:
                        mod.object = arp_armature
    
    print('  Remove humanoid armature...')
    # remove humanoid
    delete_object(humanoid_armature)
    
    # untag
    del arp_armature['arp_export_rig_set']
    
    
    #restore simplification
    bpy.context.scene.render.use_simplify = simplify
    bpy.context.scene.render.simplify_subdivision = simplify_value
    print('  Unset.')
    # end unset_export_rig()


def _save_mesh_weights(rig_name):
    # get all deformed meshes
    skinned_meshes = []
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        if obj.find_armature() == None:
            continue
        
        if obj.find_armature().name == rig_name:
            skinned_meshes.append(obj.name)
            
    # save weights
    for obj_name in skinned_meshes:
        obj = get_object(obj_name)       
        weight_dict = {}
        for v in obj.data.vertices:
            for vgroup in v.groups:
                grp_name = obj.vertex_groups[vgroup.group].name
                if grp_name in weight_dict:                  
                    cur_list = weight_dict[grp_name]                  
                    cur_list.append((v.index, vgroup.weight))
                    weight_dict[grp_name] = cur_list                   
                else:
                    weight_dict[grp_name] = [(v.index, vgroup.weight)]
                    
        # save unassigned vgroups too
        for vg in obj.vertex_groups:
            if not vg.name in weight_dict:
                weight_dict[vg.name] = None
        
        obj['arp_saved_weights'] = weight_dict
    
    
def _set_humanoid_rig(armature_name, armature_add_name, manual_set_debug, self):
    print("\n..............................Building humanoid rig..............................")
    scn = bpy.context.scene
    sides = ['.l', '.r']

    retro_softlink = scn.arp_retro_export_soft_fix

    arm_stretch_name = 'arm_stretch'
    arm_twist_name = 'arm_twist'
    thigh_stretch_name = 'thigh_stretch'
    thigh_twist_name = 'thigh_twist'

    # multi-lips support
    for bname in ard.get_variable_lips('.x', btype='CONTROLLER', no_side=True):
        if not bname in additional_facial_bones:
            additional_facial_bones.append(bname)
        if not bname in facial_transfer_head and 'top_' in bname:
            facial_transfer_head.append(bname)
        if not bname in facial_transfer_jaw and 'bot_' in bname:
            facial_transfer_jaw.append(bname)
            
    # multi-eyelids support
    for bname in ard.get_variable_eyelids('.x', btype='CONTROLLER', no_side=True):
        if not bname in additional_facial_bones:
            additional_facial_bones.append(bname)
        if not bname in facial_transfer_head and 'top' in bname:
            facial_transfer_head.append(bname)
            
    for side in ['.l', '.r']:# eyelid twk
        for lvl in ['bot', 'top']:
            facial_transfer_head.append('c_eyelid_twk_'+lvl+side)        

    # Select the arp armature
    arp_armature = None
    if manual_set_debug:
        arp_armature = get_object(armature_name)
    else:
        arp_armature = get_object(armature_name+'_arpexp')

    set_active_object(arp_armature.name)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(arp_armature.name)
    bpy.ops.object.mode_set(mode='EDIT')

    # get the current limbs
    limb_sides.get_multi_limbs()

    # get skinned meshes
    collected_meshes = []
    for obj in bpy.context.view_layer.objects:
        if not(obj.type == 'MESH' and ("_arpexp" in obj.name or manual_set_debug)):
            continue
        collected_meshes.append(obj.name)

    bpy.ops.object.mode_set(mode='OBJECT')
    

    # append the humanoid armature
    file_dir = os.path.dirname(os.path.abspath(__file__))
    addon_directory = os.path.dirname(file_dir)
    filepath = addon_directory + "/misc_presets/humanoid.blend"

    # load the objects data in the file
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.objects = data_from.objects

    # add the objects in the scene
    for obj in data_to.objects:
        if obj is not None:
            scn.collection.objects.link(obj)

    humanoid_armature = get_object('rig_humanoid')
    humanoid_armature.location = arp_armature.location

    # if root motion, the armature object is constrained to the c_traj controller
    if scn.arp_ue_root_motion:
        cns = humanoid_armature.constraints.new("CHILD_OF")
        cns.name = "Child Of"
        cns.target = arp_armature
        cns.subtarget = "c_traj"
        arp_armature.data.pose_position = 'REST'
        bpy.context.evaluated_depsgraph_get().update()
        cns.inverse_matrix = arp_armature.pose.bones["c_traj"].matrix.inverted()
        arp_armature.data.pose_position = 'POSE'
        bpy.context.evaluated_depsgraph_get().update()
    else:
        # otherwise constrained to the source armature object
        cns = humanoid_armature.constraints.new("COPY_TRANSFORMS")
        cns.name = "Copy Transforms"
        cns.target = arp_armature


    print("  Humanoid loaded. Setting up...")

    # Set the scale
    humanoid_armature.scale = arp_armature.scale
    set_active_object(humanoid_armature.name)
    hide_state = humanoid_armature.hide_get()
    unhide_object(humanoid_armature)

    # Setup spine bones amount
    # more than 3 spine bones
    if arp_armature.rig_spine_count > 3:
        set_active_object(humanoid_armature.name)
        bpy.ops.object.mode_set(mode='EDIT')
        for idx in range(3, arp_armature.rig_spine_count):
            str_idx = '%02d' % idx
            prev_idx = '%02d' % (idx-1)
            spine_name = "spine_"+str_idx+".x"
            prev_spine_name = "spine_"+prev_idx+".x"
            new_spine_bone = humanoid_armature.data.edit_bones.new(spine_name)
            new_spine_bone.head, new_spine_bone.tail = [0,0,0], [0,0,1]
            new_spine_bone.parent = get_edit_bone(prev_spine_name)
            bpy.ops.object.mode_set(mode='POSE')
            new_spine_pb = get_pose_bone(spine_name)
            cns = new_spine_pb.constraints.new("COPY_TRANSFORMS")
            cns.name = "Copy Transforms"
            cns.target = humanoid_armature
            cns.subtarget = spine_name
            bpy.ops.object.mode_set(mode='EDIT')

        # reparent shoulders and neck
        str_idx = '%02d' % (arp_armature.rig_spine_count-1)
        last_spine_bone = get_edit_bone("spine_"+str_idx+".x")

        for side in [".l", ".r"]:
            shoulder = get_edit_bone("shoulder"+side)
            shoulder.parent = last_spine_bone

        neck = get_edit_bone("neck.x")
        neck.parent = last_spine_bone


    # 3 spines bones
    elif arp_armature.rig_spine_count == 3:
        set_active_object(humanoid_armature.name)
        bpy.ops.object.mode_set(mode='EDIT')
        if get_edit_bone('spine_03.x') != None:
            bpy.ops.armature.select_all(action='DESELECT')
            humanoid_armature.data.edit_bones.active = get_edit_bone('spine_03.x')
            bpy.ops.armature.delete()
            get_edit_bone('spine_02.x').tail = get_edit_bone('neck.x').head

    # less than 3 spine bones: automatically set by auto-deletion of null length bones

    bpy.ops.object.mode_set(mode='EDIT')

    # Disable X Mirror
    humanoid_armature.data.use_mirror_x = False

    # Delete non-selected bones
    if scn.arp_ge_sel_bones_only:
        for ebone in humanoid_armature.data.edit_bones:
            if not ebone.name in self.selected_bone_names:
                delete_edit_bone(ebone)

    # Delete default facial
    if not is_facial_enabled(arp_armature):     
        for bone in default_facial_bones:
            if not bone.endswith(".x"):
                for side in sides:
                    b = get_edit_bone(bone+side)
                    if b:
                        delete_edit_bone(b)
            else:
                bone_name = bone

                # exception
                if bone == "jawbone.x":
                    bone_name = "c_jawbone.x"

                b = get_edit_bone(bone_name)
                if b:
                    delete_edit_bone(b)


    bpy.ops.object.mode_set(mode='POSE')

    # Initialize bones dict: name, head (blank coords), tail (blank), roll (blank), use_deform (always True)
    #print("  Set up bones dict...")
    bones_dict = {}

    for pbone in humanoid_armature.pose.bones:
        # set constraints targets
        for cns in pbone.constraints:
            cns.target = arp_armature
            if cns.name == 'Copy Transforms':
                _subtarget = pbone.name

                if pbone.name == "c_jawbone.x":
                    _subtarget = "jawbone.x"

                if pbone.name.startswith('c_thumb1') or pbone.name.startswith('c_index1') or pbone.name.startswith('c_middle1') or pbone.name.startswith('c_ring1') or pbone.name.startswith('c_pinky1'):
                    _subtarget = pbone.name[2:]

                #store in dict
                bones_dict[pbone.name] = {"head":Vector((0.0,0.0,0.0)), "tail":Vector((0.0,0.0,0.0)), "roll":0.0, "deform":True}

                if arp_armature.data.bones.get(_subtarget):
                    cns.subtarget = _subtarget
                else:
                    cns.subtarget = ""

    # Select the arp armature
    bpy.ops.object.mode_set(mode='OBJECT')

    set_active_object(arp_armature.name)

    # Define Humanoid rest pose from ARP armature
    bpy.ops.object.mode_set(mode='POSE')

    #   lock the root translation because no stretch allowed for Humanoid
    for i in range(0,3):
        get_pose_bone("c_root.x").lock_location[i] = True

    # change secondary controllers arms/legs parent if necessary
    bpy.ops.object.mode_set(mode='EDIT')

    if scn.arp_keep_bend_bones and arp_armature.arp_secondary_type == "ADDITIVE":
        print("  Change secondary parents...")

        for edit_bone in arp_armature.data.edit_bones:
            bone_name = edit_bone.name

            if not is_proxy_bone(edit_bone):
                if 'thigh_bend_contact' in bone_name or 'thigh_bend_01' in bone_name:
                    new_parent = 'thigh_twist' + bone_name[-2:]
                    edit_bone.parent = arp_armature.data.edit_bones[new_parent]
                if 'ankle_bend' in bone_name:
                    new_parent = 'leg_twist' + bone_name[-2:]
                    edit_bone.parent = arp_armature.data.edit_bones[new_parent]
                if 'shoulder_bend' in bone_name:
                    new_parent = 'arm_twist' + bone_name[-2:]
                    edit_bone.parent = arp_armature.data.edit_bones[new_parent]
                if 'wrist_bend' in bone_name:
                    new_parent = 'forearm_twist' + bone_name[-2:]
                    edit_bone.parent = arp_armature.data.edit_bones[new_parent]


    # --Store bones data in dict
    # Store twist and stretch bones
    twist_bones_dict = {}
    twist_bones = ["c_arm_twist_offset", "forearm_twist", "thigh_twist", "leg_twist"]

    #     save the c_stretch bone if secondary are set to twist_based
    c_stretch_dict = {}
    if arp_armature.arp_secondary_type == "TWIST_BASED":
        for side in [".l", ".r"]:
            for bname in ['arm', 'forearm', 'thigh', 'leg']:
                c_stretch_name = 'c_'+bname+'_stretch'+side
                c_stretch = get_edit_bone(c_stretch_name)
                if c_stretch == None:
                    continue# disable limbed
                b_parent_n = bname+'_stretch'+side
                sftlink = is_softlink_bone(c_stretch_name)
                
                c_stretch_dict[c_stretch_name] = {"head":c_stretch.head.copy(), "tail":c_stretch.tail.copy(), "roll":c_stretch.roll, 
                    "parent":b_parent_n, "softlink":sftlink, 'const_interp':is_const_interp_bone(c_stretch.name)}


    if scn.arp_export_twist:
        #print("    twist...")
        for bone_name in twist_bones:
            for side in [".l", ".r"]:
                twist_bone_name = bone_name+side
                twist_bone = get_edit_bone(twist_bone_name)

                if twist_bone == None:
                    continue

                if scn.arp_ge_sel_bones_only:
                    if not twist_bone.name in self.selected_bone_names:
                        continue

                # Legs
                if bone_name == "thigh_twist" or bone_name == "leg_twist":
                    # multiple twist support
                    thigh_ref = get_edit_bone("thigh_ref"+side)
                    twist_bones_amount = 1
                    if len(thigh_ref.keys()):
                        if "twist_bones_amount" in thigh_ref.keys():
                            twist_bones_amount = thigh_ref["twist_bones_amount"]

                    if bone_name == "leg_twist":
                        # first leg twist bone (default)
                        b_parent = "leg_stretch"+side
                        
                        twist_bones_dict[twist_bone_name] = {"head":twist_bone.head.copy(), "tail":twist_bone.tail.copy(), "roll":twist_bone.roll, 
                        "parent":b_parent, "softlink":is_softlink_bone(twist_bone_name), 'type':'leg_main', 'const_interp':is_const_interp_bone(twist_bone_name),
                        'arp_bone':twist_bone_name}
                        
                        # multiple leg twist bones
                        if twist_bones_amount > 1:
                            for t_idx in range(2, twist_bones_amount+1):
                                leg_twist_idx_name = 'leg_twist_'+str(t_idx)+side
                                leg_twist_idx = get_edit_bone(leg_twist_idx_name)
                                b_parent = 'leg_stretch'+side
                                
                                twist_bones_dict[leg_twist_idx_name] = {"head":leg_twist_idx.head.copy(), "tail":leg_twist_idx.tail.copy(), "roll":leg_twist_idx.roll, 
                                "parent":b_parent, "softlink":is_softlink_bone(leg_twist_idx_name), 'type':'leg_multi', 'const_interp':is_const_interp_bone(leg_twist_idx_name),
                                'arp_bone':leg_twist_idx.name}

                    if bone_name == "thigh_twist":
                        # first thigh twist bone (default)
                        b_parent = "thigh_stretch"+side
                        twist_bones_dict[twist_bone_name] = {"head":twist_bone.head.copy(), "tail":twist_bone.tail.copy(), "roll":twist_bone.roll, 
                        "parent":b_parent, "softlink":is_softlink_bone(twist_bone_name), 'type':'thigh_main', 'const_interp':is_const_interp_bone(twist_bone_name),
                        'arp_bone':twist_bone.name}
                        
                        # multiple leg twist bones
                        if twist_bones_amount > 1:
                            for t_idx in range(2, twist_bones_amount+1):
                                thigh_twist_idx_name = 'thigh_twist_'+str(t_idx)+side
                                thigh_twist_idx = get_edit_bone(thigh_twist_idx_name)
                                b_parent = 'thigh_stretch'+side
                                
                                twist_bones_dict[thigh_twist_idx_name] = {"head":thigh_twist_idx.head.copy(), "tail":thigh_twist_idx.tail.copy(), "roll":thigh_twist_idx.roll, 
                                "parent":b_parent, "softlink":is_softlink_bone(thigh_twist_idx_name), 'type':'thigh_multi', 'const_interp':is_const_interp_bone(thigh_twist_idx_name),
                                'arp_bone':thigh_twist_idx.name}

                # Arms
                if bone_name == "c_arm_twist_offset" or bone_name == "forearm_twist":
                    # multiple twist support
                    arm_ref = get_edit_bone("arm_ref"+side)
                    twist_bones_amount = 1
                    if len(arm_ref.keys()) > 0:
                        if "twist_bones_amount" in arm_ref.keys():
                            twist_bones_amount = arm_ref["twist_bones_amount"]

                    if bone_name == "forearm_twist":
                        # first forearm twist bone (default)
                        b_parent = "forearm_stretch"+side
                        
                        twist_bones_dict[twist_bone_name] = {"head":twist_bone.head.copy(), "tail":twist_bone.tail.copy(), "roll":twist_bone.roll, 
                            "parent":b_parent, "softlink":is_softlink_bone(twist_bone_name), 'type':'forearm_main', 'const_interp':is_const_interp_bone(twist_bone_name),
                            'arp_bone':twist_bone.name}
                        
                        # multiple forearm twist bones
                        if twist_bones_amount > 1:
                            for t_idx in range(2, twist_bones_amount+1):
                                forearm_twist_idx_name = 'forearm_twist_'+str(t_idx)+side
                                forearm_twist_idx = get_edit_bone(forearm_twist_idx_name)
                                b_parent = 'forearm_stretch'+side
                                
                                twist_bones_dict[forearm_twist_idx_name] = {"head":forearm_twist_idx.head.copy(), "tail":forearm_twist_idx.tail.copy(), "roll":forearm_twist_idx.roll, 
                                    "parent":b_parent, "softlink":is_softlink_bone(forearm_twist_idx_name), 'type':'forearm_multi', 
                                    'const_interp':is_const_interp_bone(forearm_twist_idx_name), 'arp_bone':forearm_twist_idx.name}

                    if bone_name == "c_arm_twist_offset":
                        # first arm twist bone (default)
                        b_parent = "arm_stretch"+side
                        
                        twist_bones_dict[twist_bone_name] = {"head":twist_bone.head.copy(), "tail":twist_bone.tail.copy(), "roll":twist_bone.roll, 
                            "parent":b_parent, "softlink":is_softlink_bone(twist_bone_name), 'type':'arm_main', 
                            'const_interp':is_const_interp_bone(twist_bone_name), 'arp_bone':twist_bone.name}
                        
                        # multiple leg twist bones
                        if twist_bones_amount > 1:
                            for t_idx in range(2, twist_bones_amount+1):
                                arm_twist_idx_name = 'arm_twist_'+str(t_idx)+side
                                arm_twist_idx = get_edit_bone(arm_twist_idx_name)
                                b_parent = 'arm_stretch'+side
                                
                                twist_bones_dict[arm_twist_idx.name] = {"head":arm_twist_idx.head.copy(), "tail":arm_twist_idx.tail.copy(), "roll":arm_twist_idx.roll,
                                    "parent":b_parent, "softlink":is_softlink_bone(arm_twist_idx_name), 'type':'arm_multi',
                                    'const_interp':is_const_interp_bone(arm_twist_idx_name), 'arp_bone':arm_twist_idx.name}


    # Store extra limbs
    # Ears
    for dupli in limb_sides.ear_sides:
        for ear_id in range(0, 17):
            id = '%02d' % ear_id
            c_bone = get_edit_bone('c_ear_'+id+dupli)
            if c_bone == None:
                continue

            if scn.arp_ge_sel_bones_only:
                if not c_bone.name in self.selected_bone_names:
                    continue

            if is_deforming(c_bone.name):
                bones_dict[c_bone.name] = {"head":c_bone.head.copy(), "tail":c_bone.tail.copy(), "roll":c_bone.roll, 
                "deform":True, "softlink":is_softlink_bone(c_bone.name), 'const_interp':is_const_interp_bone(c_bone.name),
                'arp_bone':c_bone.name}

    # Tail
    for dupli in limb_sides.tail_sides:
        for tail_id in range(0,32):
            id = '%02d' % tail_id
            c_bone = get_edit_bone('c_tail_'+id+dupli)

            if c_bone == None:
                continue

            if c_bone:
                if scn.arp_ge_sel_bones_only:
                    if not c_bone.name in self.selected_bone_names:
                        continue

                if c_bone.use_deform:
                    bones_dict[c_bone.name] = {"head":c_bone.head.copy(), "tail":c_bone.tail.copy(), "roll":c_bone.roll, 
                    "deform":True, "softlink":is_softlink_bone(c_bone.name), 'const_interp':is_const_interp_bone(c_bone.name),
                    'arp_bone':c_bone.name}


    for edit_bone in arp_armature.data.edit_bones:
        bone_softlink = is_softlink_bone(edit_bone.name)

        if scn.arp_ge_sel_bones_only:
            if not edit_bone.name in self.selected_bone_names:
                continue

        # Custom bones
        if is_custom_bone(edit_bone.name):
            if not edit_bone.name in bones_dict:
            
                bones_dict[edit_bone.name] = {"head":edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                                            "deform":True, "softlink":bone_softlink, 'const_interp':is_const_interp_bone(edit_bone.name),
                                            'arp_bone':edit_bone.name}
            else:
                print("  "+edit_bone.name+" is marked as a custom bone but is already part of the base rig, skip it")
                exclude_custom_bone(edit_bone.name)
                
        # c_traj forced export
        if scn.arp_ge_master_traj:
            if edit_bone.name == 'c_traj':
                if not edit_bone.name in bones_dict:
                
                    bones_dict[edit_bone.name] = {"head":edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                                            "deform":True, "softlink":bone_softlink, 'const_interp':is_const_interp_bone(edit_bone.name),
                                            'arp_bone':edit_bone.name}

        # Bend Bones
        if scn.arp_keep_bend_bones:
            is_bend_bone_valid = True
            if arp_armature.arp_secondary_type == "ADDITIVE":
                if not is_bend_bone(edit_bone.name) or is_proxy_bone(edit_bone):
                    is_bend_bone_valid = False
            elif arp_armature.arp_secondary_type == "TWIST_BASED":
                if not is_bend_bone_spine_only(edit_bone.name) or is_proxy_bone(edit_bone):
                    is_bend_bone_valid = False
            else:
                is_bend_bone_valid = False

            if is_bend_bone_valid:
            
                bones_dict[edit_bone.name] = {"head":edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                        "deform":True, "softlink":bone_softlink, 'const_interp':is_const_interp_bone(edit_bone.name),
                        'arp_bone':edit_bone.name}

        # Facial
        if scn.arp_full_facial and is_facial_enabled(arp_armature):
            if edit_bone.name[:-2] in additional_facial_bones:
                bones_dict[edit_bone.name] = {"head":edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                        "deform":True, "softlink":bone_softlink, 'const_interp':is_const_interp_bone(edit_bone.name),
                        'arp_bone':edit_bone.name}

        # Toes
        if edit_bone.name.startswith('c_toes_'):
            if edit_bone.use_deform:
                bones_dict[edit_bone.name] = {"head":edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                        "deform":True, "softlink":bone_softlink, 'const_interp':is_const_interp_bone(edit_bone.name),
                        'arp_bone':edit_bone.name}

        # Breast
        if edit_bone.name[:-2] == "c_breast_01" or edit_bone.name[:-2] == "c_breast_02":
            if edit_bone.use_deform:
                bones_dict[edit_bone.name] = {"head":edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                        "deform":True, "softlink":bone_softlink, 'const_interp':is_const_interp_bone(edit_bone.name),
                        'arp_bone':edit_bone.name}

        # Bottoms
        if edit_bone.name[:-2] == "c_bot_bend":
            if edit_bone.use_deform:
                bones_dict[edit_bone.name] = {"head":edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                        "deform":True, "softlink":bone_softlink, 'const_interp':is_const_interp_bone(edit_bone.name),
                        'arp_bone':edit_bone.name}

    eyelids = ['eyelid_bot.l', 'eyelid_bot.r', 'eyelid_top.l', 'eyelid_top.r']

    # Store main bones
    for bname in bones_dict:
        if is_custom_bone(bname) or is_bend_bone(bname):
            continue

        _bname = bname
        if _bname in eyelids:
            _bname = 'c_' + _bname

        edit_bone = get_edit_bone(_bname)
        if edit_bone == None:# the bone belongs to a disabled limb, store it with null values
            bones_dict[bname] = {"head":Vector((0,0,0)), "tail":Vector((0,0,0)), "roll":0.0, "deform":False, "softlink":False, 'const_interp':False}        
            continue

        bone_softlink = is_softlink_bone(_bname)
        side = bname[-2:]

        #Check for deform - Disabled limbs
        if 'spine' in _bname or 'root' in _bname or _bname == 'c_traj' or 'arm_stretch' in _bname \
            or 'thigh_stretch' in _bname or 'leg_stretch' in _bname:#these bones can't be disabled in Humanoid, main structure
            b_use_deform = True
        #finger1 case
        elif 'c_pinky1' in _bname:
            b_use_deform = get_edit_bone('c_pinky2'+side).use_deform
        elif 'c_ring1' in _bname:
            b_use_deform = get_edit_bone('c_ring2'+side).use_deform
        elif 'c_middle1' in _bname:
            b_use_deform = get_edit_bone('c_middle2'+side).use_deform
        elif 'c_index1' in _bname:
            b_use_deform = get_edit_bone('c_index2'+side).use_deform
        elif 'c_thumb1' in _bname:
            b_use_deform = get_edit_bone('c_thumb2'+side).use_deform

        # jaw case
        elif 'c_jawbone.x' in _bname:
            b_use_deform = get_edit_bone('jawbone.x').use_deform
        else:
            b_use_deform = edit_bone.use_deform
        
 
        bones_dict[bname] = {"head": edit_bone.head.copy(), "tail":edit_bone.tail.copy(), "roll":edit_bone.roll, 
                "deform":b_use_deform, "x_axis":edit_bone.x_axis.copy(), "softlink":bone_softlink, 'const_interp':is_const_interp_bone(_bname),
                'arp_bone':edit_bone.name}


    # Get the thigh real head pose, because thigh_stretch is halfway
    for side in sides:        
        bname = 'thigh_ref'+side
        thigh_ref = get_edit_bone(bname)
        if thigh_ref:
            bones_dict[bname] = {"head":thigh_ref.head.copy(), "tail":thigh_ref.tail.copy(), "roll":thigh_ref.roll, 
                    "deform":False}


    if is_facial_enabled(arp_armature):
        # Get the jaw real transform
        jaw = get_edit_bone('jawbone.x')
        jaw_softlink = is_softlink_bone('jawbone.x')

        if jaw:
            if 'c_jawbone.x' in bones_dict:
                bones_dict['c_jawbone.x'] = {"head":jaw.head.copy(), "tail":jaw.tail.copy(), "roll":jaw.roll, 
                        "deform":bones_dict['c_jawbone.x']["deform"], "softlink":jaw_softlink, 'const_interp':is_const_interp_bone('jawbone.x'),
                        'arp_bone':'jawbone.x'}

        # Get the eyelids real transform
        for side in sides:
            eyelid_softlink = is_softlink_bone('c_eyelid_top_01'+side)

            for pos in ["_top", "_bot"]:
                bname = 'eyelid'+pos+side
                eyel = get_edit_bone(bname)

                if eyel == None or not bname in bones_dict:
                    continue

                bones_dict[bname] = {"head":eyel.head.copy(), "tail":eyel.tail.copy(), "roll":eyel.roll, 
                        "deform":bones_dict[bname]["deform"], "softlink":eyelid_softlink, 'const_interp':is_const_interp_bone('c_eyelid_top_01'+side),
                        'arp_bone':'c_eyelid_top_01'+side}

    
    all_extra_coords = {}
    
    # Store fingers metacarps (UE5)
    fingers_metacarps_coords = {}
    
    if (scn.arp_engine_type == 'UNREAL' and not scn.arp_ue4) or (scn.arp_engine_type == 'OTHERS' and scn.arp_ge_export_metacarp):        
        fingers_meta = ['c_index1_base', 'c_middle1_base', 'c_ring1_base', 'c_pinky1_base']
        
        for fname in fingers_meta:
            for side in sides:
                b = get_edit_bone(fname+side)
                if b == None: 
                    continue
                    
                if scn.arp_ge_sel_bones_only:
                    if not b.name in self.selected_bone_names:
                        continue
                        
                bone_softlink = is_softlink_bone(b.name)
                fingers_metacarps_coords[b.name] = {'head':b.head.copy(), 'tail':b.tail.copy(), 'roll':b.roll, 
                        'deform':True, 'x_axis':b.x_axis.copy(), 'softlink':bone_softlink, 'parent':'hand'+side, 'const_interp':is_const_interp_bone(b.name),
                        'arp_bone':b.name}
    
    all_extra_coords.update(fingers_metacarps_coords)
    
    # Store subnecks (humanoid)
    subneck_coords = {}
    neck_count = 1
    neck_twist_enabled = False
    neck_ref = get_edit_bone("neck_ref.x")

    if neck_ref:
        if "neck_twist" in neck_ref.keys():
            neck_twist_enabled = neck_ref["neck_twist"]
        if "neck_count" in neck_ref.keys():
            neck_count = neck_ref["neck_count"]
        if neck_count > 1:
            for idx in range(1, neck_count):
                subneck_deform_name = ""
                subneck_cont_name = "c_subneck_"+str(idx)+".x"
                if neck_twist_enabled:
                    subneck_deform_name = "subneck_twist_"+str(idx)+".x"
                else:
                    subneck_deform_name = subneck_cont_name

                subneck_deform = get_edit_bone(subneck_deform_name)
                subneck_cont = get_edit_bone(subneck_cont_name)
                subneck_parent_name = ''
                if subneck_cont.parent:
                    subneck_parent_name = subneck_cont.parent.name

                if scn.arp_ge_sel_bones_only:
                    if not subneck_deform.name in self.selected_bone_names:
                        continue

                subneck_softlink = is_softlink_bone(subneck_deform_name)

                subneck_coords[subneck_cont_name] = {"head":subneck_deform.head.copy(), "tail":subneck_deform.tail.copy(), "roll":subneck_deform.roll, 
                        "parent":subneck_parent_name, "softlink":subneck_softlink, 'const_interp':is_const_interp_bone(subneck_deform_name),
                        'arp_bone':subneck_deform.name}

    all_extra_coords.update(subneck_coords)
    
    # Store Wings (humanoid)
    wings_coords = {}
    for side in limb_sides.wing_sides:
        wings_export_to_dict(side, wings_coords, sel_bone_names=self.selected_bone_names)
        
    all_extra_coords.update(wings_coords)
    
    # Store Spline IK (humanoid)
    spline_ik_coords = {}
    for side in limb_sides.spline_sides:
        spline_name = auto_rig.get_spline_name(side)
        spline_ik_export_to_dict(spline_name, side, spline_ik_coords, sel_bone_names=self.selected_bone_names)
        
    all_extra_coords.update(spline_ik_coords)
    
    # Store Kilts (humanoid)
    kilt_coords = {}
    for side in limb_sides.kilt_sides:            
        kilt_export_to_dict(side, kilt_coords, sel_bone_names=self.selected_bone_names)
        
    all_extra_coords.update(kilt_coords)
    
    # Extra arms
    extra_arms_coords = {}
    for i, side in enumerate(limb_sides.arm_sides):
        if i > 1:# humanoid armature already has 2 arms
            arms_export_to_dict(side, extra_arms_coords)
            
    all_extra_coords.update(extra_arms_coords)
    
    # Arms joints fans (humanoid)
    arms_fans_coords = {}
    for side in limb_sides.arm_sides:      
        arms_fans_export_to_dict(side, arms_fans_coords, sel_bone_names=self.selected_bone_names)
        
    all_extra_coords.update(arms_fans_coords)
    
    legs_fans_coords = {}
    toes_ikfk_coords = {}
    
    for side in limb_sides.leg_sides: 
        # Legs joints fans
        legs_fans_export_to_dict(side, legs_fans_coords, sel_bone_names=self.selected_bone_names)    
        
        # Toes IKFK
        legs_toes_ikfk_export_to_dict(side, toes_ikfk_coords, sel_bone_names=self.selected_bone_names)  
    
    all_extra_coords.update(legs_fans_coords)
    all_extra_coords.update(toes_ikfk_coords)  
    
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    set_active_object(humanoid_armature.name)
    bpy.ops.object.mode_set(mode='EDIT')


    # Add missing bones, with blank data
    print("  Create additional bones...")
    for bname in bones_dict:
        if get_edit_bone(bname) != None:
            continue

        # do not create the thigh_ref, only there for placement reference
        if 'thigh_ref' in bname:
            continue

        new_bone = create_edit_bone(bname, deform=True)
        new_bone.head = Vector((0,0,0))
        new_bone.tail = Vector((0,1,0))
        new_bone["softlink"] = bones_dict[bname]["softlink"]
        new_bone["const_interp"] = bones_dict[bname]["const_interp"]

        
    # Add fingers metacarps (UE5 or Others)
    for bname in fingers_metacarps_coords:
        new_bone = humanoid_armature.data.edit_bones.new(bname)
        new_bone.head, new_bone.tail, new_bone.roll = fingers_metacarps_coords[bname]["head"], fingers_metacarps_coords[bname]["tail"], fingers_metacarps_coords[bname]["roll"]
        new_bone["softlink"] = fingers_metacarps_coords[bname]["softlink"]
        new_bone["const_interp"] = fingers_metacarps_coords[bname]["const_interp"]
        
    # Add subnecks
    for bname in subneck_coords:
        new_bone = humanoid_armature.data.edit_bones.new(bname)
        new_bone.head, new_bone.tail, new_bone.roll = subneck_coords[bname]["head"], subneck_coords[bname]["tail"], subneck_coords[bname]["roll"]
        new_bone["softlink"] = subneck_coords[bname]["softlink"]
        new_bone["const_interp"] = subneck_coords[bname]["const_interp"]

    # Add wings
    for bname in wings_coords:
        new_bone = humanoid_armature.data.edit_bones.new(bname)
        new_bone.head, new_bone.tail, new_bone.roll = wings_coords[bname]["head"], wings_coords[bname]["tail"], wings_coords[bname]["roll"]
        new_bone["softlink"] = wings_coords[bname]["softlink"]
        new_bone["const_interp"] = wings_coords[bname]["const_interp"]
        new_bone["arp_feather"] = 1

    # Add spline ik
    for bname in spline_ik_coords:
        new_bone = humanoid_armature.data.edit_bones.new(bname)
        new_bone.head, new_bone.tail, new_bone.roll = spline_ik_coords[bname]["head"], spline_ik_coords[bname]["tail"], spline_ik_coords[bname]["roll"]
        new_bone["arp_spline"] = 1
        new_bone["const_interp"] = spline_ik_coords[bname]["const_interp"]
        new_bone["softlink"] = spline_ik_coords[bname]["softlink"]
        
    # Add Kilts
    for bname in kilt_coords:
        new_bone = humanoid_armature.data.edit_bones.new(bname)
        new_bone.head, new_bone.tail, new_bone.roll = kilt_coords[bname]["head"], kilt_coords[bname]["tail"], kilt_coords[bname]["roll"]
        new_bone["arp_kilt"] = 1
        new_bone["const_interp"] = kilt_coords[bname]["const_interp"]
        new_bone["softlink"] = kilt_coords[bname]["softlink"]     
        
    # Add extra Arms
    for bname in extra_arms_coords:
        new_bone = humanoid_armature.data.edit_bones.new(bname)
        new_bone.head, new_bone.tail, new_bone.roll = extra_arms_coords[bname]["head"], extra_arms_coords[bname]["tail"], extra_arms_coords[bname]["roll"]
        new_bone["softlink"] = extra_arms_coords[bname]["softlink"] 
        new_bone["const_interp"] = extra_arms_coords[bname]["const_interp"]
        
    # Add arm, legs fans, toes IKFK
    fans_coords = {**arms_fans_coords, **legs_fans_coords, **toes_ikfk_coords}
    for bname in fans_coords:
        new_bone = humanoid_armature.data.edit_bones.new(bname)
        new_bone.head, new_bone.tail, new_bone.roll = fans_coords[bname]["head"], fans_coords[bname]["tail"], fans_coords[bname]["roll"]
        new_bone["softlink"] = fans_coords[bname]["softlink"] 
        new_bone["const_interp"] = fans_coords[bname]["const_interp"]
    
    
    # Add twist bones
    print("  Create twist bones...")
    if len(twist_bones_dict):
        for twist_bone_name in twist_bones_dict:
            bname = twist_bone_name
            if twist_bone_name.startswith("c_arm_twist_offset"):
                    bname = twist_bone_name.replace("c_arm_twist_offset", "arm_twist")
            new_bone = humanoid_armature.data.edit_bones.new(bname)
            new_bone.head = twist_bones_dict[twist_bone_name]["head"]
            new_bone.tail = twist_bones_dict[twist_bone_name]["tail"]
            new_bone.roll = twist_bones_dict[twist_bone_name]["roll"]
            new_bone.parent = get_edit_bone(twist_bones_dict[twist_bone_name]["parent"])
            new_bone["softlink"] = twist_bones_dict[twist_bone_name]["softlink"]
            new_bone["const_interp"] = twist_bones_dict[twist_bone_name]["const_interp"]

    # Add stretch bones
    if len(c_stretch_dict):
        for stretch_bone_name in c_stretch_dict:            
            new_bone = create_edit_bone(stretch_bone_name, deform=True)
            new_bone.head = c_stretch_dict[stretch_bone_name]["head"]
            new_bone.tail = c_stretch_dict[stretch_bone_name]["tail"]
            new_bone.roll = c_stretch_dict[stretch_bone_name]["roll"]
            new_bone.parent = get_edit_bone(c_stretch_dict[stretch_bone_name]["parent"])
            new_bone["softlink"] = c_stretch_dict[stretch_bone_name]["softlink"]
            new_bone["const_interp"] = c_stretch_dict[stretch_bone_name]["const_interp"]

    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')

    def is_in_facial_deform(bone):
        for b in ard.facial_deform:
            if b in bone:
                return True


    # matching bone parent function (humanoid)
    def find_matching_parent(par=None, item=None):
        _parent = ""

        #root
        if par == 'c_root_bend.x':
            _parent = 'root.x'
        if par == 'c_root_master.x':
            _parent = 'root.x'
        if par == 'c_root.x':
            _parent = 'root.x'

        # spines
        for id in range(1, 33):
            str_id = '%02d' % id
            if par == 'c_spine_'+str_id+'.x':
                _parent = 'spine_'+str_id+'.x'
            if par == "c_spine_"+str_id+"_bend.x":
                _parent = 'spine_'+str_id+'.x'

        if 'neck' in par:
            _parent = 'neck.x'
        elif 'head' in par or ('skull' in par and scn.arp_full_facial == False and is_facial_enabled(arp_armature) == False):
            _parent = 'head.x'
        elif par.startswith("c_skull_") and scn.arp_full_facial == False:
            _parent = "head.x"
        elif 'shoulder' in par:
            _parent = 'shoulder' + par[-2:]
        elif par.startswith("c_arm_twist_offset"):
            _parent = par.replace("c_arm_twist_offset", "arm_twist")
        elif 'arm' in par and not 'forearm' in par:
            _parent = 'arm_stretch' + par[-2:]
        elif 'forearm' in par:
            _parent = 'forearm_stretch' + par[-2:]
        elif 'hand' in par:
            _parent = 'hand' + par[-2:]
        elif 'thigh' in par:
            _parent = 'thigh_stretch' + par[-2:]
        elif 'leg' in par:
            _parent = 'leg_stretch' + par[-2:]
        elif 'foot' in par:
            _parent = 'foot' + par[-2:]
        elif 'toes' in par:
            _parent = 'toes_01' + par[-2:]
        elif 'tong_03' in par:
            _parent = 'tong_02.x'
        elif 'tong_02' in par:
            _parent = 'tong_01.x'
        elif 'tong_01' in par:
            _parent = 'c_jawbone.x'
        elif 'eyelid' in par and not ("top_0" in bone or "bot_0" in bone):# not secondary eyelids
            _parent = 'c_eye_offset' + par[-2:]
        elif "c_eyelid_bot" in par:# secondary eyelids
            _parent = "eyelid_bot" + par[-2:]
        elif "c_eyelid_top" in par:
            _parent = "eyelid_top" + par[-2:]
        elif 'teeth_top_master' in par:
            if arp_armature.data.bones.get('c_skull_01.x'):
                _parent = 'c_skull_01.x'
            else:
                _parent = 'head.x'
        elif 'teeth_bot_master' in par:
            _parent = 'c_jawbone.x'
        elif 'jawbone.x' in par:
            _parent = 'c_jawbone.x'

        return _parent

    # Set their parent
    print("  Set parents...")
    # root
    c_root_master = arp_armature.data.bones.get("c_root_master.x")    
    
    if c_root_master.parent:
        # in case the rig has custom master bones, use them as root parent
        if is_custom_bone(c_root_master.parent.name):
            parent_name = c_root_master.parent.name
            get_edit_bone('root.x').parent = get_edit_bone(parent_name)
            
        # if c_traj export is forced
        elif scn.arp_ge_master_traj:
            if c_root_master.parent.name == 'c_traj':
                get_edit_bone('root.x').parent = get_edit_bone('c_traj')
            

    for bname in bones_dict:
        if is_custom_bone(bname) or is_bend_bone(bname) or (is_in_facial_deform(bname) and scn.arp_full_facial) or bname[:-2] in additional_facial_bones or bname.startswith('c_toes_') or bname.startswith("c_tail_") or bname.startswith("c_breast_01") or bname.startswith("c_breast_02") or bname.startswith("c_ear_"):

            bone_parent_name = ''
            
            eb = arp_armature.data.bones.get(bname)
            if eb:
                if eb.parent:
                    bone_parent_name = eb.parent.name        

            # override these parents
            _parent = ""
            if 'c_eye_ref' in bname:
                bone_parent_name = 'c_eye_offset' + bname[-2:]

            # full facial case parents
            if scn.arp_full_facial and is_facial_enabled(arp_armature):
                if 'jawbone' in bname:
                    if arp_armature.data.bones.get('c_skull_01.x'):
                        bone_parent_name = 'c_skull_01.x'
                    else:
                        bone_parent_name = 'head.x'
                        
                if 'eye_offset' in bname:
                    if arp_armature.data.bones.get('c_skull_02.x'):
                        bone_parent_name = 'c_skull_02.x'
                    else:
                        bone_parent_name = 'head.x'
                        
                if 'lips_' in bname and ('_offset' in bone_parent_name or '_master' in bone_parent_name):
                    if 'top' in bname or 'smile' in bname:
                        if arp_armature.data.bones.get('c_skull_01.x'):
                            bone_parent_name = 'c_skull_01.x'
                        else:
                            bone_parent_name = 'head.x'
                            
                    if 'bot' in bname:
                        bone_parent_name = 'c_jawbone.x'

            # secondary arms/legs cases
            if scn.arp_keep_bend_bones and (arp_armature.arp_secondary_type == "ADDITIVE" or arp_armature.arp_secondary_type == "TWIST_BASED"):
                if 'thigh_bend_contact' in bname or 'thigh_bend_01' in bname:
                    bone_parent_name = 'thigh_twist' + bname[-2:]

                if 'ankle_bend' in bname:
                    bone_parent_name = 'leg_twist' + bname[-2:]

                if 'shoulder_bend' in bname:
                    bone_parent_name = 'arm_twist' + bname[-2:]

                if 'wrist_bend' in bname:
                    bone_parent_name = 'forearm_twist' + bname[-2:]

            # try to find parent bone in the humanoid armature. If not found, look for other matches
            if get_edit_bone(bone_parent_name):
                _parent = bone_parent_name                
            else:
                _parent = find_matching_parent(par=bone_parent_name, item="bone")             

            # Assign the bone parent
            if get_edit_bone(_parent):
                get_edit_bone(bname).parent = get_edit_bone(_parent)

    
    # fingers metacarps parent
    for bname in fingers_metacarps_coords:
        b = get_edit_bone(bname)
        b.parent = get_edit_bone(fingers_metacarps_coords[bname]['parent'])
        # need to parent the 1st phalange to it
        first_phal = get_edit_bone(b.name.replace('_base', ''))
        if first_phal:
            first_phal.parent = b
    
    # subnecks parent, use a dedicated dict for convenience
    last_subneck = None
    last_id = 0
    for bname in subneck_coords:
        ebone = get_edit_bone(bname)
        par_name = subneck_coords[bname]["parent"]
        ebone.parent = get_edit_bone(par_name)
        if ebone.parent == None:            
            ebone.parent = get_edit_bone(find_matching_parent(par=par_name, item="bone"))
        id = bname.split('_')[2]
        id = id.split('.')
        if len(id) > 1:
            id = id[0]
        id = int(id)
        if id > last_id:
            last_id = id
            last_subneck = bname

    if len(subneck_coords):
        neck_bone = get_edit_bone("neck.x")
        if neck_bone:
            neck_bone.parent = get_edit_bone(last_subneck)

    # wings parents
    for bname in wings_coords:
        ebone = get_edit_bone(bname)
        ebone.parent = get_edit_bone(wings_coords[bname]["parent"])

    # spline ik parents
    for bname in spline_ik_coords:
        ebone = get_edit_bone(bname)
        parent_name = spline_ik_coords[bname]["parent"]
        parent = get_edit_bone(parent_name)
        if parent == None:
            parent_name = find_matching_parent(par=parent_name, item="bone")
        #print("  spline parent:", parent_name)
        ebone.parent = get_edit_bone(parent_name)
        
    # kilt parents
    for bname in kilt_coords:
        ebone = get_edit_bone(bname)
        parent_name = kilt_coords[bname]["parent"]
        parent = get_edit_bone(parent_name)
        if parent == None:
            parent_name = find_matching_parent(par=parent_name, item='bone')
        ebone.parent = get_edit_bone(parent_name)
        
    # extra arms parents
    for bname in extra_arms_coords:
        ebone = get_edit_bone(bname)
        parent_name = extra_arms_coords[bname]["parent"]
        parent = get_edit_bone(parent_name)
        if parent == None:
            parent_name = find_matching_parent(par=parent_name, item='bone')
        ebone.parent = get_edit_bone(parent_name)
        
    # arms, legs fans parents
    for bname in fans_coords:
        ebone = get_edit_bone(bname)
        parent_name = fans_coords[bname]["parent"]
        parent = get_edit_bone(parent_name)
        if parent == None:
            parent_name = find_matching_parent(par=parent_name, item='bone')
        ebone.parent = get_edit_bone(parent_name)
        

    # Set eyelids parent to eye_offset if full facial
    eyelid_list = ['eyelid_top', 'eyelid_bot']
    if scn.arp_full_facial and is_facial_enabled(arp_armature):
        for el in eyelid_list:
            for side in [".l", ".r"]:
                if get_edit_bone(el + side) != None:
                    get_edit_bone(el + side).parent = get_edit_bone("c_eye_offset" + side)


    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.mode_set(mode='EDIT')

    # Set bones transforms rest pose from dict
    print("  Set rest pose...")

    softlink_helpers = {}

    for b in humanoid_armature.data.edit_bones:

        if not b.name in bones_dict:# only main humanoid bones
            continue

        if "softlink" in bones_dict[b.name]:
            b["softlink"] = bones_dict[b.name]["softlink"]
            if b["softlink"] == 1:
                b.use_connect = False    

        if "const_interp" in bones_dict[b.name]:
            b["const_interp"] = bones_dict[b.name]["const_interp"]

        side = b.name[-2:]
        base_name = get_bone_base_name(b.name)

        # arms and legs
        if base_name == 'arm_stretch':
            b.head = bones_dict['shoulder' + side]["tail"]

            # Backward-compatibility
            # if softlink, need to use actual arm_stretch head position
            if retro_softlink:
                if scn.arp_export_twist and b["softlink"] == 1:
                    b.head = bones_dict[b.name]["head"]

            b.tail= bones_dict[b.name]["tail"]
            b.roll = bones_dict[b.name]["roll"]
            b.use_deform = bones_dict[b.name]["deform"]
            
            # if softlink, add helper bones (if not TWIST_BASED)
            if scn.arp_export_twist and b["softlink"] == 1:
                if not retro_softlink and arp_armature.arp_secondary_type != 'TWIST_BASED':
                    arm_stretch_h_loc_name = "arm_stretch_h_loc"+side
                    arm_stretch_h_loc = humanoid_armature.data.edit_bones.new(arm_stretch_h_loc_name)
                    arm_stretch_h_loc.use_deform = False
                    arm_stretch_h_loc.head = bones_dict[b.name]["head"]
                    arm_stretch_h_loc.tail = arm_stretch_h_loc.head + (b.tail - arm_stretch_h_loc.head)*0.5
                    arm_stretch_h_loc['arp_ge_helper'] = True

                    arm_stretch_h_copy_name = "arm_stretch_h_copy"+side
                    arm_stretch_h_copy = humanoid_armature.data.edit_bones.new(arm_stretch_h_copy_name)
                    arm_stretch_h_copy.use_deform = False
                    arm_stretch_h_copy.head = b.head.copy()
                    arm_stretch_h_copy.tail = b.head + (b.tail - b.head)*0.5
                    arm_stretch_h_copy.parent = arm_stretch_h_loc
                    arm_stretch_h_copy['arp_ge_helper'] = True

                    softlink_helpers[b.name] = {'loc':arm_stretch_h_loc_name, 'copy':arm_stretch_h_copy_name}

        elif base_name == 'forearm_stretch':
            b.head = bones_dict['arm_stretch'+side]["tail"]
            if 'hand'+side in bones_dict:# bone selection export may remove hand
                b.tail= bones_dict['hand'+side]["head"]
            else:
                b.tail= bones_dict[b.name]["tail"]
            b.roll = bones_dict[b.name]["roll"]
            b.use_deform = bones_dict[b.name]["deform"]

        elif base_name == 'thigh_stretch':
            if not 'thigh_ref'+side in bones_dict:
                b.head = [0,0,0]# zero out for auto-deletion, disabled leg
                continue
            b.head = bones_dict['thigh_ref'+side]["head"]

            # Backward-compatibility
            # if softlink, need to use actual thigh_stretch position
            if retro_softlink:
                if scn.arp_export_twist and b["softlink"] == 1:
                    b.head = bones_dict[b.name]["head"]

            
            b.tail= bones_dict['thigh_ref'+side]["tail"]
            b.roll = bones_dict[b.name]["roll"]
            b.use_deform = bones_dict[b.name]["deform"]

            # if softlink, add helper bones (if not TWIST_BASED)
            if scn.arp_export_twist and b["softlink"] == 1:
                if not retro_softlink and arp_armature.arp_secondary_type != 'TWIST_BASED':
                    thigh_stretch_h_loc_name = "thigh_stretch_h_loc"+side
                    thigh_stretch_h_loc = humanoid_armature.data.edit_bones.new(thigh_stretch_h_loc_name)
                    thigh_stretch_h_loc.use_deform = False
                    thigh_stretch_h_loc.head = bones_dict[b.name]["head"]
                    thigh_stretch_h_loc.tail = thigh_stretch_h_loc.head + (b.tail - thigh_stretch_h_loc.head)*0.5
                    thigh_stretch_h_loc['arp_ge_helper'] = True

                    thigh_stretch_h_copy_name = "thigh_stretch_h_copy"+side
                    thigh_stretch_h_copy = humanoid_armature.data.edit_bones.new(thigh_stretch_h_copy_name)
                    thigh_stretch_h_copy.use_deform = False
                    thigh_stretch_h_copy.head = b.head.copy()
                    thigh_stretch_h_copy.tail = b.head + (b.tail - b.head)*0.5
                    thigh_stretch_h_copy.parent = thigh_stretch_h_loc
                    thigh_stretch_h_copy['arp_ge_helper'] = True

                    softlink_helpers[b.name] = {'loc':thigh_stretch_h_loc_name, 'copy':thigh_stretch_h_copy_name}

        elif base_name == 'leg_stretch':
            b.head = bones_dict[b.name]["head"]
            if 'foot'+side in bones_dict:
                b.tail= bones_dict['foot'+side]["head"]
            else:
                b.tail= bones_dict[b.name]["tail"]
            b.roll = bones_dict[b.name]["roll"]
            b.use_deform = bones_dict[b.name]["deform"]
        else:
            b.head = bones_dict[b.name]["head"]
            b.tail= bones_dict[b.name]["tail"]
            b.roll = bones_dict[b.name]["roll"]
            b.use_deform = bones_dict[b.name]["deform"]
            #print('set bone use deform', b.name, b.use_deform)

        #don't deform bend bones if parent doesn't
        if '_bend' in b.name:
            if b.parent:
                b.use_deform = b.parent.use_deform

        #Switch the root direction
        if b.name == "root.x":
            spine_01 = get_edit_bone("spine_01.x")
            spine_01.use_connect = False
            b_head = b.head.copy()
            b.head = b.tail.copy()
            b.tail = b_head
            # make sure to align the root x_axis to avoid issues with constraints since it's upside-down
            align_bone_x_axis(b, bones_dict[b.name]["x_axis"])

    # Make sure eyelids deform when no Full Facial
    if not scn.arp_full_facial:
        for el in eyelid_list:
            for side in [".l", ".r"]:
                if get_edit_bone(el + side) != None:
                    get_edit_bone(el + side).use_deform = True

    # Workaround to fix the wrong bones orientation at export
    if scn.arp_fix_fbx_rot:
        fix_fbx_bones_rot()


    print("\n  Add constraints...")

    ### Add constraints
    bpy.ops.object.mode_set(mode='POSE')

    for pbone in humanoid_armature.pose.bones:
        bone_softlink = "softlink" in pbone.bone.keys()
        if bone_softlink:
            if pbone.bone["softlink"] == 0:
                bone_softlink = False

        if is_custom_bone(pbone.name) or is_bend_bone(pbone.name) or (pbone.name[:-2] in additional_facial_bones) or pbone.name.startswith('c_toes_') or pbone.name.startswith("c_tail_") or pbone.name.startswith("c_ear_") or pbone.name.startswith("c_breast_") or is_bend_bone_spine_only(pbone.name):
            if len(pbone.constraints) != 0:
                continue
            if arp_armature.data.bones.get(pbone.name) == None:
                continue

            #print("Add constraint to", pbone.name, "bone_softlink:", bone_softlink)
            add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)

        if scn.arp_ge_master_traj and pbone.name == 'c_traj':
            add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)
            
        # Fingers metacarps
        if pbone.name in fingers_metacarps_coords:
            add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)

        # Subnecks
        if pbone.name.startswith("c_subneck_"):
            if neck_twist_enabled:
                subneck_twist_name = pbone.name[2:].replace("subneck_", "subneck_twist_")
                add_copy_transf(pbone, tar=arp_armature, subtar=subneck_twist_name, no_scale=bone_softlink)
            else:
                add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)

        # Wings
        if pbone.name.startswith("c_arm_feather_") or pbone.name.startswith("c_forearm_feather_") or pbone.name.startswith("c_hand_feather_"):
            add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)

        # Spline IK
        if pbone.name in spline_ik_coords:
            add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)
            
        # Kilt
        if pbone.name in kilt_coords:
            add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink) 

        # Arms fans
        if pbone.name in fans_coords:
            add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)

    #   Twist bones
    for bname in twist_bones_dict:
        bonename = bname
        if bname.startswith("c_arm_twist_offset"):
            bonename = bname.replace("c_arm_twist_offset", "arm_twist")

        pbone = get_pose_bone(bonename)
        bone_softlink = "softlink" in pbone.bone.keys()

        if len(pbone.constraints) == 0:
            subtgt = ""
            if pbone.name[:-2] == "arm_twist" and arp_armature.arp_secondary_type != "TWIST_BASED":
                subtgt = "c_arm_twist_offset" +  pbone.name[-2:]
            else:
                if arp_armature.arp_secondary_type == "ADDITIVE" or arp_armature.arp_secondary_type == "NONE":
                    subtgt = pbone.name
                elif arp_armature.arp_secondary_type == "TWIST_BASED":
                    subtgt = "c_"+pbone.name

            cns1, cns2 = add_copy_transf(pbone, tar=arp_armature, subtar=subtgt, no_scale=bone_softlink)
            if "arp_twist_fac" in scn.keys():
                cns1.influence = scn.arp_twist_fac
                if cns2:
                    cns2.influence = scn.arp_twist_fac


    #   c_stretch bones
    for bname in c_stretch_dict:
        pbone = get_pose_bone(bname)
        bone_softlink = "softlink" in pbone.bone.keys()

        if len(pbone.constraints) == 0:
            add_copy_transf(pbone, tar=arp_armature, subtar=bname, no_scale=bone_softlink)
            
            
    # Extra arms
    # Arms
    for bone_name in extra_arms_coords:
        pbone = get_pose_bone(bone_name)
        bone_side = get_bone_side(pbone.name)        
        bone_softlink = False
        if "softlink" in pbone.bone.keys():
            bone_softlink = pbone.bone["softlink"]
        
        if "shoulder" in bone_name or "hand" in bone_name:
            add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
        
        if bone_name.startswith('arm_stretch'): 
            if bone_softlink:
                cns1 = pbone.constraints.new("COPY_LOCATION")
                cns1.name = "Copy Location"
                cns1.target = arp_armature
                cns1.subtarget = 'arm'+bone_side if arp_armature.arp_secondary_type == "TWIST_BASED" else bone_name

                cns2 = pbone.constraints.new("COPY_ROTATION")
                cns2.name = "Copy Rotation"
                cns2.target = arp_armature
                cns2.subtarget = bone_name
            else:
                add_copy_transf(pbone, tar=arp_armature, subtar=bone_name)                        
                cns_loc = pbone.constraints.new("COPY_LOCATION")
                cns_loc.name = "Copy Location"
                cns_loc.target = get_object(arp_armature.name)
                cns_loc.subtarget = "c_arm_twist_offset" + bone_side
               
                
        if bone_name.startswith('c_arm_stretch'):
            add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
            
        if "forearm_stretch" in bone_name:
            add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
            
        if "forearm_twist" in bone_name :
            sbtgt = ""
            if arp_armature.arp_secondary_type == "TWIST_BASED" and not bone_name.startswith("c_"):
                sbtgt = "c_"+bone_name
            else:
                sbtgt = bone_name

            cns1, cns2 = add_copy_transf(pbone, tar=arp_armature, subtar=sbtgt, no_scale=bone_softlink)

            if "arp_twist_fac" in bpy.context.scene.keys():
                cns1.influence = scn.arp_twist_fac
                if cns2:
                    cns2.influence = scn.arp_twist_fac

        if "arm_twist" in bone_name and not "forearm" in bone_name:
            sbtgt = ''
            if not "arm_twist_" in bone_name:
                if arp_armature.arp_secondary_type == "TWIST_BASED":
                    sbtgt = bone_name
                else:
                    sbtgt = "c_arm_twist_offset" + bone_side
            else:
                if arp_armature.arp_secondary_type == "TWIST_BASED" and not bone_name.startswith("c_"):
                    sbtgt = "c_"+bone_name
                else:
                    sbtgt = bone_name

            cns1, cns2 = add_copy_transf(pbone, tar=arp_armature, subtar=sbtgt, no_scale=bone_softlink)
                

        # Fingers
        for fing in fingers_names:
            if "c_toes" in bone_name:
                continue
            if not (fing + "1" in bone_name or fing + "2" in bone_name or fing + "3" in bone_name):
                continue
            target_bone = bone_name

            if arp_armature.data.bones.get(bone_name) == None:
                target_bone = "c_" + bone_name

            add_copy_transf(pbone, tar=arp_armature, subtar=target_bone, no_scale=bone_softlink)
    
        
    # Replace other copy_transforms constraints if soft_linking enabled
    for pb in humanoid_armature.pose.bones:
        if not "softlink" in pb.bone.keys():
            continue
        if pb.bone["softlink"] == 0:
            continue

        side = get_bone_side(pb.name)

        if pb.name == thigh_stretch_name+side or pb.name == arm_stretch_name+side:
            # Backward-compatibility
            if retro_softlink:
                # thigh_stretch and arm_stretch were at actual position if softlinked
                for cns in pb.constraints:
                    if cns.type == "COPY_LOCATION":
                        pb.constraints.remove(cns)
                        break

            # add helper bones constraints
            else:
                if arp_armature.arp_secondary_type != 'TWIST_BASED':
                    if pb.name in softlink_helpers:
                        for i, cns in enumerate(pb.constraints):
                            if cns.type == 'COPY_TRANSFORMS' or cns.type == 'COPY_LOCATION':
                                pb.constraints.remove(cns)

                        stretch_h_loc_name = softlink_helpers[pb.name]['loc']
                        stretch_h_copy_name = softlink_helpers[pb.name]['copy']
                        stretch_h_loc = get_pose_bone(stretch_h_loc_name)
                        add_copy_transf(stretch_h_loc, tar=arp_armature, subtar=pb.name, h_t=0.0, no_scale=True)
                        add_copy_transf(pb, tar=humanoid_armature, subtar=stretch_h_copy_name, h_t=0.0, no_scale=True)

                        continue


        for i, cns in enumerate(pb.constraints):
            if cns.type == "COPY_TRANSFORMS":
                add_copy_transf(pb, tar=arp_armature, subtar=cns.subtarget, h_t=cns.head_tail, no_scale=True)
                pb.constraints.move(len(pb.constraints)-1, i)
                pb.constraints.move(len(pb.constraints)-1, i)
                pb.constraints.remove(cns)

    
    # Copy custom props on pose bone data
    all_coords = {**bones_dict, **all_extra_coords}
    
    for pb in humanoid_armature.pose.bones:
        if pb.name in all_coords:
            if 'arp_bone' in all_coords[pb.name]:
                arp_bone_name = all_coords[pb.name]['arp_bone']
                arp_bone = arp_armature.pose.bones.get(arp_bone_name)
                if arp_bone:                  
                    for propname in arp_bone.keys():
                        if propname == 'cc':#skip custom control prop...
                            continue
                        # copy
                        pb[propname] = arp_bone[propname]
    
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.mode_set(mode='OBJECT')

    humanoid_armature.hide_set(hide_state)
    humanoid_armature.hide_viewport = hide_state

    #### Set armature modifiers ####

    # Iterates over armature meshes (humanoid)
    deprecated_groups_list = ["pinky1", "ring1", "middle1", "index1", "thumb1", "jawbone.x"]
    found_deprecated = False

    twist_dict = {'leg_twist':['leg_stretch'], 'thigh_twist':['thigh_stretch'], 'c_arm_twist_offset':['arm_stretch'], 'forearm_twist':['forearm_stretch']}
    fingers_meta_dict_ue4 = {'c_index1_base':['hand'], 'c_middle1_base':['hand'], 'c_ring1_base':['hand'], 'c_pinky1_base':['hand'], 'c_thumb1_base':['c_thumb1']}
    fingers_meta_dict = {'c_thumb1_base':['c_thumb1']}
    clamp_dict = {'c_thigh_bend_contact': 'thigh_twist', 'c_thigh_bend_01': 'thigh_twist', 'c_thigh_bend_02': 'thigh_twist', 'c_knee_bend': 'leg_stretch', 'c_ankle_bend': 'leg_stretch', 'c_leg_bend_01':'leg_stretch', 'c_leg_bend_02': 'leg_stretch','c_elbow_bend': 'arm_stretch', 'c_shoulder_bend': 'arm_stretch', 'c_wrist_bend': 'forearm_twist', 'c_forearm_bend': 'forearm_twist'}
    secondary_eyelids_dict = {'c_eyelid_top_01': ['eyelid_top'], 'c_eyelid_top_02': ['eyelid_top'], 'c_eyelid_top_03': ['eyelid_top'], 'c_eyelid_bot_01': ['eyelid_bot'], 'c_eyelid_bot_02': ['eyelid_bot'], 'c_eyelid_bot_03': ['eyelid_bot'], 'c_eyelid_corner_01': ['head.x'], 'c_eyelid_corner_02': ['head.x']}
    multiply_weight_dict = {"c_waist_bend":0.5, "c_elbow_bend":0.5}
    bend_bones_main = {'c_root_bend': ['root.x'], 'c_spine_01_bend': ['spine_01.x'], 'c_spine_02_bend': ['spine_02.x'], 'c_neck_01': ['spine_02.x']}

    # transfer neck_01 to the last spine bone
    last_spine_idx = '%02d' % arp_armature.rig_spine_count
    last_spine_name = "spine_"+last_spine_idx+".x"
    if arp_armature.data.bones.get(last_spine_name):
        bend_bones_main['c_neck_01'] = last_spine_name

    rig_add = None
    if armature_add_name:
        rig_add = get_object(armature_add_name)

    jawbone_name = "jawbone.x" if humanoid_armature.data.bones.get("jawbone.x") else "c_jawbone.x"

    print("  Assign modifiers and weights...")

    full_facial_export = True if scn.arp_full_facial else False
    facial_enabled = is_facial_enabled(arp_armature)

    # Iterate over meshes (humanoid)
    
    for obj_name in collected_meshes:
        #print("iterating object", obj_name)

        obj = get_object(obj_name)

        if len(obj.modifiers) == 0:
            continue

        for modif in obj.modifiers:
            if modif.type != 'ARMATURE':
                continue
            if modif.object == None:
                continue
            if rig_add != None and modif.object == rig_add:
                obj.modifiers.remove(modif)
                continue 
            if obj_name != 'arp_dummy_mesh_arpexp' and modif.object.name != arp_armature.name:
                continue

            set_active_object(obj.name)
            
            # print
            sys.stdout.write("\r  " + 'mesh: ' + obj.name + '                                                       ')
            sys.stdout.flush()

            # replace with humanoid armature
            modif.object = humanoid_armature
            modif.use_deform_preserve_volume = False

            c_jaw_vg = obj.vertex_groups.get("c_jawbone.x")
            if c_jaw_vg:
                obj.vertex_groups.remove(c_jaw_vg)
                
            jawbone_vg = obj.vertex_groups.get("jawbone.x")
            if jawbone_vg:
                jawbone_vg.name = "c_jawbone.x"


            # Transfer weights (per vert, faster)
            for vert in obj.data.vertices:
                if len(vert.groups) == 0:
                    continue

                for grp in vert.groups:
                    try:
                        grp_name = obj.vertex_groups[grp.group].name
                    except:
                        continue

                    weight = grp.weight

                    # Twist bones
                    if not scn.arp_export_twist:# in case of multiple twist bones used, assumes we need to export twist bones
                        transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=twist_dict)

                    # Advanced - Bend Bones
                    if not scn.arp_keep_bend_bones:# and (arp_armature.arp_secondary_type == "ADDITIVE" or arp_armature.arp_secondary_type == "TWIST_BASED"):
                        transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=bend_bones_main)
                    else:
                        # Clamp weights (make sure additive legs/arms bones influence is contained inside limbs for better deformations)
                        if arp_armature.arp_secondary_type == "ADDITIVE":
                            clamp_weights(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=clamp_dict)

                    # Full Facial
                    if not full_facial_export:
                        #transfer skulls
                        transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, list=["c_skull_01", "c_skull_02", "c_skull_03"], target_group_name = "head.x")

                        if facial_enabled:
                            # facial head
                            transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, list=facial_transfer_head, target_group_name='head.x')

                            # facial jaw
                            transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, list=facial_transfer_jaw, target_group_name = jawbone_name)

                            # secondary eyelids to main eyelids
                            transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=secondary_eyelids_dict)

                    # Lower some weights for better results
                    multiply_weight(object=obj, vertice=vert, vertex_weight=grp.weight, group_name=grp_name, dict=multiply_weight_dict)

                    # Others                    
                    if (scn.arp_ue4 and scn.arp_engine_type == 'UNREAL') \
                        or scn.arp_engine_type in ['UNITY', 'GODOT'] \
                        or (scn.arp_engine_type == 'OTHERS' and scn.arp_ge_export_metacarp == False):# transfer metacarp weights to hand
                        transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=fingers_meta_dict_ue4)
                    else:# transfer only thumb metacarp weight to hand
                        transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=fingers_meta_dict)


        # Rename the vgroups if necessary
        for vgroup in obj.vertex_groups:
            # fingers
            for name in deprecated_groups_list:
                if name in vgroup.name and not "base" in vgroup.name and not '_def' in vgroup.name and not vgroup.name.startswith("c_"):
                    new_group_name = "c_" + vgroup.name
                    if obj.vertex_groups.get(new_group_name):
                        #print("warning!", new_group_name, "already exists")
                        continue

                    vgroup.name = new_group_name
                    found_deprecated = True
            # root
            if vgroup.name == "root.x" and humanoid_armature.data.bones.get("c_root_bend.x"):
                if obj.vertex_groups.get("c_root_bend.x"):# check the c_root_bend does not exist yet
                    obj.vertex_groups["c_root_bend.x"].name = "c_root_bend_old.x"
                vgroup.name = "c_root_bend.x"

            # arm twist vgroup
            if "c_arm_twist_offset" in vgroup.name:
                new_vgname = vgroup.name.replace("c_arm_twist_offset", "arm_twist")
                overwrite_vgroup(obj, vgroup, new_vgname)

            # twist_based mode
            if arp_armature.arp_secondary_type == "TWIST_BASED":
                if vgroup.name.startswith("c_thigh_twist") or vgroup.name.startswith("c_leg_twist") or vgroup.name.startswith("c_arm_twist") or vgroup.name.startswith("c_forearm_twist"):
                    new_vgname = vgroup.name[2:]
                    overwrite_vgroup(obj, vgroup, new_vgname)

            # subneck twists
            if vgroup.name.startswith("subneck_twist_"):
                new_vgname = "c_"+vgroup.name.replace("_twist", "")
                overwrite_vgroup(obj, vgroup, new_vgname)


    # Assign parent bones of objects that are directly parented to bones (humanoid)
    set_active_object(humanoid_armature.name)

    bpy.ops.object.mode_set(mode='POSE')
    
    print('')
    
    for mesh in collected_meshes:
        obj = get_object(mesh)
        if len(obj.keys()):
            if "arp_parent_bone" in obj.keys():
                b_parent = obj["arp_parent_bone"]

                # Look for the parent bone in the humanoid armature
                parent_found = False

                if humanoid_armature.data.bones.get(b_parent):
                    parent_found = True
                    print('  Object: "'+ obj.name + '" found direct parent bone "' + b_parent + '" in the humanoid armature.')

                # If not found, tries to match with other bones
                if not parent_found:
                    print('  Object: "' + obj.name + '" did not find direct parent bone "' + b_parent + '" in the humanoid armature. Look for other bones...')
                    b_parent = find_matching_parent(par = b_parent, item = "object")

                obj_matrix = obj.matrix_world.copy()
                obj.parent = humanoid_armature
                obj.parent_bone = b_parent
                obj.matrix_world = obj_matrix


    #Change deprecated constraints
    #print("  Change deprecated constraints...")
    set_active_object(humanoid_armature.name)

    bpy.ops.object.mode_set(mode='POSE')

    if found_deprecated:
        for i in deprecated_groups_list:
            for side in sides:
                _side = side
                if i[-2:] == ".x":
                    _side = ""

                pbone = get_pose_bone("c_" + i + _side)
                if pbone:
                    pbone.constraints[0].subtarget = i + _side


    # Workaround to keep a proper bones hierarchy when Softlink is enabled
    # Since Softlink needs the actual stretch and twist bones position for thighs and arms,
    # re-order the twist and stretch bones hierarchy
    """
    if (not retro_softlink and arp_armature.arp_secondary_type != 'TWIST_BASED'):

        bpy.ops.object.mode_set(mode='EDIT')

        for bone_type in ['thigh', 'arm']:
            stretch_name = ''
            twist_name = ''
            twist_var_name = ''

            if bone_type == 'thigh':
                stretch_name = thigh_stretch_name
                twist_name = thigh_twist_name
                twist_var_name = twist_name
            elif bone_type == 'arm':
                stretch_name = arm_stretch_name
                twist_name = arm_twist_name
                twist_var_name = 'c_arm_twist_offset'

            bone_names = [stretch_name, twist_name]

            for side in sides:
                # check both thigh_stretch and thigh_twist are set as softlink (required)
                found = False
                b_stretch = get_edit_bone(stretch_name+side)
                b_twist = get_edit_bone(twist_name+side)

                if b_stretch and b_twist:
                    if is_softlink_bone(b_stretch.name) and is_softlink_bone(twist_var_name+side):
                        found = True

                if not found:
                    continue

                print("  Correcting softlink bones hierarchy:", bone_type+side)
                #print("Operate on:", stretch_name+side, twist_name+side)

                # change thigh_stretch and thigh_twist parent to thigh_twist
                b_twist.parent = b_stretch.parent
                b_stretch.parent = b_twist

                #   multiple twist bones
                for bname in twist_bones_dict:
                    type = twist_bones_dict[bname]['type']
                    bside = get_bone_side(bname)

                    if type == bone_type+'_multi' and bside == side:
                        b = get_edit_bone(bname)
                        b.parent = b_twist

                # rename
                b_twist.name = stretch_name+'_temp'+side
                b_stretch.name = twist_name+side
                b_twist.name = stretch_name+side

                # change children parent
                for child in b_stretch.children:
                    child.parent = b_twist

    """

    bpy.ops.object.mode_set(mode='OBJECT')


    # Push the bend bones?
    if scn.arp_keep_bend_bones and scn.arp_push_bend and (arp_armature.arp_secondary_type == "ADDITIVE"):
        print("  Push bend bones...")

        for _action in bpy.data.actions:
            if not check_id_root(_action):
                continue

            _push_bend_bones(_action, 2)
            self.actions_pushed_changed.append(_action.name)

    humanoid_armature.data.pose_position = 'POSE'
    humanoid_armature['set'] = True
    humanoid_armature['binded'] = True

    # tag the rig as set for humanoid
    arp_armature['arp_export_rig_set'] = humanoid_armature.name
            
    print("  Humanoid set.")
    #Done _set_humanoid_rig()


def fix_fbx_bones_rot(include_keywords = None, exclude_keywords = None):
    # optional include/exclude lists are used to only operate on given bones

    print("\n  Fix FBX rotation...")
    angle_tolerance = 1
    min_angle = 0.0
    max_angle = 0.0

    def set_angle_tolerance(atype):
        if atype == "normal":
            min_angle = 180-angle_tolerance
            max_angle = 180+angle_tolerance
        elif atype == "short":
            min_angle = 179.5
            max_angle = 180.5

        return min_angle, max_angle

    # Check if the bone-bone parent angle = 179-180° to fix the Fbx rotation issue!
    # Find bones with tedious angles
    bones_to_fix = []
    for b in bpy.context.active_object.data.edit_bones:
        operate_on_this_bone = True
        min_angle, max_angle = set_angle_tolerance("normal")
        if 'thigh' in b.name:
            min_angle, max_angle = set_angle_tolerance("short")

        if include_keywords != None:
            operate_on_this_bone = False
            for str in include_keywords:
                if str in b.name:
                    operate_on_this_bone = True
                    break

        if exclude_keywords != None:
            for str in exclude_keywords:
                if str in b.name:
                    operate_on_this_bone = False
                    break

        if operate_on_this_bone and b.parent != None:
            vec1 = b.y_axis
            vec1[1] = 0
            vec2 = b.parent.y_axis
            vec2[1] = 0
            if vec1.magnitude != 0 and vec2.magnitude != 0:
                angle = math.degrees(vec1.angle(vec2))
                if angle > min_angle and angle < max_angle:
                    if bpy.context.scene.arp_debug_mode:
                        print("180 angle:", b.name, angle)
                    bones_to_fix.append(b)

    # Add some slight offset to fix this - clumsy :( but works
    print("\n  Adding noise...")

    def compare_vectors(vec1, vec2):
        true_count = 0
        for i in range(0, len(vec1)):
            if vec1[i] != 0 and vec2[i] != 0:
                if vec1[i]/vec2[i] < 1.001 and vec1[i]/vec2[i] > 0.999:
                    true_count += 1

        if true_count == len(vec1):
            return True

    # store the x axis to preserve the bone roll after position changes
    saved_x_axes = {}
    for b in bpy.context.active_object.data.edit_bones:
        saved_x_axes[b] = b.x_axis.copy()

    for b in bones_to_fix:
        angle_check = False
        count = 0
        base_length = b.length
        base_pos = b.tail.copy()
        chd_name = ""
        chd_base_pose = None

        min_angle, max_angle = set_angle_tolerance("normal")
        if 'thigh' in b.name:
            min_angle, max_angle = set_angle_tolerance("short")

        while not angle_check:
            count += 1
            b_magnitude = (b.tail - b.head).magnitude

            # check if the bone has connected bones children, move the head too
            if len(b.children) > 0:
                for chd in b.children:
                    if compare_vectors(chd.head, b.tail):
                        # save the base pos
                        if not chd_base_pose:
                            chd_base_pose = chd.head.copy()
                            chd_name = chd.name
                        chd.head += Vector((b_magnitude*0.002, b_magnitude*0.002, 0.0))


            b.tail += Vector((b_magnitude*0.002, b_magnitude*0.002, 0.0))

            vec1 = b.y_axis
            vec1[1] = 0
            vec2 = b.parent.y_axis
            vec2[1] = 0
            if vec1.magnitude != 0 and vec2.magnitude != 0:
                angle = math.degrees(vec1.angle(vec2))

                if count > 1000:
                    print(b.name, "Iteration exceeded maximum allowed, exit")
                    angle_check = True

                if b.length / base_length > 1.001:
                    print('  '+b.name, ":bone length too high, reset transforms and exit")
                    b.tail = base_pos
                    if chd_base_pose:
                        get_edit_bone(chd_name).head = chd_base_pose
                    angle_check = True

                if angle < min_angle:
                    angle_check = True

    # make sure to preserve the bone roll
    for b in saved_x_axes:
        align_bone_x_axis(b, saved_x_axes[b])


def spline_ik_export_to_dict(spline_name, side, dict, sel_bone_names=None):
    # collect spline IK deforming bones
    
    first_ref_bone = get_edit_bone(spline_name+'_01_ref'+side)
    
    # get props
    amount = first_ref_bone['spline_count']
    stype = '1'
    if 'spline_type' in first_ref_bone.keys():
        stype = first_ref_bone['spline_type']
    spline_fk = False
    if 'spline_fk' in first_ref_bone.keys():
        spline_fk = first_ref_bone['spline_fk']
    spline_twist = False
    if 'spline_twist' in first_ref_bone.keys():
        spline_twist = first_ref_bone['spline_twist']
    
    
    for i in range(1, amount+1):
        prev_id = '%02d' % (i-1)
        id = '%02d' % i
        # get deforming bone
        def_name = ''
        if spline_twist:
            def_name = spline_name+'_twist_'+id+side            
        elif spline_fk:
            def_name = spline_name+'_def_'+id+side
        else:
            if stype == '1':
                def_name = spline_name+'_'+id+side
            elif stype == '2':
                def_name = 'c_'+spline_name+'_'+id+side
        
        def_eb = get_edit_bone(def_name)
        if def_eb.use_deform == False:
            continue

        # get parent
        if spline_twist:
            b_parent = spline_name+'_twist_'+prev_id+side    
            if i == 1:
                if def_eb.parent.parent == None:# def_eb<c_spline_root<parent
                    b_parent = 'c_traj'
                    print("  Spline IK root parent not set, assigned to null")
                else:
                    b_parent = def_eb.parent.parent.parent.name
        elif spline_fk:
            b_parent = def_eb.parent.name
            if i == 1:
                if def_eb.parent.parent == None:# def_eb<c_spline_root<parent
                    b_parent = 'c_traj'
                    print("  Spline IK root parent not set, assigned to null")
                else:
                    b_parent = def_eb.parent.parent.name
        else:
            if stype == '1':
                b_parent = def_eb.parent.name
                if i == 1:
                    if def_eb.parent.parent == None:# def_eb<c_spline_root<parent
                        b_parent = 'c_traj'
                        print("  Spline IK root parent not set, assigned to null")
                    else:
                        b_parent = def_eb.parent.parent.name
            
            elif stype == '2':           
                b_parent = 'c_'+spline_name+'_'+prev_id+side         
                if i == 1:
                    if def_eb.parent.parent.parent == None:# def_eb<spline<c_spline_root<parent
                        b_parent = "c_traj"
                        print("  Spline IK root parent not set, assigned to null")
                    else:
                        b_parent = def_eb.parent.parent.parent.name

        # register
        if sel_bone_names:
            if bpy.context.scene.arp_ge_sel_bones_only:
                if not def_eb.name in sel_bone_names:
                    continue
                    
        dict[def_name] = {"head":def_eb.head.copy(), "tail":def_eb.tail.copy(), "roll":def_eb.roll, "parent":b_parent, 
                            "type":"ik_spline", "arp_bone":def_eb.name, "softlink":is_softlink_bone(def_name), "const_interp":is_const_interp_bone(def_eb.name)}
                            
                            
                            
def wings_export_to_dict(side, bones_coords, sel_bone_names=None):
    __rig = bpy.context.active_object
    arm_feathers = [i.name for i in __rig.data.edit_bones if i.name.startswith("c_arm_feather_") and i.name[-len(side):] == side and len(i.name[:-len(side)][14:])==8]
    forearm_feathers = [i.name for i in __rig.data.edit_bones if i.name.startswith("c_forearm_feather_") and i.name[-len(side):] == side and len(i.name[:-len(side)][18:])==8]
    hand_feathers = [i.name for i in __rig.data.edit_bones if i.name.startswith("c_hand_feather_") and i.name[-len(side):] == side and len(i.name[:-len(side)][15:])==8]

    for bname in arm_feathers+forearm_feathers+hand_feathers:
        ebone = get_edit_bone(bname)
        b_parent = ebone.parent.name

        if not ebone.parent.name.startswith("c_"):
            top_parent = ebone.parent.parent
            if "_master" in top_parent.name:
                top_parent = ebone.parent.parent.parent

            b_parent = top_parent.name

        if sel_bone_names:
            if bpy.context.scene.arp_ge_sel_bones_only:
                if not ebone.name in sel_bone_names:
                    continue

        bones_coords[bname] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), 
                                "roll":ebone.roll, "parent":b_parent, "arp_bone":ebone.name, "type": "wings",
                                "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}


def kilt_export_to_dict(side, bones_coords, sel_bone_names=None):
    for b in bpy.context.active_object.data.edit_bones:
        if 'arp_kilt' in b.keys():
            bside = get_bone_side(b.name)
            if bside[:-2] == side[:-2]:
                if b.name.startswith('c_') and not b.name in bones_coords and not '_row_' in b.name and not '_main_' in b.name:
                    kilt_name = b['kilt_name']
                    bpar_name = ''
                    if b.parent:
                        bpar_name = b.parent.name
                        if not b.name.startswith('c_'+kilt_name+'_master'):
                            str_idx = b.name.split('_')[3][:2]
                            idx = int(str_idx)
                            if idx == 1:
                                bpar_name = 'c_'+kilt_name+'_'+'master'+side
                           
                    if sel_bone_names:
                        if bpy.context.scene.arp_ge_sel_bones_only:
                            if not b.name in sel_bone_names:
                                continue
                
                    bones_coords[b.name] = {"head":b.head.copy(), "tail":b.tail.copy(), "roll":b.roll, 
                                            "parent":bpar_name, "arp_bone":b.name, "softlink":is_softlink_bone(b.name), 
                                            'type':'kilt', "const_interp":is_const_interp_bone(b.name)}
                                

def legs_toes_ikfk_export_to_dict(side, dict, sel_bone_names=None):
    armature = bpy.context.active_object
    scn = bpy.context.scene
    
    for toes_def_name in ard.get_leg_toes_ikfk(side, btype='DEFORM'):
        c_eb = get_edit_bone(toes_def_name)        
        bpar_name = c_eb.parent.name
        
        if sel_bone_names:
            if bpy.context.scene.arp_ge_sel_bones_only:
                if not toes_def_name in sel_bone_names:
                    continue
                    
        dict[toes_def_name] = {"head":c_eb.head.copy(), "tail":c_eb.tail.copy(), "roll":c_eb.roll, 
                        "parent":bpar_name, "arp_bone":toes_def_name, "softlink":is_softlink_bone(c_eb.name), 
                        'type':'toe_def', "const_interp":is_const_interp_bone(c_eb.name)}
                        
                                
def legs_fans_export_to_dict(side, dict, sel_bone_names=None):
    armature = bpy.context.active_object
    scn = bpy.context.scene
    
    for c_name in ard.get_leg_joint_fans(side, btype='CONTROLLER'):
        c_eb = get_edit_bone(c_name)
        bpar_name = c_eb.parent.parent.name
        
        if sel_bone_names:
            if bpy.context.scene.arp_ge_sel_bones_only:
                if not c_name in sel_bone_names:
                    continue
                                
        dict[c_name] = {"head":c_eb.head.copy(), "tail":c_eb.tail.copy(), "roll":c_eb.roll, 
                        "parent":bpar_name, "arp_bone":c_name, "softlink":is_softlink_bone(c_eb.name), 
                        'type':'joint_fan', "const_interp":is_const_interp_bone(c_eb.name)}
                                
                                
def arms_fans_export_to_dict(side, dict, sel_bone_names=None):
    armature = bpy.context.active_object
    scn = bpy.context.scene
    
    for c_name in ard.get_arm_joint_fans(side, btype='CONTROLLER'):
        c_eb = get_edit_bone(c_name)
        bpar_name = c_eb.parent.parent.name
        
        if sel_bone_names:
            if bpy.context.scene.arp_ge_sel_bones_only:
                if not c_name in sel_bone_names:
                    continue
                    
        dict[c_name] = {"head":c_eb.head.copy(), "tail":c_eb.tail.copy(), "roll":c_eb.roll, 
                        "parent":bpar_name, "arp_bone":c_name, "softlink":is_softlink_bone(c_eb.name), 
                        'type':'joint_fan', "const_interp":is_const_interp_bone(c_eb.name)}
                                
                                
def arms_export_to_dict(side, bones_coords):
    armature = bpy.context.active_object
    scn = bpy.context.scene
    
    for bone_name in ard.arm_deform:
        if armature.arp_secondary_type == "TWIST_BASED":
            if ("twist" in bone_name or "stretch" in bone_name):
                if not bone_name.startswith("c_"):# c_twist_offset case
                    bone_name = "c_"+bone_name
                else:
                    bone_name = "c_arm_twist"
    
        if is_deforming(bone_name + side):
            ebone = get_edit_bone(bone_name + side)

            if bone_name == "shoulder":
                b_parent = get_edit_bone("c_shoulder" + side).parent.name           
                
                bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":b_parent, "arp_bone":ebone.name, 
                    "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

            if "arm_stretch" in bone_name and not "forearm_stretch" in bone_name:
                arm_softlink = is_softlink_bone(ebone.name)
                if arm_softlink and not armature.arp_secondary_type == "TWIST_BASED":
                    arm_head_pos = ebone.head.copy()
                else:
                    arm_head_pos = get_edit_bone("c_arm_twist_offset" + side).head.copy()
                
                bones_coords["arm_stretch"+side] = {"head":arm_head_pos, "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":"shoulder"+side, "arp_bone":ebone.name, 
                    "softlink":arm_softlink, 'const_interp':is_const_interp_bone(ebone.name)}

                if armature.arp_secondary_type == "TWIST_BASED":
                    bones_coords["c_arm_stretch"+side] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":"arm_stretch"+side, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

            if "forearm_stretch" in bone_name:
                bones_coords["forearm_stretch"+side] = {"head":ebone.head.copy(), "tail":get_edit_bone("forearm_twist" + side).tail.copy(), "roll":ebone.roll, "parent":"arm_stretch"+side, "arp_bone":ebone.name, 
                    "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                if armature.arp_secondary_type == "TWIST_BASED":
                    bones_coords["c_forearm_stretch"+side] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":"forearm_stretch"+side, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

            if bone_name == "hand":
                bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":"forearm_stretch"+side, "arp_bone":ebone.name, 
                    "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

            if scn.arp_export_twist or armature.arp_secondary_type == "TWIST_BASED":
                # multiple twist support
                arm_ref = get_edit_bone("arm_ref"+side)
                twist_bones_amount = 1
                if len(arm_ref.keys()):
                    if "twist_bones_amount" in arm_ref.keys():
                        twist_bones_amount = arm_ref["twist_bones_amount"]

                if "c_arm_twist" in bone_name:
                    # first arm twist bone (default)
                    b_parent = "arm_stretch" + side 
                    arm_twist_name = 'arm_twist'+side
                    if armature.arp_secondary_type == 'TWIST_BASED':
                        arm_twist_name = 'c_'+arm_twist_name
                        
                    bones_coords[arm_twist_name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":b_parent, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}
                        
                    # multiple arm twist bones
                    if twist_bones_amount > 1:
                        for t_idx in range(2, twist_bones_amount+1):
                            arm_twist_idx_name = 'arm_twist_'+str(t_idx)+side
                            if armature.arp_secondary_type == "TWIST_BASED":
                                arm_twist_idx_name = 'c_'+arm_twist_idx_name
                            arm_twist_idx = get_edit_bone(arm_twist_idx_name)
                            b_parent = 'arm_stretch'+side
                            
                            bones_coords[arm_twist_idx.name] = {"head":arm_twist_idx.head.copy(), "tail":arm_twist_idx.tail.copy(), "roll":arm_twist_idx.roll, "parent":b_parent, "arp_bone":arm_twist_idx.name, 
                                "softlink":is_softlink_bone(arm_twist_idx.name), 'const_interp':is_const_interp_bone(arm_twist_idx.name)}

                if "forearm_twist" in bone_name:
                    forearm_twist_name = 'forearm_twist'+side
                    if armature.arp_secondary_type == "TWIST_BASED":
                        forearm_twist_name = 'c_'+forearm_twist_name
                        
                    # first forearm twist bone (default)
                    b_parent = "forearm_stretch" + side
                    bones_coords[forearm_twist_name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":b_parent, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}
                        
                    # multiple forearm twist bones
                    if twist_bones_amount > 1:
                        for t_idx in range(2, twist_bones_amount+1):
                            forearm_twist_idx_name = 'forearm_twist_'+str(t_idx)+side
                            if armature.arp_secondary_type == "TWIST_BASED":
                                forearm_twist_idx_name = 'c_'+forearm_twist_idx_name
                            forearm_twist_idx = get_edit_bone(forearm_twist_idx_name)
                            b_parent = 'forearm_stretch'+side
                            
                            bones_coords[forearm_twist_idx.name] = {"head":forearm_twist_idx.head.copy(), "tail":forearm_twist_idx.tail.copy(), "roll":forearm_twist_idx.roll, 
                            "parent":b_parent, "arp_bone":forearm_twist_idx.name, 
                            "softlink":is_softlink_bone(forearm_twist_idx.name), 'const_interp':is_const_interp_bone(forearm_twist_idx.name)}


    # Fingers
    for b_finger in fingers_deform:
        finger_name = b_finger+side
        if is_deforming(finger_name):
            ebone = get_edit_bone(finger_name)

            if finger_name.startswith("c_"):
                finger_name = finger_name[2:]

            b_parent = ""

            if "thumb1" in finger_name or "index1_base" in finger_name or "middle1_base" in finger_name or "ring1_base" in finger_name or "pinky1_base" in finger_name:
                b_parent = "hand" + side
            else:
                if "thumb2" in finger_name:
                    b_parent = "thumb1" + side
                if "thumb3" in finger_name:
                    b_parent = "thumb2" + side
                if "index1" in finger_name:
                    b_parent = "index1_base" + side
                if "index2" in finger_name:
                    b_parent = "index1" + side
                if "index3" in finger_name:
                    b_parent = "index2" + side
                if "middle1" in finger_name:
                    b_parent = "middle1_base" + side
                if "middle2" in finger_name:
                    b_parent = "middle1" + side
                if "middle3" in finger_name:
                    b_parent = "middle2" + side
                if "ring1" in finger_name:
                    b_parent = "ring1_base" + side
                if "ring2" in finger_name:
                    b_parent = "ring1" + side
                if "ring3" in finger_name:
                    b_parent = "ring2" + side
                if "pinky1" in finger_name:
                    b_parent = "pinky1_base" + side
                if "pinky2" in finger_name:
                    b_parent = "pinky1" + side
                if "pinky3" in finger_name:
                    b_parent = "pinky2" + side

            bones_coords[finger_name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":b_parent, "arp_bone":ebone.name, 
                "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}
                                            
                                            
        
def _set_mped_rig(armature_name, armature_add_name, manual_set_debug, self):
    print("\n..............................Building Mped rig..............................")

    scn = bpy.context.scene
    sides = [".l", ".r"]

    # Select the arp armature
    arp_armature = None
    if manual_set_debug:
        arp_armature = get_object(armature_name)
    else:
        arp_armature = get_object(armature_name + '_arpexp')

    set_active_object(arp_armature.name)

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(arp_armature.name)
    bpy.ops.object.mode_set(mode='EDIT')

    # get the current limbs
    limb_sides.get_multi_limbs()

    def is_bone_in_dict(bone):
        for b in bones_coords.keys():
            if b == bone:
                return True


    def find_matching_parent(bone_parent_name=None, item=None):

        def fallback_parent(bone_parent_name):
            print('  Error with ' + item.name + ', could not find the associated parent bone in the M-Ped armature: ' + bone_parent_name + '\nAssign to "root.x" bone instead.')
            bone_parent_name = "root.x"

        found = False
        bone_par = arp_armature.data.bones.get(bone_parent_name)
        bone_par_keys = []
        if bone_par:
            bone_par_keys = bone_par.keys()
                
        if bone_parent_name.startswith("c_"):
             # spines
            for id in range(1, 33):
                str_id = '%02d' % id
                if bone_parent_name == 'c_spine_'+str_id+'.x':
                    bone_parent_name = 'spine_'+str_id+'.x'
                    found = True
                if bone_parent_name == "c_spine_"+str_id+"_bend.x":
                    bone_parent_name = 'spine_'+str_id+'.x'
                    found = True

            if is_bone_in_dict(bone_parent_name[2:]):
                print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_parent_name[2:] + '"')
                bone_parent_name = bone_parent_name[2:]
                found = True

            elif bone_parent_name.startswith("c_arm_twist_offset"):
                bone_parent_name = bone_parent_name.replace("c_arm_twist_offset", "arm_twist")
                found = True

            elif "leg_fk" in bone_parent_name:
                bone_match = bone_parent_name[2:].replace("leg_fk", "leg_stretch")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif "thigh_fk" in bone_parent_name:
                bone_match = bone_parent_name[2:].replace("thigh_fk", "thigh_stretch")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif bone_parent_name.startswith("c_arm_fk"):
                bone_match = bone_parent_name[2:].replace("arm_fk", "arm_stretch")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif bone_parent_name.startswith("c_forearm_fk"):
                bone_match = bone_parent_name[2:].replace("forearm_fk", "forearm_stretch")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif bone_parent_name.startswith("c_hand_fk"):
                bone_match = bone_parent_name.replace("c_hand_fk", "hand")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif bone_parent_name.startswith("c_hand_ik"):
                bone_match = bone_parent_name.replace("c_hand_ik", "hand")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif bone_parent_name.startswith("c_foot_fk"):
                bone_match = bone_parent_name.replace("c_foot_fk", "foot")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif bone_parent_name.startswith("c_foot_ik"):
                bone_match = bone_parent_name.replace("c_foot_ik", "foot")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            elif bone_parent_name.startswith("c_root_master"):
                bone_match = bone_parent_name[2:].replace("root_master", "root")

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True

            
            elif bone_parent_name.startswith("c_spline_") or ("arp_spline" in bone_par_keys):
                print("  "+item.name+" has a Spline IK parent")
                bone_match = bone_parent_name[2:]

                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True
                else:# may be the tip controller, decrement
                    print("  could not find c_spline bone parent: "+bone_match+", try to decrement...")
                    idx_string = bone_parent_name.split('_')[2].split('.')[0]
                    if idx_string.isdigit():
                        i = int(idx_string)
                        i = i-1
                        decrement_idx = '%02d' % i
                        bone_match = bone_parent_name[2:].replace(idx_string, decrement_idx)

                        if is_bone_in_dict(bone_match):
                            print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                            bone_parent_name = bone_match
                            found = True
                        else:
                            print("  "+bone_match+" not in dict")

        else:# if not bone_parent_name.startswith("c_")
            
            if bone_parent_name.startswith("c_spline_") or ("arp_spline" in bone_par_keys):
                print("  "+item.name+" has a Spline IK parent")
                bone_match = ''
                
                spline_name = 'spline'
                if 'arp_spline' in bone_par_keys:
                    spline_name = bone_par['arp_spline']
                    
                # get first ref bone for props
                first_ref_db = arp_armature.data.bones.get(spline_name+'_01_ref'+get_bone_side(bone_par.name))
                spline_twist = False
                if 'spline_twist' in first_ref_db.keys():
                    spline_twist = first_ref_db['spline_twist']
                spline_fk = False
                if 'spline_fk' in first_ref_db.keys():
                    spline_fk = first_ref_db['spline_fk']
                
                if spline_twist:
                    bone_match = bone_par.name.replace(spline_name, spline_name+'_twist')
                elif spline_fk:
                    bone_match = bone_par.name.replace(spline_name, spline_name+'_def')                
                
                if is_bone_in_dict(bone_match):
                    print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                    bone_parent_name = bone_match
                    found = True
                
            # Case where the user parented the custom bones to the twist bones, without exporting the twist bone!
            if not scn.arp_export_twist:
                if "leg_twist" in bone_parent_name:
                    bone_match = bone_parent_name.replace("leg_twist", "leg_stretch")

                    if is_bone_in_dict(bone_match):
                        print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                        bone_parent_name = bone_match
                        found = True
                elif "thigh_twist" in bone_parent_name:
                    bone_match = bone_parent_name.replace("thigh_twist", "thigh_stretch")
                    #print(bone_match)
                    if is_bone_in_dict(bone_match):
                        print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                        bone_parent_name = bone_match
                        found = True
                elif "arm_twist" in bone_parent_name and not "forearm" in bone_parent_name:
                    bone_match = bone_parent_name.replace("arm_twist", "arm_stretch")

                    if is_bone_in_dict(bone_match):
                        print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                        bone_parent_name = bone_match
                        found = True
                elif "forearm_twist" in bone_parent_name:
                    bone_match = bone_parent_name.replace("forearm_twist", "forearm_stretch")

                    if is_bone_in_dict(bone_match):
                        print('    >Found matching parent: "' + bone_parent_name + '" > "' + bone_match + '"')
                        bone_parent_name = bone_match
                        found = True

        if not found:
            # try with a 'c_' prefix
            c_par = get_edit_bone('c_'+bone_parent_name)
            if c_par:
                bone_parent_name = 'c_'+bone_parent_name
                found = True
                
        
        if not found:
            fallback_parent(bone_parent_name)

        return bone_parent_name


    #### Collect deforming bones datas ####
    print("  Collect deforming bones...")
    bones_coords = {}
    facial_duplis = []


    if self.is_arp_armature:
        # Spine
        spine_count = arp_armature.rig_spine_count

        if is_deforming("root.x"):
            ebone = get_edit_bone("root.x")
            parent_name = "None"
            # in case the rig has custom master bones, use it as root parent
            c_root_master = get_edit_bone("c_root_master.x")
            if c_root_master.parent:
                if is_custom_bone(c_root_master.parent.name):
                    parent_name = c_root_master.parent.name
                    
                if scn.arp_ge_master_traj:# if c_traj export is forced
                    if c_root_master.parent.name == 'c_traj':
                        parent_name = 'c_traj'
                
            bones_coords["root.x"] = {"head":ebone.tail.copy(), "tail":ebone.head.copy(), "roll":ebone.roll, "parent":parent_name, 
                                    "x_axis":ebone.x_axis.copy(), "arp_bone":ebone.name, 
                                    "softlink":is_softlink_bone("root.x"), 'const_interp':is_const_interp_bone('root.x')}

        for idx in range(1, spine_count+1):
            prev_str_idx = '%02d' % (idx-1)
            str_idx = '%02d' % idx
            spine_name = "spine_"+str_idx+".x"
            if is_deforming(spine_name):
                ebone = get_edit_bone(spine_name)
                b_parent = "spine_"+prev_str_idx+".x"
                if idx == 1:
                    b_parent = "root.x"
                bones_coords[spine_name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":b_parent, "arp_bone":ebone.name, 
                    "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                # update spine bend bones list
                spine_bend_name = "c_spine_"+str_idx+"_bend.x"
                if not spine_bend_name in bend_bones_spine_only:
                    bend_bones_spine_only.append(spine_bend_name)
                if not spine_bend_name in bend_bones:
                    bend_bones.append(spine_bend_name)

        # Neck - Head
        neck_twist_enabled = False

        for dupli in limb_sides.head_sides:
            # neck
            neck_name = 'neck'+dupli
            neck = get_edit_bone(neck_name)
            if neck:# and is_deforming(neck_name):              
                b_parent_name=""
                neck_ref = get_edit_bone("neck_ref"+dupli)
                # get neck parent bone
                if neck_ref.parent:                
                    ref_parent_name = neck_ref.parent.name
                    if "_ref" in ref_parent_name:
                        # look for the final neck bone parent
                        neck_parent_rig_name = ref_parent_name.replace("_ref", "")
                        
                        neck_parent_rig = get_edit_bone(neck_parent_rig_name)
                        if neck_parent_rig:
                            b_parent_name = neck_parent_rig_name
                        elif get_edit_bone("c_"+neck_parent_rig_name):
                            b_parent_name = "c_"+neck_parent_rig_name

                        print("  Assign neck parent:", b_parent_name)
                    else:
                        b_parent_name = ref_parent_name
                        #print("  Neck parent = ", b_parent_name)
                else:
                    print("  Could not find neck_ref" + dupli + " parent. Assign to None.")
                    b_parent_name = ""

                bones_coords[neck.name] = {"head":neck.head.copy(), "tail":neck.tail.copy(), "roll":neck.roll, 
                    "parent":b_parent_name, "arp_bone":neck.name, "deform":is_deforming(neck_name),
                    "softlink":is_softlink_bone(neck.name), 'const_interp':is_const_interp_bone(neck.name)}

                # subnecks
                neck_count = 1
                if "neck_twist" in neck_ref.keys():
                    neck_twist_enabled = neck_ref["neck_twist"]
                if "neck_count" in neck_ref.keys():
                    neck_count = neck_ref["neck_count"]
                if neck_count > 1:
                    for idx in range(1, neck_count):
                        subneck_deform_name = ""
                        subneck_cont_name = "c_subneck_"+str(idx)+dupli
                        if neck_twist_enabled:
                            subneck_deform_name = "subneck_twist_"+str(idx)+dupli
                        else:
                            subneck_deform_name = subneck_cont_name

                        subneck_deform = get_edit_bone(subneck_deform_name)
                        subneck_cont = get_edit_bone(subneck_cont_name)

                        subneck_parent_name = ''
                        if subneck_cont.parent:
                            subneck_parent_name = subneck_cont.parent.name

                        bones_coords[subneck_cont_name] = {"head":subneck_deform.head.copy(), "tail":subneck_deform.tail.copy(), "roll":subneck_deform.roll, 
                            "parent":subneck_parent_name, "arp_bone":subneck_deform.name, 
                            "softlink":is_softlink_bone(subneck_deform.name), 'const_interp':is_const_interp_bone(subneck_deform.name)}

                # Neck 01
                if get_edit_bone('c_neck_01' + dupli) != None and is_deforming('c_neck_01' + dupli):
                    neck01 = get_edit_bone('c_neck_01' + dupli)
                    b01_parent = b_parent_name
                    bones_coords[neck01.name] = {"head":neck01.head.copy(), "tail":neck01.tail.copy(), "roll":neck01.roll, 
                        "parent":b01_parent, "arp_bone":neck01.name, 
                        "softlink":is_softlink_bone(neck01.name), 'const_interp':is_const_interp_bone(neck01.name)}


            # Head
            if get_edit_bone('head' + dupli) != None and is_deforming('head' + dupli):
                headb = get_edit_bone('head' + dupli)
                b_parent =""
                if get_edit_bone("head_ref" + dupli) != None:
                    #print("  Found head ref bone")
                    head_ref = get_edit_bone("head_ref" + dupli)
                    if head_ref.parent != None:
                        b_parent = head_ref.parent.name.replace("_ref", "")
                    else:
                        print("  Could not retrieve head parent. Assign to root.")
                        b_parent = "root.x"
                else:
                    print("  Could not retrieve head parent. Assign to root.")
                    b_parent = "root.x"

                bones_coords[headb.name] = {"head":headb.head.copy(), "tail":headb.tail.copy(), "roll":headb.roll, 
                    "parent":b_parent, "arp_bone":headb.name, 
                    "softlink":is_softlink_bone(headb.name), 'const_interp':is_const_interp_bone(headb.name)}

            #Skulls
            for i in range(1,4):
                if get_edit_bone("c_skull_0" + str(i) + dupli):
                    skull = get_edit_bone("c_skull_0" + str(i) + dupli)                    
                    bones_coords[skull.name] = {"head":skull.head.copy(), "tail":skull.tail.copy(), "roll":skull.roll, 
                        "parent":skull.parent.name, "arp_bone":skull.name, 
                        "softlink":is_softlink_bone(skull.name), 'const_interp':is_const_interp_bone(skull.name)}


        # Facial
        # Multi limb support
        #if get_edit_bone("jawbone.x") != None and is_deforming("jawbone.x"):
        if is_facial_enabled(arp_armature):        
            facial_duplis.append(".x")

        for bone in arp_armature.data.edit_bones:
            #if "jawbone_dupli_" in bone.name:
            if "head_ref_dupli_" in bone.name:                
                if 'facial' in bone.keys():   
                    if bone['facial'] == 1:  
                        dupli = bone.name[-12:]
                        if not dupli in facial_duplis:
                            facial_duplis.append(dupli)
        
        for dupli in facial_duplis:
            # Eyes targets
            bname = "c_eye_target" + dupli
            if get_edit_bone(bname) != None:
                ebone = get_edit_bone(bname)
                bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                    "parent":"None", "arp_bone":ebone.name, 
                    "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

            for side in sides:
                bname = "c_eye_target" + dupli[:-2] + side
                if get_edit_bone(bname) != None:
                    ebone = get_edit_bone(bname)
                    bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                        "parent":ebone.parent.name, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}


            # Eyebrow full
            for side in sides:
                bname = "c_eyebrow_full" + dupli[:-2] + side
                if get_edit_bone(bname):
                    ebone = get_edit_bone(bname)
                    b_parent = ""
                    if get_edit_bone("c_skull_02" + dupli):
                        b_parent = "c_skull_02" + dupli
                    elif get_edit_bone("head" + dupli):
                        b_parent = "head" + dupli
                    bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                        "parent":b_parent, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}


            # Main facial bones
            bones_parent_dict = {}
            facial_bones = ard.facial_deform + ["eyelid_top", "eyelid_bot"] + \
            ard.get_variable_lips(dupli, btype='CONTROLLER', no_side=True) + \
            ard.get_variable_eyelids(dupli, btype='CONTROLLER', no_side=True)
            
            for f_bone in facial_bones:                
                if f_bone.endswith('.x'):
                    bname = f_bone[:-2] + dupli
                    b = get_edit_bone(bname)
                    if b:
                        if b.parent:
                            parent_name = b.parent.name
                            bones_parent_dict[bname] = parent_name
            
                else:
                    for side in sides:
                        suff = dupli[:-2] + side
                        b = get_edit_bone(f_bone + suff)
                        if b:                 
                            if b.parent:
                                bones_parent_dict[f_bone + suff] = b.parent.name
                                
            
            for bname in bones_parent_dict:
                if "jawbone" in bname:
                    if get_edit_bone("c_skull_01"+dupli):
                        bones_parent_dict[bname] = "c_skull_01" + dupli
                    else:
                        bones_parent_dict[bname] = "head" + dupli
                    
                if "c_lips_bot" in bname:
                    bones_parent_dict[bname] = "jawbone" + dupli
                if "c_lips_top" in bname:
                    if get_edit_bone("c_skull_01" + dupli):
                        bones_parent_dict[bname] = "c_skull_01" + dupli
                    else:
                        bones_parent_dict[bname] = "head" + dupli
                if 'c_lips_smile' in bname:
                    if get_edit_bone("c_skull_01" + dupli):
                        bones_parent_dict[bname] = "c_skull_01" + dupli
                    else:
                        bones_parent_dict[bname] = "head" + dupli
                if 'c_lips_corner_mini' in bname:
                    if get_edit_bone('c_lips_smile'+dupli):
                        bones_parent_dict[bname] = 'c_lips_smile'+dupli
                        
                if "tong_01" in bname:
                    bones_parent_dict[bname] = "jawbone" + dupli
                if "tong_02" in bname:
                    bones_parent_dict[bname] = "tong_01" + dupli
                if "tong_03" in bname:
                    bones_parent_dict[bname] = "tong_02" + dupli                
           
                #if "eyelid" in bname and not ("_01" in bname or "_02" in bname or '_03' in bname or '_corner_' in bname):
                if bname == 'eyelid_top'+dupli[:-2]+bname[-2:] or bname == 'eyelid_bot'+dupli[:-2]+bname[-2:]:                    
                    bones_parent_dict[bname] = "c_eye_offset" + dupli[:-2] + bname[-2:]
                
                if "c_eye_ref_track" in bname:
                    bones_parent_dict[bname] = "c_eye_offset" + dupli[:-2] + bname[-2:]
                if "c_teeth_top" in bname:
                    if get_edit_bone("c_skull_01" + dupli):
                        bones_parent_dict[bname] = "c_skull_01" + dupli
                    else:
                        bones_parent_dict[bname] = "head" + dupli
                if "c_teeth_bot" in bname:
                    bones_parent_dict[bname] = "jawbone" + dupli

                ebone = get_edit_bone(bname)
                bones_coords[bname] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                    "parent":bones_parent_dict[bname], "arp_bone":ebone.name, 
                    "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

        # Ears
        # Multi-limb support
        for dupli in limb_sides.ear_sides:
            ears_list = ard.get_ears_controllers(dupli)
            
            for ear in ears_list:
                if is_deforming(ear):
                    ebone = get_edit_bone(ear)
                    b_parent = ebone.parent.name
                    bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                        "parent":b_parent, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

        # Breast
        breast_list = ["c_breast_01", "c_breast_02"]
        if get_data_bone("c_breast_01.l"):
            for side in sides:
                for breast_name in breast_list:
                    if is_deforming(breast_name + side):
                        ebone = get_edit_bone(breast_name + side)
                        b_parent = ebone.parent.name
                        #if scn.arp_keep_bend_bones and (arp_armature.arp_secondary_type == "ADDITIVE" or arp_armature.arp_secondary_type == "TWIST_BASED"):
                        #    b_parent = "spine_02_bend.x"
                        #print("SAVE BREAST PARENT", b_parent)
                        bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                            "parent":b_parent, "arp_bone":ebone.name, 
                            "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

        # Bottoms
        for side in sides:
            bot_name = "c_bot_bend"+side
            bot_bone = get_data_bone(bot_name)
            if bot_bone:
                if is_deforming(bot_name):
                    ebone = get_edit_bone(bot_name)
                    b_parent = "root.x"
                    bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                        "parent":b_parent, "arp_bone":ebone.name, 
                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

        # Tail
        for tside in limb_sides.tail_sides:
            first_tail_name = "c_tail_00" + tside
            if get_data_bone(first_tail_name):             
                tail_count = auto_rig.get_tail_count(tside)

                for i in range(0, tail_count):
                    t_idx = '%02d' % i
                    tail_name = 'c_tail_' + t_idx + tside

                    ebone = get_edit_bone(tail_name)
                    if ebone == None:
                        continue

                    if is_deforming(tail_name):
                        b_parent = None
                        if ebone.parent:
                            b_parent = ebone.parent.name

                        if "_00" in ebone.name:
                            if b_parent:
                                if b_parent[:2] == "c_":
                                    if get_edit_bone(b_parent[2:]) != None:
                                        b_parent = b_parent[2:]

                        if not b_parent:
                            b_parent = "c_traj"
                            print("  Tail parent not set, assigned to null")

                        bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                            "parent":b_parent, "arp_bone":ebone.name, 
                            "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}


        # Legs
        #   Get bones transforms
        for bone_name in ard.leg_deform:
            if arp_armature.arp_secondary_type == "TWIST_BASED":
                if "twist" in bone_name or "stretch" in bone_name:
                    bone_name = "c_"+bone_name

            for side in limb_sides.leg_sides:
                if is_deforming(bone_name+side):
                    ebone = get_edit_bone(bone_name+side)

                    if bone_name.startswith('c_toes'):
                        b_parent =  get_edit_bone(bone_name + side).parent.name
                        bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                                                    "parent":b_parent, "arp_bone":ebone.name, 
                                                    "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}
                                                    
                        # toes_01 must be stored even if it does not deform
                        toes_01 = get_edit_bone("toes_01"+side)
                        bones_coords["toes_01"+side] = {"head":toes_01.head.copy(), "tail":toes_01.tail.copy(), "roll":toes_01.roll, 
                                                        "parent":"foot"+side, "arp_bone":ebone.name, 
                                                        "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                    if bone_name == "foot":
                        b_parent = "leg_stretch" + side
                        bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                            "parent":b_parent, "arp_bone":ebone.name, 
                            "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                    if bone_name == "toes_01":
                        b_parent = "foot" + side
                        bones_coords[ebone.name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, "parent":b_parent, 
                            "arp_bone":ebone.name, 
                            "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                    if 'thigh_stretch' in bone_name:                       
                        thigh_twist = get_edit_bone('thigh_twist'+side)
                        c_thigh_b = thigh_twist.parent
                        thigh_ref = get_edit_bone('thigh_ref'+side)                        
                        
                        is_fk_lock = False
                        if 'thigh_fk_lock' in thigh_ref.keys():# thigh FK lock has a different setup
                            if thigh_ref['thigh_fk_lock'] == 1:
                                is_fk_lock = True
                        if is_fk_lock:
                            thigh_b_loc = get_edit_bone('thigh_b_loc'+side)
                            b_parent = thigh_b_loc.parent.name
                        else:# no thigh FK lock
                            b_parent = thigh_twist.parent.parent.name
                            
                        # 3 bones leg
                        if "c_thigh_b" in thigh_twist.parent.name:
                            if get_edit_bone('c_thigh_b'+side).use_deform:
                                b_parent = 'c_thigh_b'+side

                        thigh_softlink = is_softlink_bone(ebone.name)
                        if thigh_softlink and not arp_armature.arp_secondary_type == "TWIST_BASED":
                            thigh_head_pos = ebone.head.copy()
                        else:
                            thigh_head_pos = thigh_twist.head.copy()
                        bones_coords["thigh_stretch"+side] = {"head":thigh_head_pos, "tail":ebone.tail.copy(), "roll":ebone.roll, 
                            "parent":b_parent, "arp_bone":ebone.name, 
                            "softlink":thigh_softlink, 'const_interp':is_const_interp_bone(ebone.name)}
                            
                        if arp_armature.arp_secondary_type == "TWIST_BASED":
                            bones_coords['c_thigh_stretch'+side] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                                "parent":"thigh_stretch"+side, "arp_bone":ebone.name, 
                                "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                    if "leg_stretch" in bone_name:
                        b_parent = "thigh_stretch" + side
                        #print("  set parent", b_parent, bone_name)
                        bones_coords["leg_stretch"+side] = {"head":ebone.head.copy(), "tail":get_edit_bone("leg_twist" + side).tail.copy(), "roll":ebone.roll, 
                            "parent":b_parent, "arp_bone":ebone.name, 
                            "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                        if arp_armature.arp_secondary_type == "TWIST_BASED":
                            bones_coords["c_leg_stretch"+side] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                                "parent":"leg_stretch"+side, "arp_bone":ebone.name, 
                                "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                    if scn.arp_export_twist or arp_armature.arp_secondary_type == "TWIST_BASED":
                        # multiple twist support
                        thigh_ref = get_edit_bone("thigh_ref"+side)
                        twist_bones_amount = 1
                        if len(thigh_ref.keys()):
                            if "twist_bones_amount" in thigh_ref.keys():
                                twist_bones_amount = thigh_ref["twist_bones_amount"]

                        if "leg_twist" in bone_name:
                            # first leg twist bone (default)
                            b_parent = "leg_stretch"+side
                            leg_twist_name = "leg_twist"+side
                            if arp_armature.arp_secondary_type == "TWIST_BASED":
                                leg_twist_name = 'c_'+leg_twist_name
                            bones_coords[leg_twist_name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                                "parent":b_parent, "arp_bone":ebone.name, 
                                "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}
                            
                            # multiple leg twist bones
                            if twist_bones_amount > 1:
                                for t_idx in range(2, twist_bones_amount+1):
                                    leg_twist_idx_name = 'leg_twist_'+str(t_idx)+side
                                    if arp_armature.arp_secondary_type == "TWIST_BASED":
                                        leg_twist_idx_name = 'c_'+leg_twist_idx_name
                                    leg_twist_idx = get_edit_bone(leg_twist_idx_name)
                                    b_parent = 'leg_stretch'+side
                                    bones_coords[leg_twist_idx.name] = {"head":leg_twist_idx.head.copy(), "tail":leg_twist_idx.tail.copy(), "roll":leg_twist_idx.roll, 
                                        "parent":b_parent, "arp_bone":leg_twist_idx.name, 
                                        "softlink":is_softlink_bone(leg_twist_idx.name), 'const_interp':is_const_interp_bone(leg_twist_idx.name)}
                                    

                        if "thigh_twist" in bone_name:
                            # first thigh twist bone (default)
                            b_parent = "thigh_stretch"+side
                            thigh_twist_name = "thigh_twist"+side
                            if arp_armature.arp_secondary_type == "TWIST_BASED":
                                thigh_twist_name = 'c_'+thigh_twist_name
                            bones_coords[thigh_twist_name] = {"head":ebone.head.copy(), "tail":ebone.tail.copy(), "roll":ebone.roll, 
                                "parent":b_parent, "arp_bone":ebone.name, 
                                "softlink":is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}
                            # multiple thigh twist bones
                            if twist_bones_amount > 1:
                                for t_idx in range(2, twist_bones_amount+1):
                                    thigh_twist_idx_name = 'thigh_twist_'+str(t_idx)+side
                                    if arp_armature.arp_secondary_type == "TWIST_BASED":
                                        thigh_twist_idx_name = 'c_'+thigh_twist_idx_name
                                    thigh_twist_idx = get_edit_bone(thigh_twist_idx_name)
                                    b_parent = 'thigh_stretch'+side                                    
                                    bones_coords[thigh_twist_idx.name] = {"head":thigh_twist_idx.head.copy(), "tail":thigh_twist_idx.tail.copy(), "roll":thigh_twist_idx.roll, 
                                        "parent":b_parent, "arp_bone":thigh_twist_idx.name, 
                                        "softlink":is_softlink_bone(thigh_twist_idx.name), 'const_interp':is_const_interp_bone(thigh_twist_idx.name)}
                            
                    if bone_name == 'c_thigh_b':
                        c_thigh_b = get_edit_bone(bone_name+side)

                        if c_thigh_b.parent:
                            # 3 leg bones case
                            if get_edit_bone('thigh_b_ref'+side):
                                thigh_ref = get_edit_bone('thigh_ref'+side)
                                is_fk_lock = False
                                if 'thigh_fk_lock' in thigh_ref.keys():# handles thigh FK lock setup
                                    if thigh_ref['thigh_fk_lock'] == 1:
                                        is_fk_lock = True
                                if is_fk_lock:
                                    thigh_b_loc = get_edit_bone('thigh_b_loc'+side)
                                    b_parent = thigh_b_loc.parent.name
                                else:# no thigh FK lock
                                    # get the parent of the parent (controller < ik chain < root)                                    
                                    if c_thigh_b.parent.parent:
                                        b_parent = c_thigh_b.parent.parent.name
                            else:
                                b_parent = c_thigh_b.parent.name

                        bones_coords[ebone.name] = {'head':ebone.head.copy(), 'tail':ebone.tail.copy(), 'roll':ebone.roll, 
                            'parent':b_parent, 'arp_bone':ebone.name, 
                            'softlink':is_softlink_bone(ebone.name), 'const_interp':is_const_interp_bone(ebone.name)}

                legs_fans_export_to_dict(side, bones_coords)
                legs_toes_ikfk_export_to_dict(side, bones_coords)
                
        # Arms
        for side in limb_sides.arm_sides:
            arms_export_to_dict(side, bones_coords)
            arms_fans_export_to_dict(side, bones_coords)

        # Wings
        for side in limb_sides.wing_sides:
            wings_export_to_dict(side, bones_coords)    
        
        # Spline IK (mped)
        for side in limb_sides.spline_sides:
            spline_name = auto_rig.get_spline_name(side)
            spline_ik_export_to_dict(spline_name, side, bones_coords)

        # Kilt
        for side in limb_sides.kilt_sides:
            kilt_export_to_dict(side, bones_coords)
            
        
        # Advanced bones (bend bones)
        if scn.arp_keep_bend_bones:
            for eb in arp_armature.data.edit_bones:
                if arp_armature.arp_secondary_type == "ADDITIVE":
                    if not is_bend_bone(eb.name) or is_proxy_bone(eb):
                        continue
                elif arp_armature.arp_secondary_type == "TWIST_BASED":
                    if not is_bend_bone_spine_only(eb.name) or is_proxy_bone(eb):
                        continue
                else:
                    continue
                
                if is_bone_in_layer(eb.name, 'mch_disabled') or eb.use_deform == False:#check for disabled limb
                    continue

                b_parent = eb.parent.name

                bone_side = get_bone_side(eb.name)

                # Set parent
                if scn.arp_export_twist:
                    if 'thigh_bend_contact' in eb.name or 'thigh_bend_01' in eb.name:
                        b_parent = 'thigh_twist' + bone_side
                    if 'ankle_bend' in eb.name:
                        b_parent = 'leg_twist' + bone_side
                    if 'shoulder_bend' in eb.name:
                        b_parent = 'arm_twist' + bone_side
                    if 'wrist_bend' in eb.name:
                        b_parent = 'forearm_twist' + bone_side
                else:
                    if 'thigh_bend_contact' in eb.name or 'thigh_bend_01' in eb.name:
                        b_parent = 'thigh_stretch' + bone_side
                    if 'ankle_bend' in eb.name:
                        b_parent = 'leg_stretch' + bone_side
                    if 'shoulder_bend' in eb.name:
                        b_parent = 'arm_stretch' + bone_side
                    if 'wrist_bend' in eb.name:
                        b_parent = 'forearm_stretch' + bone_side

                c_spine_list = []
                for n in range(2, spine_count+1):
                    str_idx = '%02d' % n
                    c_spine_list.append("c_spine_"+str_idx+".x")

                if b_parent in c_spine_list:
                    b_parent = b_parent[2:]

                if 'c_root_bend' in eb.name:
                    b_parent = "root.x"
                if 'c_waist_bend' in eb.name:
                    b_parent = "root.x"

                # Store bone in dict
                bones_coords[eb.name] = {"head":eb.head.copy(), "tail":eb.tail.copy(), "roll":eb.roll, 
                    "parent":b_parent, "arp_bone":eb.name, 
                    "softlink":is_softlink_bone(eb.name), 'const_interp':is_const_interp_bone(eb.name)}

        
        #for side in limb_sides.bbones_sides:# TODO bendy-bones limbs, convert bbones to real bones with armature + damped track constraints            
        
        
    # Custom bones
    for cc_bone in arp_armature.data.edit_bones:
        if not is_custom_bone(cc_bone.name):
            continue
            
        if not cc_bone.name in bones_coords:
            print('\n  Adding custom bone "' + cc_bone.name + '"...')

            # Find parent
            b_parent = ''

            if cc_bone.parent:
                b_parent = cc_bone.parent.name

            # look for the parent bone in the m-ped armature
            parent_found = False

            if is_bone_in_dict(b_parent):
                parent_found = True
                print('  Custom bone: "'+ cc_bone.name + '" found direct parent bone "' + b_parent + '" in the m-ped armature.')

            # if not found, tries to match with other bones
            if not parent_found:
                print('  Custom bone: "' + cc_bone.name + '" did not found direct parent bone "' + b_parent + '" in the m-ped armature. Look for other bones...')

                b_parent = find_matching_parent(bone_parent_name = b_parent, item = cc_bone)

            # custom props
            cprops = None
            if len(cc_bone.keys()):
                cprops = {}
                for cprop_name in cc_bone.keys():
                    if cprop_name != "_RNA_UI":
                        if isinstance(cc_bone[cprop_name], int) or isinstance(cc_bone[cprop_name], float) or isinstance(cc_bone[cprop_name], str) or isinstance(cc_bone[cprop_name], bool):          
                            cprops[cprop_name] = cc_bone[cprop_name]

            #Store bone in dict
            bones_coords[cc_bone.name] = {"head":cc_bone.head.copy(), "tail":cc_bone.tail.copy(), "roll":cc_bone.roll, 
                                        "parent":b_parent, "custom_props":cprops, "arp_bone":cc_bone.name, 
                                        "softlink":is_softlink_bone(cc_bone.name), 'const_interp':is_const_interp_bone(cc_bone.name)}

        else:
            print("  "+cc_bone.name+" is marked as a custom bone but is already part of the base rig, skip it")
            exclude_custom_bone(cc_bone.name)


    # c_traj forced export
    if scn.arp_ge_master_traj:      
        c_traj = arp_armature.data.edit_bones.get('c_traj')
        if c_traj:
            if not c_traj.name in bones_coords:
                bones_coords[c_traj.name] = {"head":c_traj.head.copy(), "tail":c_traj.tail.copy(), "roll":c_traj.roll,
                                            "parent":'', 'arp_bone':c_traj.name,
                                            "softlink":is_softlink_bone(c_traj.name), 'const_interp':is_const_interp_bone(c_traj.name)}
                                            
            
    # Remove unselected bone if export selection is enabled
    if scn.arp_ge_sel_bones_only:
        to_pop = []
        for b in bones_coords:
            arp_bone_name = bones_coords[b]["arp_bone"]
            if arp_bone_name not in self.selected_bone_names:
                #print(arp_bone_name, "not found, pop!")
                to_pop.append(b)

        for i in to_pop:
            bones_coords.pop(i)


    #### Create M-Ped rig ####
    print("\n  Create the Mped rig...")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    # Create the armature
    amt = bpy.data.armatures.new('rig_mped_data')
    rig_mped = bpy.data.objects.new('rig_mped', amt)
    rig_mped.show_in_front= True
    rig_mped.location = arp_armature.location
    rig_mped.scale = arp_armature.scale
    
    if bpy.app.version >= (4,0,0):
        rig_mped.data.collections.new("Bones")

    # if root motion, the armature object is constrained to the c_traj controller
    if scn.arp_ue_root_motion:
        cns = rig_mped.constraints.new("CHILD_OF")
        cns.name = "Child Of"
        cns.target = arp_armature
        cns.subtarget = "c_traj"
        arp_armature.data.pose_position = 'REST'
        bpy.context.evaluated_depsgraph_get().update()
        cns.inverse_matrix = arp_armature.pose.bones["c_traj"].matrix.inverted()
        arp_armature.data.pose_position = 'POSE'
        bpy.context.evaluated_depsgraph_get().update()
    else:
        cns = rig_mped.constraints.new('COPY_TRANSFORMS')
        cns.name = 'Copy Transforms'
        cns.target = arp_armature

    scn.collection.objects.link(rig_mped)
    bpy.context.view_layer.objects.active = rig_mped
    bpy.context.evaluated_depsgraph_get().update()
    mped_armature = get_object("rig_mped")

    #   create the bones
    print("  Create bones...")
    bpy.ops.object.mode_set(mode='EDIT')

    for bone_name in bones_coords:  
        new_bone = mped_armature.data.edit_bones.new(bone_name)
        if bpy.app.version >= (4,0,0):
            set_bone_layer(new_bone, "Bones")
            
        new_bone.head = bones_coords[bone_name]["head"]
        new_bone.tail = bones_coords[bone_name]["tail"]
        new_bone.roll = bones_coords[bone_name]["roll"]
        
        # deform
        if 'deform' in bones_coords[bone_name]:
            new_bone.use_deform = bones_coords[bone_name]['deform']

        # bone type tag
        if "type" in bones_coords[bone_name]:
            new_bone["type"] = bones_coords[bone_name]["type"]

        # softlink tag
        softlink = False
        if "softlink" in bones_coords[bone_name]:
            softlink = bones_coords[bone_name]["softlink"]

        new_bone["softlink"] = softlink
        
        # const interpolation tag
        const_interp = False
        if 'const_interp' in bones_coords[bone_name]:
            const_interp = bones_coords[bone_name]['const_interp']
        if const_interp:
            new_bone["const_interp"] = const_interp

        # make sure to align the root x_axis to avoid issues with constraints since it's upside-down
        if bone_name == "root.x" and not is_custom_bone(bone_name):
            align_bone_x_axis(new_bone, bones_coords[bone_name]["x_axis"])

        if arp_armature.arp_secondary_type == "TWIST_BASED":
            bparent = bones_coords[bone_name]["parent"]
            if bone_name.startswith("thigh_stretch") and bparent == "root.x":
                new_bone.use_deform = False
            if bone_name.startswith("leg_stretch") and bparent.startswith("thigh_stretch"):
                new_bone.use_deform = False
            if bone_name.startswith("arm_stretch") and bparent.startswith("shoulder"):
                new_bone.use_deform = False
            if bone_name.startswith("forearm_stretch") and bparent.startswith("arm_stretch"):
                new_bone.use_deform = False
        
        # custom props
        if 'custom_props' in bones_coords[bone_name]:
            cprops = bones_coords[bone_name]['custom_props']
            if cprops:                       
                for cprop_name in cprops:            
                    if cprop_name != "_RNA_UI":
                        prop_val = cprops[cprop_name]
                        prop_type = type(prop_val)# hack: evaluating the prop type here leads to exit the try loop if any error, instead of crashing Blender next line                  
                        new_bone[cprop_name] = prop_val                       
                       
                    
    print("  Set parents...")
    for bone_name in bones_coords:
        new_bone = get_edit_bone(bone_name)
        parent_name = bones_coords[bone_name]["parent"]
        if parent_name != "None":
            direct_parent = get_edit_bone(parent_name)
            if direct_parent == None:# the saved parent is not in the mped armature
                parent_name = find_matching_parent(parent_name, new_bone)

            new_bone.parent = get_edit_bone(parent_name)


    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.mode_set(mode='EDIT')

    if scn.arp_fix_fbx_rot:
        fix_fbx_bones_rot()

    # Add constraints
    print("\n  Create constraints...")

    # for debug only
    set_constraints = True

    bpy.ops.object.mode_set(mode='POSE')

    if set_constraints:
        if self.is_arp_armature:
            spine_list = []

            for n in range(1, spine_count+1):
                str_idx = '%02d' % n
                spine_list.append("spine_"+str_idx+".x")

        for bone_name in bones_coords:
            pbone = get_pose_bone(bone_name)
            bone_side = get_bone_side(pbone.name)
            bone_softlink = False
            if "softlink" in pbone.bone.keys():
                bone_softlink = pbone.bone["softlink"]


            bone_type = None
            if "type" in bones_coords[bone_name]:
                bone_type = bones_coords[bone_name]["type"]

            if self.is_arp_armature:
                # Spine
                if bone_name == "root.x":
                    add_copy_transf(pbone, tar=arp_armature, subtar="root.x", h_t=1.0, no_scale=bone_softlink)

                    cns2 = pbone.constraints.new("LOCKED_TRACK")
                    cns2.name = "Locked Track"
                    cns2.target = arp_armature
                    cns2.subtarget = "root.x"
                    cns2.track_axis = "TRACK_Y"
                    cns2.lock_axis = "LOCK_X"

                if bone_name in spine_list:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                if bone_name.startswith("neck") and bone_name.endswith(".x"):
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                if bone_name.startswith("c_subneck_"):
                    if neck_twist_enabled:
                        subneck_twist_name = bone_name[2:].replace("subneck_", "subneck_twist_")
                        add_copy_transf(pbone, tar=arp_armature, subtar=subneck_twist_name, no_scale=bone_softlink)
                    else:
                        add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                if "head" in bone_name and ".x" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                if "c_skull_" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Facial
                for bname in ard.facial_deform:
                    _s = bname
                    if ".x" in bname:
                        _s = bname.replace(".x", "")
                    if _s in bone_name:
                        if len(pbone.constraints) == 0:
                            add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                if "c_eye_target" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Ears
                if "c_ear_" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Tail
                if "c_tail" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Breast
                if "c_breast_" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Legs
                if bone_name.startswith("c_thigh_b") and not bone_name.startswith("c_thigh_bend"):
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                    
                if bone_name.startswith('thigh_stretch'):
                    if bone_softlink:
                        cns1 = pbone.constraints.new("COPY_LOCATION")
                        cns1.name = "Copy Location"
                        cns1.target = arp_armature
                        cns1.subtarget = 'thigh'+bone_side if arp_armature.arp_secondary_type == "TWIST_BASED" else bone_name

                        cns2 = pbone.constraints.new("COPY_ROTATION")
                        cns2.name = "Copy Rotation"
                        cns2.target = arp_armature
                        cns2.subtarget = bone_name
                    else:
                        add_copy_transf(pbone, tar=arp_armature, subtar=bone_name)
                        cns2 = pbone.constraints.new("COPY_LOCATION")
                        cns2.name = "Copy Location"
                        cns2.target = arp_armature
                        cns2.subtarget = 'thigh'+bone_side
                        
                if bone_name.startswith('c_thigh_stretch'):
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                        
                if 'leg_stretch' in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                if 'thigh_twist' in bone_name or 'leg_twist' in bone_name:
                    sbtgt = ""
                    if arp_armature.arp_secondary_type == "TWIST_BASED" and not bone_name.startswith("c_"):
                        sbtgt = "c_"+bone_name
                    else:
                        sbtgt = bone_name

                    cns1, cns2 = add_copy_transf(pbone, tar=arp_armature, subtar=sbtgt, no_scale=bone_softlink)

                    if "arp_twist_fac" in bpy.context.scene.keys():
                        cns1.influence = scn.arp_twist_fac
                        if cns2:
                            cns2.influence = scn.arp_twist_fac                    
                    
                if "toes_01" in bone_name or "foot" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                    
                # Toes
                if "c_toes" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Arms
                if "shoulder" in bone_name or "hand" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                
                if bone_name.startswith('arm_stretch'): 
                    if bone_softlink:
                        cns1 = pbone.constraints.new("COPY_LOCATION")
                        cns1.name = "Copy Location"
                        cns1.target = arp_armature
                        cns1.subtarget = 'arm'+bone_side if arp_armature.arp_secondary_type == "TWIST_BASED" else bone_name

                        cns2 = pbone.constraints.new("COPY_ROTATION")
                        cns2.name = "Copy Rotation"
                        cns2.target = arp_armature
                        cns2.subtarget = bone_name
                    else:
                        add_copy_transf(pbone, tar=arp_armature, subtar=bone_name)                        
                        cns_loc = pbone.constraints.new("COPY_LOCATION")
                        cns_loc.name = "Copy Location"
                        cns_loc.target = get_object(arp_armature.name)
                        cns_loc.subtarget = "c_arm_twist_offset" + bone_side
                       
                        
                if bone_name.startswith('c_arm_stretch'):
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                    
                if "forearm_stretch" in bone_name:
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                    
                if "forearm_twist" in bone_name :
                    sbtgt = ""
                    if arp_armature.arp_secondary_type == "TWIST_BASED" and not bone_name.startswith("c_"):
                        sbtgt = "c_"+bone_name
                    else:
                        sbtgt = bone_name

                    cns1, cns2 = add_copy_transf(pbone, tar=arp_armature, subtar=sbtgt, no_scale=bone_softlink)

                    if "arp_twist_fac" in bpy.context.scene.keys():
                        cns1.influence = scn.arp_twist_fac
                        if cns2:
                            cns2.influence = scn.arp_twist_fac

                if "arm_twist" in bone_name and not "forearm" in bone_name:
                    sbtgt = ''
                    if not "arm_twist_" in bone_name:
                        if arp_armature.arp_secondary_type == "TWIST_BASED":
                            sbtgt = bone_name
                        else:
                            sbtgt = "c_arm_twist_offset" + bone_side
                    else:
                        if arp_armature.arp_secondary_type == "TWIST_BASED" and not bone_name.startswith("c_"):
                            sbtgt = "c_"+bone_name
                        else:
                            sbtgt = bone_name

                    cns1, cns2 = add_copy_transf(pbone, tar=arp_armature, subtar=sbtgt, no_scale=bone_softlink)
                        

                # Fingers
                for fing in fingers_names:
                    if "c_toes" in bone_name:
                        continue
                    if not (fing + "1" in bone_name or fing + "2" in bone_name or fing + "3" in bone_name):
                        continue
                    target_bone = bone_name

                    if arp_armature.data.bones.get(bone_name) == None:
                        target_bone = "c_" + bone_name

                    add_copy_transf(pbone, tar=arp_armature, subtar=target_bone, no_scale=bone_softlink)

                # Wings
                if bone_name.startswith("c_arm_feather_") or bone_name.startswith("c_forearm_feather_") or bone_name.startswith("c_hand_feather_"):
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Spline IK
                if (bone_name.startswith("spline_") or bone_name.startswith("c_spline_") or bone_type == "ik_spline") and not is_custom_bone(bone_name):
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Bend bones
                if is_bend_bone(bone_name):
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)

                # Kilt
                if bone_type == 'kilt':
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                    
                # Arms, Legs Fans
                if bone_type == 'joint_fan':
                    add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                    
                
            # Custom Bones
            if is_custom_bone(bone_name):
                add_copy_transf(pbone, tar=arp_armature, subtar=bone_name, no_scale=bone_softlink)
                
            if scn.arp_ge_master_traj and pbone.name == 'c_traj':
                add_copy_transf(pbone, tar=arp_armature, subtar=pbone.name, no_scale=bone_softlink)

    
    # Copy custom props on pose bone data
    for pb in mped_armature.pose.bones:
        if pb.name in bones_coords:
            if 'arp_bone' in bones_coords[pb.name]:
                arp_bone_name = bones_coords[pb.name]['arp_bone']
                arp_bone = arp_armature.pose.bones.get(arp_bone_name)
                if arp_bone:                  
                    for propname in arp_bone.keys():
                        if propname == 'cc':#skip custom control prop...
                            continue
                        # copy
                        pb[propname] = arp_bone[propname]
                        
    
    #### Assign the armature modifiers and weights ####
    print("\n  Assign modifiers and weights...")

    def select_overlap(obj, vgroup1, vgroup2, vgroups):
        if scn.arp_debug_mode:
            print("  Select Overlap")

        bpy.ops.mesh.select_all(action='DESELECT')#first
        vgroups.active_index = vgroups[vgroup1].index
        bpy.ops.object.vertex_group_select()
        mesh = bmesh.from_edit_mesh(obj.data)
        list1 = [vert.index for vert in mesh.verts if vert.select]
        bpy.ops.mesh.select_all(action='DESELECT')#second
        vgroups.active_index = vgroups[vgroup2].index
        bpy.ops.object.vertex_group_select()
        list2 = [vert.index for vert in mesh.verts if vert.select]
        bpy.ops.mesh.select_all(action='DESELECT')
        overlap = [i for i in list1 if i in list2]

        for vert in mesh.verts:
            if vert.index in overlap:
                vert.select = True


    twist_dict = {'leg_twist':['leg_stretch'], 'thigh_twist':['thigh_stretch'], 'c_arm_twist_offset':['arm_stretch'], 'forearm_twist':['forearm_stretch']}
    other_dict = {'c_thumb1_base':['c_thumb1']}
    bend_bones_dict = {'c_root_bend': ['root.x']}

    # add spine bones to bend_bones_dict
    if self.is_arp_armature:
        for idx in range(1, spine_count+1):
            str_idx = '%02d' % idx
            bend_bones_dict["c_spine_"+str_idx+".x"] = ["spine_"+str_idx+".x"]

    multiply_weight_dict = {"c_waist_bend":0.5, "c_elbow_bend":0.5}
    clamp_dict = {'c_thigh_bend_contact': 'thigh_twist', 'c_thigh_bend_01': 'thigh_twist', 'c_thigh_bend_02': 'thigh_twist', 'c_knee_bend': 'leg_stretch', 'c_ankle_bend': 'leg_stretch', 'c_leg_bend_01': 'leg_stretch', 'c_leg_bend_02': 'leg_stretch','c_elbow_bend': 'arm_stretch', 'c_shoulder_bend': 'arm_stretch', 'c_wrist_bend': 'forearm_twist', 'c_forearm_bend': 'forearm_twist'}

    collected_meshes = []

    # Iterate over meshes (mped)
    for obj in bpy.data.objects:
        if not(obj.type == 'MESH' and ("_arpexp" in obj.name or manual_set_debug)):
            continue

        collected_meshes.append(obj.name)

        if len(obj.modifiers) == 0:
            continue

        for modif in obj.modifiers:
            if modif.type != 'ARMATURE':
                continue
            if modif.object == None:
                continue
            if armature_add_name:
                if modif.object.name == armature_add_name:
                    obj.modifiers.remove(modif)
                    continue
            if modif.object.name != arp_armature.name:
                continue
            if scn.arp_debug_mode:
                print("  ..", obj.name)

            # print
            sys.stdout.write("\r  " + 'mesh: ' + obj.name + '                                                       ')
            sys.stdout.flush()

            # replace with mped armature
            modif.object = get_object("rig_mped")
            modif.use_deform_preserve_volume = False

            # Transfer weights
            for vert in obj.data.vertices:
                if len(vert.groups) == 0:
                    continue

                for grp in vert.groups:
                    try:
                        grp_name = obj.vertex_groups[grp.group].name
                    except:
                        continue

                    weight = grp.weight

                    # Twist bones
                    if not scn.arp_export_twist:# in case of multiple twist bones used, assumes we need to export twist bones
                        transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=twist_dict)

                    # Advanced - Bend bones
                    # transfer additive weights if they're not exported
                    if not scn.arp_keep_bend_bones and (arp_armature.arp_secondary_type == "ADDITIVE" or arp_armature.arp_secondary_type == "TWIST_BASED"):
                        transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=bend_bones_dict)
                    # if they're exported, clamp weights for better deformations
                    else:
                        if arp_armature.arp_secondary_type != "TWIST_BASED":
                            # Clamp weights (make sure additive influence is contained inside the main groups for correct deformations)
                            clamp_weights(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=clamp_dict)

                    # Multiply some weights for better results
                    multiply_weight(object=obj, vertice=vert, vertex_weight=grp.weight, group_name=grp_name, dict=multiply_weight_dict)

                    # Others
                    transfer_weight(object=obj, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=other_dict)

            # Change some vertex groups names
            for vgroup in obj.vertex_groups:
                # fingers
                for f_name in fingers_names:
                    if not f_name in vgroup.name or is_custom_bone(vgroup.name):
                        continue
                    if vgroup.name.startswith("c_") and not vgroup.name.startswith("c_toes_"):
                        vgroup.name = vgroup.name[2:]
                
                # arm
                if "c_arm_twist_offset" in vgroup.name:
                    new_vgrpname = vgroup.name.replace("c_arm_twist_offset", "arm_twist")
                    overwrite_vgroup(obj, vgroup, new_vgrpname)
                    
                # arm, leg twists
                '''
                if arp_armature.arp_secondary_type == "TWIST_BASED":
                    if vgroup.name.startswith("c_thigh_twist") or vgroup.name.startswith("c_leg_twist") or vgroup.name.startswith("c_arm_twist") or vgroup.name.startswith("c_forearm_twist"):
                        new_vgrpname = vgroup.name[2:]
                        overwrite_vgroup(obj, vgroup, new_vgrpname)
                '''
                
                # root
                if vgroup.name == "root.x" and mped_armature.data.bones.get("c_root_bend.x"):
                    if obj.vertex_groups.get("c_root_bend.x"):# check the c_root_bend does not exist yet
                        obj.vertex_groups["c_root_bend.x"].name = "c_root_bend_old.x"
                    vgroup.name = "c_root_bend.x"

                # subneck twists
                if vgroup.name.startswith("subneck_twist_"):
                    new_vgrpname = "c_"+vgroup.name.replace("_twist", "")
                    overwrite_vgroup(obj, vgroup, new_vgrpname)

    # Rename some bones for retro-compatibility or better clarity
    facial_def_names = {"eyelid_top": "c_eyelid_top", "eyelid_bot": "c_eyelid_bot", "jawbone.x": "c_jawbone.x"}
    print("\n  Bones renaming...")
    renamed_bones = {}

    for dupli in facial_duplis:
        for side in sides:
            for b_name in facial_def_names:
                suffix = dupli[:-2] + side
                _b_name = b_name

                if b_name[-2:] == ".x":
                    suffix = dupli
                    _b_name = b_name[:-2]

                #print('  ', _b_name + suffix)

                if mped_armature.data.bones.get(_b_name + suffix):
                    n = facial_def_names[b_name] + suffix
                    if facial_def_names[b_name][-2:] == ".x":
                        n = facial_def_names[b_name][:-2] + suffix

                    renamed_bones[_b_name+suffix] = n# store the renamed bones in a dict to correct object parented to bones names
                    mped_armature.data.bones[_b_name+suffix].name = n

                    if scn.arp_debug_mode:
                        print("  Renamed:", _b_name+suffix, "to", n)

    set_active_object("rig_mped")
    bpy.ops.object.mode_set(mode='POSE')

    # Assign parent bones of objects that are directly parented to bones (mped)
    for mesh in collected_meshes:
        obj = get_object(mesh)
        if len(obj.keys()) > 0:
            if "arp_parent_bone" in obj.keys():
                b_parent = obj["arp_parent_bone"]

                # Look for the parent bone in the m-ped armature
                parent_found = False

                if is_bone_in_dict(b_parent):
                    if b_parent in renamed_bones:#check for renamed bones
                        b_parent = renamed_bones[b_parent]
                    parent_found = True
                    print('  Object: "'+ obj.name + '" found direct parent bone "' + b_parent + '" in the m-ped armature.')

                # If not found, tries to match with other bones
                if not parent_found:
                    print('  Object: "' + obj.name + '" did not found direct parent bone "' + b_parent + '" in the m-ped armature. Look for other bones...')
                    b_parent = find_matching_parent(bone_parent_name = b_parent, item = obj)

                obj_matrix = obj.matrix_world.copy()
                obj.parent = get_object("rig_mped")
                obj.parent_bone = b_parent
                obj.matrix_world = obj_matrix


    # Create and key first and last action frame range
    bpy.ops.pose.select_all(action='SELECT')

    if scn.arp_bake_anim:
        if len(bpy.data.actions) == 0:
            try:
                action = get_object(arp_armature.name).animation_data.action
                current_frame = scn.frame_current#save current frame

                for f in action.frame_range:
                    scn.frame_current = f
                    scn.frame_set(scn.frame_current)#debug
                    bpy.context.evaluated_depsgraph_get().update()

                    for bone in bpy.context.selected_pose_bones:
                        bone.keyframe_insert(data_path="rotation_euler")
                        bone.keyframe_insert(data_path="location")

                #restore current frame
                scn.frame_current = current_frame
                scn.frame_set(scn.frame_current)#debug

                get_object(mped_armature.name).animation_data.action.name = action.name + "_mped"

            except:
                print("  No action to create")


    #Push the bend bones?
    if scn.arp_keep_bend_bones and scn.arp_push_bend and arp_armature.arp_secondary_type == "ADDITIVE":
        for _action in bpy.data.actions:

            if not check_id_root(_action):
                continue

            _push_bend_bones(_action, 2)
            self.actions_pushed_changed.append(_action.name)

    bpy.data.armatures[mped_armature.data.name].pose_position = 'POSE'
    mped_armature['set'] = True
    mped_armature['binded'] = True
    
    # tag the rig as set for humanoid
    arp_armature['arp_export_rig_set'] = mped_armature.name

    print("\nMped rig built.")
    

def _constraint_rig(state):
    scn = bpy.context.scene
    baked_armature = None

    if scn.arp_export_rig_type == 'HUMANOID':
        baked_armature = get_object('rig_humanoid')
    if scn.arp_export_rig_type == 'UNIVERSAL':
        baked_armature = get_object('rig_mped')

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    # Unhide if hidden
    mute_state = baked_armature.hide_get()
    unhide_object(baked_armature)

    set_active_object(baked_armature.name)

    # Switch to Pose mode
    bpy.ops.object.mode_set(mode='POSE')

    # Mute or Unmute constraints
    for bone in baked_armature.pose.bones:
        for cns in bone.constraints:
            if cns.name == "Track To" or cns.name == "Stretch To":
                continue
            enable_constraint(cns, not state)

    for cns in bpy.context.active_object.constraints:    
        enable_constraint(cns, not state)
        
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.evaluated_depsgraph_get().update()

    #reset hide state
    baked_armature.hide_set(mute_state)

    baked_armature['binded'] = not state


def update_engine_type(self, context):
    scn = context.scene
    if scn.arp_engine_type in ['UNREAL', 'OTHERS']:  
        scn.arp_export_bake_axis_convert = False
        scn.arp_ge_master_traj = False
    elif scn.arp_engine_type == 'GODOT':
        scn.arp_ge_master_traj = True
    elif scn.arp_engine_type == 'UNITY':
        scn.arp_ge_master_traj = False


def update_only_active(self, context):
    scn = context.scene
    if scn.arp_bake_only_active:
        #scn.arp_see_actions = False
        scn.arp_only_containing = False


def update_bake_type(self, context):
    scn = context.scene
    if scn.arp_bake_type == 'NLA':
        if scn.arp_frame_range_type == 'MARKERS' or scn.arp_frame_range_type == 'FULL':
            scn.arp_frame_range_type = 'SCENE'


def revert_rename_for_ue():
    if get_object("rig_humanoid") != None:
        for pbone in get_object('rig_humanoid').pose.bones:
            if not '_bend' in pbone.name:
                if 'thigh' in pbone.name and not 'stretch' in pbone.name:
                    if not 'twist' in pbone.name:
                        pbone.name = pbone.name.replace('thigh', 'thigh_stretch')
                    else:
                        pbone.name = pbone.name.replace('thigh_twist_01', 'thigh_twist')
                if 'calf' in pbone.name:
                    if not 'twist' in pbone.name:
                        pbone.name = pbone.name.replace('calf', 'leg_stretch')
                    else:
                        pbone.name = pbone.name.replace('calf_twist_01', 'leg_twist')
                if 'ball' in pbone.name:
                    pbone.name = pbone.name.replace('ball', 'toes_01')
                if 'clavicle' in pbone.name:
                    pbone.name = pbone.name.replace('clavicle','shoulder')
                if 'upperarm' in pbone.name:
                    if not 'twist' in pbone.name:
                        pbone.name = pbone.name.replace('upperarm', 'arm_stretch')
                    else:
                        pbone.name = pbone.name.replace('upperarm_twist_01', 'arm_twist')
                if 'lowerarm' in pbone.name:
                    if not 'twist' in pbone.name:
                        pbone.name = pbone.name.replace('lowerarm', 'forearm_stretch')
                    else:
                        pbone.name = pbone.name.replace('lowerarm_twist_01', 'forearm_twist')
                if 'index_01' in pbone.name:
                    pbone.name = pbone.name.replace('index_01', 'c_index1')
                if 'index_02' in pbone.name:
                    pbone.name = pbone.name.replace('index_02', 'c_index2')
                if 'index_03' in pbone.name:
                    pbone.name = pbone.name.replace('index_03', 'c_index3')
                if 'middle_01' in pbone.name:
                    pbone.name = pbone.name.replace('middle_01', 'c_middle1')
                if 'middle_02' in pbone.name:
                    pbone.name = pbone.name.replace('middle_02', 'c_middle2')
                if 'middle_03' in pbone.name:
                    pbone.name = pbone.name.replace('middle_03', 'c_middle3')
                if 'ring_01' in pbone.name:
                    pbone.name = pbone.name.replace('ring_01', 'c_ring1')
                if 'ring_02' in pbone.name:
                    pbone.name = pbone.name.replace('ring_02', 'c_ring2')
                if 'ring_03' in pbone.name:
                    pbone.name = pbone.name.replace('ring_03', 'c_ring3')
                if 'pinky_01' in pbone.name:
                    pbone.name = pbone.name.replace('pinky_01', 'c_pinky1')
                if 'pinky_02' in pbone.name:
                    pbone.name = pbone.name.replace('pinky_02', 'c_pinky2')
                if 'pinky_03' in pbone.name:
                    pbone.name = pbone.name.replace('pinky_03', 'c_pinky3')
                if 'thumb_01' in pbone.name:
                    pbone.name = pbone.name.replace('thumb_01', 'c_thumb1')
                if 'thumb_02' in pbone.name:
                    pbone.name = pbone.name.replace('thumb_02', 'c_thumb2')
                if 'thumb_03' in pbone.name:
                    pbone.name = pbone.name.replace('thumb_03', 'c_thumb3')
                if 'neck_01' in pbone.name:
                    pbone.name = 'neck.x'
                if 'spine_01' in pbone.name:
                    pbone.name = 'spine_01.x'
                if 'spine_02' in pbone.name:
                    pbone.name = 'spine_02.x'
                if 'spine_03' in pbone.name:
                    pbone.name = 'spine_03.x'
                if 'head' in pbone.name:
                    pbone.name = 'head.x'
                if 'pelvis' in pbone.name:
                    pbone.name = 'root.x'

    else:
        print("rig_humanoid not found.")
        
        
def _run_custom_export_script():
    scn = bpy.context.scene
    script_path = bpy.path.abspath(scn.arp_custom_export_script)    
    
    if os.path.isfile(script_path) and script_path.endswith('.py'):
        print('Running custom export script:', script_path)
        exec(open(script_path).read())
   
   
def rename_custom(self):    
    scn = bpy.context.scene
    rig = bpy.context.active_object
    
    # get renaming dict from file
    fp = bpy.path.abspath(scn.arp_rename_fp)
    
    # renaming dict from text datablock
    if scn.arp_rename_fp in bpy.data.texts:
        file = StringIO(bpy.data.texts[scn.arp_rename_fp].as_string())
        
    else:# or from external file
        # get renaming dict from file
        fp = bpy.path.abspath(scn.arp_rename_fp)
        
        try:           
            file = open(fp, 'r') if sys.version_info >= (3, 11) else open(fp, 'rU')
        except:
            print('')
            print('Rename file path:', fp)
            print("Rename Bone File not found! Skip renaming")
            return
    
    file_lines = file.readlines()
   
    for line in file_lines:
        line = str(line)
        if len(line.split('=')) < 2:
            print("Invalid renaming syntax, skip:", line)
            continue
        arp_name = line.split('=')[0].strip()
        rename = line.split('=')[1].strip()      
        b = rig.data.bones.get(arp_name)
        if b:
            b.name = rename
    
    
    file.close()


def rename_for_ue():

    print("\nRename for UE")

    # save the rig_fist data paths, since it's being renamed as well by blender automatically by mistake(c_ring1 > ring1)
    actions_fist = {}

    for action in bpy.data.actions:

        if not check_id_root(action):
            continue

        if "rig_fist" in action.name:
            print("  saving rig fist action data path...", action.name)
            fc_list = [fc.data_path for fc in action.fcurves]
            actions_fist[action] = fc_list


    rig_humanoid = get_object('rig_humanoid')

    # collect subnecks
    last_subneck = None
    last_id = 0
    for bone in rig_humanoid.data.bones:
        if not bone.name.startswith("c_subneck_"):
            continue
        id = bone.name.split('_')[2]
        id = id.split('.')
        if len(id) > 1:
            id = id[0]
        id = int(id)
        if id > last_id:
            last_id = id
            last_subneck = bone.name

    # collect spines
    spine_bones_list = []
    for idx in range(1, 33):
        str_idx = '%02d' % idx
        spine_bones_list.append("spine_"+str_idx+".x")

        
    def get_twist_idx(name):
        for i in name.split('_'):
            i = i.split('.')[0]
            if i.isdigit() and len(i) in [1,2]:
                return int(i)    
        return 0# no string idx found, is zero
        
    for pbone in rig_humanoid.pose.bones:
        # exclude secondary bones, custom controllers, helpers, from renaming
        if is_bend_bone(pbone.name) or is_custom_bone(pbone.name) or 'arp_ge_helper' in pbone.bone.keys():
            continue

        if 'thigh' in pbone.name:
            if not 'twist' in pbone.name:
                pbone.name = pbone.name.replace('thigh_stretch', 'thigh')
            else:
                if len(pbone.name.split('_')) == 2:
                    pbone.name = pbone.name.replace('thigh_twist', 'thigh_twist_01')#thigh_twist.l thigh_twist_02.l
                elif len(pbone.name.split('_')) > 2:# multiple twist bones
                    pbone.name = pbone.name.replace('thigh_twist_', 'thigh_twist_0')
        if 'leg' in pbone.name:
            if not 'twist' in pbone.name:
                pbone.name = pbone.name.replace('leg_stretch', 'calf')
            else:
                if len(pbone.name.split('_')) == 2:
                    pbone.name = pbone.name.replace('leg_twist', 'calf_twist_01')
                elif len(pbone.name.split('_')) > 2:# multiple twist bones
                    pbone.name = pbone.name.replace('leg_twist_', 'calf_twist_0')
        if 'toes' in pbone.name:
            pbone.name = pbone.name.replace('toes_01', 'ball')
        
        if 'shoulder' in pbone.name:
            pbone.name = pbone.name.replace('shoulder','clavicle')
        if 'arm_stretch' in pbone.name and not 'forearm_stretch' in pbone.name:
            pbone.name = pbone.name.replace('arm_stretch', 'upperarm')
        if 'arm_twist' in pbone.name and not 'forearm_twist' in pbone.name:
            sep_len = 2 if not "_dupli_" in pbone.name else 4
           
            if len(pbone.name.split('_')) == sep_len:
                pbone.name = pbone.name.replace('arm_twist', 'upperarm_twist_01')
            elif len(pbone.name.split('_')) > sep_len:# multiple twist bones
                    twist_idx = get_twist_idx(pbone.name)
                    str_i = '%02d' % twist_idx
                    pbone.name = pbone.name.replace('arm_twist_'+str(twist_idx), 'upperarm_twist_'+str_i)            
                    
        if 'forearm_stretch' in pbone.name:
            pbone.name = pbone.name.replace('forearm_stretch', 'lowerarm')
            
        if 'forearm_twist' in pbone.name:
            sep_len = 2 if not "_dupli_" in pbone.name else 4 
            
            if len(pbone.name.split('_')) == sep_len:
                pbone.name = pbone.name.replace('forearm_twist', 'lowerarm_twist_01')
            elif len(pbone.name.split('_')) > sep_len:# multiple twist bones
                twist_idx = get_twist_idx(pbone.name)
                str_i = '%02d' % twist_idx
                pbone.name = pbone.name.replace('forearm_twist_'+str(twist_idx), 'lowerarm_twist_'+str_i)         
                    
        if 'forearm_inter' in pbone.name:
            pbone.name = pbone.name.replace('forearm_inter', 'lowerarm_inter')
        if 'index1' in pbone.name:#pinky_metacarpal_l
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_index1_base', 'index_metacarpal')
            else:
                pbone.name = pbone.name.replace('c_index1', 'index_01')
            
        if 'index2' in pbone.name:            
            pbone.name = pbone.name.replace('c_index2', 'index_02')
        if 'index3' in pbone.name:
            pbone.name = pbone.name.replace('c_index3', 'index_03')
        if 'middle1' in pbone.name:
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_middle1_base', 'middle_metacarpal')
            else:
                pbone.name = pbone.name.replace('c_middle1', 'middle_01')
                
        if 'middle2' in pbone.name:
            pbone.name = pbone.name.replace('c_middle2', 'middle_02')
        if 'middle3' in pbone.name:
            pbone.name = pbone.name.replace('c_middle3', 'middle_03')
        if 'ring1' in pbone.name:
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_ring1_base', 'ring_metacarpal')
            else:
                pbone.name = pbone.name.replace('c_ring1', 'ring_01')
                
        if 'ring2' in pbone.name:
            pbone.name = pbone.name.replace('c_ring2', 'ring_02')
        if 'ring3' in pbone.name:
            pbone.name = pbone.name.replace('c_ring3', 'ring_03')
        if 'pinky1' in pbone.name:
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_pinky1_base', 'pinky_metacarpal')
            else:
                pbone.name = pbone.name.replace('c_pinky1', 'pinky_01')
                
        if 'pinky2' in pbone.name:
            pbone.name = pbone.name.replace('c_pinky2', 'pinky_02')
        if 'pinky3' in pbone.name:
            pbone.name = pbone.name.replace('c_pinky3', 'pinky_03')
        if 'thumb1' in pbone.name:
            pbone.name = pbone.name.replace('c_thumb1', 'thumb_01')
        if 'thumb2' in pbone.name:
            pbone.name = pbone.name.replace('c_thumb2', 'thumb_02')
        if 'thumb3' in pbone.name:
            pbone.name = pbone.name.replace('c_thumb3', 'thumb_03')
            
        if 'neck' in pbone.name and not 'c_neck_01.x' in pbone.name and not "subneck" in pbone.name:
            if last_subneck == None:
                pbone.name = 'neck_01'
            else:
                neck_id = '%02d' % (last_id + 1)
                pbone.name = 'neck_' + neck_id
        if pbone.name.startswith("c_subneck_"):
            id = pbone.name.split('_')[2]
            id = id.split('.')
            if len(id) > 1:
                id = id[0]
            id = int(id)
            id = '%02d' % id
            pbone.name = "neck_" + id

        if pbone.name in spine_bones_list:
            idx = spine_bones_list.index(pbone.name)+1
            str_idx = '%02d' % idx
            pbone.name = "spine_"+str_idx

        if 'head' in pbone.name:
            pbone.name = 'head'
        if 'root' in pbone.name:
            pbone.name = 'pelvis'

        # rename sides
        if pbone.name.endswith(".l"):
            pbone.name = pbone.name[:-2] + "_l"
        if pbone.name.endswith(".r"):
            pbone.name = pbone.name[:-2] + "_r"

    # restore the rig_fist action data path
    if len(actions_fist) > 0:
        for action in actions_fist:

            if not check_id_root(action):
                continue

            print("  restoring rig fist action data path...", action.name)
            for i, fc in enumerate(action.fcurves):
                fc.data_path = actions_fist[action][i]

        print("  restored.")


def rename_for_godot():

    print('\nRename for Godot')

    # save the rig_fist data paths, since it's being renamed as well by blender automatically by mistake(c_ring1 > ring1)
    actions_fist = {}

    for action in bpy.data.actions:

        if not check_id_root(action):
            continue

        if 'rig_fist' in action.name:
            print('  saving rig fist action data path...', action.name)
            fc_list = [fc.data_path for fc in action.fcurves]
            actions_fist[action] = fc_list


    rig_humanoid = get_object('rig_humanoid')

    # collect subnecks
    last_subneck = None
    last_id = 0
    for bone in rig_humanoid.data.bones:
        if not bone.name.startswith('c_subneck_'):
            continue
        id = bone.name.split('_')[2]
        id = id.split('.')
        if len(id) > 1:
            id = id[0]
        id = int(id)
        if id > last_id:
            last_id = id
            last_subneck = bone.name

    # collect spines
    spine_bones_list = []
    for idx in range(1, 33):
        str_idx = '%02d' % idx
        spine_bones_list.append("spine_"+str_idx+".x")

    for pbone in rig_humanoid.pose.bones:
        # exclude secondary bones, custom controllers, helpers, from renaming
        if is_bend_bone(pbone.name) or is_custom_bone(pbone.name) or 'arp_ge_helper' in pbone.bone.keys():
            continue

        side_pre = ''        
        if pbone.name.endswith('.r'):
            side_pre = 'Right'
        elif pbone.name.endswith('.l'):
            side_pre = 'Left'   
        
        if pbone.name.startswith('thigh_stretch'):
            pbone.name = pbone.name.replace('thigh_stretch', 'UpperLeg')
        elif pbone.name.startswith('thigh_twist'):
            if len(pbone.name.split('_')) == 2:
                pbone.name = pbone.name.replace('thigh_twist', 'UpperLeg_twist_01')#thigh_twist.l thigh_twist_02.l
            elif len(pbone.name.split('_')) > 2:# multiple twist bones
                pbone.name = pbone.name.replace('thigh_twist_', 'UpperLeg_twist_0')
        elif pbone.name.startswith('leg_stretch'):           
            pbone.name = pbone.name.replace('leg_stretch', 'LowerLeg')
        elif pbone.name.startswith('leg_twist'):  
            if len(pbone.name.split('_')) == 2:
                pbone.name = pbone.name.replace('leg_twist', 'LowerLeg_twist_01')
            elif len(pbone.name.split('_')) > 2:# multiple twist bones
                pbone.name = pbone.name.replace('leg_twist_', 'LowerLeg_twist_0')
        elif pbone.name.startswith('foot'):
            pbone.name = pbone.name.replace('foot', 'Foot')
        elif pbone.name.startswith('toes_01'):
            pbone.name = pbone.name.replace('toes_01', 'Toes')
            
            
        elif pbone.name.startswith('shoulder'):
            pbone.name = pbone.name.replace('shoulder','Shoulder')
        elif pbone.name.startswith('arm_stretch'):
            pbone.name = pbone.name.replace('arm_stretch', 'UpperArm')
        elif pbone.name.startswith('arm_twist'):
            if len(pbone.name.split('_')) == 2:
                pbone.name = pbone.name.replace('arm_twist', 'UpperArm_twist_01')
            elif len(pbone.name.split('_')) > 2:# multiple twist bones
                pbone.name = pbone.name.replace('arm_twist_', 'UpperArm_twist_0')
        elif pbone.name.startswith('forearm_stretch'):
            pbone.name = pbone.name.replace('forearm_stretch', 'LowerArm')
        elif pbone.name.startswith('forearm_twist'):
            if len(pbone.name.split('_')) == 2:
                pbone.name = pbone.name.replace('forearm_twist', 'LowerArm_twist_01')
            elif len(pbone.name.split('_')) > 2:# multiple twist bones
                pbone.name = pbone.name.replace('forearm_twist_', 'LowerArm_twist_0')
        elif 'forearm_inter' in pbone.name:
            pbone.name = pbone.name.replace('forearm_inter', 'LowerArm_inter')
        elif pbone.name.startswith('hand'):
            pbone.name = pbone.name.replace('hand', 'Hand')
            
         
        # index
        elif pbone.name.startswith('c_index1'):
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_index1_base', 'IndexMetacarpal')
            else:
                pbone.name = pbone.name.replace('c_index1', 'IndexProximal')            
        elif pbone.name.startswith('c_index2'):            
            pbone.name = pbone.name.replace('c_index2', 'IndexIntermediate')
        elif pbone.name.startswith('c_index3'):   
            pbone.name = pbone.name.replace('c_index3', 'IndexDistal')
            
        # middle
        elif pbone.name.startswith('c_middle1'):
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_middle1_base', 'MiddleMetacarpal')
            else:
                pbone.name = pbone.name.replace('c_middle1', 'MiddleProximal')            
        elif pbone.name.startswith('c_middle2'):            
            pbone.name = pbone.name.replace('c_middle2', 'MiddleIntermediate')
        elif pbone.name.startswith('c_middle3'):   
            pbone.name = pbone.name.replace('c_middle3', 'MiddleDistal')
            
        # ring
        elif pbone.name.startswith('c_ring1'):
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_ring1_base', 'RingMetacarpal')
            else:
                pbone.name = pbone.name.replace('c_ring1', 'RingProximal')            
        elif pbone.name.startswith('c_ring2'):            
            pbone.name = pbone.name.replace('c_ring2', 'RingIntermediate')
        elif pbone.name.startswith('c_ring3'):   
            pbone.name = pbone.name.replace('c_ring3', 'RingDistal')
            
        # pinky
        elif pbone.name.startswith('c_pinky1'):
            if '_base' in pbone.name:
                pbone.name = pbone.name.replace('c_pinky1_base', 'LittleMetacarpal')
            else:
                pbone.name = pbone.name.replace('c_pinky1', 'LittleProximal')            
        elif pbone.name.startswith('c_pinky2'):            
            pbone.name = pbone.name.replace('c_pinky2', 'LittleIntermediate')
        elif pbone.name.startswith('c_pinky3'):   
            pbone.name = pbone.name.replace('c_pinky3', 'LittleDistal')
      
        # thumb
        elif 'thumb1' in pbone.name:
            pbone.name = pbone.name.replace('c_thumb1', 'ThumbMetacarpal')
        elif 'thumb2' in pbone.name:
            pbone.name = pbone.name.replace('c_thumb2', 'ThumbProximal')
        elif 'thumb3' in pbone.name:
            pbone.name = pbone.name.replace('c_thumb3', 'ThumbDistal')
            
        elif 'neck' in pbone.name and not 'c_neck_01.x' in pbone.name and not 'subneck' in pbone.name:
            if last_subneck == None:
                pbone.name = 'Neck'
            else:
                neck_id = '%02d' % (last_id + 1)
                pbone.name = 'Neck_' + neck_id
        elif pbone.name.startswith('c_subneck_'):
            id = pbone.name.split('_')[2]
            id = id.split('.')
            if len(id) > 1:
                id = id[0]
            id = int(id)
            id = '%02d' % id
            pbone.name = 'Neck_' + id

        elif pbone.name in spine_bones_list:
            idx = spine_bones_list.index(pbone.name)+1
            
            if idx == 1:
                pbone.name = 'Spine'
            elif idx == 2:
                pbone.name = 'Chest'
            elif idx == 3:
                pbone.name = 'UpperChest'
            else:
                str_idx = '%02d' % idx
                pbone.name = "Spine_"+str_idx

        elif 'head' in pbone.name:
            pbone.name = 'Head'
        elif 'root' in pbone.name:
            pbone.name = 'Hips'
        elif 'c_traj' in pbone.name:
            pbone.name = 'Root'

        # rename sides
        if pbone.name.endswith('.l') or pbone.name.endswith('.r') or pbone.name.endswith('.x'):
            pbone.name = side_pre+pbone.name[:-2]
        

    # restore the rig_fist action data path
    if len(actions_fist) > 0:
        for action in actions_fist:

            if not check_id_root(action):
                continue

            print("  restoring rig fist action data path...", action.name)
            for i, fc in enumerate(action.fcurves):
                fc.data_path = actions_fist[action][i]

        print("  restored.")
        
        
###########  UI PANEL  ###################

class ARP_PT_auto_rig_GE_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ARP"
    bl_label = "Auto-Rig Pro: Export"
    bl_idname = "ARP_PT_auto_rig_ge"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):

        layout = self.layout
        object = context.active_object
        scn = context.scene
        global custom_icons
        
        # non exportable rig if locked (Quick Rig preserve mode)
        if object:
            if object.type == "ARMATURE":
                if 'arp_locked' in object.data.keys():
                    if object.data['arp_locked'] == True:
                        col = layout.column(align=True)
                        col.label(text='Locked rig',  icon='LOCKED')
                        col.label(text='Rig not exportable with Auto-Rig Pro')
                        return

        #BUTTONS
        
        # help
        if bpy.context.preferences.addons[__package__.split('.')[0]].preferences.beginner_mode:
            row = layout.column().row(align=True).split(factor=0.9)        
            row.label(text="")
            but = row.operator("arp.open_link_internet", text='', icon_value=custom_icons['question'].icon_id)
            but.link_string = "http://lucky3d.fr/auto-rig-pro/doc/ge_export_doc.html"
        
        
        col = layout.column(align=True)
        if '2.80' in blender_version:
            icon_check = 'CHECKBOX_HLT'
        else:
            icon_check = 'CHECKMARK'
        col.operator("arp.check_rig_export", text="Check Rig", icon=icon_check)
        col.operator("arp.fix_rig_export", text="Fix Rig")
        
        layout.prop(scn, "arp_show_ge_advanced", text="Show Advanced")
        
        col = layout.column(align=True)
        row = col.row(align=True).split(factor=0.75, align=True)
        row.operator("arp.set_custom_bones", text="Set Custom Bones")
        row.operator("arp.unset_custom_bones", text="Unset")
        
        if scn.arp_show_ge_advanced:
            row = col.row(align=True).split(factor=0.75, align=True)
            row.operator("arp.set_softlink_bones", text="Set Soft-Link Bones")
            row.operator("arp.unset_softlink_bones", text="Unset")
            
            row = col.row(align=True).split(factor=0.75, align=True)
            row.operator("arp.set_const_bones", text="Set Const. Bones")
            row.operator("arp.unset_const_bones", text="Unset")
        
        col.label(text='Rename Bones from File:')
        col.prop(scn, 'arp_rename_fp', text='')
        
        if scn.arp_show_ge_advanced:
            col.label(text='Custom Export Script:')
            col.prop(scn, 'arp_custom_export_script', text='')
        
        col = layout.column()
        col.operator('arp.show_retro_options_ge', text="Legacy...", icon='SETTINGS')
        layout.separator()

        col = layout.column()
        col.operator(ARP_OT_GE_export_fbx_panel.bl_idname, text="Export FBX...", icon_value=custom_icons['export'].icon_id)        
        col.operator(ARP_OT_GE_export_gltf_panel.bl_idname, text="Export GLTF...", icon_value=custom_icons['export'].icon_id)
        col.scale_y = 1.2
        layout.separator()
        layout.prop(scn, "arp_show_ge_debug")

        if scn.arp_show_ge_debug:
            col = layout.column(align=True)
            col.label(text="Warning, breaks Auto-Rig Pro edit")
            col.label(text="and export tools, use with care")

            if object:
                if 'arp_export_rig_set' in object.keys():
                    col.operator("id.unset_export_rig", text="Unset Export Rig", icon='X')
                else:
                    col.operator("id.set_humanoid_rig", text="Set Humanoid Rig")
                    col.operator("id.set_mped_rig", text="Set Universal Rig")
            layout.separator()
        
            
def show_action_row_manager(_col, _act_name):
    row2 = _col.row(align=True)    
    icon_name = 'CHECKBOX_HLT'
    act = bpy.data.actions.get(_act_name)
    
    if bpy.app.version >= (3,5,0):  
        row2.prop(act, '["arp_export"]', text='')
    else:        
        if len(act.keys()) > 0:
            if "arp_export" in act.keys():
                if act["arp_export"] == False:
                    icon_name = 'CHECKBOX_DEHLT'
        
        op1 = row2.operator('arp.toggle_action', text='', icon=icon_name)
        op1.action_name = _act_name
    
    op = row2.operator('arp.actions_list_remove_action', text='', icon = 'REMOVE')
    op.action_name = _act_name
    row2.label(text=' '+_act_name)


def show_action_row(_col, _act_name):
    row2 = _col.row(align=True)    
    icon_name = 'CHECKBOX_HLT'
    act = bpy.data.actions.get(_act_name)
    
    if bpy.app.version >= (3,5,0):
        row2.prop(act, '["arp_export"]', text='')
    else:# cannot display the int props as bools in older Blender version    
        if len(act.keys()) > 0:
            if 'arp_export' in act.keys():
                if act['arp_export'] == False:
                    icon_name = 'CHECKBOX_DEHLT'    
    
        op1 = row2.operator('arp.toggle_action', text='', icon=icon_name)
        op1.action_name = _act_name
        
    op = row2.operator('arp.delete_action', text='', icon = 'X')
    op.action_name = _act_name
    row2.label(text=' '+_act_name)


def is_arp_armature(obj):
    if obj.type == "ARMATURE":
        if obj.data.bones.get("c_traj"):
            return True
    return False
    
    
def export_panel_invoke(self, context, event):
    scn = context.scene
    
    if bpy.app.version >= (3,5,0):
        # tag actions with boolean 'arp_export' prop
        for act in bpy.data.actions:
            # the prop type was set to int in previous Blender version
            # instead of bool, convert it by removing when adding new
            val = False
            if 'arp_export' in act.keys():
                if act['arp_export'] == 1:
                    val = True
                del act['arp_export']
                
            if not 'arp_export' in act.keys():
                act['arp_export'] = val
            
            
    # Check if the armature is selected
    for obj in context.selected_objects:
        if obj.type == "ARMATURE":
            self.rig = obj

    if self.rig == None:
        # maybe the object is active but not stored in 'selected_objects', weirdly
        if bpy.context.active_object:
            if bpy.context.active_object.type == "ARMATURE":
                self.rig = bpy.context.active_object

    if self.rig == None:
        self.report({'ERROR'}, "Select the armature")
        return {'FINISHED'}
    

    self.is_arp_armature = is_arp_armature(self.rig)

    # force Universal export for non ARP armatures
    if not self.is_arp_armature:
        scn.arp_export_rig_type = 'UNIVERSAL'
        scn.arp_ue_root_motion = False
        
        # check custom bones of non ARP armatures
        found_custom = False
        for b in self.rig.data.bones:
            if b.name.startswith('cc_') or 'cc' in b.keys():
                found_custom = True
        if found_custom == False:
            self.report({'ERROR'}, "No custom bones were found on this armature.\nAt least one custom bone must be set for export")
            return {'FINISHED'}
    
    if scn.arp_ge_fp == '':# default file path
        self.filepath = bpy.path.basename(bpy.context.blend_data.filepath)[:-6] + self.filename_ext
    else:# restore file path from previous export
        self.filepath = scn.arp_ge_fp
        
            
    context.window_manager.fileselect_add(self)

    return {'RUNNING_MODAL'}
    
    
def export_panel_draw(self, context):
    layout = self.layout
    object = context.active_object
    scn = context.scene    
    rig = self.rig

    def anim_export_ui():
        box = layout.box()
        col = box.column(align=False)
        col.prop(scn, "arp_bake_anim")

        if scn.arp_bake_anim == False:
            return

        col.prop(scn, 'arp_bake_type')

        if scn.arp_bake_type == 'ACTIONS':
            #if self.export_format == 'FBX':
            col.prop(scn, 'arp_export_separate_fbx', text='As Multiple '+self.export_format+' Files')
            if scn.arp_export_separate_fbx:
                row = col.row(align=True).split(factor=0.4)
                row.label(text="File Names:")
                row.prop(scn, "arp_export_file_separator", text="")
        
        if self.export_format == 'GLTF':
            col.prop(scn, 'arp_ge_gltf_sample_anim')
            
        col = box.column(align=True)
        
     
        row = col.row(align=True).split(factor=0.4)
        row.label(text="Frame Range:")
        row.prop(scn, "arp_frame_range_type", text="")
        if scn.arp_frame_range_type == "CUSTOM":
            row = col.row(align=True)
            row.prop(scn, "arp_export_start_frame")
            row.prop(scn, "arp_export_end_frame")
        elif scn.arp_frame_range_type == "SCENE":
            row = col.row(align=True)
            row.label(text='Start: '+str(scn.frame_start)+' End: '+str(scn.frame_end))
                
        if self.export_format == 'FBX':
            col.separator()

            row = col.row(align=True).split(factor=0.4)
            row.label(text="Action Names:")
            row.prop(scn, "arp_export_act_name", text="")

            col = box.column(align=True)
            col.prop(scn, "arp_simplify_fac")
            col.prop(scn, 'arp_ge_bake_sample')
            col.prop(scn, 'arp_ge_startend_keying')

        if scn.arp_bake_type == 'NLA':
            return

        col.separator()
        col.prop(scn, 'arp_export_use_actlist', text='Actions Manager')

        if scn.arp_export_use_actlist:
            row = layout.row(align=True)
            row.template_list("ARP_UL_actions_list", "", scn, "arp_export_actlist", scn, "arp_export_actlist_idx", rows=5)
            col = row.column(align=True)
            col.operator(ARP_OT_actions_list_add.bl_idname, text="", icon="ADD")
            col.operator(ARP_OT_actions_list_remove.bl_idname, text="", icon="REMOVE")
            col.separator()
            col.separator()
            col.separator()
            col.separator()
            col.separator()
            col.separator()
            col.operator(ARP_OT_actions_list_move.bl_idname, text="", icon="TRIA_UP").direction = 'UP'
            col.operator(ARP_OT_actions_list_move.bl_idname, text="", icon="TRIA_DOWN").direction = 'DOWN'

            if len(scn.arp_export_actlist):
                col = layout.column(align=True)
                col.prop_search(scn.arp_export_actlist[scn.arp_export_actlist_idx], "action_to_add", bpy.data, "actions", text="")
                col.operator(ARP_OT_actions_list_add_action.bl_idname, text='Add Action', icon='PLUS')

                current_actlist = scn.arp_export_actlist[scn.arp_export_actlist_idx]

                if len(current_actlist.actions):
                    col.separator() 
                    list = [i.action.name for i in current_actlist.actions if i.action]
                    list.sort()# sort alphabetically
                    for act_name in list:      
                        show_action_row_manager(col, act_name)

        else:
            row = col.row(align=True)
            row.prop(scn, "arp_bake_only_active")

            row = col.row(align=True)
            row.prop(scn, "arp_only_containing", text="Only Containing:")

            row1 = row.row()
            row1.enabled = scn.arp_only_containing
            row1.prop(scn, "arp_export_name_string", text="")
            row.prop(scn, "arp_see_actions", text="", icon="HIDE_OFF")

            # show actions list
            if scn.arp_see_actions:
                if len(bpy.data.actions) > 0:
                    found_one_act = False
                    for act in bpy.data.actions:

                        if not check_id_root(act):
                            continue

                        show_it = True

                        if scn.arp_bake_only_active:# only the active action
                            if rig.animation_data == None:
                                col.label(text="No active action")
                                break

                            else:
                                if rig.animation_data.action == None:
                                    col.label(text="No active action")
                                    break
                                elif act != rig.animation_data.action:
                                    show_it = False

                        if scn.arp_only_containing:
                            if not scn.arp_export_name_string in act.name:
                                show_it = False

                        if show_it:
                            show_action_row(col, act.name)
                            found_one_act = True

                    if found_one_act == False:
                        col.label(text="No actions to export")

                else:
                    col.label(text="No actions to export")

    
    # Presets 
    row = layout.row(align=True)
    txt_label = 'Choose a preset...' if len(ARP_MT_ge_import_preset_menu.custom_presets) else 'No presets yet'
    row.menu('ARP_MT_ge_import_preset_menu', text=txt_label)
    row.operator('arp.ge_save_preset', text='', icon='ADD')
    row.operator('arp.ge_remove_preset', text='', icon='REMOVE')
    
    layout.separator()

    col = layout.column(align=True)
    if self.export_format == 'GLTF':
        col.prop(scn, 'arp_ge_gltf_format')
        col.separator()
        
    if self.is_arp_armature:
        row = col.row(align=True)
        row.prop(scn, 'arp_engine_type', text='')

        row = col.row(align=True)
        row.prop(scn, 'arp_export_rig_type', expand=True)

        col.separator()
        if '2.80' in blender_version:
            icon_check = 'CHECKBOX_HLT'
        else:
            icon_check = 'CHECKMARK'
        col.operator("arp.check_rig_export", text="Check Rig", icon=icon_check)
        col.operator("arp.fix_rig_export", text="Fix Rig")

    col.separator()
    row = col.row(align=True)
    row.prop(scn, 'arp_export_show_panels', expand=True)

    if scn.arp_export_show_panels == 'RIG':
        col.separator()
        col.prop(scn, 'arp_ge_sel_only')
        col.prop(scn, 'arp_ge_sel_bones_only')
        box = layout.box()
        
        box.label(text='Rig Definition:')
        
        col = box.column(align=True)
        if self.is_arp_armature:
            row = col.row(align=True)
            row.prop(scn, 'arp_keep_bend_bones')
            row1 = row.row()
            if scn.arp_keep_bend_bones:
                row1.enabled = True
            else:
                row1.enabled = False

            row1.prop(scn, 'arp_push_bend')

            row = col.row(align=True)
            if scn.arp_export_rig_type == 'HUMANOID':
                row.prop(scn, 'arp_full_facial')
            row.prop(scn, 'arp_export_twist')
            col = box.column(align=True)
            row = col.row(align=True)
            if not scn.arp_export_twist:
                row.enabled = False
            else:
                row.enabled = True
            
            row.prop(scn, "arp_twist_fac", slider=True)
            
            col = box.column(align=True)
            if scn.arp_export_rig_type == 'HUMANOID' and scn.arp_engine_type == 'OTHERS':
                col.prop(scn, 'arp_ge_export_metacarp')
            col.prop(scn, 'arp_ge_master_traj', text='Export Root Bone (c_traj)')
            
        col.prop(scn, 'arp_export_noparent', text='No Parents (allow animated stretch)')
        
        col.prop(scn, 'arp_export_renaming', text='Rename Bones from File')                
        row = col.row(align=True).split(factor=0.3)
        row.label(text='Rig Name:')            
        row.prop(scn, 'arp_export_rig_name', text='')                                           
        
        box = layout.box()
        box.label(text="Units:")
        col = box.column(align=True)            
        col_sub = col.column()
        
        if self.export_format == 'FBX':
            if scn.arp_engine_type == 'UNITY':
                col.prop(scn, 'arp_export_bake_axis_convert')
            col_sub.prop(scn, "arp_units_x100")
            col_sub.enabled = not scn.arp_export_bake_axis_convert
        elif self.export_format == 'GLTF':
            col_sub.prop(scn, 'arp_ge_gltf_unitsx100')
        
        if scn.arp_export_rig_type == 'HUMANOID' or (scn.arp_export_rig_type == 'UNIVERSAL' and self.is_arp_armature):
            box = layout.box()
            box.label(text="Root Motion:")
            col = box.column(align=True)             
            col.prop(scn, "arp_ue_root_motion")
        
        if scn.arp_engine_type == 'UNREAL' and scn.arp_export_rig_type == 'HUMANOID':
            box = layout.box()
            box.label(text="Unreal Options:")
            col = box.column(align=True)

            row = col.row(align=True)
            row.prop(scn, "arp_ue4", text="UE4 Legacy")# TODO...

            row.prop(scn, "arp_rename_for_ue")

            row = col.row(align=True)
            row.prop(scn, "arp_ue_ik")

            row1 = row.row(align=True)
            row1.enabled = scn.arp_rename_for_ue
            row1.prop(scn, "arp_mannequin_axes", text="Mannequin Axes")

            row = col.row(align=True)
            row.enabled = scn.arp_ue_ik
            row.prop(scn, "arp_ue_ik_anim", text="Anim. IK Bones")

            if scn.arp_mannequin_axes:
                if scn.arp_ue4:# old UE4 mannequin skeleton legacy
                    if rig.data.bones.get("c_spine_03.x") == None:
                        col.label(text="4 spine bones are required to match")
                        col.label(text="UE Mannequin hierarchy!")
                else:
                    missing = False
                    if rig.data.bones.get("c_spine_05.x") == None:
                        col.label(text="6 spine bones")
                        missing = True
                    if rig.data.bones.get("c_subneck_1.x") == None:
                        col.label(text="and 2 neck bones")
                        missing = True
                    
                    if missing:
                        col.label(text='are required to match the')
                        col.label(text="UE Mannequin hierarchy!")                    
                    
        if scn.arp_engine_type == 'GODOT' and scn.arp_export_rig_type == 'HUMANOID':
            box = layout.box()
            box.label(text="Godot Options:")
            col = box.column(align=True)
            col.prop(scn, "arp_rename_for_godot")            
            
    elif scn.arp_export_show_panels == "ANIM":
        anim_export_ui()

    elif scn.arp_export_show_panels == "MISC":
        layout.separator()
        col = layout.column()
        col.prop(scn, "arp_global_scale")
        
        box = layout.box()
        col = box.column(align=True)        
        col.label(text='Geometry:')
        if self.export_format == 'FBX':
            #col.label(text="Smoothing:")
            col.prop(scn, "arp_mesh_smooth_type", text='Smooth')
            col.prop(scn, "arp_use_tspace")
        elif self.export_format == 'GLTF':
            col.prop(scn, 'arp_use_tspace', text='Vertex Tangents')
            col.prop(scn, 'arp_ge_gltf_all_inf')
            col.prop(scn, 'arp_ge_gltf_sk_normals', text='Shape Keys Normals')
            col.prop(scn, 'arp_ge_gltf_sk_tangents', text='Shape Keys Tangents')
            
        
        col.separator()
        #col.label(text='Modifiers:')
        col.prop(scn, "arp_apply_mods", text="Apply Modifiers")
        col1 = col.column(align=True)
        col1.enabled = scn.arp_apply_mods
        col1.prop(scn, "arp_apply_subsurf", text="Apply Subsurf Modifiers") 
        
        if self.export_format == 'FBX':
            col1 = col.column(align=True)
            col1.separator()
            col1.prop(scn, 'arp_export_triangulate', text='Triangulate')
            row = col1.row()
            row.label(text='Vertex Colors:')
            row.prop(scn, 'arp_ge_vcol_type', text='')        
        
        if self.export_format == 'FBX':
            box = layout.box()
            col = box.column()
            col.label(text='Debug:')
            row = col.row()
            row.prop(scn, "arp_fix_fbx_rot")
            row.prop(scn, "arp_fix_fbx_matrix")

            if scn.arp_engine_type in ['UNITY', 'OTHERS'] or self.is_arp_armature == False:
                row = col.row()
                row.prop(scn, 'arp_ge_add_dummy_mesh')
                row = col.row()
                row.prop(scn, 'arp_ge_force_rest_pose_export')
        
        
        box = layout.box()
        col = box.column(align=True)
        col.label(text='Armature Axes:')
        col_sub = col.column(align=True) 
        if self.export_format == 'FBX':
            if scn.arp_engine_type == 'UNITY':
                col.prop(scn, "arp_export_bake_axis_convert", text='Bake Axis Conversion')        
            col_sub.enabled = not scn.arp_export_bake_axis_convert
            
        col_sub.prop(scn, "arp_init_fbx_rot")
        col_sub2 = col_sub.column(align=True)
        col_sub2.prop(scn, "arp_init_fbx_rot_mesh")
        col_sub2.enabled = scn.arp_init_fbx_rot
        
        col = box.column(align=True) 
        if self.export_format == 'FBX':
            col.separator()
            col.label(text="Bones Axes:")
            col.prop(scn, "arp_bone_axis_primary_export", text="Primary")
            col.prop(scn, "arp_bone_axis_secondary_export", text="Secondary")
        
        box = layout.box()
        col = box.column(align=True) 
        col.label(text='Textures:')
        col.separator()
        col.prop(scn, 'arp_export_tex', text='Embed Textures')


class ARP_OT_GE_export_fbx_panel(Operator, ExportHelper):
    """Export the rigged character in Fbx file format"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Auto-Rig Pro FBX Export'
    bl_idname = 'arp.arp_export_fbx_panel'
    
    export_format = 'FBX'
    filepath: StringProperty(subtype='FILE_PATH', default='untitled')
    filename_ext = '.fbx'
    filter_glob : StringProperty(default='*.fbx', options={'HIDDEN'})
    message_final = ''
    non_armature_actions = []
    rig = None
    is_arp_armature = True

    def invoke(self, context, event):
        return export_panel_invoke(self, context, event)
        

    def draw(self, context):
        export_panel_draw(self, context)


    def execute(self, context):
        return ARP_OT_export.execute(self, context)
        
        
class ARP_OT_GE_export_gltf_panel(Operator, ExportHelper):
    """Export the rigged character in Gltf/Glb file format\nRequires Blender 3.4 and higher"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Auto-Rig Pro GLTF Export"
    bl_idname = "arp.arp_export_gltf_panel"

    export_format = 'GLTF'
    filepath: StringProperty(subtype='FILE_PATH', default='untitled')
    filename_ext = '.glb'
    filter_glob : StringProperty(default='*.glb', options={'HIDDEN'})
    message_final = ''
    non_armature_actions = []
    rig = None
    is_arp_armature = True

    @classmethod
    def poll(cls, context):
        return bpy.app.version >= (3, 4, 0)# gltf exporter only compatible with ARP in Blender 3.4+            
    
    def invoke(self, context, event):
        return export_panel_invoke(self, context, event)
        

    def draw(self, context):
        export_panel_draw(self, context)


    def execute(self, context):
        return ARP_OT_export.execute(self, context)


##################  REGISTER  ##################

classes = (ARP_OT_toggle_action, ARP_OT_delete_action, ARP_OT_set_mped_rig, ARP_OT_set_humanoid_rig,
    ARP_OT_unset_export_rig, ARP_OT_export, ARP_OT_bind_humanoid, ARP_OT_unbind_humanoid,
    ARP_PT_auto_rig_GE_panel, ARP_OT_GE_export_fbx_panel, ARP_OT_GE_export_gltf_panel, ARP_OT_GE_check_rig, ARP_OT_GE_fix_rig,
    ARP_OT_GE_set_custom_bones, ARP_OT_GE_unset_custom_bones, ARP_OT_GE_set_softlink_bones, ARP_OT_GE_unset_softlink_bones,
    ARP_OT_GE_set_const_bones, ARP_OT_GE_unset_const_bones,
    ActionItem, ActionsList, ARP_UL_actions_list, ARP_OT_actions_list_remove, ARP_OT_actions_list_add, ARP_OT_actions_list_move,
    ARP_OT_actions_list_add_action, ARP_OT_actions_list_remove_action, ARP_OT_GE_show_retro,
    ARP_OT_ge_save_preset, ARP_OT_ge_load_preset, ARP_OT_ge_remove_preset, ARP_OT_exec_rem_export_presets, ARP_MT_ge_import_preset_menu)

def update_arp_tab():
    try:
        bpy.utils.unregister_class(ARP_PT_auto_rig_GE_panel)
    except:
        pass
    ARP_PT_auto_rig_GE_panel.bl_category = bpy.context.preferences.addons[__package__.split('.')[0]].preferences.arp_tab_name
    bpy.utils.register_class(ARP_PT_auto_rig_GE_panel)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    update_arp_tab()
    update_ge_presets()
    
    global custom_icons
    custom_icons = auto_rig.custom_icons

    bpy.types.Scene.arp_export_rig_type = EnumProperty(items=(
        ('HUMANOID', 'Humanoid', 'Humanoid rig type, simple bones hierarchy to ensure animation retargetting'),
        ('UNIVERSAL', 'Universal', 'Universal rig type, simple bones hierarchy for any creature (dog, spider...)')
        ), name = 'Unity Rig Type Export', description='Rig type to export', default='UNIVERSAL')
    bpy.types.Scene.arp_engine_type = EnumProperty(items=(        
        ('UNITY', 'Unity', 'Show settings to export to Unity engine'),
        ('UNREAL', 'Unreal Engine', 'Show settings to export to Unreal Engine'),
        ('GODOT', 'Godot', 'Show settings to export to Godot engine'),
        ('OTHERS', 'Others', 'Show universal settings to export to any engine'),
        ), name = "Game Engine Type", description="Game engine to export the character", 
        default='UNITY', update=update_engine_type)
    bpy.types.Scene.arp_ue4 = BoolProperty(name="UE4", description='Export as a humanoid for UE4', default=False)#backward-compatibility                                                                                                                                   
    bpy.types.Scene.arp_rename_for_ue = BoolProperty(name="Rename for UE", description="Rename bones according to Unreal Engine humanoid names convention", default=False)
    bpy.types.Scene.arp_rename_for_godot = BoolProperty(name="Rename for Godot", description="Rename bones according to Godot humanoid names convention", default=True)
    bpy.types.Scene.arp_export_twist = BoolProperty(name='Export Twist', description="If enabled, twist bones are exported. If disabled, they're not exported and the twist weights are transferred to the main weights.\nIf multiple twist bones are used, this is enabled automatically", default=True)
    bpy.types.Scene.arp_twist_fac = FloatProperty(name='Twist Amount', description="Influence of the twist bone, only if 1 twist bone if used. Generally 0.5 gives better results since game engines do not support dual quaternions\nIn case of multiple twist bones, this value is ignored since it's no more necessary", default = 0.5, min=0.0, max=1.0)
    bpy.types.Scene.arp_keep_bend_bones = BoolProperty(name='Advanced', description='Export secondary controllers ("_bend" bone). Useful for cartoons rigs. \nWarning, in Additive mode, it may change a little the bend bones skin weights. In Twist mode, arms and legs secondary controllers are always exported', default=False)
    bpy.types.Scene.arp_full_facial = BoolProperty(name='Full Facial', description="Include all facial bones, with skulls", default=False)
    bpy.types.Scene.arp_push_bend = BoolProperty(name='Push Additive', description="(Animated armature only) Push up the additive bend bones transforms to compensate the lower weights, since the additive armature modifier is not exported", default=True)
    bpy.types.Scene.arp_mannequin_axes = BoolProperty(name='Mannequin Axes', description="Set the bones orientation to match the Unreal mannequin orientations.\n4 spine bones recommended for best results", default=False)
    bpy.types.Scene.arp_ue_ik = BoolProperty(name='Add IK Bones', description="Add the IK bones (ik_foot_root, ik_foot_l...)", default=False)
    bpy.types.Scene.arp_ue_ik_anim = BoolProperty(name='Animated IK Bones', description="Animated IK bones: the IK bones will inherit the feet and hands motions", default=False)
    bpy.types.Scene.arp_ue_root_motion = BoolProperty(name='Root Motion', description='The "c_traj" controller animation will be baked to the root node for root motion in game engines', default=False)
    bpy.types.Scene.arp_only_containing = BoolProperty(name='Export Only Containing:', description='Export only actions with names containing the given text\ne.g. to export only actions associated to "Bob", name the actions "Bob_ActionName"' , default=False)
    bpy.types.Scene.arp_export_name_string = StringProperty(name="Text", description="Word/Text to be looked for in the actions name when exporting")
    bpy.types.Scene.arp_units_x100 = BoolProperty(name='Units x100', description='Export with a x100 unit scale factor. This ensures retargetting in Unreal Engine and the rig scale set to 1.0 in Unity', default=True)
    bpy.types.Scene.arp_bake_anim = BoolProperty(name='Bake Animations', description='If the character is animated, bake animations' , default=True)
    bpy.types.Scene.arp_bake_type = EnumProperty(items=(('ACTIONS', 'Actions', 'Bake each action as a separate animation track'), ('NLA', 'NLA', 'Bake a global animation track')), description='Bake individual actions or a global animation track', default='ACTIONS', name='Type', update=update_bake_type)
    bpy.types.Scene.arp_frame_range_type = EnumProperty(
            items=(('FULL', 'Default', 'Export all frames of the action, preserving Manual Frame Range if enabled'), 
                    ('CUSTOM', 'Custom', 'Export using given start/end frames'), 
                    ('SCENE', 'Scene', 'Export using start/end frames as set in the output tab'), 
                    ('MARKERS', 'Markers', 'Export frames within "Start" and "End" markers. Markers on Action data only.\nIf the action has no markers, all frames are exported')), 
                    name='Frame Range Type', default='FULL', update=update_bake_type)
    bpy.types.Scene.arp_export_start_frame = IntProperty(name='Start', description='Start frame' , default=0)
    bpy.types.Scene.arp_export_end_frame = IntProperty(name='End', description='End frame' , default=250)
    bpy.types.Scene.arp_bake_only_active = BoolProperty(name='Only Active', description='Only export the active action' , default=True, update=update_only_active)
    bpy.types.Scene.arp_simplify_fac = FloatProperty(name="Simplify Factor", default = 0.01, min=0.0, max=100, description="Simplify factor to compress the animation data size. Lower value = higher quality, higher file size")
    bpy.types.Scene.arp_ge_bake_sample = FloatProperty(name='Sampling Rate', default=1.0, min=0.001, max=1.0, description='Sampling rate when baking. Value below 1.0 allows subframe baking, e.g 0.1 = 10 keyframes per frame')
    bpy.types.Scene.arp_ge_startend_keying = BoolProperty(name='Force Start/End Keying', description='Always add a keyframe at start and end of actions for animated channels', default=True)
    bpy.types.Scene.arp_global_scale = FloatProperty(name="Global Scale", default = 1.0, description="Global scale applied")
    bpy.types.Scene.arp_mesh_smooth_type = EnumProperty(name="Smoothing", items=(('OFF', "Normals Only", "Export only normals instead of writing edge or face smoothing data"), ('FACE', "Face", "Write face smoothing"), ('EDGE', "Edge", "Write edge smoothing")), description="Export smoothing information (prefer 'Normals Only' option if your target importer understand split normals)",default='OFF')
    bpy.types.Scene.arp_use_tspace = BoolProperty(name="Tangent Space", default=False, description="Add binormal and tangent vectors, together with normal they form the tangent space (will only work correctly with tris/quads only meshes!)")
    bpy.types.Scene.arp_ge_vcol_type = EnumProperty(
            name="Vertex Colors",
            items=(('NONE', "None", "Do not import color attributes"),
                   ('SRGB', "sRGB", "Expect file colors in sRGB color space"),
                   ('LINEAR', "Linear", "Expect file colors in linear color space"),
                   ),
            description="Import vertex color attributes",
            default='SRGB',
            )

    bpy.types.Scene.arp_bone_axis_primary_export = EnumProperty(name="Primary Bone Axis", items=(('X', "X Axis", ""), ('Y', "Y Axis", ""),('Z', "Z Axis", ""),('-X', "-X Axis", ""),('-Y', "-Y Axis", ""),('-Z', "-Z Axis", "")),default='Y')
    bpy.types.Scene.arp_bone_axis_secondary_export = EnumProperty(name="Secondary Bone Axis", items=(('X', "X Axis", ""), ('Y', "Y Axis", ""),('Z', "Z Axis", ""),('-X', "-X Axis", ""),('-Y', "-Y Axis", ""),('-Z', "-Z Axis", "")),default='X')
    bpy.types.Scene.arp_fix_fbx_rot = BoolProperty(name='Fix Rotations', description='Add invisible jitter to the bones position and rotation to prevent rotations issues, by avoiding 180 angles between the child and parent' , default=False)
    bpy.types.Scene.arp_fix_fbx_matrix = BoolProperty(name='Fix Matrices', description='Use an alternative method to evaluate the bones matrices, to prevent shaky bones' , default=True)
    bpy.types.Scene.arp_init_fbx_rot = BoolProperty(name='Initialize Fbx Armature Rotation', description='Export armature with rotations values set to 0', default = False)#, update=update_init_rot_btn)
    bpy.types.Scene.arp_init_fbx_rot_mesh = BoolProperty(name='Initialize Fbx Meshes Rotation', description='Export meshes with rotations values set to 0', default=False)
    bpy.types.Scene.arp_export_tex = BoolProperty(name='Embed Textures', description='Embed textures in Fbx file, use copy path mode.\nMay not work if shaders are not Princpled BSDF shaders', default=True)
    bpy.types.Scene.arp_ge_sel_only = BoolProperty(name='Selected Objects Only', description='Export only selected objects, instead of exporting all skinned meshes' , default=False)
    bpy.types.Scene.arp_ge_sel_bones_only = BoolProperty(name='Selected Bones Only', description='Export only selected bones (only deforming bones must be selected)' , default=False)
    bpy.types.Scene.arp_see_actions =  BoolProperty(name='Display Actions', description='Show exported actions' , default=True)
    bpy.types.Scene.arp_show_ge_debug = BoolProperty(name="Show Extras", description="Show Game Engine export extra and debug tools", default=False)
    bpy.types.Scene.arp_show_ge_advanced = BoolProperty(name="Show Advanced", description="Show advanced settings", default=False)
    bpy.types.Scene.arp_export_noparent = BoolProperty(name="No Parent", description="Allow correct export of bones stretch/scale by exporting a flat hierarchy (no parenting).\nWarning, it breaks retargetting features in game engines since the bones hierarchy is not preserved", default=False)
    bpy.types.Scene.arp_export_show_panels = EnumProperty(name="Panel Type", items=(('RIG', "Rig", ""), ('ANIM', "Animations", ""),('MISC', "Misc", "")),default='RIG')
    bpy.types.Scene.arp_export_rig_name = StringProperty(name="Rig Name", default="root", description="Name of the exported skeleton")
    bpy.types.Scene.arp_export_act_name = EnumProperty(items=(
        ('DEFAULT', 'Default', 'Actions are exported with default naming:\nRigName|ActionName'),
        ('_', '_', 'Actions are exported with "_" as separator between the rig name and action name: \nRigName_ActionName'),
        ('-', '-', 'Actions are exported with "-" as separator between the rig name and action name: \nRigName-ActionName'),
        ('NONE', 'Only Action Name', 'Actions are exported with their base name only, without the rig name:\nActionName')),
        description='How to name exported actions', name='Actions Names')
    bpy.types.Scene.arp_export_file_separator = EnumProperty(items=
        (('_', '_', 'Files are named with "_" as separator between the file name and action name: \nFileName_ActionName'),
        ('-', '-', 'Files are named with "-" as separator between the file name and action name: \nFileName-ActionName'),
        ('@', '@', 'Files are named with "@" as separator between the file name and action name: \nFileName@ActionName'),
        ('NONE', 'Only Action Name', 'Files are named with the action name only:\nActionName')),
        description='How to name exported action files', name='File Names')
    bpy.types.Scene.arp_export_actlist = CollectionProperty(type=ActionsList, name="Actions List", description="List of actions list")
    bpy.types.Scene.arp_export_actlist_idx = IntProperty(name="List Index", default=0)
    bpy.types.Scene.arp_export_use_actlist = BoolProperty(default=False, description='Enable the actions manager, for more advanced ways to group and export actions')
    bpy.types.Scene.arp_export_separate_fbx = BoolProperty(default=False, description='If enabled, export each action as an individual Fbx file, otherwise a single Fbx file containing all actions is exported ')
    bpy.types.Scene.arp_export_renaming = BoolProperty(default=False, description='Rename exported bones from file (see filepath in the Auto-Rig Pro: Export tab)')
    bpy.types.Scene.arp_rename_fp = bpy.props.StringProperty(name='Rename Path', subtype='FILE_PATH', default='//', description='Path to the file containing new bone names. For example:\nhead.x = Head\nneck.x = Neck...\nEither an external text file, or the name of an internal Blender text file')
    bpy.types.Scene.arp_custom_export_script = bpy.props.StringProperty(name="Custom Export Script", subtype='FILE_PATH', default='//', description='Path to the custom script instructions for export')
    bpy.types.Scene.arp_apply_mods = BoolProperty(default=True, description='Apply modifiers when exporting. \nShape Keys are supported. Lots of shapes may increase export time, works only if the amount of verts remains constant for each shape')
    bpy.types.Scene.arp_apply_subsurf = BoolProperty(default=False, description='Apply the Subsurf modifier as well')
    bpy.types.Scene.arp_retro_ge_UE_twist_pos = BoolProperty(default=False, description='Old incorrect twist bones position when exporting for Unreal Engine humanoid')
    bpy.types.Scene.arp_retro_ge_frame_range = BoolProperty(default=False, description='If enabled, add one frame at the end of the action, like it used to with Blender versions before 4')
    bpy.types.Scene.arp_export_bake_axis_convert = BoolProperty(default=False, name='Bake Axis Conversion', description='Export with scale and axes settings to comply with Unity Bake Axis Conversion setting')
    bpy.types.Scene.arp_ge_add_dummy_mesh = BoolProperty(default=True, name="Add Dummy Mesh", description='Add a blank mesh object with no vertices when the skeleton only is exported, to prevent import issues.\nAutomatically enabled when exporting to UE, since skeleton without meshes cannot be imported in UE')
    bpy.types.Scene.arp_ge_force_rest_pose_export = BoolProperty(default=False, name="Force Rest Pose Export", description='Export the bind/rest pose even if only the skeleton is exported, without meshes.')
    bpy.types.Scene.arp_ge_fp = StringProperty(subtype="FILE_PATH", default='')
    bpy.types.Scene.arp_ge_gltf_format = EnumProperty(name='Format', items=(
                ('GLB', 'glTF Binary (.glb)',
                'Exports a single file, with all data packed in binary form. '
                'Most efficient and portable, but more difficult to edit later'),
                ('GLTF_SEPARATE', 'glTF Separate (.gltf + .bin + textures)',
                'Exports multiple files, with separate JSON, binary and texture data. '
                'Easiest to edit later')),
        description=('Output format and embedding options. Binary is most efficient, but JSON (embedded or separate) may be easier to edit later'), default='GLB')
    bpy.types.Scene.arp_ge_gltf_all_inf = BoolProperty(default=False, name='Include All Bones Influences', description='If disabled, will clamp the bones influence to max 4. If enabled, infinite')
    bpy.types.Scene.arp_ge_gltf_sk_normals = BoolProperty(default=True, name='Shape Key Normals', description='Export vertex normals with shape keys (morph targets)')   
    bpy.types.Scene.arp_ge_gltf_sk_tangents = BoolProperty(default=False, name='Shape Key Tangents', description='Export vertex tangents with shape keys (morph targets)')
    bpy.types.Scene.arp_ge_gltf_unitsx100 = BoolProperty(default=False, name='Units x100', description='Export with a x100 unit scale factor')
    bpy.types.Scene.arp_ge_gltf_sample_anim = BoolProperty(default=True, name='Always Sample Animations', description='Apply sampling to all animations')
    bpy.types.Scene.arp_export_triangulate = BoolProperty(default=False, name='Triangulate', description='Triangulate faces when exporting')
    bpy.types.Scene.arp_ge_master_traj = BoolProperty(default=False, name='Root Bone', description='Export the c_traj bone as root bone')
    bpy.types.Scene.arp_ge_export_metacarp = BoolProperty(default=False, name='Metacarpal Fingers', description='Export metacarpal finger bones')
    

def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.arp_export_rig_type
    del bpy.types.Scene.arp_engine_type
    del bpy.types.Scene.arp_ue4                           
    del bpy.types.Scene.arp_rename_for_ue
    del bpy.types.Scene.arp_rename_for_godot
    del bpy.types.Scene.arp_export_twist
    del bpy.types.Scene.arp_twist_fac
    del bpy.types.Scene.arp_keep_bend_bones
    del bpy.types.Scene.arp_full_facial
    del bpy.types.Scene.arp_push_bend
    del bpy.types.Scene.arp_mannequin_axes
    del bpy.types.Scene.arp_ue_ik
    del bpy.types.Scene.arp_ue_ik_anim
    del bpy.types.Scene.arp_ue_root_motion
    del bpy.types.Scene.arp_only_containing
    del bpy.types.Scene.arp_export_name_string
    del bpy.types.Scene.arp_units_x100
    del bpy.types.Scene.arp_bake_anim
    del bpy.types.Scene.arp_bake_type
    del bpy.types.Scene.arp_frame_range_type
    del bpy.types.Scene.arp_export_start_frame
    del bpy.types.Scene.arp_export_end_frame
    del bpy.types.Scene.arp_bake_only_active
    del bpy.types.Scene.arp_simplify_fac
    del bpy.types.Scene.arp_ge_bake_sample
    del bpy.types.Scene.arp_ge_startend_keying
    del bpy.types.Scene.arp_global_scale
    del bpy.types.Scene.arp_mesh_smooth_type
    del bpy.types.Scene.arp_use_tspace
    del bpy.types.Scene.arp_bone_axis_primary_export
    del bpy.types.Scene.arp_bone_axis_secondary_export
    del bpy.types.Scene.arp_fix_fbx_rot
    del bpy.types.Scene.arp_fix_fbx_matrix
    del bpy.types.Scene.arp_init_fbx_rot
    del bpy.types.Scene.arp_init_fbx_rot_mesh
    del bpy.types.Scene.arp_export_tex
    del bpy.types.Scene.arp_ge_sel_only
    del bpy.types.Scene.arp_ge_sel_bones_only
    del bpy.types.Scene.arp_see_actions
    del bpy.types.Scene.arp_show_ge_debug
    del bpy.types.Scene.arp_show_ge_advanced
    del bpy.types.Scene.arp_export_noparent
    del bpy.types.Scene.arp_export_show_panels
    del bpy.types.Scene.arp_export_rig_name
    del bpy.types.Scene.arp_export_act_name
    del bpy.types.Scene.arp_export_file_separator
    del bpy.types.Scene.arp_export_actlist
    del bpy.types.Scene.arp_export_actlist_idx
    del bpy.types.Scene.arp_export_use_actlist
    del bpy.types.Scene.arp_export_separate_fbx
    del bpy.types.Scene.arp_export_renaming
    del bpy.types.Scene.arp_rename_fp
    del bpy.types.Scene.arp_custom_export_script
    del bpy.types.Scene.arp_apply_mods
    del bpy.types.Scene.arp_apply_subsurf
    del bpy.types.Scene.arp_retro_ge_UE_twist_pos
    del bpy.types.Scene.arp_retro_ge_frame_range
    del bpy.types.Scene.arp_export_bake_axis_convert
    del bpy.types.Scene.arp_ge_add_dummy_mesh
    del bpy.types.Scene.arp_ge_force_rest_pose_export
    del bpy.types.Scene.arp_ge_fp
    del bpy.types.Scene.arp_ge_gltf_format
    del bpy.types.Scene.arp_ge_gltf_all_inf
    del bpy.types.Scene.arp_ge_gltf_sk_normals
    del bpy.types.Scene.arp_ge_gltf_sk_tangents
    del bpy.types.Scene.arp_ge_gltf_unitsx100
    del bpy.types.Scene.arp_ge_gltf_sample_anim
    del bpy.types.Scene.arp_export_triangulate
    del bpy.types.Scene.arp_ge_master_traj
    del bpy.types.Scene.arp_ge_export_metacarp
