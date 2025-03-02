# -*- coding: utf-8 -*-
"""
Created on Sat Apr  2 18:09:36 2022

@author: jced0001
"""

from .Panel import Panel
import tkinter as tk
import customtkinter as ctk
import numpy as np
import os
import nanonispy2 as nap
import math
from scipy.signal import savgol_filter as savgol
import matplotlib.patheffects as patheffects
import pickle
from   tkinter import filedialog

class STSPanel(Panel):
    datFile = []; stsPos = []; stsOffset = False                                # list of .dat filenames. stspos: location of xy pos 
    logScale = False
    datFileCustom = []; customSTSPos = []
    dat_xchannel = 'Bias calc (V)'
    dat_ychannel = 'Current (A)'
    reference = [[]]
    referencePath = ""
    removeRef = False
    showRef   = False
    sg_pts  = 3; sg_poly = 1
    allcurves = {}
    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, master, width, height, dpi, mainPanel):
        super().__init__(master, width, height, dpi, mainPanel=mainPanel)
        self.buttons()
    ###########################################################################
    # Panel
    ###########################################################################
    def buttons(self):
        self.btn = {
            "datSpec":  ctk.CTkComboBox(self.master, values=["STS.dat"],command=self.datSpec),
            "GridSpec": ctk.CTkComboBox(self.master, values=["STS.grid"],command=self.gridSpec),
            "Reference":ctk.CTkComboBox(self.master, values=["Reference"],command=self._reference),
            # "RemRef":   ctk.CTkButton(self.master, text="Remove Ref", command=self.removeReference),  # See how it goes getting rid of this, now that fitPanel exists
            "Channel":  ctk.CTkButton(self.master, text="Current (A)",command=self._cycleChannel),
            "PlotProp": ctk.CTkComboBox(self.master, values=["Plot Props"],command=self.plotProps),
            "Inset":    ctk.CTkButton(self.master, text="Inset",      command=super().addInset),
            "Imprint":  ctk.CTkButton(self.master, text="Imprint",    command=super()._imprint),
            "Fitting":  ctk.CTkButton(self.master, text="Fit",        command=self.mainPanel.fitPanel.create),
            "Export":   ctk.CTkButton(self.master, text="Export",     command=self.exportSTS),
            "Close":    ctk.CTkButton(self.master, text="Close",      command=self.destroy)
            }
        
        datSpecValues = ["STS.dat","Add Single","Add Manual","Add Folder","Undo Last","Clear All"]
        self.btn['datSpec'].configure(values=datSpecValues,fg_color=['#3B8ED0', '#1F6AA5'])
        
        gridSpecValues = ["STS.grid","Add Single","Add Averaged","Undo Single","Undo Averaged","Clear All"]
        self.btn['GridSpec'].configure(values=gridSpecValues,fg_color=['#3B8ED0', '#1F6AA5'])
        
        gridSpecValues = ["Plot Props","Toggle Offset","Linear"]
        self.btn['PlotProp'].configure(values=gridSpecValues,fg_color=['#3B8ED0', '#1F6AA5'])
        
        gridSpecValues = ["Reference","Load New","Hide"]
        self.btn['Reference'].configure(values=gridSpecValues,fg_color=['#3B8ED0', '#1F6AA5'])
        
    def buttonHelp(self):
        helpStr = "Add spectra from .dat file.\nAdd Single: Select a single .dat file and auto plot location on Main Figure.\nAdd Manual: Manually locate marker on main figure.\nAdd Folder: Plot all .dat files in the selected folder"
        self.btn['datSpec'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Add spectra from the grid panel.(Grid panel must be active and a .3ds file loaded)\nAdd Single: Left click within the grid to plot a spectrum.\nAdd Averaged: Left click multiple locations to plot an averaged spectra. Right click to finish"
        self.btn['GridSpec'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Change plot properties"
        self.btn['PlotProp'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Load in a refrence .dat file. This will also be the reference used in the fitting panel"
        self.btn['Reference'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Change data channel"
        self.btn['Channel'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Add the above plot as an inset on the main figure. Double click a location in the main figure to repoisition the inset and use the scroll wheel to change its size"
        self.btn['Inset'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Imprint the overlay drawn by this panel on the main figure so it persits after closing this panel"
        self.btn['Imprint'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Close this panel"
        self.btn['Close'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Open the curve fitting panel"
        self.btn['Fitting'].bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
        helpStr = "Adjust the slider to smooth curves"
        self.slider.bind('<Enter>',lambda event, s=helpStr: self.updateHelpLabel(s))
        
    def special(self):                                                          # Special canvas UI
        self.slider = ctk.CTkSlider(self.master, orientation=tk.HORIZONTAL, from_=0, to=9, width=420, command=self.smoothing) # Slider to select which bias/sweep signal slice to look show
        self.slider.grid(row=10,column=self.pos,columnspan=4,rowspan=2)          # Make it take up the entire length of the panel
        self.slider.set(1)

    def removeSpecial(self):
        self.slider.grid_forget()                                               # Called when panel is closed
        
    ###########################################################################
    # Update and Plotting
    ###########################################################################
    def update(self):
        if(not self.mainPanel.init): return
        if(not self.active): return
        
        self.ax.cla()                                                           # Clear the axis
        self.plotReference()
        self.plotSTSFromGrid()                                                  # Plot chosen spectra from Grid
        self.plotAveragedSTSFromGrid()                                          # Plot curves corresponding to averaged points on the grid
        self._plotSTS()                                                         # Loops through .dat files, takes the derivative of IV curves and plot dI/dV
        self.ax.set_position([0.13, 0.1, 0.83, 0.83])                           # Leave room for axis labels and title
        
        self.canvas.figure = self.fig                                           # Assign the figure to the canvas
        self.canvas.draw()                                                      # Redraw the canvas with the updated figure
        
        self.mainPanel.fitPanel.update()
        
    def plotReference(self):
        self.allcurves['reference'] = []
        if(not self.showRef): return
        V,didv = self.getDIDV(self.referencePath)
        self.reference = V,didv
        
        self.ax.plot(V,didv,linewidth=1.3,c='black',linestyle='dashed')
        
        self.allcurves['reference'] = [V,didv]
        
    def plotSTSFromGrid(self):
        self.allcurves['Grid'] = []
        if(not self.mainPanel.gridPanel.active):
            if(not self.mainPanel.gridPanel.imprint):
                return
        
        sweep,spectra = self.mainPanel.gridPanel.getPointSpectra()
        
        offset = 0; cnt = 0; num_offset = 3; max_val = 0
        for s in spectra:
            if(self.removeRef):
                reference = self.getReferenceForCurve(x=sweep)
                s -= reference
                
            self.ax.plot(sweep,s + cnt*offset,linewidth=1.3)
            
            self.allcurves['Grid'].append([sweep,s])
            
            max_val = max(max_val,s.max())
            if cnt == 0:                                                        # Only do this on the first iteration
               offset = num_offset*0.25*max_val*self.stsOffset                  # offset for the next curve
            cnt += 1
            
        if(self.mainPanel.gridPanel.active):
            Vb = self.mainPanel.gridPanel.getBias()
            self.ax.axvline(x=Vb,linestyle='dashed',c='black',linewidth=0.9)
    
    def plotAveragedSTSFromGrid(self):
        self.allcurves['AveragedGrid'] = []
        if(not self.mainPanel.gridPanel.active):
            if(not self.mainPanel.gridPanel.imprint):
                return
        sweep,spectra = self.mainPanel.gridPanel.getAveragedPointSpectra()
        
        offset = 0; cnt = 0; num_offset = 3; max_val = 0
        for idx,s in enumerate(spectra):
            if(self.removeRef):
                reference = self.getReferenceForCurve(x=sweep)
                s -= reference
                
            c = self.mainPanel.mplibColours[idx+1]                              #+1 because I don't wanna start from black
            self.ax.plot(sweep,s + cnt*offset,linewidth=1.3,c=c,path_effects=[patheffects.withTickedStroke(angle=60, length=0.25)])
            
            self.allcurves['AveragedGrid'].append([sweep,s])
            
            max_val = max(max_val,s.max())
            if cnt == 0:                                                        # Only do this on the first iteration
               offset = num_offset*0.25*max_val*self.stsOffset                  # offset for the next curve
            cnt += 1
            
        if(self.mainPanel.gridPanel.active):
            Vb = self.mainPanel.gridPanel.getBias()
            self.ax.axvline(x=Vb,linestyle='dashed',c='black')
    
    def _plotSTS(self):
        self.allcurves['datFile'] = []
        
        num_offset = 3                                                          # These will eventually be user input #todo
        max_val = 0; offset = 0; cnt = 0                                        # Loop variables
        
        datFiles = self.datFile.copy()
        if(self.datFileCustom): datFiles.append(self.datFileCustom)             # Weird way to loop through combined list but only way I could figure out how to do it
            
        for df in datFiles:                                                     # Loop through each .dat file, get the IV curve, take the derivative and plot a filtered version of dI/dV
            V, didv = self.getDIDV(df)
            
            self.allcurves['datFile'].append([V,didv])
            
            if(self.removeRef):
                reference = self.getReferenceForCurve(x=V)
                didv -= reference
                
            self.ax.plot(V,didv + cnt*offset,linewidth=1.3)
           
            max_val = max(max_val,didv.max())
            if cnt == 0:                                                        # Only do this on the first iteration
               offset = num_offset*0.25*max_val*self.stsOffset                  # offset for the next curve
            cnt += 1
            
        self.ax.set_xlabel("Bias (V)")
        self.ax.set_ylabel(["dI/dV (arb)","log(dI/dV) (arb)"][self.logScale]);
        self.ax.set_title("Point Spectroscopy")
        
    def exportSTS(self):
        default = 'sts.pk'
        path = filedialog.asksaveasfilename(title="Save as",initialfile=default)
        if(not path.endswith('.pk')): path += '.pk'
        
        pickle.dump(self.allcurves,open(path,'wb'))
        
    ###########################################################################
    # Data
    ###########################################################################
    def getDIDV(self,datFile="",curve=[],xchannel="",ychannel=""):
        if(xchannel == ""): xchannel = self.dat_xchannel
        if(ychannel == ""): ychannel = self.dat_ychannel
        V = 0; didv = 0
        if(datFile):
            dat = nap.read.Spec(datFile)
            V = dat.signals[self.dat_xchannel]
            I = dat.signals[ychannel]
        elif(len(curve)):
            V = curve[0]
            I = curve[1]
        else:
            return V,didv
        
        dV = V[1] - V[0]
        
        didv = 0*I
        if('Current' in ychannel):
            didv = savgol(I,self.sg_pts,self.sg_poly,deriv=1,delta=dV)
            if(self.logScale): didv = np.log(didv); didv = didv - np.min(didv)
        
        if('Demod' in ychannel):
            didv = savgol(I,self.sg_pts,self.sg_poly,deriv=0)
            if(self.logScale): didv = np.log(didv); didv = didv - np.min(didv)
        
        return V,didv
    
    def smoothing(self,event):
        self.sg_pts = 2*int(event) + 1                                          # Change the bias on a slider event
        if(self.sg_pts <= self.sg_poly):
            self.sg_pts  = self.sg_poly + 1                                     # Window must be greater than poly order
            self.sg_pts += int((self.sg_pts+1)%2)                               # Window must be odd
        self.mainPanel.gridPanel.smooth()
        self.update()                                                           # Update this panel and the STS panel (to show the vertical dashed line at selected bias)
    ###########################################################################
    # STS Reference
    ###########################################################################
    def loadReference(self):
        stsPath      = super()._browseFile()
        if(not stsPath.endswith(".dat")):                                       # Needs to be dat file
            print("Expecting .dat file")
            return
        self.referencePath = stsPath
        self.showRef = True
        self.update()
    
    def removeReference(self):
        self.removeRef = not self.removeRef
        if(not self.referencePath):
            self.removeRef = False
        self.btn['RemRef'].configure(bg=['SystemButtonFace','red'][self.removeRef])
        self.update()
        
    def showReference(self):
        self.showRef = not self.showRef
        if(not self.referencePath):
            self.showRef = False
        self.update()
    
    def getReferenceForCurve(self,x,reference=[]):
        """
        This function is useful when the reference spectra is not exactly the 
        same range/number of points as the data. To return a valid reference, 
        the domain of the data must be within the domain of the refernce.
        Simple linear interpolation is used when the number of data points is
        greater than the number of points in the reference spectrum in the 
        overlapping region
        """
        if(not len(reference)):
            if(not self.referencePath): return 0*x
            reference = self.reference
        try:
            return np.interp(x, reference[0], reference[1])
        except Exception as e:
            print(e)
            return 0
        
    ###########################################################################
    # Browsing STS Files
    ###########################################################################
    def _browseMulti(self):                                                     # Select folder containing STS spectra to display. Returns False if no files found, otherwise true
        stsPath      = super()._browseFolder()
        if(stsPath):
            file_list    = os.listdir(stsPath)
            self.stsPos  = []
            self.datFile = [stsPath + "/" + f for f in file_list if f.endswith(".dat")] # Get .dat filenames in selected directory
            if(self.datFile):
                for df in range(len(self.datFile)):
                    dat = nap.read.Spec(self.datFile[df])                       # dat Spec object
                    
                    # Location of STS on image
                    x = (np.array(dat.header['X (m)']).astype(float)*self.mainPanel.pixelCalibration[0] - self.mainPanel.im_offset[0])
                    y = (np.array(dat.header['Y (m)']).astype(float)*self.mainPanel.pixelCalibration[1] - self.mainPanel.im_offset[1])
                    
                    ox,oy = (0,0)                                               # Origin before rotation is at 0,0 (bottom left)
                    rotAbout = self.mainPanel.lxy/2                             # Nanonis rotates frame about centre
                    angle = -math.pi*self.mainPanel.scanAngle/180.0             # Angle of the frame in nanonis (convert to rad)
                    oX,oY = super().rotate(rotAbout,(ox,oy),angle)              # Rotate the origin about the centre of the frame by angle
                    X = x - oX                                                  # x w.r.t new origin is X
                    Y = y - oY                                                  # y w.r.t new origin is Y
                    Xb = X*math.cos(angle) + Y*math.cos(math.pi/2 - angle)      # Xb is x w.r.t new basis
                    Yb = Y*math.cos(angle) + X*math.cos(math.pi/2 + angle)      # Yb is y w.r.t new basis
                    
                    self.stsPos.append([Xb,Yb])
                    self.mainPanel.update(upd=[0,3])
                return True
            else:
                print("No .dat files in folder")
                return False
    
    def _browseSingle(self):
        stsPath      = super()._browseFile()
        if(not stsPath.endswith(".dat")):                                       # Needs to be dat file
            print("Expecting .dat file")
            return                                                              # Return if no SXM file chosen
        self.datFile.append(stsPath)
        
        dat = nap.read.Spec(stsPath)                                            # dat Spec object
        
        # Location of STS on image
        x = (np.array(dat.header['X (m)']).astype(float)*self.mainPanel.pixelCalibration[0] - self.mainPanel.im_offset[0])
        y = (np.array(dat.header['Y (m)']).astype(float)*self.mainPanel.pixelCalibration[1] - self.mainPanel.im_offset[1])
        
        ox,oy = (0,0)                                                           # Origin before rotation is at 0,0 (bottom left)
        rotAbout = self.mainPanel.lxy/2                                         # Nanonis rotates frame about centre
        angle = -math.pi*self.mainPanel.scanAngle/180.0                         # Angle of the frame in nanonis (convert to rad)
        oX,oY = super().rotate(rotAbout,(ox,oy),angle)                          # Rotate the origin about the centre of the frame by angle
        X = x - oX                                                              # x w.r.t new origin is X
        Y = y - oY                                                              # y w.r.t new origin is Y
        Xb = X*math.cos(angle) + Y*math.cos(math.pi/2 - angle)                  # Xb is x w.r.t new basis
        Yb = Y*math.cos(angle) + X*math.cos(math.pi/2 + angle)                  # Yb is y w.r.t new basis
        
        self.stsPos.append([Xb,Yb])
        self.mainPanel.update(upd=[0,3])
    ###########################################################################
    # Custom STS Files
    ###########################################################################
    def _browseCustom(self):
        stsPath      = self._browseFile()
        if(not stsPath.endswith(".dat")):                                       # Needs to be dat file
            print("Expecting .dat file")
            return                                                              # Return if no SXM file chosen
        self.datFileCustom = stsPath
        self.mainPanel.customSTSBind()                                          # Follow logic for cursor bind in LineProfilePanel
        self.update()
        
    def setMarkSTS(self,stsPos,setMarker=False):
        self.customSTSPos = stsPos
        if(setMarker):
            self.datFile.append(self.datFileCustom)
            self.stsPos.append(stsPos)
            self.datFileCustom = []
            self.customSTSPos  = []
    
    def cancelMarkSTS(self):
        self.datFileCustom = []
        self.customSTSPos  = []
        self.update()
    ###########################################################################
    # Plot from location in STS Grid
    ###########################################################################
    def addFromGrid(self):
        if(self.mainPanel.gridPanel.active):
            self.mainPanel.gridPanel.extractBind()
        
    ###########################################################################
    # Average spectra from points within grid
    ###########################################################################
    def avgFromGrid(self):
        if(self.mainPanel.gridPanel.active):
            self.mainPanel.gridPanel.averageGridPointsBind()
        
    ###########################################################################
    # Misc Button Functions
    ###########################################################################
    def _undo(self):
        self.stsPos  = self.stsPos[0:-1]
        self.datFile = self.datFile[0:-1]
        self.mainPanel.update(upd=[0,3])
        
    def _reset(self):
        self.stsPos = []
        self.datFile = []
        self.mainPanel.update(upd=[0,3])
    
    def _scale(self):
        self.logScale = not self.logScale
        self.update()
    
    def _offset(self):
        self.stsOffset = not self.stsOffset
        self.update()
        
    def _cycleChannel(self):
        if(not self.datFile): return
        df = nap.read.Spec(self.datFile[0])
        channels = list(df.signals.keys())
        
        if(not self.dat_ychannel in channels):
            self.dat_ychannel = channels[0]
            return
        
        idx = channels.index(self.dat_ychannel) + 1
        if(idx == len(channels)): idx = 0
        self.dat_ychannel = channels[idx]
        
        self.btn['Channel'].configure(text=self.dat_ychannel)
        
        self.update()
        
    def datSpec(self,option):
        if(option == "Add Single"): self._browseSingle()
        if(option == "Add Manual"): self._browseCustom()
        if(option == "Add Folder"): self._browseMulti()
        if(option == "Undo Last"):  self._undo()
        if(option == "Clear All"):  self._reset()
        self.btn['datSpec'].set("STS.dat")
    
    def gridSpec(self,option):
        if(option == "Add Single"):   self.addFromGrid()
        if(option == "Add Averaged"): self.avgFromGrid()
        if(option == "Undo Single"):  self.mainPanel.gridPanel._undo()
        if(option == "Undo Averaged"):self.mainPanel.gridPanel.undoAverage()
        if(option == "Clear All"):    self.mainPanel.gridPanel._reset()
        self.btn['GridSpec'].set("STS.grid")
    
    def _reference(self,option):
        if(option == "Load New"): self.loadReference()
        if(option == "Hide"):
            self.showReference()
            newValues = ["Reference","Load New","Show"]
            self.btn["Reference"].configure(values=newValues)
        if(option == "Show"):
            self.showReference()
            newValues = ["Reference","Load New","Hide"]
            self.btn["Reference"].configure(values=newValues)
        self.btn['Reference'].set("Reference")
            
    def plotProps(self,option):
        if(option == "Toggle Offset"): self._offset()
        if(option == "Linear"):
            self._scale()
            newValues = ["Plot Props","Toggle Offset","Log"]
            self.btn['PlotProp'].configure(values=newValues)
        if(option == "Log"):
            self._scale()
            newValues = ["Plot Props","Toggle Offset","Linear"]
            self.btn['PlotProp'].configure(values=newValues)
        self.btn['PlotProp'].set("Plot Props")
        
    ###########################################################################
    # Save
    ###########################################################################
    def buildSaveDict(self):
        saveDict = {}
        saveDict['stsOffset'] = self.stsOffset
        saveDict['logScale']  = self.logScale
        saveDict['datFile']   = self.datFile
        saveDict['stsPos']    = self.stsPos
        
        saveDict['datFileCustom']   = self.datFileCustom
        saveDict['customSTSPos']    = self.customSTSPos
        saveDict['dat_xchannel']    = self.dat_xchannel
        saveDict['dat_ychannel']    = self.dat_ychannel
        
        saveDict['reference']       = self.reference
        saveDict['referencePath']   = self.referencePath
        saveDict['showRef']         = self.showRef
        saveDict['sg_pts']          = self.sg_pts
        saveDict['sg_poly']         = self.sg_poly
        saveDict['removeRef']       = self.removeRef
        
        saveDict['imprint']       = self.imprint
        
        return saveDict
    ###########################################################################
    # Load
    ###########################################################################
    def loadFromDict(self,loadDict):
        for key,value in loadDict.items():
            setattr(self,key,value)