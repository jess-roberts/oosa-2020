# OOSA Assignment 2020

This repository contains 6 scripts, 4 of which have been specifically constructed to answer the tasks set by the assignment for 'object-oriented programming and spatial algorithms' (OOSA) course at the University of Edinburgh. Each of the scripts (task 1-4) are described below in accordance with the question they were answering. 

The overall aim of this assignment was to write programs capable of handling LVIS (both singular files and batch processing of multiple) LiDAR data, namely over Antarctica as part of the [IceBridge mission](https://lvis.gsfc.nasa.gov/Home/index.html) where the data is also available to download. The assumed file structure in the scripts is as follows:

>./*Working directory*<br>
././*2015* (for 2015 file IO)<br>
././*2009* (for 2009 file IO)<br>
././*results* (for results IO)<br>

## task1.py
#### Reading a single LVIS flight line

The code submitted for this task involves the class flightLine inheriting `lvisGround`, a class which has inherited `lvisData` in the files provided in the [OOSA-code-public repository](https://github.com/edinburgh-university-OOSA/OOSA-code-public), designed to process and read the LVIS data respectively. The code operates by finding the bounds of the dataset submitted, then using these bounds to define what area of the dataset is written into a geotiff format.

The processing steps run once a checkpoint condition is met. This `flightLine.checkpoint` condition represents a flag which is set when the object is initialised in `lvisData.readLVIS()`, indicating whether the dataset (or its subset) contains any data, thus preventing the code from trying to run analysis on an empty dataset and crashing out. If the dataset is not empty, the `flightLine.CofG()` function is run to correct the elevations found in `lvisData.setElevations()`, before spatial indexing and geo-transformation into raster format, after reprojection to a metric system (`lvisData.reproject()`), written out by `flightLine.WriteSingleTiff()`.

Command line arguments have been set for this file as follows:

>`--input` [input file] *Default: /geos/netdata/avtrain/data/3d/oosa/assignment/lvis/2015/ILVIS1B_AQ2015_1017_R1605_057119.h5*<br>
`--output` [output filename] *Default: “lvis_flightline_raster_output.tif”*<br>
`--outres` [output resolution (m)] *Default: 10*<br>

Example: `python3 task1.py --output ‘another_name.tif’ --outres 25`

## task2.py
#### Reading multiple flight lines into a DEM

The code submitted for this task is an evolution of the script submitted for Task 1, enabling significantly more user control (with more command line arguments to control key variables) as well as the automated batch processing, including reprojection to a desired resolution, of all relevant files prior to then merging them to later gap-fill and convert into a DEM.

The main difference between the Task 1 and 2 script is the addition of the class `fillTiff`. While the first part of the script initialised in the main block iterates over the class `flightLine` from Task 1 which writes a LVIS data object into a geotiff, before then writing over that object to save memory, and repeats the process for all files. The second half of the block then reads these geotiffs back in (`fillTiff.readRaster()`), merges them together (using `rasterio.merge()`) then attempts to fill any holes (`fillTiff.getSurround()`) in the data before reading it back out (`fillTiff.writeFilledTiff()`). 

The additional command line arguments are as follows:

The class flightLine is imported from Task 1, which the additional following command line commands added:

>`--inEPSG` [co-ordinate system of the input data] *Default: 4326*<br>
`--outEPSG` [co-ordinate system of the output data] *Default: 3031*<br>
`--minX` [minimum X of bounding box] *Default: 260*<br>
`--maxX` [maximum X of bounding box] *Default: 290*<br>
`--minY` [minimum Y of bounding box] *Default: -90*<br>
`--maxY` [maximum Y of bounding box] *Default: -80*<br>
`--year` [year of LVIS data to process] *Default: 2009*<br>
`--window` [search area for focal function gap filling] *Default: 30*<br>

Example usage: `python3 task2.py --year 2015 --window 50`

The default values for the command line arguments are currently set to optimise data processing. The bounding box values isolate data contained in Antarctica, and the default year (2009) represents the smaller dataset to process (compared to 2015). Projected system EPSG:3031 is set as the output default co-ordinate system as it is specific to Antarctica and its unit is metres, allowing a sensible resolution (of metres) to be set later on. 

## task3.py
#### Change detection and calculation between DEMs

This script starts with a standardisation step, allowing the user to define the area they wish to investigate between the DEMs, otherwise an approximate default window of overlap is set. These standardised rasters are then read back into the script as arrays (`handleTiff.readTiff=True`), before being passed into the changeDetection class for calculations. Calculations include simply finding the difference in elevation (`changeDetection.arrayCalc()`) and also calculating the total volume difference as a result (`changeDetection.volumeCalc()`). 

The array of choice (although not by the command line as it depends on the objects having been initialised) is then read out to a raster (`changeDetection.writeTiff()`) to show any change calculated. The total volume of change is also available.

This file can use the following command line arguments to determine the area of overlap the user wants to investigate:

>`--minX` [minimum X of bounding box] *Default: 260*<br>
`--maxX` [maximum X of bounding box] *Default: 290*<br>
`--minY` [minimum Y of bounding box] *Default: -90*<br>
`--maxY` [maximum Y of bounding box] *Default: -80*<br>

Example usage: `python3 task3.py --minX 240 --maxX 300 --minY -100 --maxY -70`

## task4.py
### Contour generation

This script provides the foundation for constructing contours from 3-dimensional data of any kind. Currently, it is set to draw contours for the raster which shows elevation change (ie lines of constant change) but the array can be changed in `array_to_write` argument of `ContourRast.writeTiff()`. The idea of this task is not to use a contour package but instead create a customisable one.

This algorithm starts by taking the target array (for contouring) and reclassing each value into its respective contour interval (`ContourRast.roundCont()`) which can be defined by the user on the command line. These reclassed values are then searched to see if they are entirely surrounded by alike values, and thus are not representative of a change interval. Those that failed that test, are considered 'edge' values and therefore viable for contouring in the function `ContourRast.findEdge()`. Once the edge values have been isolated, then algorithm checks the surrounding values again, and instead looks for the maximum as a contour is meant to represent a step-up interval. Any value that is not the maximum in its immediate vicinity is also discarded as *not* a contour (`ContourRast.findCont()`). 

Next, these array values identified as contours need to be grouped according to the line they form (as not all values of '10m' in the array will comprise part of the same contour line). For this, `ContourRast.groupConts()` identifies all the unique values it must search for, within a defined search structure (to include diagonal connections) and labels to separate groups of unique values accordingly. The actual position of these 'contour points' of the array must also be found. This is done in `ContourRast.findPosition()` which takes the origin of the array, its resolution and the contour points' relative position (index) to calculate its longitude and latitude in real space.

The penultimate function `ContourRast.groupFeatures()` creates a list, wherein each item of the list is a dictionary grouping the unique ID of the contour line (from `ContourRast.groupConts()`), the latitude and longitude of all the points in that line (from `ContourRast.findPosition()`) and the line's elevation value (originally from `ContourRast.roundCont()`). The outputs of this script is a rasterized contour geotiff and a .png of a plot of the contour points.

The following command line arguments are available:

>`--interval` [contour interval (m)] *Default:50*<br>
`--minX` [minimum X of bounding box] *Default: -1607050*<br>
`--maxX` [maximum X of bounding box] *Default: -1572275*<br>
`--minY` [minimum Y of bounding box] *Default: -281171*<br>
`--maxY` [maximum Y of bounding box] *Default: -20369*<br>
`--output` [output filename] *Default: "raster_contours.tif*<br>

Example usage: `python3 task4.py --interval 25 --minX -2207050 --maxX -1002275 -minY -501171 --maxY -53369`

*Note: the default CRS here is EPSG:3031*

The final function `ContourRast.writeMultiString()` does not currently work, but represents an ideal development whereby the the contour points are translated to a multi-polyline shapefile for use in program such as ArcGIS and QGIS.  
