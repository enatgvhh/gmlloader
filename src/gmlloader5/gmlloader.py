# -*- coding: UTF-8 -*-
#gmlloader.py
import sys
import psycopg2
import re
from lxml import etree
from osgeo import ogr

class GmlLoader(object):
    """Class GmlLoader zum Laden von GML-FeatureMembers in einen deegree BLOB FeatureStore."""
    
    def __init__(self, logger, dbConnection, dbSchema, sourceEpsg, descEpsg, sourcefile):
        """Konstruktor der Klasse GmlLoader.
        
        Konstruktor baut eine PostgreSQL-Connection zur Datenbank auf.
        Liest von dort die 'ft_types' aus der Tabelle 'feature_types' ein und legt damit ein Dictionary an.
        
        Liest aus dem sourcefile 'gml_id' und 'WKT-Extent' (fuer jedes Geometrie-Objekt) in ein Dictionary ein.
        Es wird der ogr.GMLAS-Driver verwendet. Das erspart es, die Geometrie aus dem GML-Objekten zu extrahieren (was nicht so einfach ist),
        da im Dictionary die zugehoerige Geometrie gespeichert ist.
        
        Args:
            logger: Objekt logging.Logger
            dbConnection: String mit Datenbank-Connection
            dbSchema: String mit Datenbank-Schema
            sourceEpsg: String mit EPSG-Notation im GML-File, z.B. 'http://www.opengis.net/def/crs/EPSG/0/'
            descEpsg: String mit EPSG-Notation fuer BLOB-FeatureStrore, zwingend: 'EPSG:'
            sourcefile: GML-SourceFile
        """
        
        self.__logger = logger
        self.__strConnection = dbConnection
        self.__dbSchema = dbSchema
        self.__sourceEpsg = sourceEpsg
        self.__descEpsg = descEpsg
        self.conn = None
        self.cur = None
        self.__codeList = {}
        self.geomDict = self.getGeomDict(sourcefile)
        #nur fuer Methode loadGmlSimple()
        self.__geoTypes = ['gml:GeometryCollection','gml:MultiSurface','gml:MultiCurve','gml:MultiPoint','gml:MultiPolygon','gml:MultiLineString','gml:Surface','gml:Curve','gml:Point','gml:Polygon','gml:LineString']#SimpleFeature Spez., Multi for Single!
           
        try:
            self.conn = psycopg2.connect(self.__strConnection)
            self.cur = self.conn.cursor()
            strSql = "SELECT * FROM " + self.__dbSchema + ".feature_types"
            self.cur.execute(strSql)
            
            #Dictionary ft_type    
            rows = self.cur.fetchall()
            for row in rows:
                strTypeList = row[1].split("}")
                strType = strTypeList[1]
                self.__codeList.update({strType: row[0]})
        except:
            message = "connection failed: " + str(sys.exc_info()[0]) + "; " + str(sys.exc_info()[1])
            self.__logger.error(message)
            self.closeConnection()
            sys.exit()
    
    def getGeomEnvelope(self, geom):
        """Methode gibt den Extent der uebergebenden Geometrie zurueck.
        
        Args:
            geom: feature geometry
            
        Returns:
            geom: feature geometry als Extent
        """
        geo = None
        (minX, maxX, minY, maxY) = geom.GetEnvelope()
        
        if geom.GetGeometryName() == 'POINT':
            geo = ogr.Geometry(ogr.wkbPoint)
            geo.AddPoint(minX, minY)
            geo.FlattenTo2D()
        else:
            ring = ogr.Geometry(ogr.wkbLinearRing)#right hand rule
            ring.AddPoint(minX, minY)
            ring.AddPoint(minX, maxY)
            ring.AddPoint(maxX, maxY)
            ring.AddPoint(maxX, minY)  
            ring.AddPoint(minX, minY)
            
            geo = ogr.Geometry(ogr.wkbPolygon)
            geo.AddGeometry(ring)
            geo.FlattenTo2D()
        
        return geo
    
    def getGeomDict(self, sourcefile):
        """Methode extrahiert gmlId & wkt (from extent) only if geom true!
        
        Args:
            sourcefile: GML-File
            
        Returns:
            geomDict: Dictionary {'gml_id' : 'wkt from extent'}
        """
        geomDict = {}
        driver = ogr.GetDriverByName("GMLAS")
        ds = driver.Open("GMLAS:" + sourcefile, 0)
    
        for lyr in ds:
            lyr.GetFeatureCount()#ohne diesen comment verdrehen sich die x und y values. Keine Erklaerung dafuer.
            
            if lyr.FindFieldIndex("id", True) != -1:
                for feat in lyr:
                    geom = feat.GetGeometryRef()
                    
                    if geom:
                        #wkt = geom.ExportToWkt()
                        wkt = self.getGeomEnvelope(geom).ExportToWkt()#so speichere ich kleinere geoms im dict!
                        gmlId = feat.GetField('id')
                        geomDict.update({gmlId: wkt})
                        
        return geomDict
    
    def commitTransaction(self):
        """Methode speichert die Inserts in der Datenbank."""
        
        self.conn.commit()
        
    def closeConnection(self):
        """Methode schliesst die Datenbankverbindung."""
        
        self.cur.close()
        self.conn.close()

    def loadGmlSimple(self, element):
        """Methode erzeugt aus dem Parameter 'element' ein SQL-Statement und setzt es gegen die Datenbank ab.
        
        Args:
            element: String mit dem GML-FeatureMember z.B. '<tn-ro:RoadLink>...</tn-ro:RoadLink>'
        """
        
        node = etree.fromstring(element.replace(self.__sourceEpsg,self.__descEpsg))
        
        gmlIdList = node.xpath('/*/@gml:id', namespaces={'gml':'http://www.opengis.net/gml/3.2'})
        featureTypeList = node.xpath('/*', namespaces={'gml':'http://www.opengis.net/gml/3.2'})
        
        #extract geometry
        geomList = None
        for geoType in self.__geoTypes:
            expression = "//" + geoType
            geomList = node.xpath(expression, namespaces={'gml': 'http://www.opengis.net/gml/3.2'})
            
            if geomList:
                break
          
        gmlId = gmlIdList[0]
        strType = featureTypeList[0].tag.split("}")[1]
        intType = None
        for dictKeyType, dictValueType in self.__codeList.items():
            if strType == dictKeyType:
                intType = dictValueType
                break
        
        strBinary = etree.tostring(node, encoding='unicode')
        #xml minify
        strBinary = re.sub('\n\s*', '', strBinary)
        #for SQL Insert-Error
        strBinary = re.sub("'", "''", strBinary)
        strBinary = re.sub(r'\\', '/', strBinary)
        
        if geomList:
            geom = etree.tostring(geomList[0], encoding='unicode')
            #with PostGIS-Functions        
            postgisSql = "Box2D(ST_GeomFromGML('" + geom + "'))"

            strSql = "INSERT INTO " + self.__dbSchema + ".gml_objects (gml_id,ft_type,binary_object,gml_bounded_by) VALUES ('" + gmlId + "'," + str(intType) + ",'" + strBinary + "'," + postgisSql + ")"
        else:
            strSql = "INSERT INTO " + self.__dbSchema + ".gml_objects (gml_id,ft_type,binary_object) VALUES ('" + gmlId + "'," + str(intType) + ",'" + strBinary + "')"
        
        try:                
            self.cur.execute(strSql)
        except:
            message = "execute " + gmlId + " failed: " + str(sys.exc_info()[0]) + "; " + str(sys.exc_info()[1]).replace("\n","")
            self.__logger.error(message)
            self.conn.rollback()
            self.closeConnection()
            sys.exit()

    def loadGml(self, element):
        """Methode erzeugt aus dem Parameter 'element' ein SQL-Statement und setzt es gegen die Datenbank ab.
        
        Args:
            element: String mit dem GML-FeatureMember z.B. '<tn-ro:RoadLink>...</tn-ro:RoadLink>'
        """
        
        node = etree.fromstring(element.replace(self.__sourceEpsg,self.__descEpsg))
        
        gmlIdList = node.xpath('/*/@gml:id', namespaces={'gml':'http://www.opengis.net/gml/3.2'})
        featureTypeList = node.xpath('/*', namespaces={'gml':'http://www.opengis.net/gml/3.2'})
        
        gmlId = gmlIdList[0]
        strType = featureTypeList[0].tag.split("}")[1]
        intType = None
        for dictKeyType, dictValueType in self.__codeList.items():
            if strType == dictKeyType:
                intType = dictValueType
                break
        
        strBinary = etree.tostring(node, encoding='unicode')
        #xml minify
        strBinary = re.sub('\n\s*', '', strBinary)
        #for SQL Insert-Error
        strBinary = re.sub("'", "''", strBinary)
        strBinary = re.sub(r'\\', '/', strBinary)
        
        geomWkt = None
        for dictKeyType, dictValueType in self.geomDict.items():
            if dictKeyType == gmlId:
                geomWkt = dictValueType
                break
            
        if geomWkt: 
            #postgisSql = "Box2D(ST_GeomFromText('" + geomWkt + "'))"           
            postgisSql = "ST_GeomFromText('" + geomWkt + "')"
            
            strSql = "INSERT INTO " + self.__dbSchema + ".gml_objects (gml_id,ft_type,binary_object,gml_bounded_by) VALUES ('" + gmlId + "'," + str(intType) + ",'" + strBinary + "'," + postgisSql + ")"
        else:
            strSql = "INSERT INTO " + self.__dbSchema + ".gml_objects (gml_id,ft_type,binary_object) VALUES ('" + gmlId + "'," + str(intType) + ",'" + strBinary + "')"
        
        try:                
            self.cur.execute(strSql)
        except:
            message = "execute " + gmlId + " failed: " + str(sys.exc_info()[0]) + "; " + str(sys.exc_info()[1]).replace("\n","")
            self.__logger.error(message)
            self.conn.rollback()
            self.closeConnection()
            sys.exit()
            
    def deleteDatabase(self):
        """Methode leert die Datenbank und setzt den Index zurueck"""
        
        try:            
            strSqlDel = "DELETE FROM " + self.__dbSchema + ".gml_objects"
            strSqlSeq = "ALTER SEQUENCE " + self.__dbSchema + ".gml_objects_id_seq RESTART WITH 1"
            self.cur.execute(strSqlDel)
            self.cur.execute(strSqlSeq)
            self.conn.commit()    
        except:
            message = "db delete failed: " + str(sys.exc_info()[0]) + "; " + str(sys.exc_info()[1])
            self.__logger.error(message)
            self.conn.rollback()
            self.closeConnection()
            sys.exit()
                   
    def vacuumDatabase(self):
        """Methode fuehrt Vacuum und Analyse auf Datenbank aus"""
        
        try:           
            conn = psycopg2.connect(self.__strConnection)
            conn.set_isolation_level(0)#0 = autocommit
            cur = conn.cursor()
            strSql = "VACUUM VERBOSE ANALYZE " + self.__dbSchema + ".gml_objects"
            cur.execute(strSql)        
        except:
            message = "db vacuum failed: " + str(sys.exc_info()[0]) + "; " + str(sys.exc_info()[1])
            self.__logger.error(message)
            sys.exit()
        finally:
            cur.close()
            conn.close()
            