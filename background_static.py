# -*- coding: utf-8 -*-
#
# Subtract a static background from electron backscatter diffraction patterns
# using a background image from NORDIF or your own background image of the
# same pixel size as the patterns. The background pattern can either be
# subtracted or divided by. Relative intensities are maintained.
#
# Created by Håkon W. Ånes (hakon.w.anes@ntnu.no)
# 2018-11-07
#

import hyperspy.api as hs
import argparse
import os
import time
import skimage as sk


hs.preferences.General.nb_progressbar = False  # Use tqdm progressbar
hs.preferences.General.parallel = True  # Use all the CPUs!

# Parse input parameters
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('file', help='Full path of original file')
parser.add_argument('--lazy', dest='lazy', default=False, action='store_true',
                    help='Whether to read/write lazy or not')
parser.add_argument('--bg_img', help='Background image to subtract')
parser.add_argument('--divide', dest='divide', default=False,
                    action='store_true', help='Divide by static background')
args = parser.parse_args()

file = args.file
lazy = args.lazy
bg_img = args.bg_img

# Set data directory, filename and file extension
datadir, fname = os.path.split(file)
fname, ext = os.path.splitext(fname)

# Read data
print('* Read data from file')
s = hs.load(file, lazy=lazy)

# Read or create background pattern to divide by
print('* Read background image from file')
if bg_img is None:
    bg_img = hs.load(os.path.join(datadir,
                                  'Background acquisition pattern.bmp'),
                     lazy=lazy)
else:
    bg_img = hs.load(bg_img, lazy=lazy)

# Change data types (increase bit depth) to avoid negative intensites when
# subtracting background patterns
s.change_dtype('int16')
bg_img.change_dtype('int16')

# Subtract by background pattern
print('* Subtract background pattern')
if args.divide:
    s = s / bg_img
else:
    s = s - bg_img

# Create new minimum and maximum intensities, keeping the ratios
print('* Create new minimum and maximum intensities before scaling')
# First, get new maximums and minimums after background subtraction
smin = s.min(s.axes_manager.signal_axes)
smax = s.max(s.axes_manager.signal_axes)

# Set lowest intensity to zero
int_min = smin.data.min()
smin = smin - int_min
smax = smax - int_min

# Get scaling factor and scale intensities
scale = 255 / smax.data.max()
smin = smin * scale
smax = smax * scale

# Convert to uint8 and write to memory
smin.change_dtype('uint8')
smax.change_dtype('uint8')

if lazy:
    smin.compute()
    smax.compute()


def rescale_pattern(pattern, smin, smax):
    return sk.exposure.rescale_intensity(pattern, out_range=(smin, smax))


print('* Rescale patterns (timing)')
start = time.time()
s.map(rescale_pattern, parallel=True, ragged=False, smin=smin, smax=smax)
s.change_dtype('uint8')
print('* Time: %.2f s' % (time.time() - start))

# Write data to file
print('* Write data to file')
s.save(os.path.join(datadir, fname + '_bg' + ext))