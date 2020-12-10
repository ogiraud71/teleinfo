# coding: utf-8 
from time import sleep,localtime,time

#~ // Sequence lue sur mon compteur (Bleu) en mode HP/HC
#~ //  ADCO 030122369245 = Adresse du concentrateur de téléreport
#~ //  OPTARIF HC..      = Option tarifaire choisie
#~ //  ISOUSC 45         = Intensité souscrite
#~ //  HCHC 101235969    = Index Heures Creuses
#~ //  HCHP 135646371    = Index Heures Pleines
#~ //  PTEC HP..         = Période Tarifaire en cours
#~ //  IINST 002         = Intensité Instantanée
#~ //  IMAX 048          = Intensité maximale appelée
#~ //  PAPP 00470        = Puissance apparente
#~ //  HHPHC E           = Horaire Heures Pleines Heures Creuses
#~ //  MOTDETAT 000000   = Mot d'état du compteur

def heureComplete():
    chaine='%d/%d/%d %2d:%2d:%2d'%(localtime().tm_mday,localtime().tm_mon,localtime().tm_year,localtime().tm_hour,localtime().tm_min,localtime().tm_sec)
    return(chaine)

def checksum(chaine):
    cs=0
    for ch in chaine:
        cs+=ord(ch)
    cs&=0x3F
    cs+=0x20
    return(cs)

class helice:
    def __init__(self):
        self.indice=0
        self.liste=["\\","|","/","-"]
    def run(self):
        self.indice+=1
        if self.indice>3 : self.indice=0
        return self.liste[self.indice]
        
class teleinfo():
    def __init__(self):
        self.premiereLecture=True
        self.etiquette=""
        self.donnee=""

        self.valeurs={
            #~ "ADCO":"",
            #~ "OPTARIF":"",
            #~ "ISOUSC":0,
            "HCHC": 0,
            "HCHP":0,
            "BASE":0,
            "PTEC":0,
            "IINST":0,
            "IMAX":0,
            "PAPP":0,
            "AVG":0,
            }
        
        self.previous_base=0 #valeur lue lors de la minute precedente
        self.previous_time=time() #heure lors de la mesure precedente
        
    def calcAVG(self):
        if self.previous_base!=0:
            self.valeurs['AVG']=3600*(self.valeurs['BASE']-self.previous_base)/(time()-self.previous_time) #pour passer de Wh Ã  W
        else:
            self.valeurs['AVG']=0
        self.previous_base=self.valeurs['BASE']
        self.previous_time=time()
    
    def verifLigne(self,chaine):
        '''Gestion du checksum'''
        #Methode 1 : Ne marche pas qd caractere de CS est espace
        #~ try:
            #~ self.etiquette,self.donnee,controle=chaine.split(" ") 
        #~ except Exception as detail :
            #~ print("Ligne non valide (%s)"%chaine)
            #~ return(detail)
            
        #Methode2
        espace1=chaine.find(' ')
        if espace1==-1:
            return('LINE')
        espace2=chaine[espace1+1:].find(' ')+espace1+1
        if espace2==-1:
            return('LINE')
        try:
            self.etiquette=chaine[:espace1]
            self.donnee=chaine[espace1+1:espace2]
            controle=chaine[espace2+1]
        except Exception as detail :
            return("Ligne %s non valide :%s"%(chaine,detail))
        else:
            #~ print('etiquette=%s donnee=%s'%(self.etiquette,self.donnee)) #pour debug
            cs=checksum(self.etiquette+' '+self.donnee)
            if cs!=ord(controle[0]):
                #~ print('Checksum error: cs lu=%d cs calc=%d'%(cs,ord(controle[0]))) # pour debug
                return('CS')
            else:
                return('')

    def decodeLigne(self):
        '''enregistrement valeur lue dans tableau au bon endroit'''
        if self.etiquette in ["HCHC","HCHP","IINST","IMAX","PAPP","BASE"]:
            try:
                self.valeurs[self.etiquette]=int(self.donnee)
            except:
                return('%s=%s !'%(self.etiquette,self.donnee))
            else:
                return('')
        elif self.etiquette=="PTEC":
            if self.donnee=="TH.." or self.donnee=="HP..":
                self.valeurs[self.etiquette]=0
                return('')
            elif self.donnee=="HC..":
                self.valeurs[self.etiquette]=1
                return('')
            else:
                return('%s=%s !'%(self.etiquette,self.donnee))
        else:
            return('ETIQ')
            
#*********************************************
if __name__ == '__main__':
    import serial
    import sys

    try :
        delais=float(sys.argv[1])
    except:
        delais=0.25
    print('delais = %f'%delais)
    #delais=0.5s => une actualisation ttes les 5s Ã  6s
    #delais=0.4s => une actualisation ttes les 4s Ã  5s
    #delais=0.3s => une actualisation ttes les 3s Ã  4s
    #delais=0.2s => une actualisation ttes les 2s Ã  3s
    #delais=0.17s => une actualisation ttes les 2s .... voir 3s une fois ttes les 70sec
    #delais=0.15s => une actualisation ttes les 2s .... voir 3s une fois ttes les 70sec
    #delais=0.1s => une actualisation ttes les 2s .... voir 3s une fois ttes les 70sec
    #delais=0.05s => une actualisation ttes les 2s .... voir 3s une fois ttes les 70sec

    monCompteur=teleinfo()
    h=helice()
    reste=''
    with serial.Serial('/dev/ttyS0') as ser:
        try:
            ser.baudrate=1200
            ser.bytesize=serial.SEVENBITS
            #~ ser.parity=serial.PARITY_EVEN
            ser.stopbits=serial.STOPBITS_ONE
            ser.timeout=0#secondes
        except Exception as detail :
            print('Pb %d avec la liaison serie : %s'%(err,detail))
        while(1):
            tout=ser.read_all().decode("utf-8").split('\n')
            tout[0]=reste+tout[0]
            try:
                ligne=tout[-2]
                reste=tout[-1]
            except:
                ligne=tout[-1]
                reste=''
            print(' ligne=%s reste=%s'%(ligne,reste),end='',flush=True)#pour debug

            #~ octets=[ord(car) for car in ligne]   #pour debug detail
            #~ print("%s ==> %s"%(octets,ligne[:-1]))   #pour debug
            error=monCompteur.verifLigne(ligne)
            if not error:
                error=monCompteur.decodeLigne()
                if not error:
                    print('\r%s %s=%s'%(h.run(),monCompteur.etiquette,monCompteur.valeurs[monCompteur.etiquette]),end='',flush=True)
                    
                    if monCompteur.etiquette=="PAPP":
                        if monCompteur.premiereLecture:
                            monCompteur.premiereLecture=False
                        else:
                            #MAJ valeurs complete, on peut calculer
                            #~ monCompteur.calcStats()
                            #~ print('%s %s '%(heureComplete(),monCompteur.valeurs))
                            #~ print('%s %dA %dW %s %s %s'%(heureComplete(),monCompteur.valeurs['IINST'],monCompteur.valeurs['PAPP'],monCompteur.StatMin,monCompteur.StatMax,monCompteur.StatMoyenne))
                            print('\r%s %dA %dW HC=%s HC=%.3f HP=%.3f BASE=%.3f'%(heureComplete(),monCompteur.valeurs['IINST'],monCompteur.valeurs['PAPP'],monCompteur.valeurs['PTEC']==1,monCompteur.valeurs['HCHC']/1000,monCompteur.valeurs['HCHP']/1000,monCompteur.valeurs['BASE']/1000))
            else:
                print('\nerreur:'+error)
            sleep(delais)
