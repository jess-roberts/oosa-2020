from __future__ import division
# Importing local classes
from task3 import changeDetection
from task3 import clipTiff
from task2 import handleTiff

# Importing external packages
import numpy as np
import matplotlib.pyplot as plt
import argparse
from scipy.ndimage import label
from shapely.geometry import Point
import pandas as pd
import time


def readCommands():
  """
  Read commandline arguments
  """
  p = argparse.ArgumentParser(description=("Contouring a raster"))
  p.add_argument("--interval", dest ="interval", type=int, default=50, help=("Contour interval (m)"))
  p.add_argument("--minX", dest ="minX", type=int, default=-1607050, help=("Minimum X bound"))
  p.add_argument("--maxX", dest ="maxX", type=int, default=-1572275, help=("Maximum X bound"))
  p.add_argument("--minY", dest ="minY", type=int, default=-281171, help=("Minimum Y Bound"))
  p.add_argument("--maxY", dest ="maxY", type=int, default=-20369, help=("Maximum Y bound"))
  p.add_argument("--output", dest ="outfile", type=str, default="raster_contours.tif", help=("Output filename"))
  cmdargs = p.parse_args()
  return cmdargs


class ContourRast(changeDetection):
    def roundCont(self,interval):
        """
            Reclassing the array's values to
            the contour interval set by the user
        """
        self.rounded = np.copy(self.array_difference) # copy array to round

        for i in np.arange(0,self.reference.nY):
            for j in np.arange(0,self.reference.nX):
                self.rounded[i][j] = interval*round(self.array_difference[i][j]/interval) # find its nearest-whole-multiple of the interval

        self.findEdge()

    def findEdge(self):
        """
            Finding values at the edge of interval change (i.e a contour)
            and taking the maximum value of that change
        """
        self.edge = np.copy(self.rounded)

        for i in np.arange(1,self.reference.nY): # search the data in the x dimension
            for j in np.arange(1,self.reference.nX): # search the data in the y dimension
                    surround_mean = np.nanmean(self.rounded[i-1:i+2,j-1:j+2])
                    # if the mean of all pixels isn't the same as the centre pixel (must be an edge)
                    # if its the maximum of the edge then use it (contour interval upwards)
                    if self.rounded[i][j] != surround_mean:
                         self.edge[i][j] = self.rounded[i][j] # then its a contour
                    else: # otherwise discard it as no data
                        self.edge[i][j] = np.nan
                    self.edge[0][j] = np.nan
                    self.edge[i][-1] = np.nan
                    self.edge[i][0] = np.nan
                    self.edge[-1][j] = np.nan

        self.findCont()

    def findCont(self):
        """
            Function to find the raster array value locations ideal
            for Contouring
        """

        self.cont = np.copy(self.edge)

        for i in np.arange(1,self.reference.nY): # search the data in the x dimension
            for j in np.arange(1,self.reference.nX): # search the data in the y dimension
                surround_max = np.nanmax(self.edge[i-1:i+2,j-1:j+2]) # find the maximum surrounding value
                if self.edge[i][j] == surround_max: # if the value == maximum then it must be the upper contour
                    self.cont[i][j] = self.edge[i][j] # so keep it
                else:
                    self.cont[i][j] = np.nan # otherwise clear the data point

        self.findPosition()

    def findPosition(self):
        """
            Extracting the latitude and longitude
            of the contour points
        """
        self.cont_lon = np.copy(self.cont)
        self.cont_lat = np.copy(self.cont)

        for i in np.arange(0,self.reference.nY): # search the data in the x dimension
            for j in np.arange(0,self.reference.nX): # search the data in the y dimension
                if np.isnan(self.cont_lon[i][j]) == False: # if it is a contour
                    self.cont_lon[i][j] = self.reference.xOrigin + (self.xRes*i) # find its longitude
                if np.isnan(self.cont_lat[i][j]) == False: # if it is a contour
                    self.cont_lat[i][j] = self.reference.yOrigin + (self.yRes*j) # find its latitude

        self.groupConts()


    def groupConts(self):
        """
            Grouping each line of unique contour
            values according to points adjacent (including
            the diagonal)
        """

        # Only works well if number of unique values isn't very high (ie contour interval is high), otherwise its slow
        values = np.unique(self.cont.ravel()) # extract all unique values to consider for grouping
        offset = 0
        self.result = np.zeros_like(self.cont) # set an empty array
        s = [[1,1,1], # structure feature to consider features diagonally as well
            [1,1,1],
            [1,1,1]]

        for v in values: # find each unique value and its adjacent values
            labelled, num_features = label(self.cont == v, structure=s)
            # label each unique combination of touching unique values
            self.result += labelled + offset*(labelled > 0)
            offset += num_features

        self.groupFeatures()

    def groupFeatures(self):
        """
            Creating dictionary to store each contour
            line's ID, co-orindates and value
        """
        # Find how many unique contours were made
        self.feature_ids = np.unique(self.result.ravel())

        self.list_of_features = []
        lon_list = []
        lat_list = []
        for k in np.arange(1,self.feature_ids.max()+1):
            for i in np.arange(1,self.reference.nY): # search the data in the x dimension
                for j in np.arange(1,self.reference.nX): # search the data in the y dimension
                    if self.result[i][j] == k:
                        # Separate grouped results according to their id (k)(and thus elevation value)
                        lon_list.append(float(self.cont_lon[i][j]))
                        lat_list.append(float(self.cont_lat[i][j]))
                        value = self.cont[i][j]

            # dictionary Grouping points of each contour line and the line's value
            self.list_of_features.append({'id': k, 'lon': lon_list, 'lat': lat_list, 'elev': value})
            lon_list = []
            lat_list = []

    def writeMultistring(self):
        """
            Writing the coordinates out to a Shapefile
        """
        try: # extract data values to a pandas datafrom
            df = pd.DataFrame([self.list_of_features.items()], columns=['elev','id','lat','lon'])
            geometry =[Point(xy) for xy in zip(df.lon,df.lat)]

            # assign its geometry
            geo_df = gp.GeoDataFrame(df,crs='epsg:3031',geometry=geometry)

            # write out as a shapefile
            geo_df.to_file(driver='ESRI Shapefile', filename='data.shp')
        except:
            print("Ah well you tried")


if __name__=="__main__":
    # The following script attempts to contour the 'difference' raster
    # which shows the change in elevation between 2009 and 2015.
    # This could be adapted to plot contours on whatever file desired
    # in the roundCont() function. Currently not possible as a command
    # line argument.
    start_time = time.time()

    cmd = readCommands()

    # Load the two filled DEMs (2009 and 2015) for clipping
    clip_file_1 = clipTiff(filename=r'./2009_LVIS_dem_window_15_filled_200m.tif',minX=cmd.minX,minY=cmd.minY,maxX=cmd.maxX,maxY=cmd.maxY)
    clip_file_2 = clipTiff(filename=r'./2015_LVIS_dem_window_85_filled_200m.tif',minX=cmd.minX,minY=cmd.minY,maxX=cmd.maxX,maxY=cmd.maxY)

    # Read out the clipped arrays
    array_1 = handleTiff(filename=str(clip_file_1.out_filename),readTiff=True)
    array_2 = handleTiff(filename=str(clip_file_2.out_filename),readTiff=True)

    out = ContourRast(array_1,array_2) # Loading in these arrays that we want
    out.roundCont(interval=cmd.interval) # finding the contours (of elevation difference) at a set interval

    out.writeMultistring() # writing out a shapefile of the contours
    out.writeTiff(array_to_write=out.cont,filename=cmd.outfile)
    out.writeTiff(array_to_write=out.result,filename="./results/contours_classed.tif") # writing out a raster of the contours

    print("--- %s seconds ---" % (time.time() - start_time))

    # plotting contour point locations
    plt.plot(-out.cont_lat,out.cont_lon)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Contour Point Locations")
    plt.savefig("Contour_Points.png")
