# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 15:18:13 2021

@author: skye
"""
import arcpy
import copy
import importlib
import math
import os
import sys

import GeMS_utilityFunctions
import Linda_GeMS_Definition
from Linda_GeMS_Definition import tableDict, GeoMaterialConfidenceValues, DefaultExIDConfidenceValues, IDLength

reload(GeMS_utilityFunctions)
reload(Linda_GeMS_Definition)


"""The source code of the tool."""
    
versionString = 'mapOutline_Arc10.py, version of 2 September 2017'

"""
INPUTS
maxLongStr  # in D M S, separated by spaces. Decimals OK.
            #   Note that west values must be negative
            #   -122.625 = -122 37 30
            #   if value contains spaces it should be quoted
minLatStr   # DITTO
dLong       # in decimal degrees OR decimal minutes
            #   values <= 5 are assumed to be degrees
            #   values  > 5 are assumed to be minutes
dLat        # DITTO
            # default values of dLong and dLat are 7.5
ticInterval # in decimal minutes! Default value is 2.5
isNAD27     # NAD27 or NAD83 for lat-long locations
outgdb      # existing geodatabase to host output feature classes
outSpRef    # output spatial reference system
scratch     # scratch folder, must be writable
"""

def addMsgAndPrint(msg, severity=0): 
    	# prints msg to screen and adds msg to the geoprocessor (in case this is run as a tool) 
    	# print msg 
    	try: 
    	  for string in msg.split('\n'): 
    		# Add appropriate geoprocessing message 
    		if severity == 0: 
    			arcpy.AddMessage(string) 
    		elif severity == 1: 
    			arcpy.AddWarning(string) 
    		elif severity == 2: 
    			arcpy.AddError(string) 
    	except: 
    		pass 


def dmsStringToDD(dmsString):
    dms = dmsString.split()
    dd = abs(float(dms[0]))
    if len(dms) > 1:
        dd = dd + float(dms[1])/60.0
    if len(dms) > 2:
        dd = dd + float(dms[2])/3600.0
    if dms[0][0] == '-':
        dd = 0 - dd
    return(dd)


def ddToDmsString(dd):
    degreeSymbol = '°'
    minuteSymbol = "'"
    secondSymbol = '"'
    dd = abs(dd)
    degrees = int(dd)
    minutes = int((dd-degrees)* 60)
    seconds = int(round((dd-degrees-(minutes/60.0))* 3600))
    if seconds == 60:
        minutes = minutes+1
        seconds = 0
    dmsString = str(degrees)+degreeSymbol
    dmsString = dmsString+str(minutes)+minuteSymbol
    if seconds <> 0:
        dmsString = dmsString+str(seconds)+secondSymbol
    return dmsString


def fieldNameList(aTable):
    fns = arcpy.ListFields(aTable)
    fns2 = []
    for fn in fns:
        fns2.append(fn.name)
    return fns2



def gdbTool(outputDir,thisDB,coordSystem,OptionalElements,
        nCrossSections,trackEdits,cartoReps,addLTYPE,addConfs):
    
    # GeMS_CreateDatabase_Arc10.1.py
    #   Python script to create an empty NCGMP09-style
    #   ArcGIS 10 geodatabase for geologic map data
    #
    #   Ralph Haugerud, USGS
    #
    # RUN AS TOOLBOX SCRIPT FROM ArcCatalog OR ArcMap
    
    # 9 Sept 2016: Made all fields NULLABLE
    # 19 Dec 2016: Added GeoMaterialDict table, domains
    # 8 March 2017: Added  ExistenceConfidence, IdentityConfidence, ScientificConfidence domains, definitions, and definitionsource
    # 17 March 2017  Added optional table MiscellaneousMapInformation
    # 30 Oct 2017  Moved CartoRepsAZGS and GeMS_lib.gdb to ../Resources
    # 4 March 2018  changed to use writeLogfile()
    # 8 June 2020 In transDict (line 31), changed 'NoNulls':'NON_NULLABLE' to 'NoNulls':'NULLABLE'
    #   " "       Fixed bug with addTracking(), where EnableEditorTracking_management apparently wants in_dataset to be a full pathname
    #   " "       Added MapUnitLines to list of feature classes that could be created (line 153)
    # 28 Sept 2020 Now defines coordinate system for CMU and cross section feature datasets (= map coordinate system)
    # 7 Oct 2020 Improved definition of cross section feature classes to match specification
    # 9 November 2020 added def rename_field to avoid use of AlterField which was throwing an error for some undeterminable reason - ET
    # 23 December 2020: Changed how MapUnitPoints feature class is created, so that it follows definition in GeMS_Definitions.py - RH
    
    
    versionString = 'GeMS_CreateDatabase_Arc10.py, version of 23 December 2020'
    
    debug = True
    
    default = '#'
    
    
    
    #cartoReps = False # False if cartographic representations will not be used
    
    transDict =     { 'String': 'TEXT',
                      'Single': 'FLOAT',
                      'Double': 'DOUBLE',
                      'NoNulls':'NULLABLE', #NB-enforcing NoNulls at gdb level creates headaches; instead, check while validating
                      'NullsOK':'NULLABLE',   
                      'Optional':'NULLABLE',
                      'Date'  : 'DATE'  }
    
    usage = """Usage:
       systemprompt> GeMS_CreateDatabase_Arc10.1.py <directory> <geodatabaseName> <coordSystem>
                    <OptionalElements> <#XSections> <AddEditTracking> <AddRepresentations> <AddLTYPE>
       <directory> is existing directory in which new geodatabaseName is to 
          be created, use # for current directory
       <geodatabaseName> is name of gdb to be created, with extension
          .gdb causes a file geodatabase to be created
          .mdb causes a personal geodatabase to be created
       <coordSystem> is a fully-specified ArcGIS coordinate system
       <OptionalElements> is either # or a semicolon-delimited string specifying
          which non-required elements should be created (e.g.,
          OrientationPoints;CartographicLines;RepurposedSymbols )
       <#XSections> is an integer (0, 1, 2, ...) specifying the intended number of
          cross-sections
       <AddEditTracking> is either true or false (default is true). Parameter is ignored if
          ArcGIS version is less than 10.1
       <AddRepresentations> is either true or false (default is false). If true, add
          fields for Cartographic representions to all feature classes
       <AddLTYPE> is either true or false (default is false). If true, add LTYPE field
          to feature classes ContactsAndFaults and GeologicLines, add PTTYPE field
          to feature class OrientationData, and add PTTYPE field to MapUnitLabelPoints    
    
      Then, in ArcCatalog:
      * If you use the CorrelationOfMapUnits feature data set, note that you will 
        have to manually create the annotation feature class CMUText and add field 
        ParagraphStyle. (I haven't yet found a way to script the creation of an 
        annotation feature class.)
      * If there will be non-standard point feature classes (photos, mineral 
        occurrences, etc.), copy/paste/rename feature class GenericPoint or 
        GenericSample, as appropriate, rename the _ID field, and add necessary
        fields to the new feature class.
      * Load data, if data already are in GIS form. 
      Edit data as needed.
    
    """
    
    def addMsgAndPrint(msg, severity=0): 
        # prints msg to screen and adds msg to the geoprocessor (in case this is run as a tool) 
        #print msg 
        try: 
            for string in msg.split('\n'): 
                # Add appropriate geoprocessing message 
                if severity == 0: 
                    arcpy.AddMessage(string) 
                elif severity == 1: 
                    arcpy.AddWarning(string) 
                elif severity == 2: 
                    arcpy.AddError(string) 
        except: 
            pass 
    
    def createFeatureClass(thisDB,featureDataSet,featureClass,shapeType,fieldDefs):
        addMsgAndPrint('    Creating feature class '+featureClass+'...')
        try:
            arcpy.env.workspace = thisDB
            arcpy.CreateFeatureclass_management(featureDataSet,featureClass,shapeType)
            thisFC = thisDB+'/'+featureDataSet+'/'+featureClass
            for fDef in fieldDefs:
                try:
                    if fDef[1] == 'String':
                        # note that we are ignoring fDef[2], NullsOK or NoNulls
                        arcpy.AddField_management(thisFC,fDef[0],transDict[fDef[1]],'#','#',fDef[3],'#','NULLABLE')
                    else:
                        # note that we are ignoring fDef[2], NullsOK or NoNulls
                        arcpy.AddField_management(thisFC,fDef[0],transDict[fDef[1]],'#','#','#','#','NULLABLE')
                except:
                    addMsgAndPrint('Failed to add field '+fDef[0]+' to feature class '+featureClass)
                    addMsgAndPrint(arcpy.GetMessages(2))
        except:
            addMsgAndPrint(arcpy.GetMessages())
            addMsgAndPrint('Failed to create feature class '+featureClass+' in dataset '+featureDataSet)
            
    def addTracking(tfc):
        if arcpy.Exists(tfc):
            addMsgAndPrint('    Enabling edit tracking in '+tfc)
            try:
                arcpy.EnableEditorTracking_management(tfc,'created_user','created_date','last_edited_user','last_edited_date','ADD_FIELDS','DATABASE_TIME')
            except:
                addMsgAndPrint(tfc)
                addMsgAndPrint(arcpy.GetMessages(2))
    
    
    def cartoRepsExistAndLayer(fc):
        crPath = os.path.dirname(os.path.realpath(__file__))+'/../Resources/CartoRepsAZGS'      
        hasReps = False
        repLyr = ''
        for repFc in 'ContactsAndFaults','GeologicLines','OrientationPoints':
            if fc.find(repFc) > -1:
                hasReps = True
                repLyr = os.path.join(crPath,repFc+'.lyr')
        return hasReps,repLyr
        
    def rename_field(defs, start_name, end_name):
        """renames a field in a list generated from tableDict for
        special cases; CrossSections and OrientationPoints
        instead of using AlterField after creation which was throwing errors"""
        f_list = copy.deepcopy(defs)
        list_item = [n for n in f_list if n[0] == start_name] #finds ['MapUnitPolys_ID', 'String', 'NoNulls', 50], for instance
        i = f_list.index(list_item[0]) #finds the index of that item
        f_list[i][0] = end_name #changes the name in the list
        arcpy.AddMessage(f_list[i][0] +  ' becoming ' + end_name)
        arcpy.AddMessage(f_list)
        return f_list
    
    def main(thisDB,coordSystem,nCrossSections,trackEdits,cartoReps,addLTYPE,addConfs):
        # create feature dataset GeologicMap
        addMsgAndPrint('  Creating feature dataset GeologicMap...')
        try:
            arcpy.CreateFeatureDataset_management(thisDB,'GeologicMap',coordSystem)
        except:
            addMsgAndPrint(arcpy.GetMessages(2))
    
        # create feature classes in GeologicMap
        # poly feature classes
        featureClasses = ['MapUnitPolys']
        for fc in ['DataSourcePolys','MapUnitOverlayPolys','OverlayPolys']:
            if fc in OptionalElements:
                featureClasses.append(fc)
        for featureClass in featureClasses:
            fieldDefs = tableDict[featureClass]
            if addLTYPE and fc <> 'DataSourcePolys':
                fieldDefs.append(['PTYPE','String','NullsOK',50])
            createFeatureClass(thisDB,'GeologicMap',featureClass,'POLYGON',fieldDefs)
                
        # line feature classes
        featureClasses = ['ContactsAndFaults']
        for fc in ['GeologicLines','CartographicLines','IsoValueLines','MapUnitLines']:
            if fc in OptionalElements:
                featureClasses.append(fc)
        for featureClass in featureClasses:
            fieldDefs = tableDict[featureClass]
            if featureClass in ['ContactsAndFaults','GeologicLines'] and addLTYPE:
                fieldDefs.append(['LTYPE','String','NullsOK',50])
            createFeatureClass(thisDB,'GeologicMap',featureClass,'POLYLINE',fieldDefs)
    
        # ADDED GeochemPoints and GeologicalPoints
        # point feature classes
        featureClasses = []
        for fc in ['OrientationPoints','GeochronPoints','FossilPoints','Stations',
                  'GenericSamples','GenericPoints','GeochemPoints',
                  'GeologicPoints', 'MapUnitPoints']:
            if fc in OptionalElements:
                featureClasses.append(fc)
        for featureClass in featureClasses:
            """
            The following block of code was bypassing the MapUnitPoints definition now in GeMS_Definitions.py and
            appending PTYPE to the resulting feature class, along with the PTTYPE field appended in the 
            next statement. I think we don't need it, but need to talk with Evan about this.
            If he concurs, will delete this block.
    
            Ralph Haugerud
            23 December 2020
    
            # the following if statement used to be here, but was removed at some point
            # putting it back to allow for creation of MapUnitPoints after discussion
            # with Luke Blair - Evan Thoms
            if featureClass == 'MapUnitPoints': 
                fieldDefs = tableDict['MapUnitPolys']
                if addLTYPE:
                    fieldDefs.append(['PTYPE','String','NullsOK',50])
            else:	
                fieldDefs = tableDict[featureClass]
                if addLTYPE and featureClass in ['OrientationPoints']:
                    fieldDefs.append(['PTTYPE','String','NullsOK',50])
            # end of re-inserted if statement   
            """
            fieldDefs = tableDict[featureClass]
            if addLTYPE:
                fieldDefs.append(['PTTYPE','String','NullsOK',50])
            createFeatureClass(thisDB,'GeologicMap',featureClass,'POINT',fieldDefs)
    
        # create feature dataset CorrelationOfMapUnits
        if 'CorrelationOfMapUnits' in OptionalElements:
            addMsgAndPrint('  Creating feature dataset CorrelationOfMapUnits...')
            arcpy.CreateFeatureDataset_management(thisDB,'CorrelationOfMapUnits',coordSystem)
            fieldDefs = tableDict['CMUMapUnitPolys']
            createFeatureClass(thisDB,'CorrelationOfMapUnits','CMUMapUnitPolys','POLYGON',fieldDefs)
            fieldDefs = tableDict['CMULines']
            createFeatureClass(thisDB,'CorrelationOfMapUnits','CMULines','POLYLINE',fieldDefs)
            fieldDefs = tableDict['CMUPoints']
            createFeatureClass(thisDB,'CorrelationOfMapUnits','CMUPoints','POINT',fieldDefs)
        
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        if int(nCrossSections) == 0:
            addMsgAndPrint('  No Cross Sections created.')
       
        else:
            for n in range(int(nCrossSections)):
                xsLetter = alphabet[n]

                xsName = 'CrossSection'+xsLetter
                xsN = 'CS'+xsLetter
                addMsgAndPrint('  Creating feature data set CrossSection'+xsLetter+'...')
                arcpy.CreateFeatureDataset_management(thisDB,xsName,coordSystem)

                addMsgAndPrint(coordSystem)
                muDefs = rename_field(tableDict['MapUnitPolys'], 'MapUnitPolys_ID', xsN+'MapUnitPolys_ID')
                createFeatureClass(thisDB, xsName, xsN+'MapUnitPolys', 'POLYGON', muDefs)


                cfDefs = rename_field(tableDict['ContactsAndFaults'], 'ContactsAndFaults_ID', xsN+'ContactsAndFaults_ID')
                createFeatureClass(thisDB, xsName, xsN+'ContactsAndFaults', 'POLYLINE', cfDefs)
        
                if 'OrientationPoints' in OptionalElements:
                    opDefs = rename_field(tableDict['OrientationPoints'], 'OrientationPoints_ID', xsN+'OrientationPoints_ID')
                    createFeatureClass(thisDB, xsName, xsN+'OrientationPoints', 'POINT', opDefs)
        
        
        # create tables
        tables = ['DescriptionOfMapUnits','DataSources','Glossary']
        for tb in ['RepurposedSymbols','StandardLithology','GeologicEvents','MiscellaneousMapInformation']:
            if tb in OptionalElements:
                tables.append(tb)
        for table in tables:
            addMsgAndPrint('  Creating table '+table+'...')
            try:
                arcpy.CreateTable_management(thisDB,table)
                fieldDefs = tableDict[table]
                for fDef in fieldDefs:
                    try:
                        if fDef[1] == 'String':
                            arcpy.AddField_management(thisDB+'/'+table,fDef[0],transDict[fDef[1]],'#','#',fDef[3],'#',transDict[fDef[2]])
                        else:
                            arcpy.AddField_management(thisDB+'/'+table,fDef[0],transDict[fDef[1]],'#','#','#','#',transDict[fDef[2]])
                    except:
                        addMsgAndPrint('Failed to add field '+fDef[0]+' to table '+table)
                        addMsgAndPrint(arcpy.GetMessages(2))		    
            except:
                addMsgAndPrint(arcpy.GetMessages())
    
        ### GeoMaterials
        addMsgAndPrint('  Setting up GeoMaterialDict table and domains...')
        #  Copy GeoMaterials table

        arcpy.Copy_management(os.path.dirname(os.path.realpath(__file__))+'/../Resources/GeMS_lib.gdb/GeoMaterialDict', thisDB+'/GeoMaterialDict')
#        arcpy.Copy_management(os.path.dirname(outputDir)+'/../Resources/GeMS_lib.gdb/GeoMaterialDict', thisDB+'/GeoMaterialDict')
        #   make GeoMaterials domain
        arcpy.TableToDomain_management(thisDB+'/GeoMaterialDict','GeoMaterial','IndentedName',thisDB,'GeoMaterials')
        #   attach it to DMU field GeoMaterial
        arcpy.AssignDomainToField_management(thisDB+'/DescriptionOfMapUnits','GeoMaterial','GeoMaterials')       
        #  Make GeoMaterialConfs domain, attach it to DMU field GeoMaterialConf
        arcpy.CreateDomain_management(thisDB,'GeoMaterialConfidenceValues','','TEXT','CODED')
        for val in GeoMaterialConfidenceValues:
            arcpy.AddCodedValueToDomain_management(thisDB,'GeoMaterialConfidenceValues',val,val)
        arcpy.AssignDomainToField_management(thisDB+'/DescriptionOfMapUnits','GeoMaterialConfidence','GeoMaterialConfidenceValues')
        
        #Confidence domains, Glossary entries, and DataSources entry
        if addConfs:
            addMsgAndPrint('addConfs found')
            addMsgAndPrint('  Adding standard ExistenceConfidence and IdentityConfidence domains')
            #  create domain, add domain values, and link domain to appropriate fields
            addMsgAndPrint('    Creating domain, linking domain to appropriate fields')
            arcpy.CreateDomain_management(thisDB,'ExIDConfidenceValues','','TEXT','CODED')
            for item in DefaultExIDConfidenceValues:  # items are [term, definition, source]
                code = item[0]
                arcpy.AddCodedValueToDomain_management(thisDB,'ExIDConfidenceValues',code,code)
            arcpy.env.workspace = thisDB
            dataSets = arcpy.ListDatasets()
            for ds in dataSets:
                arcpy.env.workspace = thisDB+'/'+ds
                fcs = arcpy.ListFeatureClasses()
                for fc in fcs:
                    fieldNames = fieldNameList(fc)
                    for fn in fieldNames:
                        if fn in ('ExistenceConfidence', 'IdentityConfidence','ScientificConfidence'):
                            #addMsgAndPrint('    '+ds+'/'+fc+':'+fn)
                            arcpy.AssignDomainToField_management(thisDB+'/'+ds+'/'+fc,fn,'ExIDConfidenceValues')
            # add definitions of domain values to Glossary
            addMsgAndPrint('    Adding domain values to Glossary')
            ## create insert cursor on Glossary
            cursor = arcpy.da.InsertCursor(thisDB+'/Glossary',['Term','Definition','DefinitionSourceID'])
            for item in DefaultExIDConfidenceValues:
                cursor.insertRow((item[0],item[1],item[2]))
            del cursor
            # add definitionsource to DataSources
            addMsgAndPrint('    Adding definition source to DataSources')        
            ## create insert cursor on DataSources
            cursor = arcpy.da.InsertCursor(thisDB+'/DataSources',['DataSources_ID','Source','URL'])
            cursor.insertRow(('FGDC-STD-013-2006','Federal Geographic Data Committee [prepared for the Federal Geographic Data Committee by the U.S. Geological Survey], 2006, FGDC Digital Cartographic Standard for Geologic Map Symbolization: Reston, Va., Federal Geographic Data Committee Document Number FGDC-STD-013-2006, 290 p., 2 plates.','https://ngmdb.usgs.gov/fgdc_gds/geolsymstd.php'))
            del cursor 
    
        
    # if cartoReps, add cartographic representations to all feature classes
        # trackEdits, add editor tracking to all feature classes and tables
        if cartoReps:
            arcpy.env.workspace = thisDB
            tables = arcpy.ListTables()
            datasets = arcpy.ListDatasets()
            for dataset in datasets:
                addMsgAndPrint('  Dataset '+dataset)
                arcpy.env.workspace = thisDB+'/'+dataset
                fcs = arcpy.ListFeatureClasses()
                for fc in fcs:
                    hasReps,repLyr = cartoRepsExistAndLayer(fc)
                    if cartoReps and hasReps:
                        addMsgAndPrint('    Adding cartographic representations to '+fc)
                        try:
                            #arcpy.AddRepresentation_cartography(fc,fc+'_Rep',"RuleID","Override",default,repLyr,"ASSIGN")
                            arcpy.AddRepresentation_cartography(fc,fc+'_rep1','RuleID1','Override1',default,repLyr,'NO_ASSIGN')
                            """
                                Note the 1 suffix on the representation name (fc+'_rep1') and the RuleID1 and Override1 fields.
                            If at some later time we wish to add additional representations to a feature class, each will
                            require it's own RuleID and Override fields which may be identified, and tied to the appropriate
                            representation, by suffixes 2, 3, ...
                                Naming representations fc+'_rep'+str(n) should be sufficient to identify each representation in a 
                            geodatabase uniquely, and allow for multiple representations within a single feature class.
                                It appears that ArcGIS provides no means of scripting an inventory of representations within
                            feature class or geodatabase. So, the convenience of establishing a coded-value domain that ties
                            representation rule IDs (consecutive integers) to some sort of useful text identifier becomes a
                            necessity for flagging the presence of a representation: One CAN script the inventory of domains
                            in a geodatabase. Run arcpy.da.ListDomains. Check the result for names of the form
                            <featureClassName>_rep??_Rule and voila, you've got a list of representations (and their associated
                            feature classes) in the geodatabase.
                                Moral: If you add a representation, be sure to add an associated coded-value domain and name
                            it appropriately!
                            """
                        except:
                            addMsgAndPrint(arcpy.GetMessages(2))

        if trackEdits:
            addTracking(os.path.join(thisDB,fc))
            addMsgAndPrint('  Tables ')
            arcpy.env.workspace = thisDB
            for aTable in tables:
                if aTable <> 'GeoMaterialDict':
                    addTracking(os.path.join(thisDB,aTable))
    
    
    
    def createDatabase(outputDir,thisDB):
        addMsgAndPrint('  Creating geodatabase '+thisDB+'...')
        if arcpy.Exists(outputDir+'/'+thisDB):
            addMsgAndPrint('  Geodatabase '+thisDB+' already exists.')
            addMsgAndPrint('   forcing exit with error')
            raise arcpy.ExecuteError
        try:
            if thisDB[-4:] == '.mdb':
                arcpy.CreatePersonalGDB_management(outputDir,thisDB)
            if thisDB[-4:] == '.gdb':
                arcpy.CreateFileGDB_management(outputDir,thisDB)
            return True
        except:
            addMsgAndPrint('Failed to create geodatabase '+outputDir+'/'+thisDB)
            addMsgAndPrint(arcpy.GetMessages(2))
            return False
    
    #########################################
        
    addMsgAndPrint(versionString)
    
    addMsgAndPrint('Starting script')

    #if outputDir == '#':
    #    outputDir = os.getcwd()
    #outputDir = outputDir.replace('\\','/')

    # test for extension; if not given, default to file geodatabase
    if not thisDB[-4:].lower() in ('.gdb','.mdb'):
        thisDB = thisDB+'.gdb'

    if OptionalElements is None:
        OptionalElements = []
    else:
        OptionalElements = OptionalElements.split(';')
    if debug:
        addMsgAndPrint('Optional elements = '+str(OptionalElements))

    try:
        if trackEdits == 'true':
            trackEdits = True
        else:
            trackEdits = False
    except:
        trackEdits = False
        
    if arcpy.GetInstallInfo()['Version'] < '10.1':
        trackEdits = False
        
    try:
        if cartoReps == 'true':
            cartoReps = True
        else:
            cartoReps = False
    except:
        cartoReps = False

    try:
        if addLTYPE == 'true':
            addLTYPE = True
        else:
            addLTYPE = False
    except:
        addLTYPE = False
        
    try:
        if addConfs == 'true':
            addConfs = True
        else:
            addConfs = False
    except:
        addConfs = False
        
        
    # create personal gdb in output directory and run main routine
    if createDatabase(outputDir,thisDB):
        thisDB = outputDir+'/'+thisDB
        arcpy.RefreshCatalog(thisDB)
        main(thisDB,coordSystem,nCrossSections,trackEdits,cartoReps,addLTYPE,addConfs)

    # try to write a readme within the .gdb
    if thisDB[-4:] == '.gdb':
        try:
            writeLogfile(thisDB,'Geodatabase created by '+versionString)
        except:
            addMsgAndPrint('Failed to write to'+thisDB+'/00log.txt')
    
    





def mapOutline(SELongStr, SELatStr, dLong, dLat, ticInterval, isNAD27, outgdb, outSpRef, scratch):
    
    addMsgAndPrint(versionString)
    
    if isNAD27:
        xycs = 'GEOGCS["GCS_North_American_1927",DATUM["D_North_American_1927",SPHEROID["Clarke_1866",6378206.4,294.9786982]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433],AUTHORITY["EPSG",4267]]'
    else:
        xycs = 'GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433],AUTHORITY["EPSG",4269]]'
    
    # set workspace
    arcpy.env.workspace = outgdb
    arcpy.env.scratchWorkspace = scratch
    # calculate maxLong and minLat, dLat, dLong, minLong, maxLat
    maxLong = dmsStringToDD(SELongStr)
    minLat = dmsStringToDD(SELatStr)
    if dLong > 5:
        dLong = dLong/60.0
    if dLat > 5:
        dLat = dLat/60.0
    minLong = maxLong - dLong
    maxLat = minLat + dLat
    
    # test for and delete any feature classes to be created
    for xx in ['xxMapOutline','MapOutline','xxTics','Tics']:
        if arcpy.Exists(xx):
            arcpy.Delete_management(xx)
            addMsgAndPrint('  deleted feature class '+xx)
    
    ## MAP OUTLINE
    # make XY file for map outline
    addMsgAndPrint('  writing map outline file')

    genf = open(scratch+'\\xxxbox.csv','w')
    genf.write('LONGITUDE,LATITUDE\n')
    genf.write(str(minLong)+','+str(maxLat)+'\n')
    genf.write(str(maxLong)+','+str(maxLat)+'\n')
    genf.write(str(maxLong)+','+str(minLat)+'\n')
    genf.write(str(minLong)+','+str(minLat)+'\n')
    genf.write(str(minLong)+','+str(maxLat)+'\n')
    genf.close()
    
    # convert XY file to .dbf table
    boxdbf = arcpy.CreateScratchName('xxx','.dbf','',scratch)
    boxdbf = os.path.basename(boxdbf)
    arcpy.TableToTable_conversion(scratch+'/xxxbox.csv',scratch,boxdbf)
    # make XY event layer from .dbf table
    arcpy.MakeXYEventLayer_management(scratch+'/'+boxdbf,'LONGITUDE','LATITUDE','boxlayer',xycs)
    # convert event layer to preliminary line feature class with PointsToLine_management
    arcpy.PointsToLine_management('boxlayer','xxMapOutline')
    # densify MapOutline
    arcpy.Densify_edit('xxMapOutline','DISTANCE',0.0001)
    
    # project to correct spatial reference
    ### THIS ASSUMES THAT OUTPUT COORDINATE SYSTEM IS HARN AND WE ARE IN OREGON OR WASHINGTON!!
    if isNAD27:
        geotransformation = 'NAD_1927_To_NAD_1983_NADCON;NAD_1983_To_HARN_OR_WA'
    else:
        geotransformation = 'NAD_1983_To_HARN_OR_WA'
    
    geotransformation = ''
    
    arcpy.Project_management('xxMapOutline', 'MapOutline', outSpRef, geotransformation,xycs)
    
    ##############################################################################
    # Linda Tedrow
    # Skye Swoboda-Colberg
    # Idaho Geological Survey
    ##############################################################################
    # Notes:
    
    mxd = arcpy.mapping.MapDocument("CURRENT")
    activeFrame = mxd.activeDataFrame
    
    # Set CoordinateSystem to outSpRef for CalculateGridConvergenceAngle
    arcpy.env.cartographicCoordinateSystem = outSpRef
    
    # Define Features in Feature Dataset defined by workspace
    fd= arcpy.ListDatasets("*", "Feature")[0]
    
    # add attributes
    arcpy.AddField_management(outgdb+'\\MapOutline','Rotate','DOUBLE')
    arcpy.AddField_management(outgdb+'\\MapOutline','TYPE','STRING')
    arcpy.AddField_management(outgdb+'\\MapOutline','Symbol','STRING')
    
    # create update cursor, add Rotate value from "CalculateGridConvergence" tool
    addMsgAndPrint('--->adding Rotate value')
    arcpy.CalculateGridConvergenceAngle_cartography(outgdb+"\\MapOutline","Rotate")
    
    cursor = arcpy.da.SearchCursor(outgdb+"\\MapOutline",'Rotate')
    for row in cursor:
        rotate = row[0]
    del(cursor)
    
    activeFrame.rotation = rotate
    
    cursor = arcpy.da.UpdateCursor(outgdb+"\\MapOutline",['TYPE','Symbol'])
    for row in cursor:
        row[0] = 'MapBoundary'
        row[1] = '31.08'
        cursor.updateRow(row)
    del(cursor)
    
    
    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()
    
    # Append MapOutline TYPE to ConcactsAndFaults
    arcpy.Append_management(outgdb+'\\MapOutline', outgdb+'\\'+fd+'\\ContactsAndFaults', schema_type="NO_TEST")
    
    ##############################################################################

    ## TICS
    # calculate minTicLong, minTicLat, maxTicLong, maxTiclat
    ticInterval = ticInterval / 60.0 # convert minutes to degrees
    minTicLong = int(round(0.1 + minLong // ticInterval)) 
    maxTicLong = int(round(1.1 + maxLong // ticInterval))
    minTicLat = int(round(0.1 + minLat // ticInterval)) 
    maxTicLat = int(round(1.1 + maxLat // ticInterval))
    if minTicLong < 0:
        minTicLong = minTicLong + 1
    if maxTicLong < 0:
        maxTicLong = maxTicLong + 1
    # make xy file for tics
    addMsgAndPrint('  writing tic file')
    genf = open(scratch+'\\xxxtics.csv','w')
    genf.write('ID,LONGITUDE,LATITUDE\n')
    nTic = 1
    for y in range(minTicLat,maxTicLat):
        ticLat = y * ticInterval
        for x in range(minTicLong,maxTicLong):
            ticLong = x * ticInterval
            genf.write(str(nTic)+','+str(ticLong)+','+str(ticLat)+'\n')
            nTic = nTic+1
    genf.close()
    # convert to dbf
    ticdbf = arcpy.CreateScratchName('xxx','.dbf','',scratch)
    print ticdbf
    ticdbf = os.path.basename(ticdbf)
    print ticdbf
    arcpy.TableToTable_conversion(scratch+'\\xxxtics.csv',scratch,ticdbf)
    # make XY event layer from table
    arcpy.MakeXYEventLayer_management(scratch+'/'+ticdbf,'LONGITUDE','LATITUDE','ticlayer',xycs)
    # copy to point featureclass
    arcpy.FeatureToPoint_management('ticlayer','xxtics')
    
    # project to correct coordinate system
    arcpy.Project_management('xxtics', 'tics', outSpRef, geotransformation,xycs)
    
    # add attributes 
    for fld in ['Easting','Northing']:
        arcpy.AddField_management('tics',fld,'DOUBLE')
    for fld in ['LatDMS','LongDMS']:
        arcpy.AddField_management('tics',fld,'TEXT',"","",20)
    arcpy.AddXY_management('tics')
    # calc Easting = Point_X, Northing = Point_Y
    arcpy.CalculateField_management('tics','Easting','!Point_X!','PYTHON')
    arcpy.CalculateField_management('tics','Northing','!Point_Y!','PYTHON')
    
    # create update cursor, cycle through tics, and add LatDMS and LongDMS
    addMsgAndPrint('  adding lat-long text strings')
    rows = arcpy.UpdateCursor('tics')
    for row in rows:
        row.LatDMS = ddToDmsString(row.LATITUDE)
        row.LongDMS = ddToDmsString(row.LONGITUDE)
        rows.updateRow(row)
    del row
    del rows
    
    # delete csv files, dbf files, and preliminary featureclasses
    addMsgAndPrint('  cleaning up scratch workspace')
    for xx in [boxdbf,boxdbf+'.xml',ticdbf,ticdbf+'.xml','xxxbox.csv','xxxtics.csv']:
        os.remove(scratch+'\\'+xx)
    addMsgAndPrint('  deleting temporary feature classes')
    arcpy.Delete_management('xxtics')
    arcpy.Delete_management('xxMapOutline')
    arcpy.Delete_management('xxx0.dbf')
    arcpy.Delete_management('xxx1.dbf')
    
    #sys.exit()   # force exit with failure
    
    




def xcTool(gdb,projectAll,fcToProject,dem,xsLine,startQuadrant,outFdsTag,
 vertEx,bufferDistance,addLTYPE,forceExit,scratchws,saveIntermediate):

    '''
    Projects all data in GeologicMap feature dataset (inFds) to cross-section plane
    Creates featureclasses with names prefixed by 'ed_'
    Output feature classes have all input FC attributes. In addition, point feature
      classes are given attribute:
        DistanceFromSection 
        LocalCsAzimuth  (Trend of section line at projected point,
             0..360, measured CCW from grid N)
    If points are OrientationData, we also calculate attributes:
        ApparentInclination
        Obliquity
        PlotAzimuth (= apparentInclination + 90)
    
    Assumptions:
      Input FDS is GeologicMap
      xsLine has only ONE LINE (one row in data table)
      We don't project points that are beyond ends of xsLine,
         even though to do so is often desirable
      We don't project feature classes whose names begin with
         the strings 'errors_'  or 'ed_'
    
    Much of this code is modeled on cross-section routines written by
    Evan Thoms, USGS, Anchorage.
    
    Ralph Haugerud
    rhaugerud@usgs.gov
    '''
    
    versionString = 'GeMS_ProjectCrossSectionData_Arc10.py, version of 2 September 2017'
    
    ##inputs
    #  gdb          geodatabase with GeologicMap feature dataset to be projected
    #  projectAll
    #  fcToProject
    #  dem          
    #  xsLine       cross-section line: _single-line_ feature class or layer
    #  startQuadrant start quadrant (NE,SE,SW,NW)
    #  outFdsTag   output feature dataset. Input value is appended to 'CrossSection'
    #  vertEx       vertical exaggeration; a number
    #  bufferDistance  a number
    #  forcExit
    #  scratchWS
    #  saveIntermediate (boolean)
    
    lineCrossingLength = 1000   # length (in map units) of vertical line drawn where arcs cross section line
    exemptedPrefixes = ('errors_','ed_')  # prefixes that flag a feature class as not to be projected
    
    transDict =   { 'String': 'TEXT',
    		'Single': 'FLOAT',
    		'Double': 'DOUBLE',
    	    	'NoNulls':'NON_NULLABLE',
        		'NullsOK':'NULLABLE',
        		'Date'  : 'DATE'  }
    
    ##### UTILITY FUNCTIONS ############################
    
    def doProject(fc):
        doPrj = True
        for exPfx in exemptedPrefixes:
            if fc.find(exPfx) == 0:
                doPrj = False
        return doPrj
    
    def shortName(obj):
        return os.path.basename(obj)
    
    def wsName(obj):
        return os.path.dirname(obj)
    
    def cartesianToGeographic(angle):
        ctg = -90 - angle
        if ctg < 0:
            ctg = ctg+360
        return ctg
    
    def isAxial(ptType):
        m = False
        for s in ('axis','lineation',' L'):
            if ptType.upper().find(s.upper()) > -1:
                m = True
        return m
    
    def obliq(theta1,theta2):
        obl = abs(theta1-theta2)
        if obl > 180:
            obl = obl-180
        if obl > 90:
            obl = 180 - obl
        return obl
    
    def azimuthDifference(a,b):
        # a, b are two azimuths in clockwise geographic notation
        # azDiff is in range -180..180
        # if azDiff < 0, a is counterclockwise of b
        # if azDiff > 0, a is clockwise of b
        azDiff = a - b
        if azDiff > 180:
            azDiff = azDiff - 360
        if azDiff < -180:
            azDiff = azDiff + 360
        return azDiff
    
    def plotAzimuth(inclinationDirection, thetaXS, apparentInclination):
        azDiff = azimuthDifference(thetaXS,inclinationDirection)
        if azDiff >= -90 and azDiff <= 90:
            return 270 + apparentInclination
        else:
            return 270 - apparentInclination
    
    def apparentPlunge(azi,inc,thetaXS):
        obliquity = obliq(azi,thetaXS)  
        appInc = math.degrees(math.atan(vertEx * math.tan(math.radians(inc)) * math.cos(math.radians(obliquity))))
        return appInc,obliquity
    
    def apparentDip(azi,inc,thetaXS):
        obliquity = obliq(azi,thetaXS) 
        appInc = math.degrees(math.atan(vertEx * math.tan(math.radians(inc)) * math.sin(math.radians(obliquity))))
        return appInc,obliquity
    
    def getIdField(fc):
        idField = ''
        fcFields = arcpy.ListFields(fc)
        for fld in fcFields:
            if fld.name.find('_ID') > 0:
                idField = fld.name
        return idField
    
    #  copied from NCGMP09v1.1_CreateDatabase_Arc10.0.py, version of 20 September 2012
    def createFeatureClass(thisDB,featureDataSet,featureClass,shapeType,fieldDefs):
        try:
            arcpy.env.workspace = thisDB
            arcpy.CreateFeatureclass_management(featureDataSet,featureClass,shapeType)
            thisFC = thisDB+'/'+featureDataSet+'/'+featureClass
            for fDef in fieldDefs:
                try:
                    if fDef[1] == 'String':
                        arcpy.AddField_management(thisFC,fDef[0],transDict[fDef[1]],'#','#',fDef[3],'#',transDict[fDef[2]])
                    else:
                        arcpy.AddField_management(thisFC,fDef[0],transDict[fDef[1]],'#','#','#','#',transDict[fDef[2]])
                except:
                    addMsgAndPrint('Failed to add field '+fDef[0]+' to feature class '+featureClass)
                    addMsgAndPrint(arcpy.GetMessages(2))
        except:
            addMsgAndPrint(arcpy.GetMessages())
            addMsgAndPrint('Failed to create feature class '+featureClass+' in dataset '+featureDataSet)
    
    
    def locateEventTable(gdb,inFC,pts,dem,sDistance,eventProperties,zType,isLines = False):
        desc = arcpy.Describe(pts)
    
        if not desc.hasZ:
            addMsgAndPrint('      adding Z values')
            arcpy.AddSurfaceInformation_3d (pts, dem, zType, 'LINEAR')
    
        ## working around bug in LocateFeaturesAlongRoutes
        # add special field for duplicate detection
        dupDetectField = 'xDupDetect'
        arcpy.AddField_management(pts,dupDetectField,'LONG')
        # and calc this field = OBJECTID
        OID = arcpy.Describe(pts).OIDFieldName
        expr = '"!'+OID+'!"'
        arcpy.CalculateField_management(pts,dupDetectField,expr,"PYTHON")
        # locate linePts along route
        addMsgAndPrint('      making event table')
        eventTable = gdb+'/evTb_'+inFC
        testAndDelete(eventTable)
        arcpy.LocateFeaturesAlongRoutes_lr(pts,ZMline,idField,sDistance,eventTable,eventProperties)
        nRows = numberOfRows(eventTable)
        nPts = numberOfRows(pts)
        if nRows > nPts and not isLines:  # if LocateFeaturesAlongRoutes has made duplicates  (A BUG!)
            addMsgAndPrint('      correcting for bug in LocateFeaturesAlongRoutes')
            addMsgAndPrint('        '+str(nRows)+' rows in event table')
            addMsgAndPrint('        removing duplicate entries in event table')
            arcpy.DeleteIdentical_management(eventTable, dupDetectField)  
            addMsgAndPrint('        '+str(numberOfRows(eventTable))+' rows in event table')
        arcpy.DeleteField_management(eventTable,dupDetectField)
        return eventTable
    
    ###############################################################
    addMsgAndPrint('\n  '+versionString)  
    
    ##for arg in sys.argv:
        ##    addMsgAndPrint(str(arg))
        
    if projectAll == 'true': projectAll = True
    else: projectAll = False
    
    if addLTYPE == 'true': addLTYPE = True
    else: addLTYPE = False
    
    if forceExit == 'true': forceExit = True
    else: forceExit = False
    
    if saveIntermediate == 'true': saveIntermediate = True
    else: saveIntermediate = False
    
    inFds = gdb+'/GeologicMap'
    outFds = gdb+'/CrossSection'+outFdsTag
    
    if arcpy.Exists(scratchws):
        scratch = scratchws
    else:
        scratch = outFds
    addMsgAndPrint('  Scratch directory is '+scratch)
    
    arcpy.env.overwriteOutput = True
    
    try:
        arcpy.CheckOutExtension('3D')
    except:
        addMsgAndPrint('\nCannot check out 3D-analyst extension.')
        sys.exit()
    
    ## Create temporary section line
    ## Checking section line
    addMsgAndPrint('  Checking section line')
    idField = getIdField(xsLine)
    ##   does xsLine have 1-and-only-1 arc? if not, bail
    i = numberOfRows(xsLine)
    expression = None
    if i > 1:
        expression = "Label = '" + outFdsTag +"'"
        addMsgAndPrint("Expression: ",expression)
    elif i == 0:
        addMsgAndPrint('OOPS! Mo arcs in '+xsLine)
        sys.exit()
    
    ## make output fds if it doesn't exist
    #  set output fds spatial reference to input fds spatial reference
    if not arcpy.Exists(outFds):
        addMsgAndPrint('  Making feature data set '+shortName(outFds))
        arcpy.CreateFeatureDataset_management(gdb,shortName(outFds),inFds)
    
    
    
    addMsgAndPrint('  Prepping section line')
    ## make copy of section line
    tempXsLine = arcpy.CreateScratchName('xx',outFdsTag+"xsLine",'FeatureClass',scratch)
    addMsgAndPrint('    copying '+shortName(xsLine)+' to xxxXsLine')
    #addMsgAndPrint(xsLine+' '+scratch)
    arcpy.FeatureClassToFeatureClass_conversion(xsLine,scratch,shortName(tempXsLine), expression)
    
    desc = arcpy.Describe(tempXsLine)
    xslfields = fieldNameList(tempXsLine)
    idField = ''
    for fld in xslfields:
        if fld.find('_ID') > 0:
            idField = fld
    if idField == '':
        idField = 'ORIG_ID'
        arcpy.AddField_management(tempXsLine,idField,'TEXT')
        arcpy.CalculateField_management (tempXsLine, idField, '01','PYTHON') 
    specialFields = [desc.OIDFieldName,desc.shapeFieldName,idField,'Shape_Length','Length']
    addMsgAndPrint('    deleting most fields')
    for nm in xslfields:
        if nm not in specialFields:
            try:
                arcpy.DeleteField_management(tempXsLine,nm)
            except:
                pass
    ##   check for Z and M values
    desc = arcpy.Describe(tempXsLine)
    if desc.hasZ and desc.hasM:
        ZMline = tempXsLine
    else:
        #Add Z values
        addMsgAndPrint('    getting elevation values for ' + shortName(tempXsLine))
        Zline = arcpy.CreateScratchName('xx',outFdsTag+'_Z','FeatureClass',scratch)
        arcpy.InterpolateShape_3d(dem, tempXsLine, Zline)
        #Add M values
        addMsgAndPrint('    measuring ' + shortName(Zline))
        ZMline = arcpy.CreateScratchName('xx',outFdsTag+'_ZM','FeatureClass',scratch)
        arcpy.CreateRoutes_lr(Zline, idField, ZMline, 'LENGTH', '#', '#', startQuadrant)
    ## buffer line to get selection polygon
    addMsgAndPrint('    buffering '+shortName(tempXsLine)+' to get selection polygon')
    tempBuffer = arcpy.CreateScratchName('xx',outFdsTag+"xsBuffer",'FeatureClass',scratch)
    arcpy.Buffer_analysis(ZMline,tempBuffer,bufferDistance,'FULL','FLAT')
    
    
    
    ## get lists of feature classes to be projected
    lineFCs = []
    polyFCs = []
    pointFCs = []
    
    if projectAll:
#        oldws = arcpy.env.workspace
        arcpy.env.workspace = gdb+'/GeologicMap'
        linefc = arcpy.ListFeatureClasses('*','Line')
        polyfc = arcpy.ListFeatureClasses('*','Polygon')
        pointfc = arcpy.ListFeatureClasses('*','Point')
        for fc in linefc:
            if doProject(fc) and numberOfRows(fc) > 0: lineFCs.append(gdb+'/GeologicMap/'+fc)
        for fc in polyfc:
            if doProject(fc) and numberOfRows(fc) > 0: polyFCs.append(gdb+'/GeologicMap/'+fc)
        for fc in pointfc:
            if doProject(fc) and numberOfRows(fc) > 0: pointFCs.append(gdb+'/GeologicMap/'+fc)
    else:
        featureClassesToProject = fcToProject.split(';')
        for fc in featureClassesToProject:
            desc = arcpy.Describe(fc)
            if desc.shapeType == 'Polyline': lineFCs.append(fc)
            if desc.shapeType == 'Polygon':  polyFCs.append(fc)
            if desc.shapeType == 'Point':    pointFCs.append(fc)
    
    
    addMsgAndPrint('\n  Projecting line feature classes:')
    for lineFC in lineFCs:
        inFC = shortName(lineFC)
        addMsgAndPrint('    '+inFC)
        arcpy.env.workspace = wsName(lineFC)
        if inFC == 'ContactsAndFaults':
            lineCrossingLength = -lineCrossingLength
        # intersect inFC with ZMline to get points where arcs cross section line
        linePts = scratch+'/xxxLinePts'+outFdsTag
        arcpy.Intersect_analysis([inFC,ZMline],linePts,'ALL','#','POINT')
        if numberOfRows(linePts) == 0:
            addMsgAndPrint('      '+inFC+' does not intersect section line')
        else:  # numberOfRows > 0
            eventProperties = 'rtID POINT M fmp' 
            eventTable = locateEventTable(gdb,inFC,linePts,dem,10,eventProperties,'Z_MEAN',True)
            addMsgAndPrint('      placing events on section line')
            eventLyr = 'xxxLineEvents'
            arcpy.MakeRouteEventLayer_lr(ZMline,idField,eventTable,eventProperties,eventLyr)
            outFC = 'ed_CS'+outFdsTag+shortName(inFC)
            addMsgAndPrint('      creating feature class '+outFC+' in '+shortName(outFds))
            # make new feature class using old as template
            testAndDelete(outFds+'/'+outFC)
            arcpy.CreateFeatureclass_management(outFds,outFC,'POLYLINE',inFC,'DISABLED','SAME_AS_TEMPLATE') 
            outFC = outFds+'/'+outFC
            addMsgAndPrint('      moving and calculating attributes')
            ## open search cursor on inFC, open insert cursor on outFC
            inRows = arcpy.SearchCursor(eventLyr)
            outRows = arcpy.InsertCursor(outFC)
            # get field names
            inFieldNames = fieldNameList(eventLyr)
            outFieldNames = fieldNameList(outFC)
            # get fields to ignore
            ignoreFields = []
            desc = arcpy.Describe(eventLyr)
            ignoreFields.append(desc.ShapeFieldName)
            ignoreFields.append(desc.OIDFieldName)
            for inRow in inRows:
                outRow = outRows.newRow()
                # do shape
                X = inRow.M
                Y = inRow.Shape.firstPoint.Z
                pnt1 = arcpy.Point(X,(Y-lineCrossingLength)*vertEx)
                pnt2 = arcpy.Point(X,Y*vertEx)
                pnt3 = arcpy.Point(X,(Y+lineCrossingLength)*vertEx)
                lineArray = arcpy.Array([pnt1,pnt2,pnt3])
                outRow.Shape = lineArray
                # transfer matching fields
                for field in inFieldNames:
                    if field in outFieldNames and not field in ignoreFields:
                        stuff = inRow.getValue(field)
                        outRow.setValue(field,stuff)
                outRows.insertRow(outRow)
            ## clean up
            if not saveIntermediate:
              for f in eventTable,eventLyr,linePts:
                testAndDelete(f)
            del inRows,outRows
            
    
    addMsgAndPrint('\n  Projecting point feature classes:')
    ## for each input point feature class:
    for pointClass in pointFCs:
        inFC = shortName(pointClass)
        addMsgAndPrint('    '+inFC)
        arcpy.env.workspace = wsName(pointClass)
        # clip inputfc with selection polygon to make tempPoints
        addMsgAndPrint('      clipping with selection polygon')
        tempPoints = scratch+'/xxx'+outFdsTag+inFC
        arcpy.Clip_analysis(pointClass,tempBuffer,tempPoints)
        # check to see if nonZero number of rows and not in excluded feature classes
        nPts = numberOfRows(tempPoints)
        addMsgAndPrint('      '+str(nPts)+' points within selection polygon')
        if nPts > 0:
            eventProperties = 'rtID POINT M fmp' 
            eventTable = locateEventTable(gdb,inFC,tempPoints,dem,bufferDistance+200,eventProperties,'Z')
            addMsgAndPrint('      placing events on section line')
            eventLyr = 'xxxPtEvents'
            arcpy.MakeRouteEventLayer_lr(ZMline,idField,eventTable,eventProperties,
                                         eventLyr,'#','#','ANGLE_FIELD','TANGENT')
            outFC = outFds+'/ed_CS'+outFdsTag+shortName(inFC)
            outFCa = outFC+'a'
            addMsgAndPrint('      copying event layer to '+shortName(outFCa))
            arcpy.CopyFeatures_management(eventLyr,outFCa)   
            addMsgAndPrint('      adding fields')
            # add DistanceFromSection and LocalXsAzimuth
            arcpy.AddField_management(outFCa,'DistanceFromSection','FLOAT')
            arcpy.AddField_management(outFCa,'LocalCSAzimuth','FLOAT')
            # set isOrientationData
            addMsgAndPrint('      checking for Azimuth and Inclination fields')
            inFieldNames = fieldNameList(inFC)
            if 'Azimuth' in inFieldNames and 'Inclination' in inFieldNames:
                isOrientationData = True
                arcpy.AddField_management(outFCa,'ApparentInclination','FLOAT')
                arcpy.AddField_management(outFCa,'Obliquity','FLOAT')
                arcpy.AddField_management(outFCa,'MapAzimuth','FLOAT')                           
            else:
                isOrientationData = False
            arcpy.CreateFeatureclass_management(outFds,shortName(outFC),'POINT',outFCa)
            addMsgAndPrint('      calculating shapes and attributes')
            ## open update cursor on outFC
            cursor = arcpy.UpdateCursor(outFCa)
            outCursor = arcpy.InsertCursor(outFC)
            i = 0
            ii = 0
            for row in cursor:
                # keep track of how many rows are processed
                i = i+1
                ii = ii+1
                ####addMsgAndPrint(str(i))
                if ii == 50:
                    addMsgAndPrint('       row '+str(i))
                    ii = 0
                #   substitute M,Z for X,Y
                try:
                    pntObj = arcpy.Point()
                    pntObj.X = row.M
                    if row.Z == None:
                        pntObj.Y = -999
                        addMsgAndPrint('OBJECTID = '+str(row.OBJECTID)+' Z missing, assigned value of -999')
                    else:
                        pntObj.Y = row.Z * vertEx
                    row.Shape = pntObj
                except:
                    addMsgAndPrint('Failed to make shape: OBJECTID = '+str(row.OBJECTID)+', M = '+str(row.M)+', Z = '+str(row.Z))
                    ## need to do something to flag rows that failed?
                #   convert from cartesian  to geographic angle
                ###addMsgAndPrint(str(pntObj.X)+'  '+str(pntObj.Y)+'  '+str(pntObj.Z))
                csAzi = cartesianToGeographic(row.LOC_ANGLE)
                row.LocalCSAzimuth = csAzi
                row.DistanceFromSection = row.Distance
                if isOrientationData:
                    row.MapAzimuth = row.Azimuth
                    if isAxial(row.Type):
                        appInc,oblique = apparentPlunge(row.Azimuth,row.Inclination,csAzi)
                        inclinationDirection = row.Azimuth
                    else:
                        appInc,oblique = apparentDip(row.Azimuth,row.Inclination,csAzi)
                        inclinationDirection = row.Azimuth + 90
                        if inclinationDirection > 360:
                            inclinationDirection = inclinationDirection - 360
                    plotAzi = plotAzimuth(inclinationDirection,csAzi,appInc)
                    row.Obliquity = round(oblique,2)
                    row.ApparentInclination = round(appInc,2)
                    row.Azimuth = round(plotAzi,2)
                ## print row data
                #fields = arcpy.ListFields(outFC)
                #for field in fields:
                #    addMsgAndPrint(field.name+' = '+str(row.getValue(field.name)))
    
                #cursor.updateRow(row)
                ##  update cursor (line above) doesn't always work, so build a new FC instead:     
                outCursor.insertRow(row)
                
            for fld in 'Distance','LOC_ANGLE','rtID':
                arcpy.DeleteField_management (outFC,fld)
            del row
            del cursor
            ## clean up
            if not saveIntermediate:
              for f in (tempPoints,eventTable,eventLyr,outFCa):
                  testAndDelete(f)
    
    
    addMsgAndPrint('\n  Projecting polygon feature classes:')
    for polyFC in polyFCs:
        inFC = shortName(polyFC)
        addMsgAndPrint('    '+inFC)
        arcpy.env.workspace = wsName(polyFC)
        # locate features along routes
        addMsgAndPrint('      making event table')
        eventTable = gdb+'/evTb_'+inFC
        addMsgAndPrint(eventTable)
        testAndDelete(eventTable)
        eventProperties = 'rtID LINE FromM ToM' 
        arcpy.LocateFeaturesAlongRoutes_lr(inFC,ZMline,idField,'#',eventTable,eventProperties) 
        addMsgAndPrint('      placing events on section line')
        eventLyr = 'xxxPolyEvents'
        arcpy.MakeRouteEventLayer_lr(ZMline,idField,eventTable,eventProperties,eventLyr)
        outFC = 'ed_CS'+outFdsTag+shortName(inFC)
        addMsgAndPrint('      creating feature class '+outFC+' in '+shortName(outFds))
        # make new feature class using old as template
        testAndDelete(outFds+'/'+outFC)
        addMsgAndPrint(outFds+' '+outFC+' '+inFC)
        try:
            arcpy.CreateFeatureclass_management(outFds,outFC,'POLYLINE',inFC,'DISABLED','SAME_AS_TEMPLATE')
        except:
            addMsgAndPrint('Failed to create copy of '+inFC+'. Maybe this feature class has a join?')
            raise arcpy.ExecuteError
        outFC = outFds+'/'+outFC
        addMsgAndPrint('      moving and calculating attributes')
        # get field names
        inFieldNames = fieldNameList(eventLyr)
        outFieldNames = fieldNameList(outFC)
        # get fields to ignore
        ignoreFields = []
        desc = arcpy.Describe(eventLyr)
        ignoreFields.append(desc.ShapeFieldName)
        ignoreFields.append(desc.OIDFieldName)
        ## open search cursor on inFC, open insert cursor on outFC
        inRows = arcpy.SearchCursor(eventLyr)
        outRows = arcpy.InsertCursor(outFC)
        for inRow in inRows:
            outRow = outRows.newRow()
            # flip shape
            oldLine = inRow.Shape
            newLine = arcpy.Array()
            a = 0
            while a < oldLine.partCount:
                array = oldLine.getPart(a)
                newArray = arcpy.Array()
                pnt = array.next()
                while pnt:
                    pnt.X = float(pnt.M)
                    pnt.Y = float(pnt.Z) * vertEx
                    newArray.add(pnt)
                    pnt = array.next()
                newLine.add(newArray)
                a = a+1
            outRow.Shape = newLine
            # transfer matching fields
            for field in inFieldNames:
                if field in outFieldNames and not field in ignoreFields:
                    stuff = inRow.getValue(field)
                    outRow.setValue(field,stuff)
            outRows.insertRow(outRow)
        ## clean up
        if not saveIntermediate:
          for f in eventTable,eventLyr:
            testAndDelete(f)
        del inRows,outRows
        
    
    ##############################################################################
    # Linda Tedrow
    # Skye Swoboda-Colberg
    # Idaho Geological Survey
    ##############################################################################
    # Notes:
    # This Code requires the Zline feature class created from the DEM
    
    import numpy
    
    def roundup(a):
        if round(a,-3)< a:
          newElev = a + 500
        else:
          newElev = a
        #return math.ceil(newElev*1000) / 1000
        return int(round(newElev,-3))
    
    def ticLength(j):
        if numpy.mod(j,1000) == 0:
            tick = 200
        elif numpy.mod(j,200) == 0:
            tick = 100
        else:
            tick = 50
        return(tick)
    
    #Pull Geometry tokens from Zline feature class
    cursor = arcpy.da.SearchCursor(Zline, ["SHAPE@"])
    row = cursor.next()
    
    #Calculate profileWidth
    profileWidth = row[0].length
    #print "Profile Width: ", profileWidth
    addMsgAndPrint('Profile Width: ' +str(profileWidth))
    
    #Calculate maxElev
    elevMax = row[0].extent.ZMax
    Ymax = roundup(elevMax)  
    #print "Maximum Elevation: ", maxElev
    addMsgAndPrint('Maximum Elevation: ' + str(Ymax))
    
    #Calculate Starting Point Z value
    startZ = row[0].firstPoint.Z
    addMsgAndPrint('Starting Point Elevation: ' + str(startZ))
    
    #Calculate Ending Point Z value
    endZ = row[0].lastPoint.Z
    addMsgAndPrint('Ending Point Elevation: ' + str(endZ))
    
    del cursor, row
    
    point = arcpy.Point()
    array = arcpy.Array()
    featureList = []    
    
    fc_name = 'CS' + outFdsTag + 'ContactsAndFaults'
    fc = outFds+'/'+fc_name
    
    if not arcpy.Exists(outFds+'/'+fc_name): 
        fc = arcpy.CreateFeatureclass_management(out_path = outFds, out_name= fc_name, geometry_type="POLYLINE", has_m="DISABLED", has_z="DISABLED")
    fc = outFds+'/'+fc_name
    
    # Check to see if fields exist
    fields = ['Symbol','Type']
    fldList = [f.name for f in arcpy.ListFields(fc)]
    
    for field in fields:
        if field not in fldList:
            arcpy.AddField_management(fc, field, 'TEXT')
    
    # InsertCursor for features going to ContactsAndFaults
    cursor = arcpy.da.InsertCursor(fc, ['Symbol', 'Type', 'SHAPE@'])
    
    #make the bottom left Axis
    x0 = 0
    xE = 0
    y0 = 0
    yE = startZ * vertEx
    point.X = x0
    point.Y = y0
    array.add(point)
    point.X = xE
    point.Y = yE
    array.add(point)
    polyline = arcpy.Polyline(array)
    array.removeAll()
    featureList.append(polyline)
    newRow = ["31.08", "map boundary", polyline]
    cursor.insertRow(newRow)
    
    #make the bottom right Axis
    x0 = profileWidth
    xE = profileWidth
    y0 = 0
    yE = endZ * vertEx
    point.X = x0
    point.Y = y0
    array.add(point)
    point.X = xE
    point.Y = yE
    array.add(point)
    polyline = arcpy.Polyline(array)
    array.removeAll()
    featureList.append(polyline)
    newRow = ["31.08", "map boundary", polyline]
    cursor.insertRow(newRow)
    
    #make the bottom line
    x0 = 0
    xE = profileWidth
    y0 = 0
    yE = 0
    point.X = x0
    point.Y = y0
    array.add(point)
    point.X = xE
    point.Y = yE
    array.add(point)
    polyline = arcpy.Polyline(array)
    array.removeAll()
    featureList.append(polyline)
    newRow = ["31.08", "map boundary", polyline]
    cursor.insertRow(newRow)
    
    del cursor
    
    # Write features to Cartographic Lines
    
    fc_name = 'CS' + outFdsTag + 'CartographicLines'
    fc = outFds+'/'+fc_name
    
    if not arcpy.Exists(outFds+'/'+fc_name): 
        fc = arcpy.CreateFeatureclass_management(out_path = outFds, out_name= fc_name, geometry_type="POLYLINE", has_m="DISABLED", has_z="DISABLED")
    fc = outFds+'/'+fc_name
    
    # Check to see if fields exist
    fields = ['Symbol','Label','orient','Type']
    fldList = [f.name for f in arcpy.ListFields(fc)]
    
    for field in fields:
        if field not in fldList:
            arcpy.AddField_management(fc, field, "TEXT")
       
    # InsertCursor for features going to CartographicLines
    cursor = arcpy.da.InsertCursor(fc, ['Symbol', 'Label', 'orient', 'Type', 'SHAPE@'])
    
    #make the top left Axis
    x0 = 0
    xE = 0
    y0 = startZ * vertEx
    yE = Ymax * vertEx
    point.X = x0
    point.Y = y0
    array.add(point)
    point.X = xE
    point.Y = yE
    array.add(point)
    polyline = arcpy.Polyline(array)
    array.removeAll()
    featureList.append(polyline)
    newRow = ["31.08", "left axis", "left", "map boundary", polyline]
    cursor.insertRow(newRow)
    
    #make the top right Axis
    x0 = profileWidth
    xE = profileWidth
    y0 = endZ * vertEx
    yE = Ymax * vertEx
    point.X = x0
    point.Y = y0
    array.add(point)
    point.X = xE
    point.Y = yE
    array.add(point)
    polyline = arcpy.Polyline(array)
    array.removeAll()
    featureList.append(polyline)
    newRow = ["31.08", "right axis", "right", "map boundary", polyline]
    cursor.insertRow(newRow)
      
    for i in range(0,roundup(Ymax*vertEx)+100,100):
          xLen = ticLength(i)
          x0 = 0 - xLen
          xE = 0
          y0 = i
          yE = i
          point.X = x0
          point.Y = y0
          array.add(point)
          point.X = xE
          point.Y = yE
          array.add(point)
          polyline = arcpy.Polyline(array)
          array.removeAll()
          featureList.append(polyline)
          
    # major ticks
          if numpy.mod(i,1000) == 0:
            newRow = ["31.11", str(i),"left", "major tick", polyline]
    # minor ticks
          else: 
            newRow = ["31.11", None, "left", "minor tick", polyline]
          cursor.insertRow(newRow)
    
          #now the same thing on the right
          x0 = profileWidth
          xE = profileWidth + xLen
          point.X = x0
          point.Y = y0
          array.add(point)
          point.X = xE
          point.Y = yE
          array.add(point)
          polyline = arcpy.Polyline(array)
          array.removeAll()
          featureList.append(polyline)
          if numpy.mod(i,1000) == 0:
            newRow = ["31.11", str(i),"right", "major tick", polyline]
          else: 
            newRow = ["31.11", None, "right", "minor tick", polyline]
          cursor.insertRow(newRow)  
    
    del cursor
    
    ##############################################################################
    
    
    arcpy.CheckInExtension('3D')
    if not saveIntermediate:
      addMsgAndPrint('\n  Deleting intermediate data sets')
      for fc in tempXsLine,ZMline,Zline,tempBuffer:
          testAndDelete(fc)

    
    # make NCGMP09 cross-section feature classes if they are not present in output FDS
    for fc in ('MapUnitPolys','ContactsAndFaults','OrientationPoints'):
        fclass = 'CS' + outFdsTag + fc
        if not arcpy.Exists(outFds+'/'+fclass):
            addMsgAndPrint('  Making empty feature class '+fclass)
            fieldDefs = GeMS_Definition.tableDict[fc]
            fieldDefs[0][0] = fclass+'_ID'
            if fc == 'MapUnitPolys':
                shp = 'POLYGON'
            elif fc == 'ContactsAndFaults':
                shp = 'POLYLINE'
                if addLTYPE: 
                    fieldDefs.append(['LTYPE','String','NullsOK',50])
            elif fc == 'OrientationPoints':
                shp = 'POINT'
                if addLTYPE:
                    fieldDefs.append(['PTTYPE','String','NullsOK',50]) 
            createFeatureClass(gdb,shortName(outFds),fclass,shp,fieldDefs)
  
   
    #########################################################################    

    
    # Transfer 'MapUnit' to 'Label so it can be appended.
    #cursor = arcpy.da.UpdateCursor(MUP,['Label','MapUnit'])
    #for row in cursor:
    #    row[0] = row[1]
    #    cursor.updateRow(row)
    #del(row)
    #del(cursor)
    
    # Append ed_CSAMapUnitPolys to CSAContactAndFaults
    MUP = outFds+'/ed_CS'+outFdsTag+'MapUnitPolys'
    CAF = outFds+'/CS'+outFdsTag+'ContactsAndFaults'
    arcpy.Append_management(MUP, CAF, schema_type="NO_TEST") 
    ###########################################################################
    
    addMsgAndPrint('\n \nFinished successfully.')
    if forceExit:
        addMsgAndPrint('Forcing exit by raising ExecuteError')
        raise arcpy.ExecuteError
    
