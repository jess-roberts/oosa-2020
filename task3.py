from osgeo import gdal
import argparse
from task2 import handleTiff
import numpy as np
import ogr, os, osr
import matplotlib.pyplot as plt

"""
Wider extent values:
minX = -2207050
maxX = -1002275
minY = -501171
maxY = -53369
"""

def readCommands():
  """
  Read commandline arguments
  """
  p = argparse.ArgumentParser(description=("Elevation change between two rasters"))
  p.add_argument("--minX", dest ="minX", type=int, default=-2207050, help=("Minimum X bound"))
  p.add_argument("--maxX", dest ="maxX", type=int, default=-1002275, help=("Maximum X bound"))
  p.add_argument("--minY", dest ="minY", type=int, default=-501171, help=("Minimum Y Bound"))
  p.add_argument("--maxY", dest ="maxY", type=int, default=-53369, help=("Maximum Y bound"))
  cmdargs = p.parse_args()
  return cmdargs

class clipTiff(object):
    """
        Class to standardize rasters for further analysis
    """
    def __init__(self,filename,minX,minY,maxX,maxY):
        self.warpRaster(filename,minX,minY,maxX,maxY)

    def warpRaster(self,filename,minX,minY,maxX,maxY):
        """
            Function using gdal.Warp to reproject a raster
            into a particular spatial extent for the EPSG:3031 projection
        """
        ds = gdal.Open(str(filename))
        self.out_filename = filename[:-4] + str("_clipped.tif") # creating output name
        try:
            ds = gdal.Warp(str(self.out_filename), filename, dstSRS='EPSG:3031', outputBounds=(minX,minY,maxX,maxY))
            ds = None
        except:
            print("Sorry your bounds choices were invalid") # checking user chose valid bounds

        return self.out_filename

class changeDetection(object):
    """
        Class to detect change between two rasters
    """
    def __init__(self,array1,array2):
        self.arrayCalc(array1,array2) # load in array objects (from Tiffs) created in handleTiff class
        self.volumnCalc(array1,array2)

    def arrayCalc(self,array1,array2):
        """
            Function to calculate the difference
            between two raster arrays
        """
        self.array_error = False # flag for calculus

        if array1.data.shape != array2.data.shape:
            print("You got an array problem boss") # arrays don't match each other
            self.array_error = True # set flag
        else:
            self.array_difference = array2.data - array1.data # otherwise find their difference

        self.reference = array2 = array1 # take each input array objects' attributes for this object

    def volumnCalc(self,array1,array2):
        """
            Function performing calculus on the arrays
            to work out the total volumn of change
            between them
        """
        if self.array_error == False: # if the input arrays match in shape (can be used for calculus)
            # get original resolution (pre-warping)
            self.xRes = round(self.reference.pixelWidth)
            self.yRes = -round(self.reference.pixelHeight)

            # find the area of each array cell
            self.cellsize = self.xRes*self.yRes # metres

            # set up new array
            self.vol_change_per_cell = np.copy(self.array_difference)

            # loop through extent
            for i in np.arange(0,self.reference.nY-1):
                for j in np.arange(0,self.reference.nX)-1:
                    # calculate volumn change per cell
                    self.vol_change_per_cell[i][j] = self.array_difference[i][j] * self.cellsize

            # total change (sum of all cells)
            self.total_vol_change = np.nansum(self.vol_change_per_cell.flat)

        # calculate total volumn per cell in each year
        array2.vol_per_cell = array2.data *  self.cellsize
        array2.total_vol = np.nansum(array2.vol_per_cell.flat)

        array1.vol_per_cell = array1.data *  self.cellsize
        array1.total_vol = np.nansum(array1.vol_per_cell.flat)

        return array1.total_vol, array2.total_vol


    def writeTiff(self,array_to_write,filename):
          """
          Take the filled elevation data and create an output raster
          """
          # string addition to output filename
          # set geolocation information (note geotiffs count down from top edge in Y)
          geotransform = (self.reference.xOrigin, self.xRes, 0, self.reference.yOrigin, 0, -self.yRes)

          # load data in to geotiff object
          dst_ds = gdal.GetDriverByName('GTiff').Create(filename, self.reference.nX, self.reference.nY, 1, gdal.GDT_Float32)
          dst_ds.SetGeoTransform(geotransform)    # specify coords
          srs = osr.SpatialReference()            # establish encoding
          srs.ImportFromEPSG(3031)                # WGS84 lat/long
          dst_ds.SetProjection(srs.ExportToWkt()) # export coords to file
          dst_ds.GetRasterBand(1).WriteArray(array_to_write)  # write image to the raster
          dst_ds.GetRasterBand(1).SetNoDataValue(np.NaN)  # set no data value
          dst_ds.FlushCache()                     # write to disk
          dst_ds = None

          print("Image written to",filename)


if __name__=="__main__":
    start_time = time.time()
    cmd = readCommands()

    # Two files being prepared for computation (standardisation prior to processing)
    clip_file_1 = clipTiff(filename=r'./2009/LVIS_dem_filled_200m.tif',minX=cmd.minX,minY=cmd.minY,maxX=cmd.maxX,maxY=cmd.maxY)
    clip_file_2 = clipTiff(filename=r'./2015/LVIS_dem_filled_200m.tif',minX=cmd.minX,minY=cmd.minY,maxX=cmd.maxX,maxY=cmd.maxY)

    # Reading out the clipped raster arrays
    array_1 = handleTiff(filename=str(clip_file_1.out_filename),readTiff=True)
    array_2 = handleTiff(filename=str(clip_file_2.out_filename),readTiff=True)

    # Reading these back in for calculations
    output = changeDetection(array_1,array_2)
    arr1_vol, arr2_vol = output.volumnCalc(array_1,array_2)

    # Write out the raster of change detection
    output.writeTiff(array_to_write=output.array_difference,filename="'./results/elevation_change_output.tif")

    print("--- %s seconds ---" % (time.time() - start_time))

    plt.plot()
    plt.ylabel("Change in Elevation (m)")
    plt.xlabel("Relative Latitude (Top to Bottom)")
    plt.title("Cross-sectional Change")
    plt.savefig("xSection_Elev_Change.png")
