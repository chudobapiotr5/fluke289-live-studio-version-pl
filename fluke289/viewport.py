# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Time navigation independent of Tk and measurement data."""

class TimeViewport:
    def __init__(self):
        self.domain = (0., .001)
        self.selection = None

    def clamp(self, bounds):
        low, high = self.domain
        width = min(max(bounds[1]-bounds[0], .001), high-low)
        start = min(max(bounds[0], low), high-width)
        return start, start+width

    def update_domain(self, low, high):
        self.domain = (low, max(high, low+.001))
        if self.selection is not None:
            self.selection = self.clamp(self.selection)

    def reset(self):
        self.selection = None

    def zoom(self, current, fraction, factor):
        fraction = min(1., max(0., fraction))
        width = current[1]-current[0]
        new_width = min(max(width*factor, .001), self.domain[1]-self.domain[0])
        anchor = current[0]+fraction*width
        self.selection = self.clamp((anchor-fraction*new_width, anchor+(1-fraction)*new_width))
        return self.selection

    def pan(self, initial, delta):
        self.selection = self.clamp((initial[0]+delta, initial[1]+delta))
        return self.selection
