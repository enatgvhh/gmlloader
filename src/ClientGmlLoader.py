# -*- coding: UTF-8 -*-
#ClientGmlLoader.py
from lxml import etree
from gmlloader5 import configloader
from gmlloader5 import gmlloader
    
def getConfigLoader(eList):
    confLoader = None
    
    for item in eList:
        strItem = etree.tostring(item, encoding='unicode')
        node = etree.fromstring(strItem)
    
        sourcefile = node.xpath('//sourcefile', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        logfile = node.xpath('//logfile', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        dbname = node.xpath('//dbname', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        user = node.xpath('//user', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        host = node.xpath('//host', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        port = node.xpath('//port', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        password = node.xpath('//password', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        schema = node.xpath('//schema', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        sourceurl = node.xpath('//sourceurl', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
        desturl = node.xpath('//desturl', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})[0].text
    
        confLoader = configloader.ConfigGmlLoader(logfile, dbname, user, host, port, password, schema, sourceurl, desturl)
        break
    
    return [confLoader,sourcefile]

def main():
    etConf = etree.parse('ConfigLoader.xml')
    eListConf = etConf.xpath('//ConfigObject', namespaces={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})
    confLoaderList = getConfigLoader(eListConf)
    confLoader = confLoaderList[0]
    sourcefile = confLoaderList[1]
    logger = confLoader.getLogger()
    logger.info('Start')
    
    gmlLoader = gmlloader.GmlLoader(logger,confLoader.getDatabaseConnection(),confLoader.getDatabaseSchema(),confLoader.getSourceCoordinate(),confLoader.getDestCoordinate(),sourcefile)
    gmlLoader.deleteDatabase()
    logger.info('delete database successfully')
    
    et = etree.parse(sourcefile)
    eList = et.xpath('//gml:featureMember/*', namespaces={'gml':'http://www.opengis.net/gml/3.2'})
    
    for item in eList:
        #gmlLoader.loadGmlSimple(etree.tostring(item, encoding='unicode'))
        gmlLoader.loadGml(etree.tostring(item, encoding='unicode'))
        
    gmlLoader.commitTransaction()
    gmlLoader.closeConnection()
    logger.info('load database successfully')
    gmlLoader.vacuumDatabase()
    logger.info('vacuum database successfully')  
    logger.info('End')
    
if __name__ == '__main__':
    main()
    