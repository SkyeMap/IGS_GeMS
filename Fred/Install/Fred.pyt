# -*- coding: utf-8 -*-

import importlib
import os
import sys

import arcpy

package_path = os.path.dirname(os.path.realpath(__file__)) + r'\Scripts'
sys.path.insert(1, package_path)

import IGS_Functions
reload(IGS_Functions)

#import GeMS_utilityFunctions
#import Linda_GeMS_Definition

#reload(GeMS_utilityFunctions)
#reload(Linda_GeMS_Definition)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [GDB_tool, MO_tool, XC_tool]


class GDB_tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create New Database"
        self.description = "This tool creates a new GeMS-style geodatabase"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(
        displayName="Output Workspace",
        name="outputDir",
        datatype="DEWorkspace",
        parameterType="Required",
        direction="Input")
        
        param1 = arcpy.Parameter(
        displayName="Name of new geodatabase",
        name="thisDB",
        datatype="GPString",
        parameterType="Required",
        direction="Input")
        
        param2 = arcpy.Parameter(
        displayName="Spatial reference system",
        name="coordSystem",
        datatype="GPCoordinateSystem",
        parameterType="Required",
        direction="Input")
        
        param3 = arcpy.Parameter(
        displayName="Optional feature classes, tables, and feature datasets",
        name="OptionalElements",
        datatype="GPString",
        parameterType="Optional",
        direction="Input",
        multiValue = True)
        param3.filter.type = "ValueList"
        param3.filter.list = ['CartographicLines','CorrelationOfMapUnits',
                              'DataSourcePolys','FossilPoints','GenericPoints',
                              'GeochemPoints','GeochronPoints','GeologicPoints',
                              'GeologicLines','IsoValueLines','MapUnitLines',
                              'MapUnitPoints','MapUnitOverlayPolys',
                              'MiscellaneousMapInformation','OrientationPoints',
                              'OverlayPolys','RepurposedSymbols','StandardLithology',
                              'Stations']
        
        param4 = arcpy.Parameter(
        displayName="Number of cross sections",
        name="nCrossSections",
        datatype='GPLong',
        parameterType="Optional",
        direction="Input")
        param4.filter.type = "Range"
        param4.filter.list = [0,26]
        param4.value = 0
        
        param5 = arcpy.Parameter(
        displayName="Enable edit tracking",
        name="trackEdits",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input")
        param5.value = True
        
        param6 = arcpy.Parameter(
        displayName="Add fields for cartographic representations",
        name="cartoReps",
        datatype="GPBoolean",
        parameterType="Required",
        direction="Input")
        param6.value = False
        
        param7 = arcpy.Parameter(
        displayName="Add LTYPE and PTTYPE",
        name="addLTYPE",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input")
        param7.value = True
        
        param8 = arcpy.Parameter(
        displayName="Add standard confidence values",
        name="addConfs",
        datatype="GPBoolean",
        parameterType="Required",
        direction="Input")
        param8.value = True
        
        params = [param0, param1, param2, param3, param4,
                  param5, param6, param7, param8]
        
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        
        outputDir               = parameters[0].valueAsText
        thisDB              = parameters[1].valueAsText
        coordSystem         = parameters[2].valueAsText
        OptionalElements    = parameters[3].valueAsText
        nCrossSections      = parameters[4].valueAsText
        trackEdits          = parameters[5].valueAsText
        cartoReps           = parameters[6].valueAsText
        addLTYPE            = parameters[7].valueAsText
        addConfs            = parameters[8].valueAsText
        
        IGS_Functions.gdbTool(outputDir,thisDB,coordSystem,OptionalElements,
        nCrossSections,trackEdits,cartoReps,addLTYPE,addConfs)
        return
    
    

class MO_tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Map Outline"
        self.description = "This tool runs the Map Outline Script"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(
        displayName="southeast longitude",
        name="SELongStr",
        datatype="GPDouble",
        parameterType="Required",
        direction="Input")
        
        param1 = arcpy.Parameter(
        displayName="southeast latitude",
        name="SELatStr",
        datatype="GPDouble",
        parameterType="Required",
        direction="Input")
        
        param2 = arcpy.Parameter(
        displayName="width (longitudinal extent)",
        name="dLong",
        datatype="GPDouble",
        parameterType="Required",
        direction="Input")
        param2.value = 7.5
        
        param3 = arcpy.Parameter(
        displayName="height (latitudinal extent)",
        name="dLat",
        datatype="GPDouble",
        parameterType="Required",
        direction="Input")
        param3.value = 7.5
        
        param4 = arcpy.Parameter(
        displayName="tic spacing",
        name="ticInterval",
        datatype="GPDouble",
        parameterType="Required",
        direction="Input")
        param4.value = 2.5
        
        param5 = arcpy.Parameter(
        displayName="Is NAD27",
        name="isNAD27",
        datatype="GPBoolean",
        parameterType="Required",
        direction="Input")
        param5.value = True
        
        param6 = arcpy.Parameter(
        displayName="output geodatabase",
        name="outgdb",
        datatype="DEWorkspace",
        parameterType="Required",
        direction="Input")
        
        param7 = arcpy.Parameter(
        displayName="output coordinate system",
        name="outSpRef",
        datatype="GPCoordinateSystem",
        parameterType="Required",
        direction="Input")
        
        param8 = arcpy.Parameter(
        displayName="scratch folder",
        name="scratch",
        datatype="DEWorkspace",
        parameterType="Required",
        direction="Input")
        
        params = [param0, param1, param2, param3, param4,
                  param5, param6, param7, param8]
        
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        SELongStr       = parameters[0].valueAsText
        SELatStr        = parameters[1].valueAsText
        dLong           = float(parameters[2].valueAsText)
        dLat            = float(parameters[3].valueAsText)
        ticInterval     = float(parameters[4].valueAsText)
        isNAD27         = parameters[5].valueAsText
        outgdb          = parameters[6].valueAsText
        outSpRef        = parameters[7].valueAsText
        scratch         = parameters[8].valueAsText
        IGS_Functions.mapOutline(SELongStr, SELatStr, dLong, dLat, ticInterval,
            isNAD27, outgdb, outSpRef, scratch)
        return


class XC_tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Project Map Data to Cross Section"
        self.description = "This tool runs the IGS Cross Section Script"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(
        displayName="GeMS-style geodatabase",
        name="gdb",
        datatype="DEWorkspace",
        parameterType="Required",
        direction="Input")
        
        param1 = arcpy.Parameter(
        displayName="Project all features in GeologicMap",
        name="projectAll",
        datatype="GPBoolean",
        parameterType="Required",
        direction="Input")
        param1.value = True
        
        param2 = arcpy.Parameter(
        displayName="Feature classes to Project",
        name="fcToProject",
        datatype="GPFeatureLayer",
        parameterType="Optional",
        direction="Input",
        multiValue = True)
        
        param3 = arcpy.Parameter(
        displayName="DEM",
        name="dem",
        datatype="DERasterDataset",
        parameterType="Required",
        direction="Input")
        
        param4 = arcpy.Parameter(
        displayName="Section line",
        name="xsLine",
        datatype=["DEShapefile","GPFeatureLayer"],
        parameterType="Required",
        direction="Input")
        
        param5 = arcpy.Parameter(
        displayName="Start quadrant",
        name="startQuadrant",
        datatype="GPString",
        parameterType="Required",
        direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = ["LOWER_LEFT", "LOWER_RIGHT",
        "UPPER_LEFT", "UPPER_RIGHT"]
        param5.value = "LOWER_LEFT"
        
        param6 = arcpy.Parameter(
        displayName="Output name token",
        name="outFdsTag",
        datatype="GPString",
        parameterType="Required",
        direction="Input")
        param6.value = "A"
        
        param7 = arcpy.Parameter(
        displayName="Vertical exaggeration",
        name="vertEx",
        datatype="GPDouble",
        parameterType="Optional",
        direction="Input")
        param7.value = 1
        
        param8 = arcpy.Parameter(
        displayName="Selection distance",
        name="bufferDistance",
        datatype="GPDouble",
        parameterType="Required",
        direction="Input")
        param8.value = 9999
        
        param9 = arcpy.Parameter(
        displayName="Add LTYPE and PTTYPE",
        name="addLTYPE",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input")
        param9.value = False
                
        param10 = arcpy.Parameter(
        displayName="Force exit",
        name="forceExit",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input")
        param10.value = False

        param11 = arcpy.Parameter(
        displayName="Scratch Geodatabase",
        name="scratchws",
        datatype="DEWorkspace",
        parameterType="Required",
        direction="Input")

        param12 = arcpy.Parameter(
        displayName="Save intermediate data",
        name="saveIntermediate",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input")
        param12.value = False
        
        params = [param0, param1, param2, param3, param4,
                  param5, param6, param7, param8, param9,
                  param10, param11, param12]
        
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        
        gdb             = parameters[0].valueAsText
        projectAll      = parameters[1].valueAsText
        fcToProject     = parameters[2].valueAsText
        dem             = parameters[3].valueAsText
        xsLine          = parameters[4].valueAsText
        startQuadrant   = parameters[5].valueAsText
        outFdsTag       = parameters[6].valueAsText
        vertEx          = float(parameters[7].valueAsText)
        bufferDistance  = float(parameters[8].valueAsText)
        addLTYPE        = parameters[9].valueAsText
        forceExit       = parameters[10].valueAsText
        scratchws       = parameters[11].valueAsText
        saveIntermediate = parameters[12].valueAsText
        
        IGS_Functions.xcTool(gdb,projectAll,fcToProject,dem,xsLine,startQuadrant,outFdsTag,
        vertEx,bufferDistance,addLTYPE,forceExit,scratchws,saveIntermediate)
        return