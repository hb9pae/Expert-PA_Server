# Expert PA  Monitoring Server 
**Anforderungsspezifikation, Architektur und Projektplan**

## Anforderungen
Ziel des Projektes ist, eine ExpertPA über das Netzwerk zu bedienen.
Das Projekt soll in zwei Phasen unterteilt werden:

* ein Expert-Server, der alle Funktionen der Expert PA via ein API zur Verfügung stellt. Dieser Server soll auf dem Raspberry PI4 
laufen und ist vorzugsweis als Python Script.

* ein GIU für die grafische Darstellung/Bedinung unter Windows
 
## Kurzbeschreibung
Die Expert PA verfügt über eine serielle Schnittstelle (RS232) die über USB 
an einem Linux Rechner (Raspberry PI4) verbunden ist. 
Auf dem Linux Recher läuft der Dients ser2net, der die serielle Schnittstelle
/dev/ttyUSB0 umber das lokale Netzwrk auf Port 22000 zur Verfügung stellt.

Der Expert-Server bietet ein API und unterstützt alle Funktionen / anzeigen vom Programm Term_2k_232.exe 
von der Firma SPE Expert s.a

IP Adresse RPI mit ser2net:	192.168.84.220  Port 22000

Expert PA: Handbuch  EXPERT2K-FA-EN-rev.2.0.pdf
		Application-Programmers-Guide-1.3K-2K-1.1 
	url: https://www.spetlc.com/en/products/expert-2k-fa-uk.html
