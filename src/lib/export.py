import bpy
from .version import *

def is_action_exportable(action):
    # check if the action is exportable to Fbx
    scn = bpy.context.scene
    
    if scn.arp_export_rig_type == 'HUMANOID' or scn.arp_export_rig_type == 'UNIVERSAL':
        if scn.arp_bake_anim and check_id_root(action):
            if len(action.keys()):
                if "arp_baked_action" in action.keys():                      
                    return True
    return False