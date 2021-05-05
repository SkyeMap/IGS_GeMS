import arcpy
import pythonaddins
import os

relPath = os.path.dirname(__file__)
toolbox = relPath + r"\Fred.pyt"
#toolbox = r"W:\DATABASE_MAPS\24K\SkyeTraining\GitHub\IGS_GeMS\Fred\Install\Fred.pyt"


class ApplySubscript(object):
    """Implementation for Fred_addin.buttonAS (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        # Define map document, layer, and fields
        mxd = arcpy.mapping.MapDocument("CURRENT")
        lyr = arcpy.mapping.ListLayers(mxd,"MapUnitPolys")[0]
        fields = ['FeatureName', 'Label']
        numbers = ['0','1','2','3','4','5','6','7','8','9']
        
        # Get database path from layer
        dirname = arcpy.os.path.dirname(arcpy.Describe(lyr).catalogPath)
        desc = arcpy.Describe(dirname)
        if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
            gdb = arcpy.os.path.dirname(dirname)

        # Set workspace environment
        arcpy.env.workspace = gdb

        # Open edit session
        edit = arcpy.da.Editor(gdb)
        edit.startEditing(False,False)
        edit.startOperation()

        # Write subscripts to Label field for all FeatureNames that end with number
        # name[-1] is the last character of the row
        # name[:-1] is the index up to but not including the last character
        with arcpy.da.UpdateCursor(lyr,fields) as cursor:
            for row in cursor:
                name = row[0]
                if name is not None:
                    if name[-1] in numbers:
                        row[1] = str(name[:-1]) + "<SUB>" + str(name[-1] + "</SUB>")
                    else:
                        row[1] = name
                cursor.updateRow(row)
                
        # Delete objects and close edit session    
        del cursor
        edit.stopOperation()
        edit.stopEditing(True)
        del edit
        del row

        # Refresh Catalog,view, and table of contents
        arcpy.RefreshCatalog(gdb)
        arcpy.RefreshActiveView()
        arcpy.RefreshTOC()



class CreateDatabase(object):
    """Implementation for Fred_addin.buttonGDB (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pythonaddins.GPToolDialog(toolbox, "GDB_tool")



class IsConcealed(object):
    """Implementation for Fred_addin.buttonIC (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        # Define map document, layer, and fields
        mxd = arcpy.mapping.MapDocument("CURRENT")
        lyr = arcpy.mapping.ListLayers(mxd,"ContactsAndFaults")[0]
        fields = ['AuthorLocationConfidence', 'IsConcealed']

        # Get database path from layer
        dirname = arcpy.os.path.dirname(arcpy.Describe(lyr).catalogPath)
        desc = arcpy.Describe(dirname)
        if hasattr(desc, "datasetType") and desc.datasetType=='FeatureDataset':
            gdb = arcpy.os.path.dirname(dirname)

        # Set workspace environment
        arcpy.env.workspace = gdb

        # Open edit session
        edit = arcpy.da.Editor(gdb)
        edit.startEditing(False,False)
        edit.startOperation()

        # Change IsConcealed = 1 (Yes) if AuthorLocationConfidence = 'concealed'
        with arcpy.da.UpdateCursor(lyr,fields) as cursor:
            for row in cursor:
                if row[0] == 'concealed':
                    row[1] = 1
                    cursor.updateRow(row)

        # Delete objects and close edit session
        del cursor
        edit.stopOperation()
        edit.stopEditing(True)
        del edit
        del row

        # Refresh Catalog,view, and table of contents
        arcpy.RefreshCatalog(gdb)
        arcpy.RefreshActiveView()
        arcpy.RefreshTOC()



class MapOutline(object):
    """Implementation for Fred_addin.buttonMO (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pythonaddins.GPToolDialog(toolbox, "MO_tool")



class XSection(object):
    """Implementation for Fred_addin.XS (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pythonaddins.GPToolDialog(toolbox, "XC_tool")
