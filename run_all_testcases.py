#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 17:48:59 2020

@author: yitaogao
"""

import run_single_test
import os

testcase_list = os.listdir('testcases')

for testcase in testcase_list:
    if testcase != ".DS_Store":
        run_single_test.start(testcase)
