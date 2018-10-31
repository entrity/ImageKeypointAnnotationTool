#!/usr/bin/env python

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.pyplot import cm
import sys, os
from PIL import Image
import numpy as np
import re

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", "--list", dest="listfile", help="list of fnames and bbs")
parser.add_option("-2", dest="interpret_x2y2", action="store_true", help="3rd and 4th items in bb tuple are x2 and y2 instead of width and height. This option should be used for AlphaPose's boxes files but not for our Mac.mat.")
(opts, args) = parser.parse_args()

rainbow = cm.rainbow(np.linspace(0,1,8))
rainbow_i = 0
legend = []

def addrect(tup):
	global ax
	global rainbow_i
	global legend
	i = 0
	x = float(tup[i])
	y = float(tup[i+1])
	a = float(tup[i+2]) # w
	b = float(tup[i+3]) # h
	if opts.interpret_x2y2:
		a -= x # w from x2
		b -= y # h from y2
	color = rainbow[rainbow_i]
	legend.append(tup)
	rect = patches.Rectangle((x,y), a, b, linewidth=1, edgecolor=color, facecolor='none')
	print('%d : %5.3f %5.3f %5.3f %5.3f' % (rainbow_i, *color))
	rainbow_i += 1
	ax.add_patch(rect)

def startimg(fpath):
	im = np.array(Image.open(fpath), dtype=np.uint8)
	fig,ax = plt.subplots(1)
	ax.imshow(im)
	global rainbow_i
	global legend
	rainbow_i = 0
	legend = []
	return ax

comment_pattern = re.compile('^\s*#')
imgfile_pattern = re.compile('^@\s*(.+)')
split_pattern   = re.compile('\s+')

if len(args):
	ax = startimg(args[0])
if opts.listfile:
	with open(opts.listfile, 'r') as f:
		for line in f:
			match = imgfile_pattern.match(line)
			if match:
				ax = startimg(match.group(1))
				print("Defined ax: %s" % ax)
				continue
			match = comment_pattern.match(line)
			if match:
				continue
			addrect(split_pattern.split(line.strip()))

for i in range(1, len(args), 4):
	addrect(sys.argv[i:i+4])

ax.legend(list(range(len(legend))))
plt.show()
