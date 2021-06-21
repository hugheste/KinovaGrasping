#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  5 14:57:24 2021

@author: orochi
"""
import time
import numpy as np
import re
import sys
import os
from pathlib import Path
sys.path.insert(0, '/home/orochi/redownload/KinovaGrasping/steph branch')
from core_classes.stats_tracker_base import *
from collections import OrderedDict


class StateMetric:
    _sim = None

    def __init__(self, data_structure):
        flag = True
        try:
            self.data = StatsTrackerArray(data_structure[0], data_structure[1])
        except TypeError:
            self.data = StatsTrackerBase(data_structure[0], data_structure[1])

        except KeyError:
            self.data = []

    def get_value(self):
        return self.data.value

    @staticmethod
    def get_xml_geom_name(keys):
        name = re.search('F\d', keys)
        name2 = re.search('((Prox)|(Dist))\d', keys)
        if name2 is None:
            if 'Obj' in keys:
                name = 'object'
            elif 'Wrist' in keys:
                name = 'palm'
        else:
            name = name.group().lower()
            name = name + '_' + name2.group()[0:4].lower()
            if '2' in name2.group():
                name = name + '_1'
        return name

    @staticmethod
    def get_rotation():
        wrist_pose = np.copy(StateMetric._sim.data.get_geom_xpos('palm'))
        Rfa = np.copy(StateMetric._sim.data.get_geom_xmat('palm'))
        temp = np.matmul(Rfa, np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]]))
        temp = np.transpose(temp)
        Tfa = np.zeros([4, 4])
        Tfa[0:3, 0:3] = temp
        Tfa[3, 3] = 1
        local_to_world = np.zeros([4, 4])
        local_to_world[0:3, 0:3] = temp
        local_to_world[3, 3] = 1
        wrist_pose = wrist_pose+np.matmul(np.transpose(local_to_world[0:3, 0:3]), [-0.009, 0.048, 0.0])
        local_to_world[0:3,3] = np.matmul(-(local_to_world[0:3, 0:3]), np.transpose(wrist_pose))
        return local_to_world


class Angle(StateMetric):
    def update(self, key): # this function finds either the joint angles or the x and z angle,
        #based on a key determined by the state group or state metric function that called it
        if 'JointState' in key:
            arr = []
            for i in range(len(StateMetric._sim.data.sensordata)-17):
                arr.append(StateMetric._sim.data.sensordata[i])
            arr[0] = -arr[0]
            arr[1] = -arr[1]
            self.data.set_value(arr)
            return self.data.value

        elif 'X,Z' in key:
            obj_pose = StateMetric._sim.data.get_geom_xpos("object")
            local_to_world = self.get_rotation()
            local_obj_pos = np.copy(obj_pose)
            local_obj_pos = np.append(local_obj_pos, 1)
            local_obj_pos = np.matmul(local_to_world, local_obj_pos)
            obj_wrist = local_obj_pos[0:3] / np.linalg.norm(local_obj_pos[0:3])
            center_line = np.array([0, 1, 0])
            z_dot = np.dot(obj_wrist[0:2], center_line[0:2])
            z_angle = np.arccos(z_dot / np.linalg.norm(obj_wrist[0:2]))
            x_dot = np.dot(obj_wrist[1:3], center_line[1:3])
            x_angle = np.arccos(x_dot / np.linalg.norm(obj_wrist[1:3]))
            self.data.set_value([x_angle, z_angle])
            return self.data.value


class Position(StateMetric):
    def update(self, keys):
        arr = []
        local_to_world = self.get_rotation()
        name = self.get_xml_geom_name(keys)
        temp = list(StateMetric._sim.data.get_geom_xpos(name))
        temp.append(1)
        temp = np.matmul(local_to_world, temp)
        arr.append(temp[0:3])
        self.data.set_value(list(arr[0]))
        return self.data.value


class Vector(StateMetric):
    def update(self, key):
        local_to_world = self.get_rotation()
        gravity = [0, 0, -1]
        self.data.set_value(np.matmul(local_to_world[0:3, 0:3], gravity))
        return self.data


class Ratio(StateMetric):
    def update(self, keylist):
        local_to_world = self.get_rotation()
        gravity = [0, 0, -1]
        gravity = np.matmul(local_to_world[0:3, 0:3], gravity)

        finger_pose = []
        local_to_world = self.get_rotation()
        for name in ["f1_prox", "f2_prox", "f3_prox", "f1_dist", "f2_dist", "f3_dist"]:
            temp = list(StateMetric._sim.data.get_geom_xpos(name))
            temp.append(1)
            temp = np.matmul(local_to_world, temp)
            finger_pose.extend(temp[0:3])

        finger_pose = np.array(finger_pose)

        s1 = finger_pose[0:3] - finger_pose[6:9]
        s2 = finger_pose[0:3] - finger_pose[3:6]
        front_area = np.linalg.norm(np.cross(s1, s2)) / 2
        top1 = np.linalg.norm(np.cross(finger_pose[0:3], finger_pose[9:12])) / 2
        top2 = np.linalg.norm(np.cross(finger_pose[9:12], finger_pose[12:15])) / 2
        top3 = np.linalg.norm(np.cross(finger_pose[3:6], finger_pose[12:15])) / 2
        top4 = np.linalg.norm(np.cross(finger_pose[6:9], finger_pose[15:18])) / 2
        top5 = np.linalg.norm(np.cross(finger_pose[9:12], finger_pose[15:18])) / 2
        total1 = top1 + top2 + top3
        total2 = top1 + top4 + top5
        top_area = max(total1, total2)

        sites = ["palm", "palm_1", "palm_2", "palm_3", "palm_4"]
        for i in range(len(sites)):
            temp = self._sim.data.get_site_xpos(sites[i])
            temp = np.append(temp, 1)
            temp = np.matmul(local_to_world, temp)
            temp = temp[0:3]

        obj_size = [0.05, 0.05, 0.05]  # THIS NEEDS TO BE FIXED
        if np.argmax(np.abs(gravity)) == 2:
            front_part = np.abs(obj_size[0] * obj_size[2]) / front_area
            top_part = np.abs(obj_size[0] * obj_size[1]) / top_area
        elif np.argmax(np.abs(gravity)) == 1:
            front_part = np.abs(obj_size[0] * obj_size[2]) / front_area
            top_part = np.abs(obj_size[1] * obj_size[2]) / top_area
        else:
            front_part = np.abs(obj_size[0] * obj_size[1]) / front_area
            top_part = np.abs(obj_size[0] * obj_size[2]) / top_area
        self.data.set_value([front_part, top_part])
        return self.data.value


class Distance(StateMetric):
    def update(self, keys):
        if 'Rangefinder' in keys:
            range_data = []
            # names=["palm","palm_top","palm_bottom","palm_left","palm_right","f1_prox","f1_prox_1","f1_dist","f1_dist_1","f2_prox","f2_prox_1","f2_dist","f2_dist_1","f3_prox","f3_prox_1","f3_dist","f3_dist_1"]
            for i in range(17):
                if StateMetric._sim.data.sensordata[i + len(StateMetric._sim.data.sensordata) - 17] == -1:
                    a = 6
                else:
                    a = StateMetric._sim.data.sensordata[i + len(StateMetric._sim.data.sensordata) - 17]
                range_data.append(a)
            self.data.set_value(range_data)
        elif 'FingerObj' in keys:
            obj = StateMetric._sim.data.get_geom_xpos("object")
            dists = []
            name = self.get_xml_geom_name(keys)
            pos = StateMetric._sim.data.get_site_xpos(name)
            dist = np.absolute(pos[0:3] - obj[0:3])
            temp = np.linalg.norm(dist)
            dists.append(temp)
            self.data.set_value(dists[0])

        elif 'Size' in keys:
            TODO fix this so that it works by using the old method
            geom_sizes = np.array(StateMetric._sim.model.geom_size)
            num_of_geoms = np.shape(geom_sizes)
            geom_poses = np.array(StateMetric._sim.data.geom_xpos)
            geom_sizes = geom_sizes[8:]
            geom_poses = geom_poses[8:]
            temp = np.copy(geom_sizes[1:, 0])
            geom_sizes[1:, 0] = np.copy(geom_sizes[1:, 2])
            geom_sizes[1:, 2] = temp
            maxes = geom_poses + geom_sizes
            mins = geom_poses - geom_sizes
            maxlist = np.max(maxes, axis=0)
            minlist = np.min(mins, axis=0)
            self.data.set_value(maxlist - minlist)
        return self.data.value


class DotProduct(StateMetric):
    def update(self, keys):
        finger_6d_pose = []
        local_to_world = self.get_rotation()
        for name in ["f1_prox", "f2_prox", "f3_prox", "f1_dist", "f2_dist", "f3_dist"]:
            temp = list(StateMetric._sim.data.get_geom_xpos(name))
            temp.append(1)
            temp = np.matmul(local_to_world, temp)
            finger_6d_pose.extend(temp[0:3])

        fingers_dot_product = []
        for i in range(6):
            fingers_dot_product.append(self._get_dot_product(finger_6d_pose[3 * i:3 * i + 3]))
        fingers_dot_product.append(self._get_dot_product())
        self.data.set_value(fingers_dot_product)
        return self.data.value

    # function to get the dot product. Only used for the pid controller
    def _get_dot_product(self, obj_state=None):
        if obj_state == None:
            obj_state = StateMetric._sim.data.get_geom_xpos('object')
        hand_pose = StateMetric._sim.data.get_body_xpos("j2s7s300_link_7")
        obj_state_x = abs(obj_state[0] - hand_pose[0])
        obj_state_y = abs(obj_state[1] - hand_pose[1])
        obj_vec = np.array([obj_state_x, obj_state_y])
        obj_vec_norm = np.linalg.norm(obj_vec)
        obj_unit_vec = obj_vec / obj_vec_norm

        center_x = abs(0.0 - hand_pose[0])
        center_y = abs(0.0 - hand_pose[1])
        center_vec = np.array([center_x, center_y])
        center_vec_norm = np.linalg.norm(center_vec)
        center_unit_vec = center_vec / center_vec_norm

        dot_prod = np.dot(obj_unit_vec, center_unit_vec)
        return dot_prod ** 20  # cuspy to get distinct reward


class StateGroup(StateMetric):
    valid_state_names = {'Position': Position, 'Distance': Distance, 'Angle': Angle, 'Ratio': Ratio, 'Vector': Vector,
                         'Dot_Product': DotProduct}

    def __init__(self, data_structure):
        super().__init__(data_structure)
        self.data = OrderedDict()
        for name, value in data_structure.items():
            state_name = name.split('_')
            try:
                self.data[name] = eval(state_name[0] + '(value)')
            except NameError:
                self.data[name] = StateGroup(value)
            except KeyError:
                print('ya done messed up a-a-ron, valid state names are', [name for name in
                                                                           StateSpace.valid_state_names.keys()])

    def update(self, keys):
        arr = []
        for name, value in self.data.items():
            temp = value.update(keys + '_' + name)
            arr.append(temp)
        return self.data

    def search_dict(self, subdict, arr=[]):
        for name, value in subdict.items():
            if type(value) is dict:
                arr = self.search_dict(subdict[name], arr)
            else:
                try:
                    arr.extend(value.get_value())
                except TypeError:
                    arr.extend([value.get_value()])
        return arr

    def get_value(self):
        return self.search_dict(self.data, [])