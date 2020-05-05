#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 01:27:47 2020

@author: yitaogao
"""

import weight_sensor_engine
import target_handler
import os
import json
from pprint import pprint

class Event:
    def __init__(self, eid, start, init_w, plate_id):
        self.eid = eid
        self.start = start
        self.init_w = init_w
        self.end_w = None
        self.end = None
        self.weight_change = None
        self.plate_id = plate_id


def output_json(db_id, user, receipts, path):
    print ('=======================')
    output = {}
    output['testcase'] = db_id
    output['user'] = user
    receipts_json = []
    for id_result in receipts:
        receipt = receipts[id_result]
        receipt_json = {}
        receipt_json['target_id'] = id_result
        products = []
        for purchase in receipt:
            product = {}
            # Workaround for db error: [JD] You are correct on BASELINE-3 and BASELINE-11:
            # The following product is scanned by our scanner with an extra "0":
            if purchase == '120130':
                productID = '01201303'
            elif purchase == '120850':
                productID = '0120850'
            else:
                productID = purchase
            product['barcode'] = productID
            product['quantity'] = int(receipt[purchase])
            products.append(product)
        receipt_json['products'] = products
        receipts_json.append(receipt_json)
    output['receipts'] = receipts_json
    with open(path, 'w') as outfile:
        json.dump(output, outfile)

def generate_output(receipts,testcase):
    # Load JSON
    f = open('testcases.json')

    test_cases = json.load(f)
    userID = 'c9e6d054-65af-4b57-ae73-e5f40aad27e8'
    output_paths = []
    for test_db in test_cases:
        if testcase == test_db['name']:
            print(test_db['name'])
            dbName = test_db['name']
            dbId = test_db['uuid']
            
            # Generate output file
            path = "outputs/output-{}.json".format(dbName)
            output_paths.append(path)
            output_json(dbId, userID, receipts, path=path)
    return output_paths

def start(testcase):

    var_threshold = 100
    gondola_num = 4
    test_case_folder = os.path.join('testcases',testcase)
    
    changed_item = weight_sensor_engine.start(var_threshold, gondola_num, test_case_folder)
    touched_dict = target_handler.start(test_case_folder,changed_item)
    
    
    changed_item.sort(key=lambda obj:(obj['id'],obj['weight_change']))
    delete_index = []
    if len(changed_item) >=2:
        for i in range(1,len(changed_item)):
            if all([(changed_item[i]['id']==changed_item[i-1]['id']), 
                    (abs(changed_item[i]['event'].start-changed_item[i-1]['event'].start)<200), 
                    (abs(changed_item[i]['event'].end-changed_item[i-1]['event'].end) <200)]):
    #                ]):
                if (changed_item[i]['event'].start-changed_item[i]['event'].end)<(changed_item[i-1]['event'].start-changed_item[i-1]['event'].end):
                    delete_index.append(i-1)
                else:
                    delete_index.append(i)
    #        if all([(changed_item[i]['id']==changed_item[i-1]['id']), 
    #                changed_item[i-1]['weight_change'] < 0,
    #                changed_item[i]['weight_change'] > 0,
    #                (abs(changed_item[i-1]['weight_change']+changed_item[i]['weight_change'])/abs(changed_item[i]['weight_change']) < 0.2)]):
    #                    delete_index.append(i-1)
    #                    delete_index.append(i)
    
    changed_item.sort(key=lambda obj:(obj['id'],obj['weight_change']))
    
    
    for ele in sorted(delete_index, reverse = True):  
        del changed_item[ele] 
    
    
    ## deal with put one thing to another plate
    delete_index = []
    for idx in range(len(changed_item)):
        
        item_prob={}
        if changed_item[idx]['weight_change'] > 0:
            for idx1 in range(len(changed_item)):
                if changed_item[idx1]['weight_change'] < 0:
                    if changed_item[idx1]['id'] == changed_item[idx]['id']:
                        item_prob[changed_item[idx1]['id']]= weight_sensor_engine.pdf(
                                changed_item[idx1]['weight_change'],abs(changed_item[idx]['weight_change']),
                                abs(changed_item[idx]['weight_change'])*0.1)
                    else:
                        item_prob[changed_item[idx1]['id']]= 0.8*weight_sensor_engine.pdf(
                                changed_item[idx1]['weight_change'],abs(changed_item[idx]['weight_change']),
                                abs(changed_item[idx]['weight_change'])*0.1)
            optimum = sorted((value,key) for (key,value) in item_prob.items())[-1]
            for i in range(len(changed_item)):
                if changed_item[i]['id'] == optimum[1] and i not in delete_index:
                    delete_index.append(i)
            if idx not in delete_index:
                delete_index.append(idx)
                        
    for ele in sorted(delete_index, reverse = True):  
        del changed_item[ele]
        
    #    for item in changed:
            
    
    
        
    receipts={}
    claimed_list = []
    for item in changed_item:
        for target in touched_dict:
            if item['id'] in touched_dict[target][target]:
                if target in receipts:
                    temp = receipts[target]
                else:
                    temp = {}
                temp[item['id']] = item['quantity']
                receipts[target]=temp
                claimed_list.append(item)
                
        
    
    if len(claimed_list) != len(changed_item):
        if len(touched_dict) == 1:
            for item in changed_item:
                if item not in claimed_list:
                    if target in receipts:
                        temp = receipts[target]
                    else:
                        temp = {}
                    temp[item['id']] = item['quantity']
                    receipts[target]=temp
    
    ######## output json receipt
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    output_paths = generate_output(receipts,testcase) 
    
    
    if '__name__' == '__main__':
        start('BASELINE-1')
                        
    
                       
    