import bpy
from math import *
from mathutils import *
import numpy as np

def resample_curve(coords, length=1.0, amount=5, symmetrical=True):
    # resample a given set of points belonging to a curve
    # only works by reduction

    resampled_coords = []
    dist_sum = 0.0
    dist = length/amount
    for i, coord in enumerate(coords):
        # special case, since we need symmetrical positioning, 
        # the first coord must be positioned half-distance
        if len(resampled_coords) == 0 and symmetrical:
            if coord == coords[0]:
                continue
            
            p_prev = coords[i-1]
            cur_dist = (coord-p_prev).magnitude
            dist_sum += cur_dist
            
            if dist_sum >= dist/2:
                dist_sum = 0.0
                #print('resample', i)
                resampled_coords.append(coord.copy())       
            
        else:
            p_prev = coords[i-1]
            cur_dist = (coord-p_prev).magnitude    
            dist_sum += cur_dist
            
            if dist_sum < dist:
                continue
            else:
                dist_sum = 0.0
                #print('resample', i)
                resampled_coords.append(coord.copy())
    
    # In case of precision error, the last coord did not fit in. 
    # Make sure to include it
    print('resampled_coords', len(resampled_coords), 'amount', amount)
    if len(resampled_coords) == amount - 1:
        print('Curve resampling error, add last coord as tip coord')
        tip_coord = coords[len(coords)-2]
        resampled_coords.append(tip_coord)
        
        
    return resampled_coords
    

def get_curve_length(coords):
    length = 0.0
    p_last = None
    
    for coord in coords:
        if p_last == None:
            p_last = coord.copy()           
        else:
            length += (coord-p_last).magnitude
            p_last = coord.copy()         
        
    print("Nurbs length:", length)
    return length
    
    
def nurbs_basis(i, degree, u, knots):
    if degree == 0:
        return 1.0 if knots[i] <= u < knots[i + 1] else 0.0
    if knots[i + degree] == knots[i]:
        left = 0.0
    else:
        left = (u - knots[i]) / (knots[i + degree] - knots[i]) * nurbs_basis(i, degree - 1, u, knots)
    if knots[i + degree + 1] == knots[i + 1]:
        right = 0.0
    else:
        right = (knots[i + degree + 1] - u) / (knots[i + degree + 1] - knots[i + 1]) * nurbs_basis(i + 1, degree - 1, u, knots)
    return left + right


def generate_nurbs_curve(points, degree=3, num_points=100):

    if len(points) < degree + 1:
        raise ValueError("Number of points should be at least degree + 1.")

    # Convert control points to numpy array
    control_points = np.array(points)

    # Calculate the number of knots needed for a closed curve
    num_knots = len(control_points) + degree + 1

    # Create a list of equally spaced parameter values for the control points
    parameter_values = np.linspace(0, 1, len(control_points))

     # Compute the knot vector (closed curve)
    knots = np.zeros(num_knots)
    knots[degree:-degree] = np.linspace(0, 1, num_knots - 2*degree)
    knots[-degree:] = 1


    # Evaluate the NURBS curve at 'num_points' points
    u_new = np.linspace(0, 1, num_points)
    
    x = np.zeros(num_points)
    y = np.zeros(num_points)
    z = np.zeros(num_points)
    for i in range(len(u_new)):
        if i == len(u_new)-1:# the last one must be set manually, sigh
            x[i] += control_points[len(points)-1, 0]
            y[i] += control_points[len(points)-1, 1]
            z[i] += control_points[len(points)-1, 2]           
            break
        for j in range(len(control_points)):
            basis = nurbs_basis(j, degree, u_new[i], knots)
            x[i] += control_points[j, 0] * basis
            y[i] += control_points[j, 1] * basis
            z[i] += control_points[j, 2] * basis            
            
    coords = []    
    for _x, _y, _z in zip(x, y, z):
        coord = Vector((_x, _y, _z))
        coords.append(coord)

    return coords#x, y, z


def signed_angle(vector_u, vector_v, normal):
    normal = normal.normalized()
    a = vector_u.angle(vector_v)
    if vector_u.cross(vector_v).angle(normal) < 1:
        a = -a
    return a
        

def mat3_to_vec_roll(mat, ret_vec=False):
    vec = mat.col[1]
    vecmat = vec_roll_to_mat3(mat.col[1], 0)
    vecmatinv = vecmat.inverted()
    rollmat = vecmatinv @ mat
    roll = atan2(rollmat[0][2], rollmat[2][2])
    if ret_vec:
        return vec, roll
    else:
        return roll


def vec_roll_to_mat3(vec, roll):
    epsi = 1e-10
    target = Vector((0, 0.1, 0))
    nor = vec.normalized()
    axis = target.cross(nor)
    if axis.dot(axis) > epsi:
        axis.normalize()
        theta = target.angle(nor)
        bMatrix = Matrix.Rotation(theta, 3, axis)
    else:
        updown = 1 if target.dot(nor) > 0 else -1
        bMatrix = Matrix.Scale(updown, 3)
        bMatrix[2][2] = 1.0

    rMatrix = Matrix.Rotation(roll, 3, nor)
    mat = rMatrix @ bMatrix
    return mat


def align_bone_x_axis(edit_bone, new_x_axis):
    new_x_axis = new_x_axis.cross(edit_bone.y_axis)
    new_x_axis.normalize()
    dot = max(-1.0, min(1.0, edit_bone.z_axis.dot(new_x_axis)))
    angle = acos(dot)
    edit_bone.roll += angle
    dot1 = edit_bone.z_axis.dot(new_x_axis)
    edit_bone.roll -= angle * 2.0
    dot2 = edit_bone.z_axis.dot(new_x_axis)
    if dot1 > dot2:
        edit_bone.roll += angle * 2.0


def align_bone_z_axis(edit_bone, new_z_axis):
    new_z_axis = -(new_z_axis.cross(edit_bone.y_axis))
    new_z_axis.normalize()
    dot = max(-1.0, min(1.0, edit_bone.x_axis.dot(new_z_axis)))
    angle = acos(dot)
    edit_bone.roll += angle
    dot1 = edit_bone.x_axis.dot(new_z_axis)
    edit_bone.roll -= angle * 2.0
    dot2 = edit_bone.x_axis.dot(new_z_axis)
    if dot1 > dot2:
        edit_bone.roll += angle * 2.0
        

def project_point_onto_plane(q, p, n):
    # q = point
    # p = point belonging to the plane
    # n = plane normal
    n = n.normalized()
    return q - ((q - p).dot(n)) * n
    
    
def project_vec_onto_plane(x, n):
    # x: Vector
    # n: plane normal vector
    d = x.dot(n) / n.magnitude
    p = [d * n.normalized()[i] for i in range(len(n))]
    return Vector([x[i] - p[i] for i in range(len(x))])


def get_pole_angle(base_bone, ik_bone, pole_location):
    pole_normal = (ik_bone.tail - base_bone.head).cross(pole_location - base_bone.head)
    projected_pole_axis = pole_normal.cross(base_bone.tail - base_bone.head)
    return signed_angle(base_bone.x_axis, projected_pole_axis, base_bone.tail - base_bone.head)


def smooth_interpolate(value, linear=0.0):
    # value: float belonging to [0, 1]
    # return the smooth interpolated value using cosinus function
    smooth = (cos((value*pi + pi )) + 1) /2    
    return (smooth*(1-linear)) + (value*linear)
    

def round_interpolate(value, linear=0.0, repeat=1):
    # value: float belonging to [0, 1]
    # return the smooth-rounded interpolated value using cosinus function
    value = abs(value)
    base_value = value
   
    for i in range(0, repeat):
        smooth_value1 = (cos((value/2*pi + pi)) + 1)
        smooth_value2 = (cos((smooth_value1/2*pi + pi)) + 1)
        value = (smooth_value1+smooth_value2)*0.5
    
    return (value*(1-linear)) + (base_value*linear)
 

def get_point_projection_onto_line_factor(a, b, p):
    # return the factor of the projected point 'p' onto the line 'a,b'
    # if below a, factor[0] < 0
    # if above b, factor[1] < 0
    return ((p - a).dot(b - a), (p - b).dot(b - a))


def project_point_onto_line(a, b, p):
    # project the point p onto the line a,b
    ap = p - a
    ab = b - a
    result_pos = a + ap.dot(ab) / ab.dot(ab) * ab
    return result_pos


def project_vector_onto_vector(a, b):
    abdot = (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])
    blensq = (b[0] ** 2) + (b[1] ** 2) + (b[2] ** 2)

    temp = abdot / blensq
    c = Vector((b[0] * temp, b[1] * temp, b[2] * temp))

    return c


def cross(a, b):
    c = Vector((a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]))
    return c


def get_line_plane_intersection(planeNormal, planePoint, rayDirection, rayPoint, epsilon=1e-6):
    ndotu = planeNormal.dot(rayDirection)
    if abs(ndotu) < epsilon:
        raise RuntimeError("no intersection or line is within plane")

    w = rayPoint - planePoint
    si = -planeNormal.dot(w) / ndotu
    Psi = w + si @ rayDirection + planePoint
    return Psi

  
def translate_object(obj, dist, dir):
    # move an object for a given distance "dist" (float)
    # along a given direction "dir" (vector 3)
    
    obj_rot_euler = obj.rotation_euler.copy()
    obj_rot_quat = obj.rotation_quaternion.copy()
    obj_scale = obj.scale.copy()
    
    loc, rot, scale = obj.matrix_world.decompose()
    tar_loc = loc + (dir*dist)
    tar_mat = Matrix.Translation(tar_loc).to_4x4()
    obj.matrix_world = tar_mat
    # restore rot and scale
    obj.rotation_euler = obj_rot_euler
    obj.rotation_quaternion = obj_rot_quat
    obj.scale = obj_scale

  
def rotate_object(obj, angle, axis, origin):
    # rotate an object around a given axis "axis" (vector 3) 
    # for the angle value "angle" (radians)
    # around the origin point "origin" (vector 3)
    
    rot_mat = Matrix.Rotation(angle, 4, axis.normalized())
    loc, rot, scale = obj.matrix_world.decompose()
    loc = loc - origin
    obj_mat = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    obj_mat_rotated = rot_mat @ obj_mat
    loc, rot, scale = obj_mat_rotated.decompose()
    loc = loc + origin
    obj.location = loc.copy()
    obj.rotation_euler = rot.to_euler()
    
    # fix numerical imprecisions
    for i in range(0,3):
        rot = obj.rotation_euler[i]
        obj.rotation_euler[i] = round(rot, 4)
        
        
def rotate_point(point_loc, angle, axis, origin):
    # rotate the point_loc (vector 3) around the "axis" (vector 3) 
    # for the angle value (radians)
    # around the origin (vector 3)
    rot_mat = Matrix.Rotation(angle, 4, axis.normalized())
    loc = point_loc.copy()
    loc = loc - origin
    point_mat = Matrix.Translation(loc).to_4x4()
    point_mat_rotated = rot_mat @ point_mat
    loc, rot, scale = point_mat_rotated.decompose()
    loc = loc + origin
    return loc
    
    
def matrix_loc_rot(mat_full):
    # returns a loc + rot matrix from a global transformation matrix (loc, rot, scale)
    mat_loc = Matrix.Translation(mat_full.to_translation())
    mat_rot = matrix_rot(mat_full)                        
    return mat_loc @ mat_rot
    
    
def matrix_rot(mat_full):
    # return a rotation matrix only from a global transformation matrix (loc, rot, scale)
    return mat_full.to_quaternion().to_matrix().to_4x4()
    
    
def compare_mat(mat1, mat2, prec):
    for i in range(0,4):
        for j in range(0,4):
            if round(mat1[i][j], prec) != round(mat2[i][j], prec):
                return False
    return True