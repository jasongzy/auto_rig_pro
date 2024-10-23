from math import *
from mathutils import *

def vectorize3(list):
    return Vector((list[0], list[1], list[2]))


def vector_to_list(vector):
    return [i for i in vector]


def dict_to_string(dico):
    if type(dico) != dict:# custom properties in Blender 3.0 are not dict type, must be converted
        dico = dico.to_dict()
    dict_str = {}
    for i in dico:
        dict_str[str(i)] = str(dico[i])
    return dict_str


def dict_to_int(dico):    
    if type(dico) != dict:# custom properties in Blender 3.0 are not dict type, must be converted
        dico = dico.to_dict()
    dict_int = {}
    for i in dico:
        dict_int[int(i)] = int(dico[i])
    return dict_int


def str_list_to_fl_list(list):
    new_list = []
    for i in list:
        new_list.append(float(i))
    return new_list


def vec_to_string(vec):
    string_var = str(vec[0])+','+str(vec[1])+','+str(vec[2])
    return string_var


def string_to_bool(string):
    if string.lower() == 'true':
        return True
    elif string.lower() == 'false':
        return False
    else:
        return None


def clamp_max(value, max):
    if value > max:
        return max
    else:
        return value