'''
Author : Yi Herng Ong

'''

import numpy as np
import xml.etree.ElementTree as ET
import random

def set_obj_size(default = False):
	hand_param = {}
	hand_param["span"] = 0.175
	hand_param["depth"] = 0.08
	hand_param["height"] = 0.15 # including distance between table and hand

	geom_types = ["box", "cylinder", "sphere"]
	geom_sizes = ["s", "m", "b"]

	geom_type = random.choice(geom_types)
	geom_size = random.choice(geom_sizes)


	# Cube w: 0.1, 0.2, 0.3
	# Cylinder w: 0.1, 0.2, 0.3
	# Sphere w: 0.1, 0.2, 0.3

	# Cube & Cylinder
	width_max = hand_param["span"] * 0.30 
	width_mid = hand_param["span"] * 0.20
	width_min = hand_param["span"] * 0.10 
	width_choice = np.array([width_min, width_mid, width_max])

	height_max = hand_param["height"] * 0.80
	height_mid = hand_param["height"] * 0.66667
	height_min = hand_param["height"] * 0.50
	height_choice = np.array([height_min, height_mid, height_max])

	# Sphere
	radius_max = hand_param["span"] * 0.30
	radius_mid = hand_param["span"] * 0.28 
	radius_min = hand_param["span"] * 0.25
	radius_choice = np.array([radius_min, radius_mid, radius_max])

	if default:
		print("here")
		return "box", np.array([width_choice[1]/2.0, width_choice[1]/2.0, height_choice[1]/2.0])
	else:

		if geom_type == "box" or geom_type == "cylinder":
			if geom_size == "s":
				geom_dim = np.array([width_choice[0] / 2.0, width_choice[0] / 2.0, height_choice[0] / 2.0])
			if geom_size == "m":
				geom_dim = np.array([width_choice[1] / 2.0, width_choice[1] / 2.0, height_choice[1] / 2.0])
			if geom_size == "b":
				geom_dim = np.array([width_choice[2] / 2.0, width_choice[2] / 2.0, height_choice[2] / 2.0])

		if geom_type == "sphere":
			if geom_size == "s":
				geom_dim = np.array([radius_choice[0]])
			if geom_size == "m":
				geom_dim = np.array([radius_choice[1]])
			if geom_size == "b":
				geom_dim = np.array([radius_choice[2]])

		return geom_type, geom_dim
						
def gen_new_obj(default = False):
	file_dir = "./gym_kinova_gripper/envs/kinova_description"
	filename = "/objects.xml"
	tree = ET.parse(file_dir + filename)
	root = tree.getroot()
	d = default
	# pick a shape and size
	geom_type, geom_dim = set_obj_size(default = d)
	root.find("geom").attrib["size"] = "{} {} {}".format(geom_dim[0], geom_dim[1], geom_dim[2])
	root.find("geom").attrib["type"] = geom_type
	tree.write(file_dir + "/objects.xml")

gen_new_obj()