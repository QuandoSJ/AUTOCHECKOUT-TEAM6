#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 21:13:54 2020

@author: yitaogao
"""

import os
import numpy as np
import pandas as pd
from scipy.stats import norm
#import matplotlib.pyplot as plt
import json_parser
from datetime import datetime

class PlateId:
    """Combines gondola, shelf, and plate info to make a unique plate id"""
    def __init__(self, gondola_id, shelf_index, plate_index):
        self.gondola_id = gondola_id
        self.shelf_index=shelf_index
        self.plate_index=plate_index

class Event:
    def __init__(self, eid, start, init_w, plate_id):
        self.eid = eid
        self.start = start
        self.init_w = init_w
        self.end_w = None
        self.end = None
        self.weight_change = None
        self.plate_id = plate_id
        
def movings(arr,n,ax=0):
    arr_avg = arr.copy()
    arr_std = arr.copy()
    for i in range(n-1,arr.shape[ax]):
        temp = arr[i-n+1:i+1,:,:].copy()
        arr_avg[i,:,:] = np.sum(temp,axis = 0)/n
        temp = arr[i-n+1:i+1,:,:].copy()
        arr_std[i,:,:] = np.var(temp,axis = 0)
    return arr_avg[n-1:-1,:,:],arr_std[n-1:-1,:,:]


def predict_item(item_weight_list,distribution,plano_map,event_list_final):
    temp_dist = distribution.copy()
    changed_items = []
#    min_weight = temp_dist['weight'].min()
    for event in event_list_final:
        temp_dist['prob'] = temp_dist.apply(lambda row: pdf(abs(event.weight_change), 
                     row['weight'], row['std']),axis = 1)
        temp_dist['prob_dist'] = temp_dist.apply(lambda row: pdf_dist(event.plate_id,plano_map,row['id']),axis = 1)
        temp_dist['prob_weight'] = temp_dist.apply(lambda row:row['prob'] * row['prob_dist'],axis = 1)
        temp_dist['count'] = temp_dist.apply(lambda row:count(abs(event.weight_change),row['weight'],row['prob_dist']),axis = 1)
        temp_dist['recalc_prob'] = temp_dist.apply(lambda row:recalc_prob(abs(event.weight_change),row['count'], row['weight'], row['std'],row['prob_weight'],row['prob_dist']),axis = 1)
        if abs(event.weight_change) > 11:
            item_index = temp_dist['recalc_prob'].idxmax()
            if temp_dist.iloc[item_index,7] !=0 and temp_dist.iloc[item_index,8]>0.001:
                changed_items.append({'id':temp_dist.iloc[item_index,0],'name':temp_dist.iloc[item_index,1],
                                      'weight_change':event.weight_change,'prob':temp_dist.iloc[item_index,8],
                                      'plano_map':plano_map[temp_dist.iloc[item_index,0]],'quantity':temp_dist.iloc[item_index,7],'event':event})
    return changed_items

def timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp)

def pdf(item_weight,weight,std):
    return norm.pdf((abs(item_weight)-weight)/std)

def count(weight_change,weight,mask):
    if mask != 0:
        return int(round(weight_change / weight))
    return 0

def pdf_dist(plate_id,plano_map,idx):
    
    if idx in plano_map and [plate_id.gondola_id,plate_id.shelf_index,plate_id.plate_index] in plano_map[idx]:
        return 1
    return 0

def recalc_prob(item_weight,count,weight,std,prob_weight,mask):
    if count > 1 and mask == 1:
        return norm.pdf((abs(item_weight/count)-weight)/std)
    return prob_weight
    

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


def start(var_threshold, gondola_num, test_case_folder):        
    ## load data
    planogram,plano_map = json_parser.load_planogram(os.path.join(test_case_folder,'planogram.json'))
    plates_list = json_parser.load_plates(os.path.join(test_case_folder,'plate_data.json'),plano_map)
    
    product = json_parser.load_product(os.path.join(test_case_folder,'products.json'))
    video_start_time_list = json_parser.load_video_time('testcase_video_start_time.json')
    video_start_str = video_start_time_list[test_case_folder.split('/')[1]]

#    plate_list_start_time = plates_list[0]['date_time']['$date']

    
    # sort time stamp
    ### slicing irrelevant timestamps
    plates_list = [x for x in plates_list if video_sync(video_start_str,x['date_time']['$date']) < 0]
    plates_list.sort(key=lambda obj:(obj['gondola_id'],obj['timestamp']))
    
    

#    time_diff = video_sync(file_list,plate_list_start_time)
    
    
    final = []
    sizex_next_gonanda = plates_list[0]['document']['plate_data']['values']['shape'][1]
    sizey_next_gonanda = plates_list[1]['document']['plate_data']['values']['shape'][2]
    gondola_dimension_list = []
    gondola_dimension_list.append((sizex_next_gonanda,sizey_next_gonanda))
    for i in range(gondola_num):
        t_total = np.empty((0,sizex_next_gonanda,sizey_next_gonanda))
        for t,_ in enumerate(plates_list):
            if plates_list[t]['gondola_id'] == i+1:
                t_total = np.append(t_total,plates_list[t]['document']['plate_data']['values']['data'],axis=0)
            elif plates_list[t]['gondola_id'] > i+1:
                sizex_next_gonanda = plates_list[t]['document']['plate_data']['values']['shape'][1]
                sizey_next_gonanda = plates_list[t]['document']['plate_data']['values']['shape'][2]
                gondola_dimension_list.append((sizex_next_gonanda,sizey_next_gonanda))
                break
        final.append(t_total)

        
    for item in plano_map:
        if plano_map[item][0][0] <= 4:
            temp = final[plano_map[item][0][0]-1]
            mask = np.ones((temp.shape), dtype=bool)
            for plate in plano_map[item]:
                mask[:,plate[1],plate[2]] = False
            temp_mask = np.ma.array(temp,mask=mask).astype(float)
        #    temp_mask = np.ndarray(temp_mask)
        #    final[plano_map[item][0][0]-1][~mask] = np.sum(temp_mask,axis = 0)
            final[plano_map[item][0][0]-1][:,plano_map[item][0][1],plano_map[item][0][2]] = np.sum(temp_mask,axis = (1,2))
            for i in range(1,len(plano_map[item])):
                final[plano_map[item][0][0]-1][:,plano_map[item][i][1],plano_map[item][i][2]] = None
        
        
    #for i in range(1,331):
    #    if plates_list[i]['timestamp'] < plates_list[i-1]['timestamp']:
    #        print('wrong')
    
    ## Calculating moving average
    maList = []
    mstdList = []
    for i in range(gondola_num):
        ma_i,mstd_i = movings(final[i],90,0)
        maList.append(ma_i)
        mstdList.append(mstd_i)
    
    ## Change list: start time, end time, weight_change, gondola, shelf, plate
    event_list = []
    event_id = 1
    
    for i in range(gondola_num):
        mask = np.zeros(gondola_dimension_list[i],dtype = int) 
        for time in range(maList[i].shape[0]):
            for shelf in range(final[i].shape[1]):
                for plate in range(final[i].shape[2]):
                    if mask[shelf,plate] ==0 and mstdList[i][time,shelf,plate] > var_threshold:
                        event_list.append(Event(event_id,time,maList[i][time,shelf,plate],PlateId(i+1,shelf,plate)))
                        mask[shelf,plate] = event_id
                        event_id +=1
                        #eid, start, end, weight_change, gondola, shelf, plate_id
                    elif mask[shelf,plate] > 0 and mstdList[i][time,shelf,plate] < var_threshold:
                        tempId = mask[shelf,plate]
                        event_list[tempId-1].end = min(time + 90, maList[i].shape[0]-1)
                        event_list[tempId-1].end_w = maList[i][event_list[tempId-1].end,shelf,plate]
                        event_list[tempId-1].weight_change = event_list[tempId-1].end_w - event_list[tempId-1].init_w 
                        mask[shelf,plate] = 0
        
                       
                        
    #weight_series = np.empty((0,final[0][:,0,0].shape[0]))
    weight_series_list = []       
    event_list_final = []
    weight_change_list =[]
    for i,event in enumerate(event_list):
        if event.weight_change is not None and np.abs(event.weight_change) >10:
            temp = final[event.plate_id.gondola_id-1][:,event.plate_id.shelf_index,event.plate_id.plate_index].copy()
            weight_series_list.append(temp)
            event_list_final.append(event)
            weight_change_list.append(abs(event.weight_change))
        t_list = []
    for idx in range(len(weight_series_list)): 
        t_list.append(np.linspace(0,1/60*weight_series_list[idx].shape[0],weight_series_list[idx].shape[0]))
    
    
    
    
#    fig, axs = plt.subplots(3,1, figsize=(15, 27), facecolor='w', edgecolor='k')
#    for i in range(3):
#        #fig.subplots_adjust(hspace = .5, wspace=.001)
#        
#        axs = axs.ravel()
#        
#        
#        axs[i].plot(t_list[i], weight_series_list[i])
#        axs[i].axvline(event_list_final[i].start/60,c='g')
#        axs[i].axvline(event_list_final[i].end/60,c='r')
#        axs[i].set_xlabel(xlabel="time of Gondola:"+str(event_list_final[i].plate_id.gondola_id)+", Shelf:"+str(event_list_final[i].plate_id.shelf_index)+", Plate:"+str(event_list_final[i].plate_id.plate_index))
#        axs[i].set_ylabel(ylabel="weight/gram")
    
    
#    plt.plot(final[0][:,6,4])
#    plt.show()
    
    return predict_item(weight_change_list,product, plano_map,event_list_final)
    
    
    



