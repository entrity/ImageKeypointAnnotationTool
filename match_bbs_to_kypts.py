#!/usr/bin/env python

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.pyplot import cm
import sys, os
from collections import OrderedDict
import tkinter
from tkinter import Tk, Canvas, mainloop
from PIL import Image, ImageTk
import numpy as np
import re

import IPython

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-b", dest="bbs_file", default='images', help="tsv of (vidid, fname, kypts-csv)")
parser.add_option("-k", dest="kps_file", default='alphapose/keypoints.tsv', help="tsv of (vidid, fname, kypts-csv)")
parser.add_option("-l", dest="listfile", help="list of fnames and bbs")
parser.add_option("-2", dest="interpret_x2y2", action="store_true", help="3rd and 4th items in bb tuple are x2 and y2 instead of width and height. This option should be used for AlphaPose's boxes files but not for our Mac.mat.")
(opts, args) = parser.parse_args()

DEFAULT_DOT_SIZE=6
DEFAULT_BB_SIZE=1

def keyify(obj):
	return tuple(obj.reshape(-1).round().astype(np.int32))

class Rainbow(dict):
	def __init__(self, bbs, kp_sets):
		colors = cm.rainbow(np.linspace( 0, 1, len(kp_sets)+len(bbs) ))
		i          = 0
		rgb_ints   = lambda : [ int(x) for x in colors[i][:-1]*255 ]
		rgb_hex    = lambda : '#%02x%02x%02x' % tuple(rgb_ints())
		for bb in bbs:
			self[keyify(bb)] = rgb_hex()
			i += 1
		for kps in kp_sets:
			self[keyify(kps)] = rgb_hex()
			i += 1

class UI(object):
	@classmethod
	def load_annotations(cls, bb_path, kp_path):
		cls.meta = []
		with open(kp_path, 'r') as f:
			for line in f: # each line is one image
				vidid, fname, csv = line.split('\t')
				impath    = os.path.join('images', vidid, fname)
				keypoints = [int(x) for x in csv.replace('99999','0').split(',')]
				keypoints = np.array(keypoints).reshape(-1,21,2)
				bbs_path  = os.path.join(bb_path, vidid, fname+'.npy')
				bbs       = np.load(bbs_path)
				cls.meta.append( (impath, bbs, keypoints) )

	@classmethod
	def start(cls):
		# Init data
		cls.load_annotations(opts.bbs_file, opts.kps_file)
		cls.all_bb2kp = {}
		cls.all_kp2bb = {}
		cls.bb2kp = OrderedDict()
		cls.kp2bb = OrderedDict()
		cls.img_i = -1
		# Init GUI
		cls.ui = Tk()
		cls.canvas = Canvas(cls.ui)
		cls.canvas.pack(fill='both', expand=True)
		cls.canvas_img = cls.canvas.create_image(0, 0, anchor='nw')
		cls.ui.bind('<Key>', cls.onkeypress)
		cls.ui.bind('<Right>', cls.onrightpress)
		cls.ui.bind('<Left>', cls.onleftpress)
		cls.ui.bind('<Button-1>', cls.onmouse1)
		cls.ui.bind('<Button-2>', cls.onmouse2)
		cls.ui.bind('<Button-3>', cls.onmouse3)
		# Load data if any
		cls.load_data()
		# Load image to canvas
		cls.next_img()
		# Start GUI
		mainloop()

	@classmethod
	def color(cls, obj):
		tup = keyify(obj)
		if tup in cls.bb2kp or tup in cls.kp2bb:
			return '#666'
		return cls.rainbow[tup]

	@classmethod
	def next_img(cls, inc=1):
		print('next_img called')
		cls.img_i += inc
		if (len(cls.all_bb2kp.keys())): cls.save_data()
		if cls.img_i < 0 or cls.img_i > len(cls.meta):
			cls.img_i -= inc
			return
		# Get annotations and meta
		cls.fpath, cls.bbs, cls.kp_sets = cls.meta[cls.img_i]
		cls.bb2kp = cls.all_bb2kp.setdefault(cls.fpath, OrderedDict()) # tuple(bb) => kps
		cls.kp2bb = cls.all_kp2bb.setdefault(cls.fpath, OrderedDict()) # map  tuple(kps) => bb
		# Assign colors
		cls.rainbow = Rainbow(cls.bbs, cls.kp_sets)
		# Clear and load
		cls.redraw()
	@classmethod
	def redraw(cls):
		cls.canvas.delete('kp')
		cls.canvas.delete('bb')
		cls.load_img()
		for bb in cls.bbs:
			cls.draw_bb(bb)
		for kps in cls.kp_sets:
			cls.draw_keypoints(kps)
	@classmethod # Load image and drawings to canvas
	def load_img(cls):
		print('Loading img (%d) %s' % (cls.img_i, cls.fpath))
		im = cls.canvas.im = ImageTk.PhotoImage(Image.open(cls.fpath))
		cls.canvas.config(width=im.width(), height=im.height())
		cls.canvas.itemconfig(cls.canvas_img, image=im)
	@classmethod
	def draw_keypoints(cls, kps, linewidth=DEFAULT_DOT_SIZE):
		if np.array_equal(cls.active_kps, kps): linewidth=12
		for x,y in kps:
			ov = cls.canvas.create_oval(x,y,x,y, outline=cls.color(kps), width=linewidth, tags=('kp',))
	@classmethod
	def draw_bb(cls, bb, linewidth=DEFAULT_BB_SIZE):
		if np.array_equal(cls.active_bb, bb): linewidth=6
		cls.canvas.create_rectangle(*bb, outline=cls.color(bb), width=linewidth, tags=('bb',))

	@classmethod
	def activate_bb(cls, x, y):
		threshold = 20
		nearest_dist = 2**20
		nearest = None
		# Check if click is close to one line in bb and between the ends of the segment
		check = lambda t, t1, t2, m, l, u: min(abs(t-t1),abs(t-t2)) < threshold and m > l and m < u
		# Iterate bbs to find active one for click
		for i, bb in enumerate(cls.bbs):
			if check(x, bb[0], bb[2], y, bb[1], bb[3]) or check(y, bb[1], bb[3], x, bb[0], bb[2]):
				dist = min( min(abs(x-bb[0]),abs(x-bb[2])), min(abs(y-bb[1]),abs(y-bb[3])) )
				if dist < nearest_dist:
					nearest_dist = dist
					nearest = i
		# Iterate bbs to draw
		cls.canvas.delete('bb')
		for i, bb in enumerate(cls.bbs):
			if i == nearest:
				cls.active_bb = bb
		cls.redraw()
		cls.set_match()
	@classmethod
	def activate_kps(cls, x, y):
		threshold = 50
		nearest_dist = 2**20
		nearest = None
		# Check if click is close to one line in bb and between the ends of the segment
		calc_dist = lambda kx, ky : np.sqrt((x-kx)**2 + (y-ky)**2)
		# Iterate bbs to find active one for click
		for i, kps in enumerate(cls.kp_sets):
			for kx,ky in kps:
				dist = calc_dist(kx,ky)
				if dist < threshold and dist < nearest_dist:
					nearest_dist = dist
					nearest = i
		# Iterate bbs to draw
		cls.canvas.delete('kp')
		for i, kps in enumerate(cls.kp_sets):
			if i == nearest:
				cls.active_kps = kps
		cls.redraw()
		cls.set_match()
	@classmethod
	def set_match(cls):
		is_set = False
		if getattr(cls,'active_kps',None) is not None and getattr(cls,'active_bb',None) is not None:
			cls.bb2kp = cls.all_bb2kp.setdefault(cls.fpath, OrderedDict()) # tuple(bb) => kps
			cls.kp2bb = cls.all_kp2bb.setdefault(cls.fpath, OrderedDict()) # map  tuple(kps) => bb
			cls.bb2kp[keyify(cls.active_bb)] = cls.active_kps
			cls.kp2bb[keyify(cls.active_kps)] = cls.active_bb
			if cls.img_i > -1: cls.redraw()
			cls.active_kps = None
			cls.active_bb = None
			is_set = True
		return is_set
	@classmethod
	def undo_match(cls):
		cls.bb2kp.popitem()
		cls.kp2bb.popitem()
		cls.redraw()

	# Write TSV: fpath, (bb), ((x,y),...)
	@classmethod
	def save_data(cls):
		with open('annotations.tsv', 'w') as f:
			for fpath in cls.all_bb2kp:
				bb2kp = cls.all_bb2kp[fpath]
				for bb_tup in bb2kp:
					f.write(fpath)
					for v in bb_tup: f.write('\t%f' % v)
					kp_tup = bb2kp[bb_tup].reshape(-1)
					for v in kp_tup: f.write('\t%f' % v)
					f.write('\n')
	@classmethod
	def load_data(cls):
		if not os.path.exists('annotations.tsv'): return
		with open('annotations.tsv', 'r') as f:
			for line in f:
				vals = line.split('\t')
				cls.fpath = vals[0]
				print(cls.fpath)
				bb_tup = tuple(np.array(vals[1:5]).astype(np.float64))
				assert(len(bb_tup) ==  4)
				kp_tup = tuple(np.array(vals[5:]).astype(np.float64))
				assert(len(kp_tup) == 21*2)
				cls.active_bb = np.array(bb_tup)
				cls.active_kps = np.array(kp_tup).reshape(21, 2)
				assert(cls.set_match())

	@staticmethod
	def onkeypress(evt):
		if evt.char.lower() == 'q':
			UI.ui.destroy()
			UI.save_data()
		elif evt.char.lower() == 'c':
			UI.canvas.delete(tkinter.ALL)
		elif evt.char.lower() == 'u':
			UI.undo_match()
		print(evt.char)
	@staticmethod
	def onrightpress(evt):
		print('right')
		UI.next_img()
	@staticmethod
	def onleftpress(evt):
		UI.next_img(-1)
	@staticmethod
	def onmouse1(evt): # Select BB
		UI.activate_bb(evt.x, evt.y)
	@staticmethod
	def onmouse2(evt): # Select KPs
		UI.activate_kps(evt.x, evt.y)
	@staticmethod
	def onmouse3(evt):
		pass
		# UI.set_match()

UI.start()
k = UI.next_img()
print(k)
