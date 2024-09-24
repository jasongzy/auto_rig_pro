# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

import os, shutil
    
bl_info = {
    "name": "Auto-Rig Pro",
    "author": "Artell",
    "version": (3, 70, 36),
    "blender": (2, 80, 0),
    "location": "3D View > Properties> Auto-Rig Pro",
    "description": "Automatic rig generation based on reference bones and various tools",
    "tracker_url": "http://lucky3d.fr/auto-rig-pro/doc/bug_report.html",    
    "doc_url": "http://lucky3d.fr/auto-rig-pro/doc/",
    "category": "Animation",
    }
    

import bpy
from bpy.app.handlers import persistent
from .src import auto_rig_prefs
from .src import rig_functions
from .src import auto_rig
from .src import auto_rig_smart
from .src import auto_rig_remap
from .src import auto_rig_ge
if bpy.app.version >= (4,1,0):
    from .src.export_fbx import arp_fbx_init
else:
    from .src.export_fbx_old import arp_fbx_init
from .src import utils
 

# gltf export specials 
class glTF2ExportUserExtension:
    
    export_action_only = ''
    
    def __init__(self):
        self.action = None

    def gather_actions_hook(self, blender_object, params, export_settings):        
        # Filter actions
        #   Only filter ARP rigs
        if not 'arp_rig_name' in blender_object:
            return
        
        act_list = []
        for act in params.blender_actions:
            if len(act.keys()):
                if "arp_baked_action" in act.keys(): 
                    if self.export_action_only == 'all_actions':
                        act_list.append(act)  
                    elif self.export_action_only == act.name:
                        act_list.append(act)
   
        params.blender_actions = act_list
        
        params.blender_tracks = {k:v for (k, v) in params.blender_tracks.items() if k in [act.name for act in params.blender_actions]}
        params.action_on_type = {k:v for (k, v) in params.action_on_type.items() if k in [act.name for act in params.blender_actions]}

    def animation_switch_loop_hook(self, blender_object, post, export_settings):

        # Before looping on actions to export
        # Store used action of original rig
        if 'arp_rig_name' in blender_object and post is False:
            original_rig = bpy.data.objects[blender_object['arp_rig_name']]
            if original_rig.animation_data and original_rig.animation_data.action:
                self.action = original_rig.animation_data.action

        # Restore initial action of the original rig
        # After looping on actions to export
        if 'arp_rig_name' in blender_object and post is True:
            original_rig = bpy.data.objects[blender_object['arp_rig_name']]
            if original_rig.animation_data:
                original_rig.animation_data.action = self.action

            self.action = None

    def post_animation_switch_hook(self, blender_object, blender_action, track_name, on_type, export_settings):

        # When switching the exported rig, also switch the original rig (same action + "_%temp")
        if 'arp_rig_name' in blender_object:
            original_rig = bpy.data.objects[blender_object['arp_rig_name']]
            if original_rig.animation_data:
                original_rig.animation_data.action = bpy.data.actions[blender_action.name + "_%temp"]
                
                
def menu_func_export(self, context):
    self.layout.operator(auto_rig_ge.ARP_OT_GE_export_fbx_panel.bl_idname, text="Auto-Rig Pro FBX (.fbx)")
    if bpy.app.version >= (3, 4, 0):
        self.layout.operator(auto_rig_ge.ARP_OT_GE_export_gltf_panel.bl_idname, text="Auto-Rig Pro GLTF (.glb/.gltf)")    
    

def cleanse_modules():
    import sys
    all_modules = sys.modules 
    all_modules = dict(sorted(all_modules.items(),key= lambda x:x[0]))
    for k in all_modules:
        if k.startswith(__name__):
            del sys.modules[k]


def register():
    auto_rig_prefs.register()
    auto_rig.register()
    auto_rig_smart.register()   
    auto_rig_remap.register()
    auto_rig_ge.register()
    rig_functions.register()
    arp_fbx_init.register()
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)   
    

def unregister():
    auto_rig_prefs.unregister()
    auto_rig.unregister()
    auto_rig_smart.unregister() 
    auto_rig_remap.unregister()
    auto_rig_ge.unregister()
    rig_functions.unregister()
    arp_fbx_init.unregister()
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)        
    cleanse_modules()
    

if __name__ == "__main__":
    register()