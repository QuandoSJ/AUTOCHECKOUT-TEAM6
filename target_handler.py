#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 15:35:49 2020

@author: yitaogao
"""
import json_parser
import numpy as np
import os


def video_sync(file_name,plate_list_start_time):
    video_time = file_name.split('.')[-2].split('_')[-1].split('-')
    # video_time in min-sec (e.g.: 33-37)
    video_mins = int(video_time[1])
    video_secs = int(video_time[2])+10

    # weight_sensor time in min-sec (e.g.: 33-06)
    if '.' in plate_list_start_time:
        plate_time = plate_list_start_time.split('.')[-2].split(':')
    else:
        plate_time = plate_list_start_time[:-1].split(':')
    plate_mins = int(plate_time[1])
    plate_secs = int(plate_time[2])

    time_diff = (video_mins - plate_mins) * 60 + video_secs - plate_secs
    
      
    return time_diff

def get_planogram_cood(test_case_folder,planogram,plano_map):
    plano_cube_coor_list = []
    for item in planogram:
        dx = item['global_coordinates']['dim_x']
        dy = item['global_coordinates']['dim_y']
        dz = item['global_coordinates']['dim_z']
    
        x = item['global_coordinates']['transform']['translation']['x'] if 'x' in item['global_coordinates']['transform']['translation'] else float(0)
        y = item['global_coordinates']['transform']['translation']['y'] if 'y' in item['global_coordinates']['transform']['translation'] else float(0)
        z = item['global_coordinates']['transform']['translation']['z'] if 'z' in item['global_coordinates']['transform']['translation'] else float(0)
        if 'id' in item['planogram_product_id']:
            plano_cube_coor_list.append({'id':item['planogram_product_id']['id'],'x':x,'y':y,'z':z,'dimx':dx,'dimy':dy,'dimz':dz})
    return plano_cube_coor_list
    
class Rectangle(object):
    def __init__(self, xrange, yrange, zrange):
        self.xrange = xrange  # (xmin, xmax)
        self.yrange = yrange
        self.zrange = zrange

    def contains_point(self, p):
        if not all(hasattr(p, loc) for loc in 'xyz'):
            raise TypeError("Can only check if 3D points are in the rect")
        return all([self.xrange[0]/1.7 <= p.x <= self.xrange[1]*1.7,
                    p.y<0.2,
                    self.zrange[0]/1.7 <= p.z <= self.zrange[1]*1.7])
    
    def distance(self,p):
        return np.sqrt((p.x-(self.xrange[1]-self.xrange[0])/2)**2+(p.y-(self.yrange[1]-self.yrange[0])/2)**2+(p.z-(self.zrange[1]-self.zrange[0])/2)**2)
    
    @classmethod
    def from_points(cls, firstcorner, secondcorner):
        """Builds a rectangle from the bounding points

        Rectangle.from_points(Point(0, 10, -10),
                              Point(10, 20, 0)) == \
                Rectangle((0, 10), (10, 20), (-10, 0))

        This also works with sets of tuples, e.g.:
        corners = [(0, 10, -10), (10, 20, 0)]
        Rectangle.from_points(*corners) == \
                Rectangle((0, 10), (10, 20), (-10, 0))
        """
        return cls(*zip(firstcorner, secondcorner))

class Point(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __iter__(self): 
        yield from (self.x, self.y, self.z)
        
def wrist_position_matrix(full_target):
    wrist_position_all_targets = {}
    for t in full_target:
        if t['document']['targets']:
            for target in t['document']['targets']['targets']:
                if target['target_id']['id'] not in wrist_position_all_targets:
                    wrist_position_all_targets[target['target_id']['id']] = {}
                timestamp = t['timestamp']
                left_hand = t['document']['targets']['targets'][0]['l_wrist']['point']
                if left_hand:
                    left_x = left_hand['x']*0.0254
                    left_y = -left_hand['y']*0.0254
                    left_z = left_hand['z']*0.0254
            
                right_hand = t['document']['targets']['targets'][0]['r_wrist']['point']
                if right_hand:
                    right_x = right_hand['x']*0.0254
                    right_y = -right_hand['y']*0.0254
                    right_z = right_hand['z']*0.0254
                    if left_hand:
                        wrist_position_all_targets[target['target_id']['id']][timestamp] = {'left':(left_x,left_y,left_z), 'right':(right_x,right_y,right_z)}

    return wrist_position_all_targets

def start(test_case_folder,changed_item):
    planogram,plano_map = json_parser.load_planogram(os.path.join(test_case_folder,'planogram.json'))
    plates_list = json_parser.load_plates(os.path.join(test_case_folder,'plate_data.json'),plano_map)
    plates_list.sort(key=lambda obj:(obj['gondola_id'],obj['timestamp']))
    # sort time stamp
    plates_list.sort(key=lambda obj:(obj['gondola_id'],obj['timestamp']))
    video_start_time_list = json_parser.load_video_time('testcase_video_start_time.json')
    video_start_str = video_start_time_list[test_case_folder.split('/')[1]]

    
    plano_coord = get_planogram_cood(test_case_folder,planogram,plano_map)
    full_target = json_parser.load_full_targets(os.path.join(test_case_folder,'full_targets.json'))
    
    
    for idx in range(len(plates_list)):
        if video_sync(video_start_str,plates_list[idx]['date_time']['$date']) < 0:
            slice_index = idx
            break
    full_target = full_target[slice_index:]
    
    full_target = [x for x in full_target if video_sync(video_start_str,x['date_time']['$date']) < 0]
    full_target.sort(key=lambda obj:(obj['timestamp']))
    
    target_list = wrist_position_matrix(full_target)
    plano_cube_list = []
    for item in plano_coord:
        plano_cube_list.append({'id':item['id'],'rect':Rectangle.from_points(Point(item['x'],item['y'],item['z']),
                               Point(item['x']+item['dimx'],item['y']-item['dimy'],item['z']+item['dimz']))})
    distance_cube={}
    for it in changed_item:
        for cube in plano_cube_list:
            if cube['id'] == it['id']:
                distance_cube[it['id']]=cube['rect']
                
    ##unit testing
    touched_dict = {}
    distance_dict = {}
    for customer in target_list:
        distance_dict[customer]={}
        touched_customer_dict={}
        touched_customer_dict[customer]={}
        for t in target_list[customer]:
            pt_l = Point(target_list[customer][t]['left'][0],target_list[customer][t]['left'][1],target_list[customer][t]['left'][2])
            pt_r = Point(target_list[customer][t]['right'][0],target_list[customer][t]['right'][1],target_list[customer][t]['right'][2])
            for item in plano_cube_list:
                if item['rect'].contains_point(pt_l):
                    if item['id'] not in touched_customer_dict[customer]:
                        touched_customer_dict[customer][item['id']]=[t]
                    else:
                        touched_customer_dict[customer][item['id']].append(t)
                    continue
                if item['rect'].contains_point(pt_r):
                    if item['id'] not in touched_customer_dict[customer]:
                        touched_customer_dict[customer][item['id']]=[t]
                    else:
                        touched_customer_dict[customer][item['id']].append(t)
            for item1 in changed_item:
                if item1['id'] in distance_dict[customer]:
                    distance_dict[customer][item1['id']]=min(distance_dict[customer][item1['id']] , min(distance_cube[item1['id']].distance(pt_l),distance_cube[item1['id']].distance(pt_r)))
                else:
                    distance_dict[customer][item1['id']]=min(distance_cube[item1['id']].distance(pt_l),distance_cube[item1['id']].distance(pt_r))
        touched_dict[customer] = touched_customer_dict
        
    
    return touched_dict

    
#rect = Rectangle((0, 10), (10, 20), (-10, 0))
## firstpoint, secondpoint in this analogy would be:
## # (0, 10, -10), (10, 20, 0)
#inside_point = Point(3, 15, -8)
#outside_point = Point(11, 15, -8)
#
#rect.contains_point(inside_point)  # True
#rect.contains_point(outside_point)  # False