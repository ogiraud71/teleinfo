# coding: utf-8 
ver='22/10/2019'
from time import sleep,localtime
import serial
import os
import teleinfo
import json
import urllib.request as url

monCompteur=teleinfo.teleinfo()

# ******** Ines *****************************
adresse='http://192.168.0.102/cgi-bin/sendmsg.lua?'
cde="cmd=GET+ALLS"
toutesLes10min='x'
chaineInes=';0;0;0'
dico={}
InesDatas={}

def decode(h):
    encoding = h.info().get_content_charset('utf-8')
    j = json.loads(h.read().decode(encoding))
    return(j)

def getInesDatas():
    h = url.urlopen(adresse+cde)
    j = decode(h)
    return(j['DATA'])
#**************************************


def aujourdhui():
    chaine='%d-%d-%d.csv'%(localtime().tm_year,localtime().tm_mon,localtime().tm_mday)
    #~ chaine='%d-%d-%d_%dh.csv'%(localtime().tm_year,localtime().tm_mon,localtime().tm_mday,localtime().tm_hour)
    return(chaine)
    
def dizaineDeMinute():
    chaine='%2d'%(localtime().tm_min)
    return(chaine[0])

def uniteDeMinute():
    chaine='%2d'%(localtime().tm_min)
    return(chaine[1])

def heureComplete():
    chaine='%d/%d/%d %2d:%2d:%2d'%(localtime().tm_mday,localtime().tm_mon,localtime().tm_year,localtime().tm_hour,localtime().tm_min,localtime().tm_sec)
    return(chaine)

def dateComplete():
    chaine='%d/%d/%d'%(localtime().tm_mday,localtime().tm_mon,localtime().tm_year)
    return(chaine)



# ***********************************************
#Liason serie
with serial.Serial('/dev/ttyS0') as ser:
    try:
        ser.baudrate=1200
        ser.bytesize=serial.SEVENBITS
        #~ ser.parity=serial.PARITY_EVEN
        ser.stopbits=serial.STOPBITS_ONE
        ser.timeout=0
        ser.rts=1
    except Exception as detail :
        #~ print('Pb avec la liaison serie : %s'%detail)
        pass
# ***********************************************

    # ***********************************************
    #Fichiers
    open('running', 'a').close()
    
    while os.path.isfile('running'):
        #Boucle permettant le changement de fichier
        
        premiereLectureDuJour=True
        fileName=aujourdhui()
        minutes='99'
        calcNeeded=False
        lastBase=0
        
        reste=''
        if os.path.isfile(fileName):
            withEntete=False
        else:
            withEntete=True
        with open(fileName,'a',buffering=65536) as f:
            if withEntete:
                #~ entete='Heure;HCHC;HCHP;PTEC;IINST;PAPP;Pmin;Pmax;Pavg'
                entete='Heure;HCHC;HCHP;PTEC;IINST;PAPP;BASE;AVG;TempRoom;TempFumees;VitessePellets'
                
                f.write(entete+'\n')
            while os.path.isfile('running'):

                # boucle liaison serie
                #~ ligne=ser.readline().decode("utf-8")
                try:
                    tout=ser.read_all().decode("utf-8").split('\r\n')
                    tout[0]=reste+tout[0]
                except:
                    print('Probleme liaison serie : %s'%ser.read_all())
                try:
                    ligne=tout[-2]
                    reste=tout[-1]
                except:
                    ligne=tout[-1]
                    reste=''
                #~ print(' ligne=%s reste=%s'%(ligne,reste))#pour debug
                
                error=monCompteur.verifLigne(ligne)
                if not error:
                    error=monCompteur.decodeLigne()
                    if error not in ['ETIQ','']:
                        print(error)
                    if not error:
                        if monCompteur.etiquette=="PAPP":
                            if monCompteur.premiereLecture:
                                monCompteur.premiereLecture=False
                            else:
                                # ***********************************************
                                #MAJ valeurs complete, on peut calculer
                                
                                if minutes!=localtime().tm_min:
                                    #Traitement en attente toutes les minutes
                                    minutes=localtime().tm_min
                                    lastBase=monCompteur.valeurs['BASE']
                                    calcNeeded=True
                                if calcNeeded and lastBase!=monCompteur.valeurs['BASE']:
                                    #Traitement juste après changement de valeur d'index
                                    monCompteur.calcAVG()
                                    calcNeeded=False

                                if toutesLes10min!=dizaineDeMinute():
                                    toutesLes10min=dizaineDeMinute()
                                    #Traitement toutes les 10 min
                                    try:
                                        InesDatas=getInesDatas()
                                        chaineInes=';%.1f;%.0f;%.1f'%(InesDatas["T1"],InesDatas["T3"],InesDatas["FDR"]) #TempRoom,TempFumees,VitessePellets
                                    except:
                                        pass
                                    
                                #Ecriture de la ligne dans fichier csv
                                chaine=heureComplete()
                                for el in ['HCHC','HCHP','PTEC','IINST','PAPP','BASE','AVG']:
                                    chaine+=';%d'%monCompteur.valeurs[el]
                                chaine+=chaineInes
                                f.write(chaine+'\n')
                                
                                #Flush fichier sur demande
                                if os.path.isfile('/mnt/ramdisk/flushing'):
                                    f.flush()
                                    os.system('sudo rm /mnt/ramdisk/flushing')#il faut les droits administreurs
                                
                                #Ecriture dans ramdisk pour consultation avec autre shell
                                try:
                                    with open('/mnt/ramdisk/teleinfo.json','w') as mj:
                                        json.dump({'Elec':monCompteur.valeurs,'Poele':InesDatas},mj)
                                except:
                                    print('erreur ecriture /mnt/ramdisk/teleinfo.json')
                                
                                #Enregistrement index initial
                                if premiereLectureDuJour:
                                    HCHC=int(monCompteur.valeurs['HCHC'])
                                    HCHP=int(monCompteur.valeurs['HCHP'])
                                    BASE=int(monCompteur.valeurs['BASE'])
                                    premiereLectureDuJour=False
                                
                                #Verif changement de jour
                                if fileName!=aujourdhui():
                                    chaine='%s;%d;%d;%d\n'%(dateComplete(),int(monCompteur.valeurs['HCHC']),int(monCompteur.valeurs['HCHP']),int(monCompteur.valeurs['BASE']))
                                    try:
                                        open('Historique.csv','a').write(chaine)
                                    except:
                                        print('Ecriture historique impossible')
                                    break                               #On sort du 1er while, mais comme running est tjs present on revient avec nouveau fichier car tjs dans autre while
                sleep(0.25)
    # ***********************************************
