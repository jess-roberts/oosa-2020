import numpy as np
import gdal, ogr, os, osr
import argparse
from processLVIS import lvisGround
import time

def readCommands():
  '''
  Read commandline arguments
  '''
  p = argparse.ArgumentParser(description=("Converting one LVIS file to a raster"))
  p.add_argument("--input", dest ="inName", type=str, default='/geos/netdata/avtrain/data/3d/oosa/assignment/lvis/2015/ILVIS1B_AQ2015_1017_R1605_057119.h5', help=("Input filename"))
  p.add_argument("--outres", dest ="outRes", type=int, default=10, help=("Output resolution (m)"))
  p.add_argument("--output", dest ="outName", type=str, default='lvis_flightline_raster_output.tif', help=("Output filename"))
  p.add_argument("--inEPSG", dest ="inEPSG", type=int, default=4326, help=("Input projection"))
  p.add_argument("--outEPSG", dest ="outEPSG", type=int, default=3031, help=("Output projection"))
  cmdargs = p.parse_args()
  return cmdargs

class flightLine(lvisGround):

  def CofG(self):
    '''
    Find centre of gravity of denoised waveforms
    sets this to an array of ground elevation
    estimates, zG
    '''

    # allocate space and put no data flags
    self.zG=np.full((self.nWaves),np.nan)

    # loop over waveforms
    for i in range(0,self.nWaves):
      if(np.sum(self.denoised[i])>0.0):   # avoid empty waveforms (clouds etc)
        self.zG[i]=np.average(self.z[i],weights=self.denoised[i])

  def writeSingleTiff(self,res,filename):
      '''
      Make a geotiff from an array of points
      '''

      # determine bounds
      minX=np.min(self.lon)
      maxX=np.max(self.lon)
      minY=np.min(self.lat)
      maxY=np.max(self.lat)

      # determine image size
      self.nX=int((maxX-minX)/res+1)
      self.nY=int((maxY-minY)/res+1)

      # pack in to array
      self.imageArr=np.full((self.nY,self.nX),np.nan)        # make an array of missing data flags

      xInds=np.array((self.lon-minX)/res,dtype=int)  # determine which pixels the data lies in
      yInds=np.array((maxY-self.lat)/res,dtype=int)  # determine which pixels the data lies in

      # this is a simple pack which will assign a single footprint to each pixel
      self.imageArr[yInds,xInds]=self.zG

      self.imageArr=np.where(self.imageArr == -999.0, np.nan, self.imageArr)

      # set geolocation information (note geotiffs count down from top edge in Y)
      geotransform = (minX, res, 0, maxY, 0, -res)

      # load data in to geotiff object
      dst_ds = gdal.GetDriverByName('GTiff').Create(filename,self.nX,self.nY, 1, gdal.GDT_Float32)

      dst_ds.SetGeoTransform(geotransform)    # specify coords
      srs = osr.SpatialReference()            # establish encoding
      srs.ImportFromEPSG(3031)                # WGS84 lat/long
      dst_ds.SetProjection(srs.ExportToWkt()) # export coords to file
      dst_ds.GetRasterBand(1).WriteArray(self.imageArr)  # write image to the raster
      dst_ds.GetRasterBand(1).SetNoDataValue(np.nan)  # set no data value
      dst_ds.FlushCache()                     # write to disk
      dst_ds = None

      print("Image written to",filename)
      return


if __name__=="__main__":
    start_time = time.time()
    com = readCommands()
    bds = flightLine(filename=com.inName,onlyBounds=True)

    # set bounds (entire set in this example - but useful for subsetting in other cases)
    x0 = bds.bounds[0]
    y0 = bds.bounds[1]
    x1 = bds.bounds[2]
    y1 = bds.bounds[3]

    # read data
    lvis = flightLine(filename=com.inName,minX=x0,minY=y0,maxX=x1,maxY=y1)

    if lvis.checkpoint == 1:
        # finding the ground
        lvis.setElevations()
        lvis.estimateGround()
        lvis.CofG()
        lvis.reproject(inEPSG=com.inEPSG,outEPSG=com.outEPSG)

        # write out the elevation to a .tif
        lvis.writeSingleTiff(filename=com.outName,res=com.outRes)

    print("--- %s seconds ---" % (time.time() - start_time))
