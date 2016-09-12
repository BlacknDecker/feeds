#! python3
import requests, bs4, re, xml.etree.ElementTree as ET, datetime, xml.dom.minidom as minidom, os, hashlib 

#########ESTRAGGO I DATI DALL'HTML######################################################
#prende l'html della pagina col codice richiesto
def getHTML(n): 
    url= 'http://www.meteoam.it/ta/previsione/'+str(n)
    user_agent= 'Mozilla/5.0 (Windows NT 6.1; WOW64)'
    headers = {'user-agent' : user_agent}               #il sito richiede un userAgent
    res = requests.get(url, headers=headers)            #scarico l'html
    res.raise_for_status()                              #se ci sono problemi interrompo il programma
    return res.text                                     #restituisco l'html in forma testuale


#Trova le date delle 3 previsioni disponibili nella pagina e le ritorna in una lista
def findDates(pageSoup):
    tagList= pageSoup.find_all('th')
    dateRegex= re.compile(r'\d\d/\d\d/\d\d\d\d')    #regex per la data
    dList= []                                       #lista delle date
    for t in tagList:
        mo= dateRegex.search(t.text)                #match object
        if mo is not None:
            dList.append(mo.group())                #se ho trovato una data la inserisco in lista
    return dList


#Prendo la stringa di codice con la localita
def getLocation(pageSoup):
    #prendo la stringa con il tag contenente la localita
    rawStr= pageSoup.find('title').get_text(' ', strip=True)
    #Tolgo il grosso:
    strList= rawStr.split('|')
    rawStr= strList[0]
    #Ora controllo se il comune esiste
    strList= rawStr.split(' ')      #lista delle parole della frase
    if strList[1].lower()=='per':   #non trovato
        return 'NF'                 #not found
    else:
        strList= strList[3:-1]  #prendo solo le parole del nome + provincia
        nameList= strList[0:-1] #prendo solo le parole del nome
        provincia= strList[-1]  #prendo la provincia
        #compongo la stringa
        strFinal= ' '.join(nameList)+' '+provincia
        return strFinal


#prende la lista dei Fenomeni Intensi segnalati
def getFIList(fiTag):   
    tmpL= fiTag.find_all('img')
    fil= []                             #fenomeni intensi list
    if tmpL is not None:
        for t in tmpL:
            fil.append(t.get('title'))  #Aggiungo il fenomeno segnalato
        return fil
    else:
        return None


#prende le info a partire dal tag dell'ora dato:
def getInfoList(hTag):
    itl= hTag.find_all('td')                        #creo la lista tag delle info (infoTagList)
    il= []                                          #infoList
    #Prendo le singole informazioni:
    fenInt= getFIList(itl[0])                       #fen. intensi
    meteo= itl[1].find_all('img')[0].get('title')   #meteo
    il.append(fenInt)
    il.append(meteo)
    il.append(itl[2].text)                          #probabilita di pioggia
    il.append(itl[3].text)                          #temperatura
    il.append(itl[4].text)                          #temp. percepita
    il.append(itl[5].text)                          #umidita
    vento= itl[6].find_all('span', class_='badge')[0].get('title')  #vento
    il.append(vento)
    il.append(itl[7].text)                          #raffiche
    #return la lista creata:
    return il


#Prende il tag del giorno e il giorno scelto e ne estrae il meteo. Ritorna una lista con le info suddivise per ore
def getDayMeteoList(dayTag, dayInt):
    hourTagList= dayTag.find_all('tr')      #Lista dei tag che suddividono le info meteo per orario
    dml= []                                 #DayMeteoList
    for ht in hourTagList:
        hml=[]                              #HourMeteoList
        ora= ht.find_all('th')[0].text      #prendo l'orario
        hml.append(ora)                     #lo aggiungo alla lista
        hml.append(getInfoList(ht))         #aggiungo la lista delle info
        dml.append(hml)                     #aggiungo la lista oraria alla lista giornaliera
    return dml                              #ritorno la DayMeteoList
        

#Imposta l'html testuale per l'estrazione
def setupMeteoList(pageSoup):
    dayTagList= pageSoup.find_all('tbody')      #lista dei tag che contengono le previsioni di una giornata
    dayTagList= dayTagList[0:3]                 #poiche esistono anche altre tabelle, prendo solo i 3 campi che mi servono (0=oggi,1=domani,2=dopodomani)
    meteoList= []
    meteoList.append(getDayMeteoList(dayTagList[0], 0))
    meteoList.append(getDayMeteoList(dayTagList[1], 1))
    meteoList.append(getDayMeteoList(dayTagList[2], 2))
    return meteoList


#Crea la stringa con l'orario dell'aggiornamento Conforme allo standard RFC822
def getUpdateTime():
    dt= datetime.datetime.now()
    strUT=''+dt.strftime('%a')+', '+dt.strftime('%d')+' '+dt.strftime('%b')+' '+dt.strftime('%Y')   #data
    dtUTC= datetime.datetime.utcnow()
    deltaH= dt.hour-dtUTC.hour                                                                      #UTC offset
    strUT+=' '+dt.strftime('%X')+' +0'+str(deltaH)+'00'                                             #ora
    return strUT


########CREO IL FEED XML###############################################################
def createXMLFeed(codLocalita,localita,dataPrevisioni,infoMeteoClassList,updateTime):
    root= ET.Element('rss')                                             #Nodo Radice
    root.set('version','2.0')                                           #attributo della radice
    #root.set('xmlns:atom','http://www.w3.org/2005/Atom')               #ATOM <-----
    channel= ET.SubElement(root,'channel')                              #Nodo Channel
    title= ET.SubElement(channel,'title')                               #Title del Channel
    title.text= 'Previsioni Meteo '+localita+' '+dataPrevisioni
    link= ET.SubElement(channel,'link')                                 #Link del Channel
    link.text= 'http://www.meteoam.it/ta/previsione/'+str(codLocalita)
    description= ET.SubElement(channel,'description')                   #Description del Channel
    description.text= 'Previsioni Meteo Orarie'
    pubDate= ET.SubElement(channel,'pubDate')                           #Data e ora dell'ultimo aggiornamento
    pubDate.text= ''+updateTime
    ##Inizio le previsioni per orario
    itemNumber= 0                                                       #Conto il numero di Item
    for h in infoMeteoClassList:                                        #infoMeteoClassList==DayMeteoList del giorno scelto
        item= ET.SubElement(channel,'item')                             #Creo un elemento per ogni ora
        title= ET.SubElement(item,'title')                              #Title dell'Item
        title.text= h[0]                                                #inserisco l'orario nel titolo
        guid= ET.SubElement(item,'guid')                                #Guid dell'Item
        guid.set('isPermaLink','false')                                 #attributo di guid
        guid.text= getGuid(updateTime, itemNumber)                      #Creo il codice univoco
        itemNumber+=1                                                   #Aggiorno il numero per l'oggetto successivo
        link= ET.SubElement(item,'link')                                #Link dell'Item
        link.text= 'http://www.meteoam.it'
        description= ET.SubElement(item,'description')                  #Description dell'Item
        description.text= getCDataInfo(h[1])                            #inserisco i CData con le info <-----------
        #description.text= getDescrizioneTestuale(h[1])                 #oppure i dati testuali
    return root


#Creo un identificatore univoco per l'Item, da inserire nel campo guid:
def getGuid(updateTime, itemNumber):
    m= hashlib.md5()                    #creo l'oggetto hash
    tmp= updateTime+' '+str(itemNumber) #creo la stringa da codificare
    m.update(tmp.encode())              #aggiungo la stringa (in byte) alla tabella
    return m.hexdigest()                #ritorno la stringa creata


#Creo una stringa CData con le info meteo
def getCDataInfo(infoL):
    cd=  '<![CDATA[ '
    if len(infoL[0])==0:
        cd+= '<strong>Fenomeni Intensi:</strong> - <br />'
    else:
        cd+= '<strong>Fenomeni Intensi:</strong> '      + str(infoL[0]) +' <br />'
    cd+= '<strong>Tempo:</strong> '                     + infoL[1] +' <br />'
    cd+= '<strong>Probabilita Precipitazioni:</strong> '+ infoL[2] +' <br />'
    cd+= '<strong>Temperatura:</strong> '               + infoL[3] +' &deg;C'+' <br />'
    cd+= '<strong>Temperatura Percepita:</strong> '     + infoL[4] +' &deg;C'+' <br />'
    cd+= '<strong>Umidita:</strong> '                   + infoL[5] +'%'+' <br />'
    cd+= '<strong>Vento:</strong> '                     + infoL[6] +' <br />'
    cd+= '<strong>Raffiche:</strong> '                  + infoL[7] +' km/h'+' <br />'
    cd+= ']]>'
    return cd

#Creo una stringa con le info in forma testuale (solo in caso che i CData non vadano bene)
def getDescrizioneTestuale(infoL):
    dt=''
    dt+= 'Fenomeni Intensi: '               + str(infoL[0]) +'\n'
    dt+= 'Tempo: '                          + str(infoL[1]) +'\n'
    dt+= 'Probabilita di Precipitazioni: '  + str(infoL[2]) +'\n'
    dt+= 'Temperatura: '                    + str(infoL[3]) +' °C'+'\n'
    dt+= 'Temperatura Percepita: '          + str(infoL[4]) +' °C'+'\n'
    dt+= 'Umidita: '                        + str(infoL[5]) +'%'+'\n'
    dt+= 'Vento: '                          + str(infoL[6]) +' km/h'+'\n'
    dt+= 'Raffiche: '                       + str(infoL[7]) +' km/h'+'\n'
    return dt

#Return a pretty-printed XML string for the Element.
def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="   ")

#Aggiusta la formattazione per i CData (che non e supportata da ElementTree)
def formattingFix(strXML):
    firstStep= strXML.replace('&lt;'.encode(),'<'.encode())
    secondStep= firstStep.replace('&gt;'.encode(),'>'.encode())
    newStr= secondStep.replace('&amp;'.encode(),'&'.encode())
    return newStr


########OPERAZIONI SUI FILE############################################################
#Salvo il feed su file:
def salvaSuFile(strXML,loc,codicePrevisione):
    if codicePrevisione==0:
        prev='oggi'
    elif codicePrevisione==1:
        prev='domani'
    else:
        prev='dopodomani'
    ind= loc.find('(')
    loc=loc[:ind-1]                                                     #prendo solo il nome
    loc= ''.join(loc.split(' '))                                        #tolgo gli spazi
    if not os.path.exists('feeds'):
        os.makedirs('feeds')                                            #creo la cartella per i feed se non esiste
    path= os.path.join('feeds', loc.lower()+'_feed_'+prev+'.xml')       #creo il path
    locFile= open(path, 'wb')                                           #salvo i feed in una sottocartella
    locFile.write(formattingFix(strXML))
    locFile.close()


#prendo le localita da File, restituisce una lista con i codici delle localita
def getLocationCodes(fileName):
    #Apro il file e prendo la lista
    locFile= open(fileName, 'r')
    listaLocStr= locFile.read()
    listaLoc= listaLocStr.split('\n')   #creo la lista
    locFile.close()
    #Estraggo i codici
    listaCod=[]
    for l in listaLoc:
        tmp= l.split('|')
        listaCod.append(tmp[0])
    return listaCod

#######################################################################################

#Master of Puppets
def init():
    fileName= 'localita_meteoAM.txt'                        #Nome del file in cui si trova la lista di localita
    codiciLoc= getLocationCodes(fileName)
    #Per ogni codice creo i file meteo
    for cod in codiciLoc:
        #Prendo l'html della pagina
        pageSoup= bs4.BeautifulSoup(getHTML(cod), 'html.parser') #uso il parser html
        #Prendo l'orario di aggiornamento
        upTime= getUpdateTime()
        #Prendo il nome della localita (per controllo):
        loc= getLocation(pageSoup)
        #prendo le date delle previsioni disponibili (oggi,domani,dopodomani)
        dateList= findDates(pageSoup)
        #prendo le info meteo classificate per giorno e ora
        listaInfoMeteoCat= setupMeteoList(pageSoup)
        #####
        print('Setup '+loc+' done!')
        #Ora creo i feed per le 3 previsioni:
        for i in range(0,3):
            rawXML= createXMLFeed(cod,loc,dateList[i],listaInfoMeteoCat[i],upTime)  #xml grezzo
            #tmpStr= prettify(rawXML)                       #xml indentato restituito come stringa <--solo per visualizzazione!!
            tmpStr= ET.tostring(rawXML, 'utf-8')
            salvaSuFile(tmpStr,loc,i)                       #salvo il feed
            #####
            print('feed '+str(i)+' creato!')
        #####
        print('Localita completata!\n')


#Let's start!
init()
