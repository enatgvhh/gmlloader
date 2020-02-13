#

Simple INSPIRE GML-File Loader for deegree SQLFeatureStore in blob mode
=======================================================================

## Inhalt
* [Einleitung](#einleitung)
* [GML-Loader in Python](#gml-loader-in-python)
* [Ausblick](#ausblick)
* [Nachnutzung für AAA NAS-Files](#nachnutzung-aaa-nas-files)


## Einleitung
Stellen wir uns vor, wir haben ein INSPIRE GML-File produziert und wollen den Inhalt in einen deegree SQLFeatureStore schreiben, um darauf einen WFS und WMS aufzusetzen. Dazu gibt es natürlich auch ein entsprechendes deegree Tool. Dieses setzt direkt auf den deegree 'GIS-Server' auf. Es ist recht ressourcenhungrig, validiert die GML-Objekte auch und löst Referenzen auf.

Auslöser um sich eine einfache Lösung auszudenken, war das INSPIRE GML-File, das aus dem okstra2inspire Konverter herauskommt. Mit diesem Konverter werden Straßendaten aus dem OKSTRA in das INSPIRE Schema transformiert. Für Hamburg ist das File ca. 350 MB groß. Und das deegree Tool kam mit diesem GML-File nicht so ohne weiteres klar.

Deshalb habe ich dieses einfache python-package erstellt. Es ist zwar sehr einfach, funktioniert aber und verbraucht sehr wenig Ressourcen und Rechenzeit. Auf jeden Fall wird es eine weitaus bessere Lösung geben. Zu beachten ist auch, dass die zu ladenden GML-Objekte valide sein müssen. Dafür trage ich bei dieser Lösung die volle Verantwortung.


## GML-Loader in Python
Das python-package 'gmlloader5' und ein Client sind im Ordner [src](src) zu finden.

Schauen wir uns etwas den Hintergrund an. Wir verwenden ein INSPIRE PlannedLandUse [GML-File](data/PlannedLandUse.gml) mit diversen GML-Feature-Membern *(SpatialPlan, ZoningElement, SupplementaryRegulation, OfficialDocumentation)*. Jedes Feature-Member soll in ein BLOB-Attribut der Datenbanktabelle 'gml_objects' verpackt werden. Das ist recht einfach. Dazu lesen wir das GML-File in einen Tree ein, schneiden quasi die einzelnen Objekte aus und fügen sie genauso in ein BLOB-Attribut der Datenbanktabelle ein. Es ist letztendlich die gleiche Vorgehensweise wie in dem hier vorgestellten INSPIRE [FME-Workflow]( https://github.com/enatgvhh/inspire/blob/master/fme4inspire.md).

Kommen wir zu dem schwierigen Teil. Die Datenbanktabelle 'gml_objects' enthält ein Attribut 'gml_bounded_by'. In diesem Attribut wird der Extent eines Geo-Objektes gespeichert. Deegree benötigt es für die räumliche Suche und Indexierung. Wie können wir aus einem GML-Objekt sein Geometrie-Element extrahieren? Eine richtig gute Lösung wird sich diese Info aus dem Schema generieren. Derzeit habe ich noch keine Ahnung wie man das anfängt. Stattdessen habe ich hier eine sehr einfache *(Methode 'loadGmlSimple')* und eine einfache Herangehensweise *(Methode 'loadGml')* gewählt.

Kommen wir zur einfachsten Methode 'loadGmlSimple'. Hierbei durchsuchen wir jedes GML-Objekt nach den Geometrie Typen der Simple Feature Spezifikation.
```
geoTypes = ['gml:GeometryCollection','gml:MultiSurface','gml:MultiCurve','gml:MultiPoint','gml:MultiPolygon','gml:MultiLineString','gml:Surface','gml:Curve','gml:Point','gml:Polygon','gml:LineString']

geomList = None
for geoType in geoTypes:
    expression = "//" + geoType
    geomList = node.xpath(expression, namespaces={'gml': 'http://www.opengis.net/gml/3.2'})

    if geomList:
        break
```
Unser Ziel dabei ist, die gesamte, die größte, umfassende Geometrie zu extrahieren. Z.b. suchen wir zuerst nach einem 'gml:MultiSurface'. Gibt es das nicht, suchen wir nach einem 'gml:Surface'. Diese Vorgehensweise ist natürlich mit einem gewissen Risiko verbunden. Man muss schon genau wissen, was für Geometrie-Elemente im GML-File vorkommen. Bei dem RoadTransportNetwork GML-File aus dem okstra2inspire Konverter funktioniert das recht gut *(enthält nur gml:LineString und gml:Point)*. Der Ladevorgang dieses 350 MB großen GML-Files dauert knapp 5 min *(Quad 2,70 GHz Intel Xeon, 32GB Memory)*. Damit ist mit diesem Ansatz der Zweck eigentlich schon erfüllt.
```
#Hinweis: ggf. muss noch der Proxy gesetzt werden!

from osgeo import gdal
gdal.SetConfigOption('GDAL_HTTP_PROXY', '111.11.111.111:80')
```
Wollen wir den Loader aber für GML-Files aller INSPIRE Themen verwenden, dann müssen wir noch etwas nachrüsten. Das ist mit der Methode 'loadGml' erfolgt. Dazu benutzen wir den GDAL [GMLAS-Driver](https://gdal.org/drivers/vector/gmlas.html#vector-gmlas) *(Installation von z.B. gdal-204-1911-x64-core.msi und GDAL-2.4.0.win-amd64-py3.7.msi erforderlich)*. Der Driver löst das ursprüngliche GML-File auf, er zerstört die GML-Struktur. Deshalb verwenden wir ihn nur dazu, die 'gml_id' und die Geometrie (Extent) in ein Dictionary zu speichern. Aus diesem Dictionary holen wir uns dann für jedes Objekt seinen Extent, um ihn in das Attribut 'gml_bounded_by' einzufügen. Ich habe den Loader nicht an dem 350 MB RoadTransportNetwork GML-File getestet. Die Rechenzeit dürfte aber so um den Faktor 6 länger sein.

Abschließend noch ein kurzer Hinweis auf das [Konfigurationsfile](src/ConfigLoader.xml), indem es auch ein epsg Element gibt. Das GML-File aus dem okstra2inspire Konverter enthält das Attribut srsName=“http://www.opengis.net/def/crs/EPSG/0/3044“. In die Datenbank werden wir es allerdings so einfügen: srsName="EPSG:3044". Die INSPIRE konforme Notation „http://www.opengis.net/def/crs/EPSG/0/...“ führt zur Umdrehung der Interpretation der Polygon Orientierung. Und darauf wollen wir uns gar nicht erst einlassen.


## Ausblick
Den GML-Loader, in seiner einfachsten Version, verwende ich um das RoadTransportNetwork GML-File aus dem okstra2inspire Konverter in einen deegree SQLFeatureStore (BLOB-Modus) zu laden. Produktiv habe ich die Client-Funktionalität noch in einen Multiprozess verpackt. Dieser Multiprozess prüft alle 24h ob sich das GML-File verändert hat. Wird eine Veränderung festgestellt, dann wird der Ladevorgang gestartet.


## Nachnutzung AAA NAS-Files
Für diverse INSPIRE Themen sind ALKIS und ATKIS Daten in die Zielschemen zu transformieren. In Hamburg erfolgt dies auf Basis von mehr 300 NAS-Files (> 10 GB). Für jedes Thema jeweils alle 300 NAS-Files zu durchlaufen, das ist sehr uneffektiv. Viel einfacher wäre es, wenn die AAA-Objekte einmal in eine Datenbank geladen werden und dann für jede Transformation nur noch die wirklich benötigten Objektarten selektiert werden. Das lässt sich natürlich auch mit dem GML-Loader, in leicht abgewandelter Version, bewerkstelligen. D.h. wir laden die AAA-Objektarten wiederum in einen deegree SQLFeatureStore (BLOB-Modus). Und da wir diesen nur als Zwischenspeicher verwenden, benötigen wir in der Datenbanktabelle auch nicht das Attribut 'gml_bounded_by' mit dem Extent. Wir können unser python-package also von der entsprechenden Funktionalität befreien.

Produktiv habe ich das Ganze wiederum in 2 Mutiprozesse (ALKIS und ATKIS) verpackt. Verwenden tue ich den Zwischenspeicher aber letztendlich nur für die Transformation in das Zielschema Geographical Names, die mit FME erfolgt. Der reine Ladevorgang dauert ca. 15 min *(Quad 2,70 GHz Intel Xeon, 32GB Memory)*.
