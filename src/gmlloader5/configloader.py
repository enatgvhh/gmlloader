# -*- coding: UTF-8 -*-
#configloader.py
import logging

class ConfigGmlLoader(object):
    """Class ConfigGmlLoader speichert die Config-Einstellungen des Loaders."""
    
    def __init__(self, logfile, dbname, user, host, port, password, schema, sourceurl, desturl):
        """Konstruktor der Klasse ConfigGmlLoader.
        
        Args:
            logfile: String mit Path/File.log
            dbname: String mit Datenbank-Name
            user: String mit Datenbank-User
            host:  String mit Datenbank-Host
            port: String mit Datenbank-Port
            password: String mit Datenbank-Password
            schema: String mit Datenbank-Schema
            sourceurl: String mit EPSG-Notation im GML-File, z.B. 'http://www.opengis.net/def/crs/EPSG/0/'
            desturl: String mit EPSG-Notation fuer BLOB-FeatureStrore, zwingend: 'EPSG:'
        """
        
        self.__logfile = logfile
        self.__dbname = dbname
        self.__user = user
        self.__host = host
        self.__port = port
        self.__password = password
        self.__schema = schema
        self.__sourceurl = sourceurl
        self.__desturl = desturl
        
    def getLogger(self):
        """Methode gibt ein Objekt logging.Logger zurueck.
        
        Returns:
            logging.Logger: Logger-Objekt
        """
        
        logging.basicConfig(filename=self.__logfile, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
        return logging.getLogger('loggerGmlLoader')
    
    def getDatabaseConnection(self):
        """Methode gibt einen String mit der Datenbank-Connection zurueck.
        
        Returns:
            String: Database Connection String <dbname='' user='' host='' port='' password=''>
        """
        
        strConn = "dbname='" + self.__dbname + "' user='" + self.__user + "' host='" + self.__host + "' port='" + self.__port + "' password='" + self.__password + "'"
        return strConn
    
    def getDatabaseSchema(self):
        """Methode gibt einen String mit dem Datenbank-Schema zurueck.
        
        Returns:
            String: Datenbank-Schema
        """
        
        return self.__schema
    
    def getSourceCoordinate(self):
        """Methode gibt einen String mit der EPSG-Notation im GML-File, z.B. 'http://www.opengis.net/def/crs/EPSG/0/' zurueck.
        
        Returns:
            String: EPSG-Notation im GML-File
        """
        
        return self.__sourceurl
    
    def getDestCoordinate(self):
        """Methode gibt einen String mit der EPSG-Notation fuer den BLOB-FeatureStrore <zwingend: 'EPSG:'> zurueck.
        
        Returns:
            String: EPSG-Notation fuer den BLOB-FeatureStrore
        """
        
        return self.__desturl
    