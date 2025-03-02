# -*- coding: utf-8 -*-
"""
Created on Sat Apr  2 18:09:36 2022

@author: jced0001
"""

from .Panel import Panel
import customtkinter as ctk
import numpy as np
from scipy.signal import convolve2d
from scipy import ndimage
from . import nanonispyfit as napfit

class FilterPanel(Panel):
    activeFilters = {"rollV" : 0,
                     "rollH" : 0}
    filterOrder = []; activeFilterOrder = []                                    # Implement this at some point
    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, master, width, height, dpi, mainPanel):
        super().__init__(master, width, height, dpi, mainPanel=mainPanel)
        self.buttons()
        self.buildFilters()
    ###########################################################################
    # Panel
    ###########################################################################
    def buttons(self):
        self.btn = {
            "RollV+": ctk.CTkButton(self.master, text="Roll Vert +", command=lambda: self.updateFilter("rollV", 1)),
            "RollV-": ctk.CTkButton(self.master, text="Roll Vert -", command=lambda: self.updateFilter("rollV",-1)),
            "RollH+": ctk.CTkButton(self.master, text="Roll Horz +", command=lambda: self.updateFilter("rollH", 1)),
            "RollH-": ctk.CTkButton(self.master, text="Roll Horz -", command=lambda: self.updateFilter("rollH",-1)),
            "HPF+":   ctk.CTkButton(self.master, text="High Pass +", command=lambda: self.updateFilter("HP",1)),
            "HPF-":   ctk.CTkButton(self.master, text="High Pass -", command=lambda: self.updateFilter("HP",-1)),
            "LPF+":   ctk.CTkButton(self.master, text="Low Pass +",  command=lambda: self.updateFilter("LP",1)),
            "LPF-":   ctk.CTkButton(self.master, text="Low Pass -",  command=lambda: self.updateFilter("LP",-1)),
            "LINF":   ctk.CTkButton(self.master, text="Linear Fit",  command=lambda: self.updateFilter("LINF",0)),
            "SetFlt": ctk.CTkButton(self.master, text="Set Filter",  command=self.setFilter),
            "Close":  ctk.CTkButton(self.master, text="Close",       command=self.destroy)
            }
    ###########################################################################
    # Update and Plotting (WIP)
    ###########################################################################
    def update(self):
        if(not self.mainPanel.init): return
        
        self.ax.cla()                                                           # Clear the axis
        self._previewFilters()                                                  # Filter the image in this panel to show a preview before setting
        self._addPlotCaption()                                                  # Add a caption to the plot in the upper left to show what filters are previewing
        self.ax.set_position([0, 0, 1, 1])                                      # Make it take up the whole canvas
        self.ax.axis('off')                                                     # Hide the axis
        self.canvas.figure = self.fig                                           # Assign the figure to the canvas
        self.canvas.draw()                                                      # Redraw the canvas with the updated figure
    
    def _previewFilters(self):                                                  # Take a snapshot of the current sxm image and preview the filters being applied to it before setting them
        im = np.copy(self.mainPanel.unfilteredIm)                               # The snapshot of the current sxm image
        
        filteredIm = self.applyFilters(im)
        
        extent = self.mainPanel.extent
        cmap = self.cmaps[self.mainPanel.cmap][1]
        self.vmin, self.vmax = napfit.filter_sigma(filteredIm)                  # cmap saturation
        self.ax.imshow(filteredIm,extent=extent,cmap=cmap(),vmin=self.vmin,vmax=self.vmax)
    
    def _addPlotCaption(self):
        plotCaption  = 'Filter List:'                                           # List of filters in the order they are applied (text box will display these)
        offset = 0                                                              # Used to offset lines in the informative textbox at the top left of the image
        for f in self.filterOrder:
            offset += 0.032                                                     # Appropriate offset between each line of new text in the text box
            plotCaption += "\n" + f + ": " + str(self.filters[f][0])
            
        extent = self.mainPanel.extent
        props = dict(boxstyle='round',facecolor='white',alpha=0.5)
        self.ax.text(0.025*extent[1],(0.95-offset)*extent[3],plotCaption,bbox=props)
    ###########################################################################
    # Filter Control
    ###########################################################################
    def buildFilters(self):
        self.filters = {"rollV" : [0, lambda im: self.rollVert(im)],
                        "rollH" : [0, lambda im: self.rollHorz(im)],
                        "HP"    : [0, lambda im: self.highPass(im)],
                        "LP"    : [0, lambda im: self.lowPass(im)],
                        "LINF"  : [False, lambda im: self.linearFit(im)]}
        self.activeFilters = self.filters.copy()
        
    def updateFilter(self,filtType,inc):
        if(inc == 0):
            # If inc is zero, we're toggling
            self.filters[filtType][0] = not(self.filters[filtType][0])
        else:
            # Otherwise the filters can be stacked
            self.filters[filtType][0] += inc
        
        if(self.filters[filtType][0] == 0):
            del self.filterOrder[self.filterOrder.index(filtType)]              # Remove this filter from the order of applied filters if it has no contribution
            
        if(self.filters[filtType][0] < 0):
            self.filters[filtType][0] = 0                                       # Bottom out at zero
        
        if(self.filters[filtType][0] > 0 and not (filtType in self.filterOrder)):
            self.filterOrder.append(filtType)                                   # Append if this filter is in use
            
        self.update()
    
    def setFilter(self):
        self.activeFilters     = self.filters.copy()
        self.activeFilterOrder = self.filterOrder.copy()
        self.mainPanel.vmin = self.vmin
        self.mainPanel.vmax = self.vmax
        self.mainPanel.update()
    ###########################################################################
    # Filters
    ###########################################################################
    def applyFilters(self,im,active=False):
        filters    = self.filters.copy()
        filterList = self.filterOrder.copy()
        
        if(active):
            filters    = self.activeFilters.copy()
            filterList = self.activeFilterOrder.copy()
        
        filteredIm = im
        for i in filterList:                                                    # Loop through the filters we're previewing and apply them in the correct order
            if isinstance(filters[i][0], bool):                                 # Check if the filter uses True/False (boolean)
                if filters[i][0]:                                               # If it's True, apply the filter once
                    filteredIm = filters[i][1](filteredIm)
            else:
                for p in range(filters[i][0]):                                  # Otherwise, apply the filter the specified number of times
                    filteredIm = filters[i][1](filteredIm)
            
        # Some filters can change the number of pixels... easier to just pad out the image to what it was
        # pad = np.zeros(self.mainPanel.unfilteredIm.shape)
        # pad[:filteredIm.shape[0],:filteredIm.shape[1]] = filteredIm
        
        return filteredIm
    
    def rollVert(self,im,p=1):
        return convolve2d(im, np.ones((2*p,1)) / 2 / p, mode='same')
       
    def rollHorz(self,im,p=1):
        return convolve2d(im, np.ones((1,2*p)) / 2 / p, mode='same')
    
    def highPass(self,im):                                                      # Gaussian hp filter taken from https://stackoverflow.com/questions/6094957/high-pass-filter-for-image-processing-in-python-by-using-scipy-numpy
        lowpass = ndimage.gaussian_filter(im, 20)
        gauss_highpass = im - lowpass
        return gauss_highpass
    
    def lowPass(self,im):
        lowpass = ndimage.gaussian_filter(im, 0.5)
        return lowpass
    
    def linearFit(self,im):
        corrected_im = np.zeros_like(im)
        
        num_cols = im.shape[1]
        x = np.arange(num_cols)

        # Loop through each row
        for i in range(im.shape[0]):
            # Perform linear fit on the current row
            coeffs = np.polyfit(x, im[i], 1)  # Degree 1 for a linear fit
            
            # Create the linear fit for this row
            linear_fit = np.polyval(coeffs, x)
            
            # Subtract the linear fit from the original row and store in the result array
            corrected_im[i] = im[i] - linear_fit
        
        return corrected_im

    ###########################################################################
    # Save (WIP)
    ###########################################################################
    def buildSaveString(self):
        saveString = "#FilterPanel\n"                                           # Line 1: Header
        
        # Save self.activeFilterOrder
        # Save self.activeFilters[f][0] for f in self.activeFilterOrder
        
        return saveString