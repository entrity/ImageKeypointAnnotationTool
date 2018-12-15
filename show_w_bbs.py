#!/usr/bin/env python

import sys, os
assert sys.version.startswith('3.')

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.pyplot import cm
from PIL import Image
import numpy as np
import re

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("fpath", nargs="?", help="image filepath")
parser.add_argument("coords", nargs=argparse.REMAINDER)
parser.add_argument("-l", "--list", dest="listfile", help="list of fnames and bbs")
parser.add_argument("-2", dest="interpret_x2y2", action="store_true", help="3rd and 4th items in bb tuple are x2 and y2 instead of width and height. This option should be used for AlphaPose's boxes files but not for our Mac.mat.")
parser.add_argument("-f", "--float", action="store_true", help="coords are in range [0,1[] relative to size of image")
parser.add_argument("-c", "--centered", action="store_true", help="x & y coords are the centre of the bounding box, not the top left corner")
opts = parser.parse_args()
print(opts)

rainbow = cm.rainbow(np.linspace(0,1,8))
rainbow_i = 0
legend = []
im = None

def addrect(tup):
	global ax
	global rainbow_i
	global legend
	i = 0
	imw = im.shape[1]
	imh = im.shape[0]
	x, y, a, b = [float(v) for v in tup] # interpreting as x,y,w,h by default
	if opts.float:
		x *= imw
		a *= imw
		y *= imh
		b *= imh
	if opts.centered:
		x -= a/2
		y -= b/2
	if opts.interpret_x2y2:
		a -= x # w from x2
		b -= y # h from y2
	color = rainbow[rainbow_i]
	legend.append(tup)
	rect = patches.Rectangle((x,y), a, b, linewidth=3, edgecolor=color, facecolor='none')
	print('%d : %5.3f %5.3f %5.3f %5.3f' % (rainbow_i, *color))
	rainbow_i += 1
	ax.add_patch(rect)

def startimg(fpath):
	global im
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

if opts.fpath:
	ax = startimg(opts.fpath)
elif opts.listfile:
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

print('coords', opts.coords)
for i in range(0, len(opts.coords), 4):
	addrect(opts.coords[i:i+4])


ax.legend(list(range(len(legend))))
plt.show()
