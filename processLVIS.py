'''
Some example functions for processing LVIS data
'''

#######################################

import numpy as np
from lvisClass import lvisData
from pyproj import Proj, transform
from scipy.ndimage.filters import gaussian_filter1d


#######################################

class lvisGround(lvisData):
  '''
  LVIS class with extra processing steps
  '''

  #######################################################

  def estimateGround(self,sigThresh=5,statsLen=10,minWidth=3,sWidth=0.5):
    '''
    Processes waveforms to estimate ground
    Only works for bare Earth. DO NOT USE IN TREES
    '''
    # find noise statistics
    self.findStats(statsLen=statsLen)

    # set threshold
    threshold=self.setThreshold(sigThresh)


    # remove background
    self.denoise(threshold,minWidth=minWidth,sWidth=sWidth)


  #######################################################

  def setThreshold(self,sigThresh):
    '''
    Set a noise threshold
    '''
    threshold=self.meanNoise+sigThresh*self.stdevNoise
    return(threshold)

  #######################################################

  def reproject(self,inEPSG,outEPSG):
    '''
    Reproject footprint coordinates
    '''
    # set projections
    inProj=Proj(init="epsg:"+str(inEPSG))
    outProj=Proj(init="epsg:"+str(outEPSG))
    # reproject data
    x,y=transform(inProj,outProj,self.lon,self.lat)
    self.lon=x
    self.lat=y


  ##############################################

  def findStats(self,statsLen=10):
    '''
    Finds standard deviation and mean of noise
    '''

    # make empty arrays
    self.meanNoise=np.empty(self.nWaves)
    self.stdevNoise=np.empty(self.nWaves)

    # determine number of bins to calculate stats over
    res=(self.z[0,0]-self.z[0,-1])/self.nBins    # range resolution
    noiseBins=int(statsLen/res)   # number of bins within "statsLen"

    # loop over waveforms
    for i in range(0,self.nWaves):
      self.meanNoise[i]=np.mean(self.waves[i,0:noiseBins])
      self.stdevNoise[i]=np.std(self.waves[i,0:noiseBins])


  ##############################################

  def denoise(self,threshold,sWidth=0.5,minWidth=3):
    '''
    Denoise waveform data
    '''

    # find resolution
    res=(self.z[0,0]-self.z[0,-1])/self.nBins    # range resolution

    # make array for output
    self.denoised=np.full((self.nWaves,self.nBins),0)

    # loop over waves
    for i in range(0,self.nWaves):
      print("Denoising wave ",i,"of ",self.nWaves)

      # subtract mean background noise
      self.denoised[i]=self.waves[i]-self.meanNoise[i]

      # set all values less than threshold to zero
      self.denoised[i,self.denoised[i]<threshold[i]]=0.0

      # minimum acceptable width
      binList=np.where(self.denoised[i]>0.0)[0]
      for j in range(0,binList.shape[0]):       # loop over waveforms
        if((j>0)&(j<(binList.shape[0]-1))):    # are we in the middle of the array?
          if((binList[j]!=binList[j-1]+1)|(binList[j]!=binList[j+1]-1)):  # are the bins consecutive?
            self.denoised[i,binList[j]]=0.0   # if not, set to zero

      # smooth
      self.denoised[i]=gaussian_filter1d(self.denoised[i],sWidth/res)


#############################################################
