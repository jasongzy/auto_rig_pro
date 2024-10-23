import bpy, sys, math
from .maths_geo import *
from .bone_pose import *
from .version import *
from .sys_print import *


def nla_exit_tweak():
    active_obj = bpy.context.active_object
    if active_obj.animation_data:        
        if active_obj.animation_data.use_tweak_mode:
            print('NLA is in tweak mode, disable it')            
            active_action = active_obj.animation_data.action
            active_obj.animation_data.use_tweak_mode = False
            # on exit, the active action is set to None. Bring it back
            active_obj.animation_data.action = active_action
            return True
    return False
    
    
def nla_restore_tweak(state):
    active_obj = bpy.context.active_object
    if state:
        if active_obj.animation_data:
            try:
                print('  restore tweak mode')
                if state:# the active action must be set to None if tweak mode
                    active_obj.animation_data.action = None
                # set tweak state
                active_obj.animation_data.use_tweak_mode = state                
            except:
                pass
    
    
def nla_mute(object):
    muted_tracks = []
    
    if object == None:
        return muted_tracks
        
    if object.animation_data:
        if object.animation_data.nla_tracks:
            for track in object.animation_data.nla_tracks:
                if track.mute == False:
                    track.mute = True
                    muted_tracks.append(track.name)

    return muted_tracks
    
    
def nla_unmute(object, tracks_names):
    if object == None:
        return
    
    if object.animation_data:
        if object.animation_data.nla_tracks:
            for track_name in tracks_names:
                track = object.animation_data.nla_tracks.get(track_name)
                track.mute = False
                

def clear_fcurve(fcurve):
    found = True
    while found:
        try:
            fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
        except:
            found = False


def get_keyf_data(key):
    # return keyframe point data
    return [key.co[0], key.co[1], key.handle_left[0], key.handle_left[1], key.handle_right[0], key.handle_right[1],
            key.handle_left_type, key.handle_right_type, key.easing]


def set_keyf_data(key, data):
    # set keyframe point from data (list)
    key.co[0] = data[0]
    key.co[1] = data[1]
    key.handle_left[0] = data[2]
    key.handle_left[1] = data[3]
    key.handle_right[0] = data[4]
    key.handle_right[1] = data[5]
    key.handle_left_type = data[6]
    key.handle_right_type = data[7]
    key.easing = data[8]
    

def bake_anim(frame_start=0, frame_end=10, only_selected=False, bake_bones=True, bake_object=False, 
    shape_keys=False, _self=None, action_export_name=None, new_action=True, new_action_name='Action', 
    interpolation_type='LINEAR', handle_type='DEFAULT',
    keyframes_dict=None, sampling_rate=1.0,
    support_constraints=False):
    
    scn = bpy.context.scene
    obj_data = []
    bones_data = []
    armature = bpy.data.objects.get(bpy.context.active_object.name)

    def get_bones_matrix():
        matrices_dict = {}

        for pbone in armature.pose.bones:
            if only_selected and not pbone.bone.select:
                continue

            def_matrix = None
            constraint = None
            bparent_name = ''
            parent_type = ''
            valid_constraint = True
            
            if support_constraints:# counter transform the ChildOf/Armature constraints            
                if len(pbone.constraints):
                    for c in pbone.constraints:
                        if not c.mute and c.influence > 0.5:
                            if c.type == 'CHILD_OF':
                                if c.target:
                                    #if bone
                                    if c.target.type == 'ARMATURE':
                                        bparent_name = c.subtarget
                                        parent_type = "bone"
                                        constraint = c
                                        break
                                    #if object
                                    else:
                                        bparent_name = c.target.name
                                        parent_type = "object"
                                        constraint = c
                                        break
                                        
                            elif c.type == 'ARMATURE':
                                for tar in c.targets:
                                    if tar.weight > 0.5:
                                        bparent_name = tar.subtarget
                                        parent_type = "bone"
                                        constraint = c
                                        break

                if constraint:
                    if parent_type == 'bone':
                        if bparent_name == '':
                            valid_constraint = False

            # apply constraint parent
            if constraint and valid_constraint:
                if parent_type == "bone":
                    bone_parent = get_pose_bone(bparent_name)
                    def_matrix = bone_parent.matrix_channel.inverted() @ pbone.matrix
                if parent_type == "object":
                    rig = bpy.data.objects[bparent_name]
                    def_matrix = constraint.inverse_matrix.inverted() @ rig.matrix_world.inverted() @ def_matrix.matrix
            
                # apply armature object matrix
                def_matrix = armature.convert_space(pose_bone=pbone, matrix=def_matrix, from_space="POSE", to_space="LOCAL")    
                
            else:
                def_matrix = armature.convert_space(pose_bone=pbone, matrix=pbone.matrix, from_space="POSE", to_space="LOCAL")
            
            matrices_dict[pbone.name] = def_matrix
            
        return matrices_dict
        

    def get_obj_matrix():
        parent = armature.parent
        matrix = armature.matrix_world
        if parent:
            return parent.matrix_world.inverted_safe() @ matrix
        else:
            return matrix.copy()

    # make list of meshes with valid shape keys
    sk_objects = []
    if shape_keys and _self and action_export_name:# bake shape keys value for animation export
        for ob_name in _self.char_objects:
            ob = bpy.data.objects.get(ob_name+"_arpexp")
            if ob.type != "MESH":
                continue
            if ob.data.shape_keys == None:
                continue
            if len(ob.data.shape_keys.key_blocks) <= 1:
                continue
            sk_objects.append(ob)
            
    # store matrices
    current_frame = scn.frame_current
    f = float(int(frame_start))

    while f <= int(frame_end):    
        f = round(f, 3)# round frame value because of decimals issues 
        scn.frame_set(math.floor(f), subframe=f-math.floor(f))
        bpy.context.view_layer.update()
       
        if bake_bones:
            bones_data.append((f, get_bones_matrix()))
        if bake_object:
            obj_data.append((f, get_obj_matrix()))

        # shape keys data (for animation export only)
        #print('f', f)
        for ob in sk_objects:
            for i, sk in enumerate(ob.data.shape_keys.key_blocks):
                if (sk.name == "Basis" or sk.name == "00_Basis") and i == 0:
                    continue

                frame_in_action = float(f-int(frame_start))
                frame_in_action = round(frame_in_action, 3)# round frame value because of decimals issues 

                if scn.arp_retro_ge_mesh == False:
                    obj_base = bpy.data.objects.get(ob.name.replace('_arpexp', ''))
                    obj_data_name = obj_base.data.name
                else:
                    obj_data_name = ob.data.name
                #print('Bake shape key', obj_data_name, sk.name, sk.value)
                dict_entry = action_export_name+'|'+'BMesh#'+obj_data_name+'|Shape|BShape Key#'+sk.name+'|'+str(frame_in_action)
                _self.shape_keys_data[dict_entry] = sk.value
                

        print_progress_bar("Baking phase 1", f-frame_start, frame_end-frame_start)
        f += sampling_rate
        f = round(f, 3)# round frame value because of decimals issues
        
    print("")

    # set new action
    action = None
    if new_action:
        action = bpy.data.actions.new(new_action_name)
        anim_data = armature.animation_data_create()
        anim_data.action = action
    else:
        action = armature.animation_data.action

    def store_keyframe(bone_name, prop_type, fc_array_index, frame, value):
        fc_data_path = 'pose.bones["' + bone_name + '"].' + prop_type
        fc_key = (fc_data_path, fc_array_index)
        if not keyframes.get(fc_key):
            keyframes[fc_key] = []
        keyframes[fc_key].extend((frame, value))


    # set transforms and store keyframes
    
    if bake_bones:
        bone_count = 0
        total_bone_count = len(armature.pose.bones)      
        
        for pbone in armature.pose.bones:
            bone_count += 1
            print_progress_bar("Baking phase 2", bone_count, total_bone_count)

            if only_selected and not pbone.bone.select:
                continue       

            euler_prev = None
            quat_prev = None
            keyframes = {}

            for (f, matrix) in bones_data:
                # optional, only keyframe given frames
                if keyframes_dict:
                    keyf_list = keyframes_dict[pbone.name]
                    if not f in keyf_list:
                        continue
                        
                pbone.matrix_basis = matrix[pbone.name].copy()
                
                for arr_idx, value in enumerate(pbone.location):
                    store_keyframe(pbone.name, "location", arr_idx, f, value)

                rotation_mode = pbone.rotation_mode
                if rotation_mode == 'QUATERNION':
                    if quat_prev is not None:
                        quat = pbone.rotation_quaternion.copy()
                        if bpy.app.version >= (2,82,0):# previous versions don't know this function
                            quat.make_compatible(quat_prev)
                        pbone.rotation_quaternion = quat
                        quat_prev = quat
                        del quat
                    else:
                        quat_prev = pbone.rotation_quaternion.copy()

                    for arr_idx, value in enumerate(pbone.rotation_quaternion):
                        store_keyframe(pbone.name, "rotation_quaternion", arr_idx, f, value)

                elif rotation_mode == 'AXIS_ANGLE':
                    for arr_idx, value in enumerate(pbone.rotation_axis_angle):
                        store_keyframe(pbone.name, "rotation_axis_angle", arr_idx, f, value)

                else:  # euler, XYZ, ZXY etc
                    if euler_prev is not None:                    
                        euler = pbone.matrix_basis.to_euler(pbone.rotation_mode, euler_prev)
                        pbone.rotation_euler = euler                      
                        del euler
                    
                    euler_prev = pbone.rotation_euler.copy()

                    for arr_idx, value in enumerate(pbone.rotation_euler):
                        store_keyframe(pbone.name, "rotation_euler", arr_idx, f, value)

                for arr_idx, value in enumerate(pbone.scale):
                    store_keyframe(pbone.name, "scale", arr_idx, f, value)

            # Add keyframes
            fi = 0
            for fc_key, key_values in keyframes.items():
                data_path, index = fc_key
                fcurve = action.fcurves.find(data_path=data_path, index=index)
                if new_action == False and fcurve:# for now always remove existing keyframes if overwriting current action, must be driven by constraints only
                    action.fcurves.remove(fcurve)
                    fcurve = action.fcurves.new(data_path, index=index, action_group=pbone.name)
                if fcurve == None:
                    fcurve = action.fcurves.new(data_path, index=index, action_group=pbone.name)

                # set keyframes points
                num_keys = len(key_values) // 2
                fcurve.keyframe_points.add(num_keys)
                fcurve.keyframe_points.foreach_set('co', key_values)
                
                # set interpolation type
                key_interp = interpolation_type
                if 'const_interp' in pbone.bone.keys():
                    if pbone.bone['const_interp'] == True:
                        key_interp = 'CONSTANT'
                        
                if bpy.app.version >= (2,90,0):# internal error when doing so with Blender 2.83, only for Blender 2.90 and higher
                    interp_value = bpy.types.Keyframe.bl_rna.properties['interpolation'].enum_items[key_interp].value                    
                    fcurve.keyframe_points.foreach_set('interpolation', (interp_value,) * num_keys)
                    
                    # set handle type
                    if handle_type != 'DEFAULT':
                        handle_enum_value = bpy.types.Keyframe.bl_rna.properties['handle_left_type'].enum_items[handle_type].value
                        fcurve.keyframe_points.foreach_set('handle_left_type', (handle_enum_value,) * num_keys)
                        fcurve.keyframe_points.foreach_set('handle_right_type', (handle_enum_value,) * num_keys)
                else:
                    for kf in fcurve.keyframe_points:
                        # set interpolation type (pre Blender 2.90 versions)
                        kf.interpolation = key_interp
                        
                        # set handle type (pre Blender 2.90 versions)
                        if handle_type != 'DEFAULT':
                            kf.handle_type_right = handle_type
                            kf.handle_type_left = handle_type

                fcurve.update()
                
    if bake_object:
        euler_prev = None
        quat_prev = None

        for (f, matrix) in obj_data:
            name = "Action Bake"
            armature.matrix_basis = matrix

            armature.keyframe_insert("location", index=-1, frame=f, group=name)

            rotation_mode = armature.rotation_mode
            if rotation_mode == 'QUATERNION':
                if quat_prev is not None:
                    quat = armature.rotation_quaternion.copy()
                    if bpy.app.version >= (2,82,0):# previous versions don't know this function
                        quat.make_compatible(quat_prev)
                    armature.rotation_quaternion = quat
                    quat_prev = quat
                    del quat
                else:
                    quat_prev = armature.rotation_quaternion.copy()
                armature.keyframe_insert("rotation_quaternion", index=-1, frame=f, group=name)
            elif rotation_mode == 'AXIS_ANGLE':
                armature.keyframe_insert("rotation_axis_angle", index=-1, frame=f, group=name)
            else:  # euler, XYZ, ZXY etc
                if euler_prev is not None:
                    euler = armature.rotation_euler.copy()
                    euler.make_compatible(euler_prev)
                    armature.rotation_euler = euler
                    euler_prev = euler
                    del euler
                else:
                    euler_prev = armature.rotation_euler.copy()
                armature.keyframe_insert("rotation_euler", index=-1, frame=f, group=name)

            armature.keyframe_insert("scale", index=-1, frame=f, group=name)


    # restore current frame
    scn.frame_set(current_frame)
    
    print("\n")
    
    
def get_bone_keyframes_list(pb, act):
    # return a list containing all keyframes frames of the given pose bone
    key_list = []

    # loc    
    for i in range(0,3):                            
        fc = act.fcurves.find('pose.bones["'+pb.name+'"].location', index=i)
        if fc:                                    
            for k in fc.keyframe_points:
                if not k.co[0] in key_list:
                    key_list.append(k.co[0])
              
    # rot
    _range = 3
    rot_path = 'rotation_euler'
    if pb.rotation_mode == 'QUATERNION':
        _range = 4
        rot_path = 'rotation_quaternion'
    for i in range(0,_range):# rot                                
        fc = act.fcurves.find('pose.bones["'+pb.name+'"].'+rot_path, index=i)
        if fc:                                    
            for k in fc.keyframe_points:
                if not k.co[0] in key_list:
                    key_list.append(k.co[0])
                    
        
    # scale
    for i in range(0,3):                            
        fc = act.fcurves.find('pose.bones["'+pb.name+'"].scale', index=i)
        if fc:                                    
            for k in fc.keyframe_points:
                if not k.co[0] in key_list:
                    key_list.append(k.co[0])
                    
    return key_list
    
    
def copy_shapekeys_tracks(obj1, obj2):
    # copy the NLA shape keys tracks from one object to another
    
    if obj1.data.shape_keys == None:
        return
    if obj1.data.shape_keys.animation_data == None:
        return
    
    for anim_track in obj1.data.shape_keys.animation_data.nla_tracks:    
        # copy sk tracks
        if obj2.data.shape_keys.animation_data == None:
            obj2.data.shape_keys.animation_data_create()
            
        track2 = obj2.data.shape_keys.animation_data.nla_tracks.get(anim_track.name)
        if track2 == None:
            track2 = obj2.data.shape_keys.animation_data.nla_tracks.new()
            track2.name = anim_track.name
            
        for strip in anim_track.strips:
            strip2 = track2.strips.get(strip.name)
            if strip2 == None:
                strip2 = track2.strips.new(strip.name, int(strip.frame_start), strip.action)
                for setting in ['action_frame_end', 'action_frame_start', 'blend_in', 'blend_out', 'blend_type', 'extrapolation', 'frame_end', 'frame_start', 'mute', 'repeat']:
                    setattr(strip2, setting, getattr(strip, setting))