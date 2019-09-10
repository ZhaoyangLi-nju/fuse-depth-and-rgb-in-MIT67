import os
import time
from collections import OrderedDict
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn
import torchvision

import util.utils as util
from util.average_meter import AverageMeter
from util.confusion_matrix import plot_confusion_matrix
import copy
import math
from torchvision.models.resnet import resnet18
from model.networks import define_TrecgNet
from torchvision.models.resnet import *
import os
from torchvision import models

from torch.nn import init
def init_weights(net, init_type='normal', gain=0.02):
    def init_func(m):
        classname = m.__class__.__name__
        if hasattr(m, 'weight') and (classname.find('Conv') != -1 or classname.find('Linear') != -1):
            if init_type == 'normal':
                init.normal_(m.weight.data, 0.0, gain)
            elif init_type == 'xavier':
                init.xavier_normal(m.weight.data, gain=gain)
            elif init_type == 'kaiming':
                init.kaiming_normal_(m.weight.data, a=0, mode='fan_in')
            elif init_type == 'orthogonal':
                init.orthogonal(m.weight.data, gain=gain)
            else:
                raise NotImplementedError('initialization method [%s] is not implemented' % init_type)
            if hasattr(m, 'bias') and m.bias is not None:
                init.constant_(m.bias.data, 0.0)
        elif classname.find('BatchNorm2d') != -1:
            init.normal_(m.weight.data, 1.0, gain)
            init.constant_(m.bias.data, 0.0)

    print('initialize network with %s' % init_type)
    net.apply(init_func)

class ReD_Model(nn.Module):
	def __init__(self, cfg, vis=None, writer=None):
	    super(ReD_Model, self).__init__()
	    self.cfg=cfg
	    self.load_model()
	def load_model(self):
		


		self.net_classification_1=torch.hub.load('facebookresearch/WSL-Images', 'resnext101_32x16d_wsl')
		# self.net_classification_2=torch.hub.load('facebookresearch/WSL-Images', 'resnext101_32x16d_wsl')
		self.net_classification_2 = models.__dict__['resnet50'](num_classes=365)

		# self.net_classification_1.fc = nn.Sequential(nn.Dropout(p=0.2), nn.Linear(2048, 1024), nn.LeakyReLU(inplace=True), nn.Dropout(p=0.2),nn.Linear(1024, 67))
		self.net_classification_1.fc = nn.Linear(2048,67)

		self.net_classification_2.fc = nn.Linear(2048,67)


		print(("=> loading checkpoint '{}'".format('Color_model_best.pth.tar')))
		checkpoint = torch.load('/home/lzy/generateDepth/resnext101_Color_1fc_3e-4_best.pth.tar')
		best_mean_color = checkpoint['best_mean_1']
		new_state_dict = OrderedDict()
		for k, v in checkpoint['state_dict'].items():
		    name = k[7:]
		    # name=k
		    new_state_dict[name] = v
		self.net_classification_1.load_state_dict(new_state_dict)
		print('best_mean_color:',best_mean_color)
		# print(self.net_classification_2)
		# self.net_classification_2=resnet18(pretrained=False)
		# num_ftrs = self.net_classification_2.fc.in_features
		# self.net_classification_2.fc = nn.Linear(num_ftrs, self.cfg.NUM_CLASSES)
		print(("=> loading checkpoint '{}'".format('Depth_model_best.pth.tar')))
		checkpoint = torch.load('/home/lzy/generateDepth/resnet50_Depth_sunrgbd+mit67_best_0909_1e-3_.pth.tar')
		best_mean_depth = checkpoint['best_mean_2']
		new_state_dict = OrderedDict()
		for k, v in checkpoint['state_dict'].items():
		    name = k[7:]
		    new_state_dict[name] = v
		self.net_classification_2.load_state_dict(new_state_dict)
		print('best_mean_depth:',best_mean_depth)
		
		self.net_classification_1 = nn.Sequential(*list(self.net_classification_1.children())[:-2])
		self.net_classification_2 = nn.Sequential(*list(self.net_classification_2.children())[:-2])
		fix_grad(self.net_classification_1)
		fix_grad(self.net_classification_2)
		# print(self.net_classification_1)
		# self.net_classification_1=self.construct_single_modal_net(self.net_classification_1)
		# self.net_classification_2=self.construct_single_modal_net(self.net_classification_2)
		self.avgpool = nn.AdaptiveAvgPool2d(output_size=(1, 1))
		# # # self.fc_1=nn.Linear(4096,1024)
		# # # # self.fc_1=nn.Linear(2048,1024)
		self.fc=nn.Sequential(nn.Linear(4096, 1024),nn.Linear(1024,67))
		# # # # init_weights(self.fc_1, 'normal')
		# # # # # init_weights(self.fc_1, 'normal')
		# # # # init_weights(self.fc_0, 'normal')
		# self.fc = nn.Sequential(nn.Dropout(p=0.5),nn.Linear(4096, 1024),nn.LeakyReLU(inplace=True),nn.Linear(1024,67))

		# print(self.net_classification_1)
		# num_ftrs = self.net_classification_1.fc.in_features
		# self.net_classification_1.fc = nn.Linear(num_ftrs, self.cfg.NUM_CLASSES)
		# num_ftrs = self.net_classification_2.fc.in_features
		# self.net_classification_2.fc = nn.Linear(num_ftrs, self.cfg.NUM_CLASSES)
		# self.fc=nn.Linear(4096,67)
		init_weights(self.fc, 'normal')

	def forward(self, input,depth_image):

		baseout_1=self.net_classification_1(input)
		baseout_2=self.net_classification_2(depth_image)

		# print(baseout_1)
		# print(baseout_2)

		# output=baseout_1+0.5*baseout_2
		# baseout_final=baseout_2
		# output=torch.max(baseout_1,0.2*baseout_2)
		# print('baseout_1:',baseout_1)
		# print('baseout_2:',baseout_2)
		# print('output:',output)
		baseout_final=torch.cat((baseout_1,0.5*baseout_2),1)
		baseout_final=self.avgpool(baseout_final)
		baseout_final=baseout_final.view(baseout_final.size(0),-1)

		# # # # # print(output_0.size())
		# output=self.fc_0(self.fc_1(baseout_final))
		output=self.fc(baseout_final)


		return output
	def get_optim_policies(self):
	    first_conv_weight = []
	    first_conv_bias = []
	    normal_weight = []
	    normal_bias = []
	    bn = []

	    conv_cnt = 0
	    bn_cnt = 0
	    for m in self.modules():
	        if isinstance(m, torch.nn.Conv2d) or isinstance(m, torch.nn.Conv1d):
	            ps = list(m.parameters())
	            conv_cnt += 1
	            if conv_cnt == 1:
	                first_conv_weight.append(ps[0])
	                if len(ps) == 2:
	                    first_conv_bias.append(ps[1])
	            else:
	                normal_weight.append(ps[0])
	                if len(ps) == 2:
	                    normal_bias.append(ps[1])
	        elif isinstance(m, torch.nn.Linear):
	            ps = list(m.parameters())
	            normal_weight.append(ps[0])
	            if len(ps) == 2:
	                normal_bias.append(ps[1])
	              
	        elif isinstance(m, torch.nn.BatchNorm1d):
	            bn.extend(list(m.parameters()))
	        elif isinstance(m, torch.nn.BatchNorm2d):
	            bn_cnt += 1
	            # later BN's are frozen
	            bn.extend(list(m.parameters()))
	        # elif len(m._modules) == 0:
	        #     if len(list(m.parameters())) > 0:
	        #         raise ValueError("New atomic module type: {}. Need to give it a learning policy".format(type(m)))

	    return [
	        {'params': first_conv_weight, 'lr_mult':  1, 'decay_mult': 1,
	         'name': "first_conv_weight"},
	        {'params': first_conv_bias, 'lr_mult':  2, 'decay_mult': 0,
	         'name': "first_conv_bias"},
	        {'params': normal_weight, 'lr_mult': 1, 'decay_mult': 1,
	         'name': "normal_weight"},
	        {'params': normal_bias, 'lr_mult': 2, 'decay_mult': 0,
	         'name': "normal_bias"},
	        {'params': bn, 'lr_mult': 1, 'decay_mult': 0,
	         'name': "BN scale/shift"},
	    ]

def fix_grad(net):
    print(net.__class__.__name__)
    def fix_func(m):
        classname = m.__class__.__name__
        if classname.find('Conv') != -1 or classname.find('BatchNorm2d') != -1:
            m.weight.requires_grad = False
            if m.bias is not None:
                m.bias.requires_grad = False

    net.apply(fix_func)
