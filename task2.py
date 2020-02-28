import numpy as np
import rasterio
import gdal, ogr, os, osr
import pandas as pd
import argparse
from processLVIS import lvisGround
from lvisClass import lvisData
from task1 import flightLine
from scipy.ndimage import label, binary_dilation
from rasterio.merge import merge
from rasterio.plot import show
import glob
import time

def readCommands():
  """
  Read commandline arguments
  """
  p = argparse.ArgumentParser(description=("Converting multiple LVIS files to a raster"))
  p.add_argument("--outres", dest ="outRes", type=int, default=200, help=("Output resolution (m)"))
  p.add_argument("--output", dest ="outName", type=str, default='lvis_rast_it_out.tif', help=("Output filename"))
  p.add_argument("--inEPSG", dest ="inEPSG", type=int, default=4326, help=("Input projection"))
  p.add_argument("--outEPSG", dest ="outEPSG", type=int, default=3031, help=("Output projection"))
  p.add_argument("--minX", dest ="minX", type=int, default=250, help=("Minimum X bound"))
  p.add_argument("--maxX", dest ="maxX", type=int, default=290, help=("Maximum X bound"))
  p.add_argument("--minY", dest ="minY", type=int, default=-90, help=("Minimum Y Bound"))
  p.add_argument("--maxY", dest ="maxY", type=int, default=-80, help=("Maximum Y bound"))
  p.add_argument("--year", dest ="LVISyear", type=int, default=2009, help=("Year of LVIS survey"))
  cmdargs = p.parse_args()
  return cmdargs


class handleTiff(object):
    def __init__(self,filename,readTiff=False,bufferTiff=False):
        if(readTiff):
            self.readRaster(filename)

        if(bufferTiff):
            self.getSurround(window)
            self.writeFilledTiff(filename)

    def readRaster(self,filename):
        '''
        Read a geotiff in to RAM
        '''
        # open a dataset object
        ds=gdal.Open(str(filename))
        # could use gdal.Warp to reproject if wanted?

        # read data from geotiff object
        self.nX=ds.RasterXSize             # number of pixels in x direction
        self.nY=ds.RasterYSize             # number of pixels in y direction
        # geolocation tiepoint
        transform_ds = ds.GetGeoTransform()# extract geolocation information
        self.xOrigin=transform_ds[0]       # coordinate of x corner
        self.yOrigin=transform_ds[3]       # coordinate of y corner
        self.pixelWidth=transform_ds[1]    # resolution in x direction
        self.pixelHeight=transform_ds[5]   # resolution in y direction
        # read data. Returns as a 2D numpy array
        self.data=ds.GetRasterBand(1).ReadAsArray(0,0,self.nX,self.nY)

        return self.data


    def getSurround(self,window):
      """
      Function to differentiate between no data to fill
      and no data to leave alone
      """
      cols = self.data.shape[0]
      rows = self.data.shape[1]

      self.fill = np.copy(self.data)

      for i in np.arange(window,cols-window): # search the data in the x dimension
          for j in np.arange(window,rows-window): # search the data in the y dimension
                  surround_sum = np.nanmean(self.data[i-window:i+window+1,j-window:j+window+1])
                  if np.isfinite(surround_sum) == True:
                      self.fill[i][j] = surround_sum
                  else:
                      self.fill[i][j] = self.data[i][j] # check the sum of surrounding values

    def writeFilledTiff(self,filename):
      """
      Take the filled elevation data and create an output raster
      """
      # set geolocation information (note geotiffs count down from top edge in Y)
      geotransform = (self.xOrigin, self.pixelWidth, 0, self.yOrigin, 0, self.pixelHeight)

      # load data in to geotiff object
      dst_ds = gdal.GetDriverByName('GTiff').Create(filename, self.nX, self.nY, 1, gdal.GDT_Float32)
      dst_ds.SetGeoTransform(geotransform)    # specify coords
      srs = osr.SpatialReference()            # establish encoding
      srs.ImportFromEPSG(3031)                # WGS84 lat/long
      dst_ds.SetProjection(srs.ExportToWkt()) # export coords to file
      dst_ds.GetRasterBand(1).WriteArray(self.fill)  # write image to the raster
      dst_ds.GetRasterBand(1).SetNoDataValue(np.nan)  # set no data value
      dst_ds.FlushCache()                     # write to disk
      dst_ds = None

      print("Image written to",filename)

if __name__=="__main__":
    start_time = time.time()
    cmd = readCommands()
    # set the directory
    """
    dataDir = b'/geos/netdata/avtrain/data/3d/oosa/assignment/lvis/'+str(cmd.LVISyear)+'/'
    x0 = cmd.minX
    x1 = cmd.maxX
    y0 = cmd.minY
    y1 = cmd.maxY

    h5s = []
    for file in os.listdir(dataDir):
        file = str(file)
        if file.endswith(".h5"): # take the files we want
            h5s.append(os.path.join(dataDir,file)) # make a list of them

    # loop through these files
    for h5 in h5s:
        # take these bounds with processing
        lvis = flightLine(filename=h5,minX=x0,minY=y0,maxX=x1,maxY=y1)
        # take checkpoint which is set upon reading the file
        # checkpoint == 0 means it contains no data
        # checkpoint == 1 means it contains data and thus to continue...
        if lvis.checkpoint == 1:
            # denoise the data and find the ground
            lvis.setElevations()
            lvis.estimateGround()
            lvis.CofG()
            lvis.reproject(inEPSG=4326,outEPSG=3031)

            # write out filled data to a tiff
            lvis.writeSingleTiff(filename=h5,res=cmd.outRes)

            # then start all over again!
    """
    # directory holding the tifs processd above
    tifDir = r'./'+str(cmd.LVISyear)+'/'
    # output name
    out_tif = r'./'+str(cmd.LVISyear)+'/'+str(cmd.LVISyear)+'_LVIS_merged_200m.tif'

    # criteria to find the geotiffs
    search_criteria = '*.tif'
    tifs = os.path.join(tifDir, search_criteria)

    # taking all the files that match and globbing together
    dem_fps = glob.glob(tifs)

    # opening each of these file names and putting them into a list for the merge
    tifs_4_mosaic = []
    for fp in dem_fps:
        src = rasterio.open(fp)
        tifs_4_mosaic.append(src)

    # merging them
    dest, out_trans = merge(tifs_4_mosaic) # merge returns single array

    #updating the metadata
    out_meta = src.meta.copy()
    out_meta.update({"driver": "Gtiff",
                        "height": dest.shape[1],
                        "width": dest.shape[2],
                        "transform": out_trans})

    # writing out the merged file
    with rasterio.open(out_tif, "w", **out_meta) as dest1:
        dest1.write(dest)

    # writing back in this merged file with smaller bounds
    dem = handleTiff(filename=out_tif,readTiff=True)
    dem.getSurround(window=30)

    # write out filled dem
    dem.writeFilledTiff(filename='./'+str(cmd.LVISyear)+'/'+str(cmd.LVISyear)+"_LVIS_dem_filled_200m.tif")

    print("--- %s seconds ---" % (time.time() - start_time))
