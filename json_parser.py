#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 09:17:19 2020

@author: yitaogao
"""

import json
import base64
import numpy as np
import pandas as pd

def load_plates(plate_data_name,plano_map):
    plate_all_data = []
    with open(plate_data_name,'rb') as f:
        for jsonObj in f:
            unit = json.loads(jsonObj)
            unit['document']['plate_data']['values']['data'] = np.frombuffer(base64.b64decode(unit['document']['plate_data']['values']['data']), dtype=np.float32)
            unit['document']['plate_data']['values']['data'] = unit['document']['plate_data']['values']['data'].reshape(unit['document']['plate_data']['values']['shape'])
            plate_all_data.append(unit)
    return plate_all_data


def load_planogram(planogram_name):
    planogram = []
    plano_map = {}
    with open(planogram_name,'r') as f:
        for jsonObj in f:
            item_dict = json.loads(jsonObj)
            if 'id' in item_dict['planogram_product_id']:
                plano_map[item_dict['planogram_product_id']['id']] = [[plate['shelf_id']['gondola_id']['id'],plate['shelf_id']['shelf_index'],plate['plate_index']] for plate in item_dict['plate_ids']]
            planogram.append(item_dict)
        
    return planogram, plano_map

def load_full_targets(full_targets_name):
    full_target_list = []
    with open(full_targets_name,'r') as f:
        for jsonObj in f:
            item_dict = json.loads(jsonObj)
            full_target_list.append(item_dict)
    return full_target_list

def load_product(product_name):
    df = pd.DataFrame(columns=['id','name','weight','std'])
    with open(product_name,'r') as f:
        for jsonObj in f:
            item_dict = json.loads(jsonObj)
            if 'weight' in item_dict['metadata']:
                info = {'id':item_dict['product_id']['id'],'name':item_dict['metadata']['name'],'weight':item_dict['metadata']['weight'],'std':item_dict['metadata']['weight']*0.1}
                df = df.append(info,ignore_index=True)
    
    return df

def load_video_time(video_time_file):
    with open(video_time_file,'rb') as f:
        a = json.load(f)
    return a